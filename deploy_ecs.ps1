param(
  [string]$Region = "us-east-1",
  [string]$Cluster = "s0571-hw1-cluster",
  [string]$Service = "s0571-hw1-service"
)

$ErrorActionPreference = "Stop"
$awsExe = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
if (-not (Test-Path $awsExe)) {
  $cmd = Get-Command aws -ErrorAction SilentlyContinue
  if (-not $cmd) { throw "aws.exe not found. Open a new terminal after installing AWS CLI." }
  $awsExe = $cmd.Source
}

function Invoke-Aws {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$AwsArgs)
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $awsExe
  $psi.Arguments = ($AwsArgs | ForEach-Object {
    if ($_ -match '[\s"]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ }
  }) -join " "
  $psi.UseShellExecute = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.CreateNoWindow = $true
  $p = [System.Diagnostics.Process]::Start($psi)
  $stdout = $p.StandardOutput.ReadToEnd()
  $stderr = $p.StandardError.ReadToEnd()
  $p.WaitForExit()
  $out = $stdout.Trim()
  return [pscustomobject]@{
    Code = $p.ExitCode
    Out  = $out
    Err  = $stderr.Trim()
    Text = ($(if ($out) { $out } else { $stderr.Trim() }))
  }
}

function AwsId([string]$value) {
  if (-not $value) { return $null }
  $value = $value.Trim()
  if ($value -in @("", "None", "null")) { return $null }
  return $value
}

$Repository = "s0571-hw1-grocery-notices"
$who = Invoke-Aws sts get-caller-identity --query Account --output text
if (-not (AwsId $who.Out)) { throw "aws sts get-caller-identity failed: $($who.Err)" }
$AccountId = $who.Out
$EcrUri = "$AccountId.dkr.ecr.$Region.amazonaws.com/$Repository"
Write-Host "Using AWS account $AccountId"

$repo = Invoke-Aws ecr describe-repositories --repository-names $Repository --region $Region
if ($repo.Code -ne 0) {
  $created = Invoke-Aws ecr create-repository --repository-name $Repository --region $Region
  if ($created.Code -ne 0) { throw "create ECR repository failed: $($created.Err)" }
}

$login = Invoke-Aws ecr get-login-password --region $Region
if ($login.Code -ne 0 -or -not $login.Out) { throw "ecr login password failed: $($login.Err)" }
$login.Out | docker login --username AWS --password-stdin "$AccountId.dkr.ecr.$Region.amazonaws.com"
if ($LASTEXITCODE -ne 0) { throw "docker login to ECR failed." }

docker build -t "${Repository}:latest" .
if ($LASTEXITCODE -ne 0) { throw "docker build failed." }
docker tag "${Repository}:latest" "${EcrUri}:latest"
docker push "${EcrUri}:latest"
if ($LASTEXITCODE -ne 0) { throw "docker push failed." }

$role = Invoke-Aws iam get-role --role-name ecsTaskExecutionRole --query Role.Arn --output text
if (-not (AwsId $role.Out)) {
  $trust = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
  [System.IO.File]::WriteAllText("$PWD\ecs-trust.json", $trust)
  $createdRole = Invoke-Aws iam create-role --role-name ecsTaskExecutionRole --assume-role-policy-document "file://ecs-trust.json"
  if ($createdRole.Code -ne 0 -and $createdRole.Err -notmatch "EntityAlreadyExists") {
    throw "create ecsTaskExecutionRole failed: $($createdRole.Err)"
  }
  Invoke-Aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy | Out-Null
  $role = Invoke-Aws iam get-role --role-name ecsTaskExecutionRole --query Role.Arn --output text
}
$ExecutionRoleArn = $role.Out
Write-Host "Task execution role: $ExecutionRoleArn"

$TaskDefinition = Get-Content -Raw "ecs-task-definition.json"
$TaskDefinition = $TaskDefinition.Replace(
  "REPLACE_WITH_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/s0571-hw1-grocery-notices",
  $EcrUri
)
$TaskDefinition = $TaskDefinition.Replace("REPLACE_WITH_ECS_TASK_EXECUTION_ROLE_ARN", $ExecutionRoleArn)
$taskFile = Join-Path (Get-Location).Path "ecs-task-definition.rendered.json"
$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($taskFile, $TaskDefinition, $utf8)
if (-not (Test-Path $taskFile)) { throw "Failed to write $taskFile" }

$logs = Invoke-Aws logs describe-log-groups --log-group-name-prefix /ecs/s0571-hw1 --query "logGroups[0].logGroupName" --output text --region $Region
if ($logs.Out -ne "/ecs/s0571-hw1") {
  Invoke-Aws logs create-log-group --log-group-name /ecs/s0571-hw1 --region $Region | Out-Null
}
Write-Host "Log group ready"

$taskUri = "file://" + ($taskFile -replace "\\", "/")
Write-Host "Registering task definition from $taskUri"
$reg = Invoke-Aws ecs register-task-definition --cli-input-json $taskUri --region $Region
if ($reg.Code -ne 0) { throw "register task definition failed: $($reg.Err)" }

$vpc = Invoke-Aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text --region $Region
$VpcId = AwsId $vpc.Out
if (-not $VpcId) {
  $vpc = Invoke-Aws ec2 describe-vpcs --query "Vpcs[0].VpcId" --output text --region $Region
  $VpcId = AwsId $vpc.Out
}
if (-not $VpcId) {
  Write-Host "No VPC found; creating default VPC"
  Invoke-Aws ec2 create-default-vpc --region $Region | Out-Null
  $vpc = Invoke-Aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text --region $Region
  $VpcId = AwsId $vpc.Out
}
if (-not $VpcId) { throw "Could not find or create a VPC in $Region. $($vpc.Err)" }
Write-Host "VPC: $VpcId"

$subnetResult = Invoke-Aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VpcId" "Name=map-public-ip-on-launch,Values=true" --query "Subnets[0:2].SubnetId" --output text --region $Region
$Subnets = @(AwsId $subnetResult.Out -split "\s+" | Where-Object { $_ })
if ($Subnets.Count -lt 1) {
  $subnetResult = Invoke-Aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VpcId" --query "Subnets[0:2].SubnetId" --output text --region $Region
  $Subnets = @(AwsId $subnetResult.Out -split "\s+" | Where-Object { $_ })
}
if ($Subnets.Count -lt 1) { throw "No subnets found in $VpcId. $($subnetResult.Err)" }
Write-Host "Subnets: $($Subnets -join ', ')"

$sg = Invoke-Aws ec2 describe-security-groups --filters "Name=group-name,Values=s0571-hw1-http" "Name=vpc-id,Values=$VpcId" --query "SecurityGroups[0].GroupId" --output text --region $Region
$SecurityGroup = AwsId $sg.Out
if (-not $SecurityGroup) {
  $createdSg = Invoke-Aws ec2 create-security-group --group-name s0571-hw1-http --description "HW1 HTTP access" --vpc-id $VpcId --query GroupId --output text --region $Region
  $SecurityGroup = AwsId $createdSg.Out
  if (-not $SecurityGroup) { throw "create security group failed: $($createdSg.Err)" }
  Invoke-Aws ec2 authorize-security-group-ingress --group-id $SecurityGroup --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $Region | Out-Null
}
Write-Host "Security group: $SecurityGroup"

Invoke-Aws iam create-service-linked-role --aws-service-name ecs.amazonaws.com | Out-Null
Invoke-Aws ecs create-cluster --cluster-name $Cluster --region $Region | Out-Null

$Network = "awsvpcConfiguration={subnets=[$($Subnets -join ',')],securityGroups=[$SecurityGroup],assignPublicIp=ENABLED}"
$existing = Invoke-Aws ecs describe-services --cluster $Cluster --services $Service --query "services[0].status" --output text --region $Region
if ((AwsId $existing.Out) -eq "ACTIVE") {
  Write-Host "Updating existing service to 1 Fargate task"
  $upd = Invoke-Aws ecs update-service --cluster $Cluster --service $Service --task-definition s0571-hw1-grocery-notices --desired-count 1 --force-new-deployment --query "service.{status:status,desired:desiredCount,running:runningCount}" --output json --region $Region
  if ($upd.Code -ne 0) { throw "update ECS service failed: $($upd.Err)" }
} else {
  Write-Host "Creating ECS service"
  $created = Invoke-Aws ecs create-service --cluster $Cluster --service-name $Service --task-definition s0571-hw1-grocery-notices --desired-count 1 --launch-type FARGATE --network-configuration $Network --region $Region
  if ($created.Code -ne 0 -and $created.Err -notmatch "already exists") {
    throw "create ECS service failed: $($created.Err)"
  }
}

Write-Host "Waiting for a RUNNING task with a public IP..."
$publicIp = $null
for ($i = 1; $i -le 36; $i++) {
  Write-Host "  check $i/36"
  $tasks = Invoke-Aws ecs list-tasks --cluster $Cluster --service-name $Service --desired-status RUNNING --query "taskArns[0]" --output text --region $Region
  $taskArn = AwsId $tasks.Out
  if ($taskArn) {
    $desc = Invoke-Aws ecs describe-tasks --cluster $Cluster --tasks $taskArn --output json --region $Region
    if ($desc.Code -eq 0 -and $desc.Out) {
      $task = ($desc.Out | ConvertFrom-Json).tasks[0]
      $eni = ($task.attachments | ForEach-Object { $_.details } | Where-Object { $_.name -eq "networkInterfaceId" } | Select-Object -First 1).value
      if ($task.lastStatus -eq "RUNNING" -and $eni) {
        $ip = Invoke-Aws ec2 describe-network-interfaces --network-interface-ids $eni --query "NetworkInterfaces[0].Association.PublicIp" --output text --region $Region
        $publicIp = AwsId $ip.Out
        if ($publicIp) { break }
      }
    }
  }
  Start-Sleep -Seconds 8
}

if (-not $publicIp) {
  Write-Host "No public IP yet. ECS events:"
  $events = Invoke-Aws ecs describe-services --cluster $Cluster --services $Service --query "services[0].events[:8].[createdAt,message]" --output text --region $Region
  Write-Host $events.Out
  Write-Host $events.Err
  exit 1
}

Write-Host ""
Write-Host "ECS app is running."
Write-Host "Open: http://$publicIp"
Write-Host "Save a screenshot of that page as reports/hw01/screenshots/ecs-public-ip.png"
