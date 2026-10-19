# HW6 run instructions

All commands run from the repository root with Python 3.12. The runs used MySQL 8 in the Docker
container `s0571-mysql` (port 3307, see `reports/hw04/README.md`), MongoDB 7 in the Docker container
`s0571-mongo` (port 27017) and Ollama serving `qwen3:8b`.

```powershell
docker run -d --name s0571-mongo -p 27017:27017 -v s0571_mongo_data:/data/db mongo:7.0
python -m pip install -r requirements.txt
python app.py
```

`.env` needs `DATABASE_URL` (HW4) and may set `MONGO_URI` and `MONGO_DB` (defaults
`mongodb://127.0.0.1:27017` and `s0571_doc`). The Part 4 runs started the server with
`OLLAMA_TIMEOUT=900`, because `/compact` writes up to 900 tokens and takes longer than the adapter's
default 180 s on this CPU. `app.py` creates the four collections with their JSON
schema validators on startup (`mongo_db.py`).

## Part 1

Document API on <http://localhost:8571>: `POST /api/doc/notices`, `GET /api/doc/notices`,
`GET/PUT/DELETE /api/doc/notices/{id}`. Files: `config.py` (settings), `mongo_db.py` (PyMongo
connection and validators), `doc_schemas.py` (Pydantic models), `routers/doc_notices.py` (routes).
The curl transcript is `raw/part1_curl.txt`, the mongosh output `raw/part1_mongosh.txt`.

## Part 2

`POST /api/chat`, `GET /api/memory/{user_id}`, `GET /api/aggregate/{user_id}` in `routers/chat.py`;
memory logic in `memory.py`. Settings in `config.py`: `SHORT_TERM_N=12`, `SUMMARIZE_EVERY_USER_MSGS=5`,
`LIFETIME_EVERY_SUMMARIES=2`, `TOP_K_EPISODES=4`. A request may override `short_term_n` and `policy`
(`none` or `compress_old`) and may set `file_memory: true` to include AGENT.md and MEMORY.md.
The mini chat page is <http://localhost:8571/chat>. Every request appends one row to
`raw/chat_log.csv`.

## Part 3

```powershell
python run_memory_cost.py        # optional argument: minutes to run before pausing, rerun to resume
python summarize_memory_cost.py
```

`run_memory_cost.py` sends the same 30-message conversation and the five probes from
`memory_probes.yaml` for the settings N=4, N=12, N=30 and N=30 with the `compress_old` policy,
each as a separate user and session, and appends every turn to `raw/sweep_turns.csv`.
`summarize_memory_cost.py` scores the probes (`raw/probe_scores.csv`) and writes
`raw/sweep_summary.json` with the means and the cost estimates.

## Part 4

File memory lives in `file_memory.py` (loading, prompt block, consolidation check, `/memory`,
`/compact`, `/dream`, `/help`); the commands are sent as the message of `POST /api/chat`.
`raw/MEMORY_original.md` is the 55-line test file and `raw/MEMORY_consolidated.md` the result of
`/compact`. `python agent_md_check.py` asks the model for one function under AGENT.md, saves it as
`raw/generated_function.py` and checks the conventions (`raw/agent_md_check.json`).

## Verification and report

```powershell
python verify_hw06.py
python make_report_pdf.py hw06
```

`verify_hw06.py` (also `make verify-hw06`) starts the app if needed, runs the document CRUD round
trip with the error cases, inserts an invalid document straight into MongoDB to show the validator,
sends one chat turn plus `/help` and `/memory` for a temporary user that it deletes again, checks the
sweep files and writes `verification.json`. It does not change application code.
