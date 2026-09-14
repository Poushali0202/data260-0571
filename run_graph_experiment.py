from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from agent_graph import run_graph

OUTCOMES = ["Valid first attempt", "Valid after 1 retry", "Valid after 2+ retries", "Hit turn ceiling"]


def classify(result: dict) -> str:
    if result["outcome"] != "done":
        return OUTCOMES[3]
    return OUTCOMES[min(result["validation_failures"], 2)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="reports/hw02/cases/schema_input.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--max-turns", type=int, default=6)
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--temperature", type=float, default=0.7)
    args = parser.parse_args()

    case = json.loads(Path(args.input).read_text(encoding="utf-8"))
    output = Path(args.output)
    rows = json.loads(output.read_text(encoding="utf-8")) if output.exists() else []
    if rows:
        print(f"{output} already holds {len(rows)} runs, continuing from run {len(rows) + 1}")

    for run_number in range(len(rows) + 1, args.runs + 1):
        result = run_graph(
            case["title"], case["content"], case["email"],
            args.model, args.base_url, args.temperature, args.max_turns,
        )
        rows.append({
            "run": run_number,
            "max_turns": args.max_turns,
            "temperature": args.temperature,
            "outcome": result["outcome"],
            "classification": classify(result),
            "validation_failures": result["validation_failures"],
            "validation_errors": result["validation_errors"],
            "planner_calls": result["planner_calls"],
            "reviewer_calls": result["reviewer_calls"],
            "turn_count": result["turn_count"],
            "tags": result["planner_proposal"].get("tags", []),
            "summary": result["planner_proposal"].get("summary", ""),
            "latency_ms": result["latency_ms"],
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(
            f"{rows[-1]['timestamp_utc']} run={run_number} outcome={rows[-1]['classification']!r} "
            f"turns={result['turn_count']} latency_ms={result['latency_ms']}"
        )

    print(f"\nSummary for {output}: {len(rows)} runs, turn ceiling {args.max_turns}, temperature {args.temperature}")
    print(f"{'Outcome':<24}{'Count':>6}{'Mean latency (ms)':>20}")
    for outcome in OUTCOMES:
        latencies = [row["latency_ms"] for row in rows if row["classification"] == outcome]
        mean = round(sum(latencies) / len(latencies)) if latencies else 0
        print(f"{outcome:<24}{len(latencies):>6}{mean:>20}")
    completed = sum(1 for row in rows if row["outcome"] == "done")
    print(f"completion rate: {completed}/{len(rows)}")
    print(f"mean latency over all runs: {round(sum(row['latency_ms'] for row in rows) / len(rows))} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
