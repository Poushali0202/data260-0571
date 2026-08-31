param(
  [string]$Region = "us-east-1",
  [string]$Cluster = "s0571-hw1-cluster",
  [string]$Service = "s0571-hw1-service"
)

$ErrorActionPreference = "Stop"
$Repository = "s0571-hw1-grocery-notices"
$AccountId = (aws sts get-caller-identity --query Account --output text)
$EcrUri = "$AccountId.dkr.ecr.$Region.amazonaws.com/$Repository"

aws ecr describe-repositories --repository-names $Repository --region $Region 2>$null
if ($LASTEXITCODE -ne 0) {
  aws ecr create-repository --repository-name $Repository --region $Region | Out-Null
}
aws ecr get-login-password --region $Region |
  docker login --username AWS --password-stdin "$AccountId.dkr.ecr.$Region.amazonaws.com"
docker build -t "$Repository`:latest" .
docker tag "$Repository`:latest" "$EcrUri`:latest"
docker push "$EcrUri`:latest"

$TaskDefinition = Get-Content -Raw "ecs-task-definition.json" `
  -replace "REPLACE_WITH_ACCOUNT_ID\.dkr\.ecr\.us-east-1\.amazonaws\.com/s0571-hw1-grocery-notices", $EcrUri
$ExecutionRoleArn = aws iam get-role --role-name ecsTaskExecutionRole --query Role.Arn --output text
$TaskDefinition = $TaskDefinition -replace "REPLACE_WITH_ECS_TASK_EXECUTION_ROLE_ARN", $ExecutionRoleArn
$TaskDefinition | Set-Content -Encoding utf8 "ecs-task-definition.rendered.json"
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.rendered.json --region $Region | Out-Null

$VpcId = aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text --region $Region
$Subnets = @(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VpcId" "Name=map-public-ip-on-launch,Values=true" --query "Subnets[0:2].SubnetId" --output text --region $Region) -split "\s+"
$SecurityGroup = aws ec2 describe-security-groups --filters "Name=group-name,Values=s0571-hw1-http" --query "SecurityGroups[0].GroupId" --output text --region $Region
if (-not $SecurityGroup -or $SecurityGroup -eq "None") {
  $SecurityGroup = aws ec2 create-security-group --group-name s0571-hw1-http --description "HW1 HTTP access" --vpc-id $VpcId --query GroupId --output text --region $Region
  aws ec2 authorize-security-group-ingress --group-id $SecurityGroup --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $Region | Out-Null
}
aws ecs create-cluster --cluster-name $Cluster --region $Region | Out-Null
$Network = "awsvpcConfiguration={subnets=[$($Subnets -join ',')],securityGroups=[$SecurityGroup],assignPublicIp=ENABLED}"
aws ecs create-service --cluster $Cluster --service-name $Service --task-definition "s0571-hw1-grocery-notices" `
  --desired-count 1 --launch-type FARGATE --network-configuration $Network --region $Region
Write-Host "Service requested. Wait for RUNNING, then read the task ENI public IP."
