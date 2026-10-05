# Reflection: one run that hit the max_steps ceiling

The run I picked is the last line of `raw/agent_runs.jsonl`: the user input was "Find milk
notices, open the newest one, then summarise its supplier." with `max_steps` set to 2, which
is one step fewer than the three tool calls the question needs.

Step 1. The harness sent the system prompt, the user message and the three tool definitions to
`qwen3:8b`. The model did not answer in text; it returned one tool call,
`search_notices({"query": "milk", "limit": 5})`. The harness passed it through `execute_tool`,
which checked the tool name, ran the safety rule (the query contains no medication term, so it
was allowed), validated the inputs and queried MySQL through the retry wrapper. The result was
an `{ok: true, ...}` envelope with five milk notices, the newest being id 4966, "Bagged whole
milk 12 oz" with 845 affected units. The harness appended the assistant tool call and the tool
result as a `tool` message and logged the step.

Step 2. With the search result in context, the model asked for
`notice_detail({"notice_id": 4966})`. `execute_tool` ran again, the detail lookup succeeded and
the envelope now carried the supplier id 15 and the supplier name "Mission Organics". The step
was logged in the same way.

Why it stopped. After step 2 the loop counter equalled `max_steps`, so the `for` loop ended
without calling the model a third time. The model never got the chance to request
`supplier_summary(15)` or to write a final sentence, which is why the logged answer is empty and
the stop reason is `max_steps` rather than `completed`. Nothing failed: both tool calls returned
`ok: true`, no safety rule fired, and the whole run took 68.5 seconds for two model turns.

What this shows is that the ceiling is a budget, not an error. The same question with
`max_steps` 5 would have finished in three tool calls plus one answer turn, as the three
completed scenarios did. For an interactive assistant a ceiling of 5 is a reasonable default;
the log line keeps every tool call, input and result, so a truncated run can still be inspected
and the partial results reused.
