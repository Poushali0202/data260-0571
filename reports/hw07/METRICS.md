# HW7 metrics

Model: qwen3:8b through Ollama on CPU (Intel Core i5-1135G7). Agent loop and Reflexion: temperature 0.7, num_ctx 4096, num_predict 400.

## Part 1: API behavior

| Request | Expected | Observed |
|---|---|---|
| POST /auth/login, valid | 200 + JWT | 200 + JWT |
| POST /auth/login, wrong password | 401 | 401 |
| GET /auth/me, no token / forged token / expired token | 401 | 401 / 401 / 401 |
| POST /api/notices as reader / writer | 403 / 201 | 403 / 201 |
| DELETE /api/notices/{id} as writer / moderator | 403 / 204 | 403 / 204 |
| GET /api/notices with reader token | 200 | 200 |

## Part 2: Tool-call reliability (21 attempts, raw/reliability_attempts.jsonl)

| Task | Attempts | Tool calls | Well formed before repair | Well formed after repair | Malformed arguments | Unknown tool | Text when a tool was required | Lost multi-step chain |
|---|---|---|---|---|---|---|---|---|
| A | 7 | 14 | 7/7 | 7/7 | 0 | 0 | 0 | 0 |
| B | 7 | 14 | 7/7 | 7/7 | 0 | 0 | 0 | 0 |
| C | 7 | 21 | 7/7 | 7/7 | 0 | 0 | 0 | 0 |
| All | 21 | 49 | 21/21 (100%) | 21/21 (100%) | 0 | 0 | 0 | 0 |

## Part 3: Original loop vs Reflexion (21 runs each, raw/comparison.csv)

| Metric | Original loop | Reflexion loop |
|---|---|---|
| Task success | 14/21 (67%) | 21/21 (100%) |
| Unsupported claims (answers with any / total) | 2 / 2 | 0 / 0 |
| Retry rate | 0/21 | 7/21 runs, 0.33 retries per run |
| Tool calls (mean per run) | 2.33 | 3.00 |
| Tokens (mean per run) | 1,653 | 2,259 |
| Latency (mean ms) | 55,167 | 89,229 |
| Verifier false rejections | 5 of 7 rejections | 2 of 7 rejections |

Stop reasons in the Reflexion loop: success 21, budget_exhausted 0, human_review 0. The first reflection prompt (v1, raw/reflexion_runs_v1.jsonl) ended task B in human_review.

## Part 4: Bike-share scenarios (reference totals computed by hand from the snapshot prices)

| Scenario | Trips | Months | Pay per use | Month pass + residual | Correct decision |
|---|---|---|---|---|---|
| Commuter (bike_commuter_membership.csv) | 616 | 14 | $4,559.19 | $1,657.37 | Buy Monthly Membership |
| Occasional (bike_occasional_payperuse.csv) | 518 | 37 | $886.98 | $1,073.00 | Pay Per Ride/Minute |

Agent results for the UI runs are in raw/bike_runs.jsonl and in the report.

## Part 6: Safety gate (raw/safety_gate_results.csv)

| Run | Correct | False allows | False blocks |
|---|---|---|---|
| First deny-list (v1) | 9/10 | 1 (`ls && rm -Rf ~/projects`) | 0 |
| Fixed deny-list | 10/10 | 0 | 0 |
