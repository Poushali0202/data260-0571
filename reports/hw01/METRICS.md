# HW1 measurements

These values must come from `python run_nondeterminism.py`; no values are
invented. The command requires Ollama to be running with the selected model.

| Metric | Temperature 0.7 | Temperature 0.0 |
|---|---:|---:|
| Distinct tag sets | pending run | pending run |
| Tags in all 20 runs | pending run | pending run |
| Tags in exactly 1 run | pending run | pending run |
| Latency p50 / p95 / p99 (ms) | pending run | pending run |

## Interpretation

Identical input can produce different tags or summaries at a nonzero
temperature, so two users may receive different but relevant labels. Variation
is acceptable for exploratory discovery; it is not acceptable for safety,
recall, compliance, or other workflows that require reproducible decisions.
Replace the pending cells with the measured values and retain the raw 40-run
JSON before submission.
