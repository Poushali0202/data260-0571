# HW5 run instructions

All commands run from the repository root with Python 3.12, Node 24 and MySQL 8 (the runs used
the Docker container `s0571-mysql` on port 3307, see `reports/hw04/README.md`).

```powershell
python -m pip install -r requirements.txt
python seed_data.py
python app.py
```

`seed_data.py` recreates the tables with the HW5 schema (`migrations/hw05_schema.sql`): 20
suppliers, 5,000 notices with `RN-000001` to `RN-005000` codes and a supplier each, 200 lots and
the two accounts (`inspector@example.com` / `recall2026`, `manager@example.com` / `shelf2026`).

## Part 1

Backend on <http://localhost:8571>: `GET/POST /api/suppliers`, `GET/PUT/DELETE /api/suppliers/{id}`,
`GET /api/suppliers/{id}/notices`, `GET/POST /api/notices`, `GET/PUT/DELETE /api/notices/{id}`.
List routes take `page` and `page_size`. Every route needs the `session_id` cookie from
`POST /auth/login`. A supplier that still has notices cannot be deleted (409 and
`ON DELETE RESTRICT` in MySQL); there is no cascade.

React client: `cd frontend; npm install; npm run dev`, then <http://localhost:5173>.

## Part 2

```powershell
mcp dev meals_server.py
npx @modelcontextprotocol/inspector python domain_server.py
```

The Inspector CLI outputs in `raw/inspector/` were produced with
`npx @modelcontextprotocol/inspector --cli python <server>.py --method tools/call --tool-name ... --tool-arg ...`.

## Parts 3 to 5

```powershell
python retry_demo.py
python run_fault_injection.py
python test_tools.py
python run_agent_scenarios.py
```

`run_fault_injection.py` writes `raw/fault_injection_calls.csv` (150 rows) and
`raw/fault_injection_summary.json`; `run_agent_scenarios.py` appends one line per run to
`raw/agent_runs.jsonl` and needs Ollama serving `qwen3:8b`.

## Verification and report

```powershell
python verify_hw05.py
python make_report_pdf.py hw05
```

`verify_hw05.py` (also `make verify-hw05`) starts the app if needed, runs the supplier and notice
round trip with the error cases, starts both MCP servers over STDIO and calls a tool on each,
rechecks the raw files and the offline tests, and writes `verification.json`. It only creates
temporary records that it deletes again and does not change application code.
