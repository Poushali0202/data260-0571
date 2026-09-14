# HW2 measurements

All runs use qwen3:8b through Ollama 0.33.2 on the laptop described in the
report (CPU only), temperature 0.7, thinking off, num_ctx 2048, num_predict 128.
Latency is the wall-clock time of one graph run (all Planner and Reviewer calls).
Raw rows: `raw/schema_validation_runs.json`, `raw/ceiling_2_runs.json`,
`raw/ceiling_10_runs.json`, `raw/adversarial_runs.json`. Console lines with
timestamps: `RUN_LOG.txt`.

## Part 4.3: schema validation, 30 runs on `cases/schema_input.json` (turn ceiling 6)

| Outcome over 30 runs | Count | Mean latency (ms) |
|---|---|---|
| Valid first attempt | 28 | 21527 |
| Valid after 1 retry | 2 | 34808 |
| Valid after 2+ retries | 0 | n/a |
| Hit turn ceiling | 0 | n/a |
| All 30 runs | 30 | 22413 |

- Validation errors seen: `summary: Value error, summary has 26 words, the limit is 25` (runs 20 and 26). Both retries passed.
- Reviewer approved at the first review in all 30 runs; turn count 3 in 28 runs, 4 in 2 runs.
- Latency: median 18825 ms, min 15493 ms, max 90653 ms. Run 1 (33865 ms) and run 12 (90653 ms) include Ollama loading the model; run 12 was the first run after Ollama had been restarted.
- 12 distinct tag sets in 30 runs; summaries of 16 to 25 words.

## Part 4.4: turn ceiling 2 versus 10, 20 runs each, same input and settings

| Turn ceiling | Runs | Completed | Completion rate | Mean latency (ms) | Median latency (ms) | Max latency (ms) | Runs with a schema retry | Turns used |
|---|---|---|---|---|---|---|---|---|
| 2 | 20 | 18 | 90% | 17886 | 17601 | 28140 | 2 (both abandoned) | 3 in every run |
| 10 | 20 | 20 | 100% | 18598 | 16343 | 29563 | 4 (all recovered) | 3 in 16 runs, 4 in 4 runs |

- Ceiling 2 failures: runs 9 and 14 (summaries of 26 and 27 words); the retry used the last turn and the Reviewer never ran.
- Ceiling 10 retries: runs 6, 11, 13, 18 (summaries of 26 or 27 words); every retry was valid and approved.
- Chosen for deployment: 10 (100% completion for 0.7 s more mean latency; the extra turns are only used by inputs that keep failing, worst case ten model calls).

## Part 4.5: adversarial input, 5 runs on `cases/adversarial_input.json` (turn ceiling 6)

| Run | Outcome | Turns used | Planner calls | Reviewer calls | Schema rejections | Latency (ms) |
|---|---|---|---|---|---|---|
| 1 | Hit turn ceiling | 7 | 4 | 2 | 2 | 191989 |
| 2 | Hit turn ceiling | 7 | 4 | 2 | 1 | 131137 |
| 3 | Hit turn ceiling | 7 | 4 | 2 | 1 | 93296 |
| 4 | Hit turn ceiling | 7 | 4 | 2 | 2 | 121530 |
| 5 | Hit turn ceiling | 7 | 4 | 2 | 1 | 102899 |
| All 5 runs | 5 of 5 hit the ceiling, 0 completed | 7 | 4 | 2 | 7 in total | mean 128170 |

- Every run followed the same cycle: valid first proposal, Reviewer adopts the injected demand for 14 tags and all lot codes, Planner's attempt to comply is cut off at 128 output tokens and fails validation (`output: Invalid JSON: EOF while parsing a string ...`), retry produces a valid proposal again, Reviewer rejects it again, ceiling reached at turn 7.
- Schema rejections: 7 over 5 runs, all truncated JSON. Reviewer issues: 10 reviews, all rejecting.
- Mean latency 128170 ms, about seven times a normal run on the frozen input.
