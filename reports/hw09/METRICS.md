# HW9 metrics

All numbers measured on 2026-11-09 on an Intel Core i5-1135G7 laptop (CPU only), qwen3:8b through Ollama, temperature 0.

## Part 1: view counter

| Accesses | Redis s0571:views:notice:4870 | MySQL view_count | Syncs |
|---|---|---|---|
| 25 | 25 | 20 | at 10 and 20 |

## Part 2: semantic cache, 12 queries, threshold 0.85

| Metric | Value |
|---|---|
| Queries | 12 (5 new, 3 exact duplicates, 4 paraphrases) |
| Served from cache | 3 (all exact duplicates) |
| Cache hit rate | 25.0% |
| Average latency, cached | 30.0 ms (27.2 to 33.7 ms) |
| Average latency, not cached | 88,758.3 ms (73.3 to 113.3 s) |
| Paraphrase similarities | 0.757, 0.759, 0.787, 0.849 (all below 0.85) |

## Part 3.2: threshold sweep, 40 labeled cases

Cost = misses x 1 + false hits x 20.

| Threshold | Hit rate | False-hit rate | Mean latency (ms) | Total cost |
|---|---|---|---|---|
| 0.75 | 27/40 = 67.5% | 12/40 = 30.0% | 23,812.9 | 13 x 1 + 12 x 20 = 253 |
| 0.80 | 25/40 = 62.5% | 10/40 = 25.0% | 26,873.2 | 15 x 1 + 10 x 20 = 215 |
| 0.85 | 22/40 = 55.0% | 8/40 = 20.0% | 31,278.8 | 18 x 1 + 8 x 20 = 178 |
| 0.90 | 20/40 = 50.0% | 7/40 = 17.5% | 34,714.2 | 20 x 1 + 7 x 20 = 160 |
| 0.95 | 18/40 = 45.0% | 7/40 = 17.5% | 38,749.4 | 22 x 1 + 7 x 20 = 162 |

Threshold to ship: 0.90 (lowest total cost).

## Part 3.5: stale answer and invalidation (RN-005000 supplier changed to Acme Foods)

| Step | is_cached | Latency | Supplier in answer |
|---|---|---|---|
| Before update | True | 157.2 ms | Natural Selection Foods |
| After update, version check off | True | 24.2 ms | Natural Selection Foods (stale) |
| After update, version check on | False | 90,783.7 ms | Acme Foods |
| Next request | True | 36.6 ms | Acme Foods |

## Part 4: lessons and validation

| Lesson | Created after | Reused for | Validation failures before / after | Decision |
|---|---|---|---|---|
| lesson_001 (lot_gap) | t11 | t13 (PASS, 1 attempt) | v02, v09 / v02 | kept |
| lesson_002 (lot_average) | t12 | t14 (REVISE), t15 (PASS, 1 attempt) | v02 / v02 | kept |

Training: 13 of 15 PASS (t11 and t14 failed after 2 attempts).

## Part 4.4: test set, 8 questions

| Variant | Correct answers | Incorrect answers | Average attempts | Average latency |
|---|---|---|---|---|
| Baseline | 8/8 | 0/8 | 1.00 | 24.3 s |
| Evaluator Repair | 8/8 | 0/8 | 1.00 | 16.5 s |
| Lesson Memory | 8/8 | 0/8 | 1.00 | 15.8 s |
| Validated Improvement | 8/8 | 0/8 | 1.00 | 12.6 s |
