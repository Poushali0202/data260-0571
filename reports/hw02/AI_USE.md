# AI-use statement

1. I used an AI assistant to scaffold the FastAPI backend (`app.py`), the
   changes to `index.html` and `feedback.js`, the LangGraph graph
   (`agent_graph.py`), the experiment runner, the smoke test
   (`verify_hw02.py`), and to draft the report, METRICS.md, and RUN_LOG.txt.
   It also ran the experiment commands and the browser screenshots on my
   laptop and helped push the repo and the `hw2` tag to GitHub. I supplied
   the assignment, the HW1 repo, and my SID values, reviewed the code and
   every generated file, took the terminal screenshots, checked the
   collaborator access, and made the Canvas submission.

2. One unsuitable output was the first `verify_hw02.py`, which parsed the
   HTML home page as JSON and crashed on its very first check without writing
   `verification.json`. Another issue was the first set of "after submit"
   screenshots, which were captured scrolled to the middle of the page so the
   updated list was not visible.

3. I found the crash by running the smoke test on the tagged commit and
   reading the traceback, which pointed at the `json.loads` call inside
   `request()`. I found the screenshot problem by opening the PNG files. I
   also checked the Pydantic error text myself with hand-made bad replies
   (four tags, a two-character tag, a 30-word summary, cut-off JSON) before
   the 30-run experiment, because that text is what the Planner sees on a
   retry.

4. `request()` now returns the raw text unless the `Content-Type` header says
   JSON, so the home page check passes and the API checks still get parsed
   objects. The screenshot script scrolls to the top after each redirect
   before it captures the page. The validator messages go through a small
   `describe()` helper that turns each problem into one `field: message`
   line, so the Planner gets a short, specific reason and the raw JSON files
   stay readable.
