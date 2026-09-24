# AI-use statement

1. I used an AI assistant for debugging and for preparing the report document
   (`report.md` / `report.pdf`). The debugging help covered the SQLAlchemy statement
   counter (keeping the per-request count in a `ContextVar` instead of a module
   variable so that concurrent requests cannot share it), the cookie and CORS
   settings needed between the Vite dev server on port 5173 and FastAPI on port
   8571, the `from_attributes` validation of the nested `lots` list in Pydantic, a
   Windows console encoding error in the RAG printouts, and the reportlab layout. I
   wrote and ran the application code, the React components, the seed and
   measurement scripts, `rag.py`, the six questions and the smoke test myself,
   reviewed every output file, and made the Canvas submission.

2. One thing I verified independently was the SQL statement count that the naive and
   fixed endpoints report, because the whole N+1 table depends on it and the number
   comes from my own event listener rather than from the database. I also checked
   what else the application sends to MySQL around those statements.

3. I turned on MySQL's general log (`SET GLOBAL general_log = 'ON'` with
   `log_output = 'TABLE'`), logged in, sent one naive and one fixed request with
   `page_size=10`, turned the log off and listed the `SELECT` statements it had
   recorded (the listing is in `RUN_LOG.txt`). The log shows exactly what the
   endpoints report: for the naive request one `SELECT ... FROM grocery_notices`
   followed by ten `SELECT ... FROM notice_lots WHERE notice_id = %s`, and for the
   fixed request one notices query followed by a single
   `SELECT ... FROM notice_lots WHERE notice_id IN (...)`. It also shows two things
   the counter does not include: every protected route runs one `SELECT sessions`
   statement (the login check) before the endpoint body starts, and the login itself
   ran two `SELECT users` statements although it only needs one.

4. The second users query came from SQLAlchemy expiring the `User` object when the
   session row was committed, so the response serialisation reloaded it. I created
   `db_session_basede26` with `expire_on_commit=False`, restarted the app and repeated
   the general log check: login now runs one users query and the naive and fixed
   counts are unchanged (11 and 2 for a page of 10, plus the one session lookup).
   The statement count in the results table is left as the count of the endpoint
   body, and the extra session statement is stated next to the table in `METRICS.md`
   and in the report, so the numbers can be checked against the log.
