import csv
import json
import random
import statistics
import time
from pathlib import Path

from domain_tools import MySQLStore, execute_tool

VERIFY_SEED = 260571
RATES = [0.0, 0.2, 0.5]
CALLS = 50
RAW = Path(__file__).resolve().parent / "reports" / "hw05" / "raw"


class FlakyStore:
    def __init__(self, store, rate, rng):
        self.store = store
        self.rate = rate
        self.rng = rng
        self.draws = ""

    def get(self, notice_id):
        failed = self.rng.random() < self.rate
        self.draws += "F" if failed else "S"
        if failed:
            raise ConnectionError("injected failure")
        return self.store.get(notice_id)


def percentile(values, p):
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    low, high = int(k), min(int(k) + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (k - low)


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    real = MySQLStore()
    rows = []
    summary = []
    for rate in RATES:
        rng = random.Random(VERIFY_SEED)
        flaky = FlakyStore(real, rate, rng)
        latencies = []
        successes = 0
        for call in range(1, CALLS + 1):
            flaky.draws = ""
            notice_id = 4800 + call
            start = time.perf_counter()
            result = json.loads(execute_tool("notice_detail", {"notice_id": notice_id}, flaky))
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
            successes += result["ok"]
            rows.append({"failure_rate": rate, "call": call, "notice_id": notice_id, "attempts": len(flaky.draws),
                         "draws": flaky.draws, "ok": result["ok"], "latency_ms": round(latency, 2), "error": result["error"] or ""})
        summary.append({"failure_rate": rate, "calls": CALLS, "successes": successes, "success_rate": successes / CALLS,
                        "mean_latency_ms": round(statistics.mean(latencies), 2), "p99_latency_ms": round(percentile(latencies, 0.99), 2)})
        print(f"rate {rate:.0%}: {successes}/{CALLS} ok, mean {summary[-1]['mean_latency_ms']} ms, p99 {summary[-1]['p99_latency_ms']} ms, "
              f"first draws {' '.join(r['draws'] for r in rows[-CALLS:][:10])}")
    with open(RAW / "fault_injection_calls.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (RAW / "fault_injection_summary.json").write_text(json.dumps({"verify_seed": VERIFY_SEED, "results": summary}, indent=2) + "\n")
    print(f"wrote {len(rows)} call records to {RAW / 'fault_injection_calls.csv'}")


if __name__ == "__main__":
    main()
