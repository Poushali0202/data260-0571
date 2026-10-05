# AI-use statement

1. I used an AI assistant for debugging and for preparing the report document
   (`report.md` / `report.pdf`). The debugging help covered the MCP Python SDK 2.x
   import path (`FastMCP` is now `MCPServer` in `mcp.server.mcpserver`), the Ollama
   tool-call message format for the `tool` role, the SQLAlchemy `IntegrityError`
   handling behind the 409 responses, and the Redux Toolkit `rejectWithValue`
   pattern for surfacing FastAPI error details in the forms. I designed the
   supplier and notice schema, wrote the routers, the Redux slice and pages, the two
   MCP servers, the retry policy, the fault-injection and agent scripts, the offline
   tests and the smoke test myself, ran every experiment on my laptop, reviewed the
   outputs and made the Canvas submission.

2. One thing I verified independently was the claim that the fault-injection
   sequence is reproducible from VERIFY_SEED, because the whole Part 3 table depends
   on it and the success rate at 50% (39/50) looked lower than the 87.5% that three
   independent attempts would give.

3. I regenerated the per-attempt draw strings in `verify_hw05.py` from
   `random.Random(260571)` with the same rule the experiment uses (draw until a
   success or three failures) and compared them with the `draws` column of all 150
   rows in `raw/fault_injection_calls.csv`; they match row for row, and the ok
   column agrees with whether the string ends in S. The lower success rate comes
   from the specific sequence that this seed produces (11 of the 50 calls drew FFF),
   not from a retry bug: the expected value is 43.75 and 39 is within the normal
   spread of a 50-call sample.

4. I kept the policy as it was (3 attempts, 0.2 s base delay, 1 s cap) and wrote
   the reproducibility check into the smoke test so the table can be rechecked on
   any machine. The evaluation in `METRICS.md` quotes the measured 78% rather than
   the theoretical value and explains the difference.
