# AI-use statement

1. I used an AI assistant (Claude Code) to write most of the HW2 code on top of
   my HW1 repo: the FastAPI backend (`app.py`), the changes to `index.html` and
   `feedback.js`, the LangGraph graph (`agent_graph.py`), the experiment runner
   (`run_graph_experiment.py`), the smoke test (`verify_hw02.py`), the table
   support in `make_report_pdf.py`, and the first draft of the report, METRICS
   and this file. It also captured the browser screenshots with Playwright and
   launched the experiment runs on my laptop. I supplied the assignment, the HW1
   repo, my SID values and domain, chose the frozen input and the adversarial
   input, reviewed the code and every generated file, took the terminal
   screenshots, and did the GitHub tag, the collaborator check, and the Canvas
   submission.

2. One AI-produced output that was wrong: the first version of `verify_hw02.py`
   crashed on its very first check. Its `request()` helper parsed every
   response body as JSON, but `GET /` returns the HTML page, so the script
   raised `JSONDecodeError` before any check was recorded and never wrote
   `verification.json`. Separately, I verified the text of the Pydantic
   validation errors myself, because that text is what gets sent back to the
   Planner on a retry, and the first "after submit" screenshots had to be
   retaken because they were captured scrolled to the middle of the page.

3. I found the crash by running the smoke test on the tagged commit, which is
   exactly what the script is for; the traceback pointed at the `json.loads`
   call inside `request()`. For the validator I ran hand-made bad replies
   through `PlannerOutput` (four tags, a two-character tag, a 30-word summary,
   and a JSON string cut off mid-way) and read the messages before the 30-run
   experiment was started.

4. `request()` now returns the raw text unless the `Content-Type` header says
   JSON, so the home page check passes and the API checks still get parsed
   objects. It works because FastAPI sets `text/html` for `FileResponse` and
   `application/json` for the API routes, which is the property the test
   should rely on. For the validator, Pydantic's default `str(error)` is
   several lines long and ends with a documentation URL; the graph uses a small
   `describe()` helper that turns each problem into one `field: message` line
   (for example `tags: List should have at most 3 items after validation,
   not 4`), so the Planner gets a short and specific reason and the raw JSON
   files stay readable.
