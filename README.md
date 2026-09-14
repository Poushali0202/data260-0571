# DATA-260 Homework 1 and 2

## Personal configuration

| Value | Result |
|---|---|
| Student | Poushali |
| SID4 | `0571` |
| PORT_BASE | `8571` |
| PREFIX | `s0571` |
| SEED | `571` |
| VERIFY_SEED | `260571` |
| DOMAIN_ID | `3` |
| Assigned domain | Grocery supply and recall notices |
| Python | 3.12 |
| Local model | `qwen3:8b` through Ollama (required for agent runs) |
| Hardware | Intel Core i5-1135G7, 15.8 GB RAM, Intel Iris Xe Graphics, Windows 11 Home Single Language |
| Tagged commits | `hw1` (HW1), `hw2` (HW2) |

## Part 1: local web application

1. Build the image: `docker build -t data260-hw1-0571 .`
2. Run it on PORT_BASE: `docker run --rm -d --name data260-hw1-0571 -p 8571:80 data260-hw1-0571`
3. Open <http://localhost:8571>, submit a valid notice, and capture the page plus browser console.
4. Stop it: `docker stop data260-hw1-0571`

Compose alternative: `docker compose up --build`, then visit <http://localhost:8571>.

## Part 2: Planner, Reviewer, Finalizer

Install the Python dependencies (the adapter itself uses only the standard library):

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
ollama serve
ollama pull qwen3:8b
```

Run the exact demo command:

```powershell
python agents_demo.py --title "Frozen berries recalled after possible contamination" --content "A retailer is removing frozen mixed berries from selected lots after a supplier reported possible contamination. Customers should check lot codes, stop using affected packages, and contact the store for a refund." --email "poushali@example.com" --model qwen3:8b --temperature 0.0 --output reports/hw01/raw/agent_demo.json
```

The program prints Planner output, Reviewer output, Finalized output, and a valid
publish JSON package. Tags and summaries are derived from the supplied title and
content rather than fixed domain keywords.

## Part 3: non-determinism

The fixed input is `reports/hw01/cases/nondeterminism_input.json`. Run exactly 20
times at each temperature:

```powershell
python run_nondeterminism.py --model qwen3:8b --runs-per-temperature 20
```

This writes all 40 raw runs to `reports/hw01/raw/nondeterminism_runs.json`.
Copy the printed p50/p95/p99 and tag-set metrics into `reports/hw01/METRICS.md`.

## Part 4: model client and accounting

Run the required five-turn demo:

```powershell
python hw1_client.py --demo --model qwen3:8b
```

Interactive commands are normal prompts, `/stats`, and `/quit`. `/stats` reports
turn count, cumulative input/output tokens, and serialized history length without
changing the history. Prior messages are resent each turn so the stateless chat
endpoint can interpret the current turn in context. A system prompt defines
behavior/instructions; a user message supplies a request or data. Input tokens
grow because the serialized history is included again; context-window limits,
model limits, or application truncation eventually stop that growth.

## AWS ECS

AWS CLI credentials and the ECS task execution role are required. After installing
and configuring AWS CLI (`aws configure`), run:

```powershell
.\deploy_ecs.ps1 -Region us-east-1
```

The script creates/uses ECR, builds and pushes the image, registers the Fargate
task, creates a security group and one-task ECS service with public IP enabled.
Wait for the task to become `RUNNING`, obtain its public IP, open
`http://PUBLIC_IP`, and save the real screenshot in `reports/hw01/screenshots/`.
Delete the ECR repository, service, cluster, task revisions, and security group
after grading to avoid charges.

## Verification

```powershell
python verify_hw01.py
```

The command writes `reports/hw01/verification.json`. The report PDF must be
regenerated after replacing the environment-specific screenshot and metrics
placeholders, then committed and tagged as `hw1`.

## Homework 2

HW2 adds a FastAPI backend (`app.py`) on PORT_BASE 8571 for the grocery notice
list, a LangGraph supervisor graph (`agent_graph.py`) that replaces the
sequential Planner/Reviewer script, the schema and turn-ceiling experiments
(`run_graph_experiment.py`), and a smoke test (`verify_hw02.py`).

```powershell
python -m pip install -r requirements.txt
python app.py
python agent_graph.py --title "..." --content "..."
python verify_hw02.py
```

Full run instructions, experiment commands, and results are in `reports/hw02/`.
