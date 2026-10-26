import json
import sys
import time
from datetime import datetime
from pathlib import Path

from reflexion import CASES, run_reflexion
from src.model_client import ModelClient

OUT = Path(__file__).resolve().parent / "reports" / "hw07" / "raw" / "reflexion_runs.jsonl"
RUNS = 21


def main(minutes):
    deadline = time.time() + minutes * 60
    done = len(OUT.read_text().splitlines()) if OUT.exists() else 0
    model = ModelClient(temperature=0.7, num_ctx=4096, num_predict=400)
    for i in range(done, RUNS):
        if time.time() > deadline:
            print("time budget used, run again to continue")
            return
        case = CASES[i % len(CASES)]
        print(f"=== reflexion run {i + 1} task {case['id']} {datetime.now().isoformat(timespec='seconds')}")
        result = run_reflexion(case, model=model)
        print(f"  stop={result['stop']} attempts={result['attempts']} tool_calls={result['tool_calls']} "
              f"tokens={result['tokens']} latency_ms={result['latency_ms']}")
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(json.dumps({"run": i + 1, "ts": datetime.now().isoformat(timespec="seconds"), **result}) + "\n")


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 600)
