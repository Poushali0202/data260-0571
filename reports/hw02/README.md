# HW2 run instructions

All commands run from the repository root with Ollama serving `qwen3:8b`
on `http://localhost:11434`.

```powershell
python -m pip install -r requirements.txt
ollama serve
ollama pull qwen3:8b
```

## Web app (Part 1 and Part 2)

```powershell
python app.py
```

Open <http://localhost:8571>. The page loads the notice list from
`GET /api/notices` and shows loading, empty, and error states. The forms call
`POST /api/notices`, `PUT /api/notices/1`, and `DELETE /api/notices/highest`,
then return to the home view. The search box calls `GET /api/notices?q=term`.
Records live in memory, so restarting the server restores the three seed notices.

## Agent graph (Part 3)

```powershell
python agent_graph.py --title "Romaine lettuce pulled from shelves after E. coli warning" --content "A regional grocery chain has removed bagged romaine lettuce from all stores after a state health department linked several illnesses to a single farm. Shoppers who bought romaine between May 3 and May 9 should throw it away and can bring the receipt to any store for a full refund."
```

Correction-loop test (the reviewer always reports an issue):

```powershell
python agent_graph.py --title "..." --content "..." --force-issue --max-turns 4
```

## Experiments (Part 4)

```powershell
python run_graph_experiment.py --input reports/hw02/cases/schema_input.json --runs 30 --max-turns 6 --output reports/hw02/raw/schema_validation_runs.json
python run_graph_experiment.py --input reports/hw02/cases/schema_input.json --runs 20 --max-turns 2 --output reports/hw02/raw/ceiling_2_runs.json
python run_graph_experiment.py --input reports/hw02/cases/schema_input.json --runs 20 --max-turns 10 --output reports/hw02/raw/ceiling_10_runs.json
python run_graph_experiment.py --input reports/hw02/cases/adversarial_input.json --runs 5 --max-turns 6 --output reports/hw02/raw/adversarial_runs.json
```

Every run is appended to the output file as soon as it finishes, so an
interrupted command can be started again and continues from the next run.
Running a command whose output file is already complete only prints the summary
table. Temperature is 0.7 for all experiments.

## Verification and report

```powershell
python verify_hw02.py
python make_report_pdf.py hw02
```

`verify_hw02.py` (also `make verify-hw02`) starts the app if it is not running,
exercises every endpoint, runs the graph once at temperature 0, and writes
`reports/hw02/verification.json`. It only creates temporary files.
