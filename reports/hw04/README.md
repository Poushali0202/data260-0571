# HW4 run instructions

All commands run from the repository root with Python 3.12, Node 24 and MySQL 8.

```powershell
python -m pip install -r requirements.txt
```

## Database

Create `.env` from `.env.example` with the MySQL connection string, for example
`DATABASE_URL=mysql+pymysql://root:PASSWORD@127.0.0.1:3306/s0571_rel`. The reported
runs used a MySQL 8.0.46 container: `docker run -d --name s0571-mysql -e MYSQL_ROOT_PASSWORD=s0571pass -p 3307:3306 mysql:8.0`
with port 3307 in `.env`.

```powershell
python seed_data.py
```

`seed_data.py` creates the database `s0571_rel` if needed, drops and recreates the four
tables (`grocery_notices`, `notice_lots`, `users`, `sessions`), and inserts the two
accounts, 5,000 notices and 200 lots with `random.seed(571)`. The resulting DDL is in
`migrations/hw04_schema.sql`, the index from Part 3 step 8 in `migrations/hw04_add_index.sql`.

Accounts: `inspector@example.com` / `recall2026` and `manager@example.com` / `shelf2026`.

## Backend (Part 2)

```powershell
python app.py
```

Runs on <http://localhost:8571>. Routes: `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`,
`GET/POST /api/notices`, `GET/PUT/DELETE /api/notices/{id}`, `GET /api/notices/naive?page_size=N`,
`GET /api/notices/fixed?page_size=N`, `GET /health`. Every `/api/notices` route needs the
`session_id` cookie set by login. The HW3 pages (`/`, `/login`, `/dashboard`, `/logout`) and the
HW2 notice page (`/notices`) use the same cookie and now log in with email and password.

## React client (Part 1)

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173> with the backend running. Routes: `/login`, `/` (Home), `/create`,
`/update/:id`, `/delete/:id`.

## N+1 measurement (Part 3)

With the backend running and nothing else using the CPU:

```powershell
python measure_n_plus_one.py
```

Logs in, sends 2 warm-up requests and then 30 measured requests for every page size (10, 50, 200)
and version (naive, fixed), and writes `raw/n_plus_one_requests.csv` (180 rows) and
`raw/n_plus_one_summary.json`. The EXPLAIN commands from step 8 are in `RUN_LOG.txt`; the index
is applied with `mysql ... s0571_rel < migrations/hw04_add_index.sql`.

## RAG (Part 4)

Ollama must be serving `qwen3:8b`.

```powershell
python rag.py
python rag.py --summary
```

`rag.py` chunks `corpus/` (21 documents), embeds the chunks with
`sentence-transformers/all-MiniLM-L6-v2` into a FAISS index, prints the retrieved chunks for
every question before the model is called, runs the six questions through the three
configurations and the k sweep, and writes `raw/rag_chunks.jsonl`, `raw/rag_retrievals.txt`,
`raw/rag_results.jsonl`, `raw/rag_comparison.md`, `raw/rag_k_sweep.md` and
`raw/rag_evaluation.md`. Finished question and configuration pairs are skipped when the
script is started again, and `--summary` only rebuilds the three markdown tables.

## Verification and report

```powershell
python verify_hw04.py
python make_report_pdf.py hw04
```

`verify_hw04.py` (also `make verify-hw04`) starts the app on port 8571 if it is not running,
checks login, the cookie, the sessions table, the CRUD round trip on a temporary record, the
naive and fixed lists and their statement counts, then checks the raw result files and writes
`verification.json`. It does not change any application code or seeded data.
