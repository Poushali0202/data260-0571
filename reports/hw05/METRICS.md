# HW5 measurements

Machine: Intel Core i5-1135G7, 15.8 GB RAM, Windows 11 Home, CPU only. MySQL 8.0 in the Docker
container `s0571-mysql` (port 3307), FastAPI on port 8571, Ollama `qwen3:8b` (temperature 0,
thinking off). Console output with timestamps: `RUN_LOG.txt`.

## Part 3: retry policy under injected failures

Policy (`retry.py`): 3 attempts, exponential backoff 0.2 s then 0.4 s (cap 1.0 s), MySQL connect,
read and write timeouts of 5 s (`database.py`). `run_fault_injection.py` wraps the real MySQL store
in a `FlakyStore` that draws `random.Random(260571).random() < rate` before every attempt and
raises `ConnectionError` on a failed draw, then sends 50 `notice_detail` calls per rate through
`execute_tool`. Latency is the wall-clock time of the whole call including backoff sleeps. All
150 call records (attempts, the draw string such as `FFS`, ok, latency, error) are in
`raw/fault_injection_calls.csv`; the summary is `raw/fault_injection_summary.json`.

| Injected failure rate | Success rate | Mean latency (ms) | p99 latency (ms) |
|---|---|---|---|
| 0% | 100% (50/50) | 41.61 | 265.24 |
| 20% | 100% (50/50) | 83.50 | 624.27 |
| 50% | 78% (39/50) | 330.68 | 664.21 |

The same seed produces the same success/failure sequence on every run: the first ten calls at
50% always draw `FS FFF FFF FS FFS S FS FFF FFF FFF`, and `verify_hw05.py` regenerates all 150
draw strings from the seed and compares them with the CSV. At 20% every call succeeded within
three attempts; at 50% eleven calls drew three failures in a row and returned the clean error
`{ok: false, data: null, error: "storage error: injected failure"}` instead of raising.

Evaluation for an interactive assistant: the policy is suitable. With no failures a call costs
about 40 ms, and even at 50% failures the worst case is bounded at 0.2 + 0.4 s of waiting plus
three storage attempts, so the p99 stays under 0.7 s, which is below what a user notices next to
a 10 to 60 s model turn. The price is that one call in five gives up at 50%, which the agent
sees as an error envelope and can report honestly.

For batch processing I would raise the attempts from 3 to 6 or 8, keep the base delay at 0.2 s
but let the cap grow to 10 or 30 s so the backoff reaches 0.2, 0.4, 0.8, 1.6, 3.2, 6.4 s, and
raise the MySQL read timeout from 5 s to 30 or 60 s so long aggregate queries are not cut off.
At 50% failures six attempts give a 98.4% success rate instead of 87.5%, and a batch job can
afford the extra seconds; it should also add jitter so that many retrying workers do not hit the
database at the same moment.

## Part 5: agent scenarios (qwen3:8b through Ollama)

`run_agent_scenarios.py` ran five scenarios through `run_agent` with the three domain tools.
One line per run is in `raw/agent_runs.jsonl` (steps, tool calls, inputs, results, stop reason).

| Scenario | max_steps | Steps used | Tool calls | Stop reason | Seconds |
|---|---|---|---|---|---|
| Is there a recall notice for baby spinach? Give me the newest one. | 5 | 2 | 1 (search_notices) | completed | 125.5 |
| Show me the details of notice 4990 and tell me which supplier it belongs to. | 5 | 2 | 1 (notice_detail) | completed | 53.5 |
| How many notices does supplier 3 have and how many units are affected in total? | 5 | 2 | 1 (supplier_summary) | completed | 37.4 |
| Has ibuprofen been recalled recently? | 5 | 1 | 1 (search_notices, blocked) | safety_block | 13.6 |
| Find milk notices, open the newest one, then summarise its supplier. | 2 | 2 | 2 | max_steps | 68.5 |

Three runs ended normally after one tool call and one answer turn, the medication question was
stopped by the safety rule inside `execute_tool` on the first step, and the three-tool question
hit the ceiling of 2 steps after two tool calls. A hosted-model comparison was not run.
