# AI-use statement

1. I used an AI assistant to draft the report (`report.md` / `report.pdf`),
   help push the repo to GitHub (`data260-0571`, tag `hw1`), and debug small
   AWS errors during ECS deploy (missing ECR repo, PowerShell `-replace`,
   service-linked role, log group already exists, Windows `file://` path).
   I also used it to scaffold the HTML/JS form, agent scripts, and Docker
   setup. I ran Docker, Ollama, the 40-run experiment, `hw1_client.py`, and
   the ECS screenshot myself, and I created the GitHub repo and Canvas
   submission.

2. One unsuitable output was treating the first form as generic course
   feedback instead of grocery supply and recall notices. Another issue was
   the ECS deploy script stopping on errors that only meant "resource
   already exists."

3. I checked the form against the homework rubric (domain heading, required
   fields, JS validation). For AWS, I read the PowerShell / AWS CLI error
   text and compared it with the console (ECR push worked, CreateService
   failed).

4. I changed the page to the grocery-notice schema and moved terms
   validation into JavaScript so the 25-character alert actually shows. For
   ECS, the deploy script was updated so existing repos, log groups, and
   roles are skipped, and the task definition file uses a full Windows path.
   After that the service reached RUNNING at http://98.84.7.49.
