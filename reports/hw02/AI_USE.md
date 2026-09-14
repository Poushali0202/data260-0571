# AI-use statement

1. I used an AI assistant to draft the report (`report.md` / `report.pdf`),
   help push the repo to GitHub (`data260-0571`, tag `hw2`), and debug small
   errors along the way (the smoke test parsing the HTML page as JSON,
   screenshots captured at the wrong scroll position, a console encoding
   error on a Unicode arrow). I also used it to scaffold the FastAPI backend,
   the page changes, the LangGraph graph, the experiment runner, and the
   smoke test. The experiments ran on my laptop with Ollama and qwen3:8b; I
   reviewed the code and every output file, took the terminal screenshots,
   and made the Canvas submission.

2. One unsuitable output was the first `verify_hw02.py`, which parsed the
   HTML home page as JSON and crashed on its very first check. Another issue
   was the first set of "after submit" screenshots, which were captured
   scrolled to the middle of the page so the updated list was not visible.

3. I found the crash by running the smoke test on the tagged commit and
   reading the traceback (the `json.loads` call inside `request()`). I found
   the screenshot problem by opening the PNG files. I also checked the
   Pydantic error text with hand-made bad replies (four tags, a
   two-character tag, a 30-word summary, cut-off JSON) before the 30-run
   experiment, because that text is what the Planner sees on a retry.

4. `request()` now returns the raw text unless the `Content-Type` header says
   JSON, so the home page check passes and the API checks still get parsed
   objects. The screenshot script scrolls to the top after each redirect
   before it captures the page. The validator messages go through a small
   `describe()` helper that turns each problem into one `field: message`
   line, so the Planner gets a short, specific reason.
