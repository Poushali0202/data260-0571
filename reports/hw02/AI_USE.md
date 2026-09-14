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

2. One AI-produced output that was unsuitable: the first set of "after submit"
   screenshots for Part 2. The browser restored the scroll position after the
   redirect, so the images showed the middle of the page and not the updated
   list that the screenshots were supposed to prove. Separately, I verified the
   text of the Pydantic validation errors myself, because that text is what
   gets sent back to the Planner on a retry.

3. I found the screenshot problem by opening the PNG files: the table header
   was cut off and the new record was only half visible. For the validator I
   ran hand-made bad replies through `PlannerOutput` (four tags, a
   two-character tag, a 30-word summary, and a JSON string cut off mid-way) and
   read the messages before the 30-run experiment was started.

4. The screenshot script now scrolls to the top of the page after each redirect
   and only then captures the viewport, so the list with the changed record is
   what appears in the report. For the validator, Pydantic's default
   `str(error)` is several lines long and ends with a documentation URL; the
   graph uses a small `describe()` helper that turns each problem into one
   `field: message` line (for example `tags: List should have at most 3 items
   after validation, not 4`). That works because the Planner prompt quotes only
   this last message, so the model gets a short and specific reason and the raw
   JSON files stay readable.
