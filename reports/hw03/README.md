# HW3 run instructions

All commands run from the repository root with Python 3.12.

```powershell
python -m pip install -r requirements.txt
```

## Part 1: login app

```powershell
python app.py
```

Open <http://localhost:8571>. Accounts: `inspector` / `recall2026` and `manager` / `shelf2026`.
Routes: `/` (home), `/login`, `/dashboard` (protected), `/logout`, plus the HW2 notice page at
`/notices` with its `/api/notices` endpoints. The session cookie is signed by Starlette's
`SessionMiddleware` with `httponly`, `samesite=lax` and `secure`. The idle timeout is
`IDLE_TIMEOUT_SECONDS` (default 600). The cookie and replay checks in `RUN_LOG.txt` were made
with curl against a server started with a 20 second timeout:

```powershell
$env:IDLE_TIMEOUT_SECONDS = "20"; python app.py
```

## Part 2: chunking comparison

```powershell
python fetch_corpus.py
python chunking_compare.py --warmup
python chunking_compare.py
python summarize_retrieval.py
```

`fetch_corpus.py` downloads fresh snapshots into `corpus/` and rewrites `CORPUS_MANIFEST.json`
(the committed corpus is the graded one; re-fetching changes the hashes if a page changed).
`chunking_compare.py --warmup` runs the three chunkers on the first 100 KB of Tiny Shakespeare
and writes `raw/warmup_*`. Without the flag it runs the five questions from `questions.yaml`
against the corpus with k=5 and writes `raw/retrieval_results.jsonl` and `raw/chunk_stats.json`.
`summarize_retrieval.py` recomputes the tables in `METRICS.md` from those files
(`--prefix warmup_` for the warm-up run). The embedding model
`sentence-transformers/all-MiniLM-L6-v2` is downloaded from Hugging Face on first use.

## Verification and report

```powershell
python verify_hw03.py
python make_report_pdf.py hw03
```

`verify_hw03.py` (also `make verify-hw03`) starts the app on port 8571 with a 5 second idle
timeout (the port must be free), checks every route, the cookie flags, the logout and idle
replays, the corpus size and hashes, the questions file and the raw results, and writes
`verification.json`.
