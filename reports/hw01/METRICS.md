# HW1 measurements

Values from `python run_nondeterminism.py --model qwen3:8b --runs-per-temperature 20`.
Raw file: `raw/nondeterminism_runs.json`.

| Metric | Temperature 0.7 | Temperature 0.0 |
|---|---|---|
| Distinct tag sets | 6 | 1 |
| Tags in all 20 runs | none | food safety, product recall, consumer protection |
| Tags in exactly 1 run | consumer advisory, contamination recall, customer recall action, frozen berries recall | none |
| Latency p50 / p95 / p99 (ms) | 79930 / 97093 / 98471 | 85534 / 93497 / 93591 |

## Interpretation

Two users sending the same frozen-berries input at temperature 0.7 can get different tag sets (6 distinct sets in 20 runs). At temperature 0.0 they got one stable set: food safety, product recall, consumer protection.

Variation is acceptable for exploratory tagging. It is not acceptable for recall, safety, or refund decisions that must be the same every time.
