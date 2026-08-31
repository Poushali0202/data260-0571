"""Run the required 20-at-0.7 and 20-at-0.0 experiment."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from agents_demo import run_pipeline


def percentile(values: list[int], percentage: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    rank = (len(ordered) - 1) * percentage / 100
    lower, upper = int(rank), min(int(rank) + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - int(rank))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="reports/hw01/cases/nondeterminism_input.json")
    parser.add_argument("--output", default="reports/hw01/raw/nondeterminism_runs.json")
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--runs-per-temperature", type=int, default=20)
    args = parser.parse_args()

    case = json.loads(Path(args.input).read_text(encoding="utf-8"))
    results: list[dict[str, object]] = []
    for temperature in (0.7, 0.0):
        for run_number in range(1, args.runs_per_temperature + 1):
            started = time.perf_counter()
            output = run_pipeline(
                case["title"], case["content"], case["email"],
                args.model, args.base_url, temperature,
            )
            latency_ms = round((time.perf_counter() - started) * 1000)
            final = output["agents"]["final"]
            results.append({
                "run": run_number,
                "temperature": temperature,
                "tags": final["tags"],
                "summary": final["summary"],
                "latency_ms": latency_ms,
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
            print(f"temperature={temperature} run={run_number} latency_ms={latency_ms}")

    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"saved {len(results)} runs to {destination}")
    for temperature in (0.7, 0.0):
        subset = [row for row in results if row["temperature"] == temperature]
        sets = {tuple(sorted(row["tags"])) for row in subset}
        tag_counts = {}
        for row in subset:
            for tag in row["tags"]:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        latencies = [int(row["latency_ms"]) for row in subset]
        print(json.dumps({
            "temperature": temperature,
            "distinct_tag_sets": len(sets),
            "tags_in_all_runs": sorted(tag for tag, count in tag_counts.items() if count == len(subset)),
            "tags_in_exactly_one_run": sorted(tag for tag, count in tag_counts.items() if count == 1),
            "latency_p50_ms": percentile(latencies, 50),
            "latency_p95_ms": percentile(latencies, 95),
            "latency_p99_ms": percentile(latencies, 99),
        }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
