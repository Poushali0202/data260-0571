import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from agent_loop import run_agent
from reflexion import CASES, VERIFIERS, unsupported_claims
from src.model_client import ModelClient

OUT = Path(__file__).resolve().parent / "reports" / "hw07" / "raw" / "reliability_attempts.jsonl"
ATTEMPTS = 21


def classify(run, case):
    kinds = [f["kind"] for f in run["failures"]]
    made = Counter(c["tool"] for c in run["tool_calls"])
    if any(made[tool] < n for tool, n in case["required_tools"].items()):
        kinds.append("lost_chain")
    return kinds


def main(minutes):
    deadline = time.time() + minutes * 60
    done = len(OUT.read_text().splitlines()) if OUT.exists() else 0
    model = ModelClient(temperature=0.7, num_ctx=4096, num_predict=400)
    for i in range(done, ATTEMPTS):
        if time.time() > deadline:
            print("time budget used, run again to continue")
            return
        case = CASES[i % len(CASES)]
        print(f"=== attempt {i + 1} task {case['id']} {datetime.now().isoformat(timespec='seconds')}")
        run = run_agent(case["prompt"], model)
        kinds = classify(run, case)
        repairable = [k for k in kinds if k != "lost_chain"]
        row = {
            "attempt": i + 1,
            "task": case["id"],
            "ts": datetime.now().isoformat(timespec="seconds"),
            "tool_calls": len(run["tool_calls"]),
            "failures": kinds,
            "well_formed_before_repair": not kinds,
            "well_formed_after_repair": "lost_chain" not in kinds and run["stop_reason"] == "final_answer",
            "repairs": len(repairable),
            "stop_reason": run["stop_reason"],
            "verifier_ok": VERIFIERS[case["id"]](run)["ok"],
            "unsupported_claims": unsupported_claims(run),
            "tokens": run["tokens"],
            "latency_ms": run["latency_ms"],
            "answer": run["answer"],
            "calls": [{"tool": c["tool"], "args": c["args"]} for c in run["tool_calls"]],
            "failure_details": run["failures"],
        }
        print(f"  failures={kinds} verifier_ok={row['verifier_ok']} tokens={row['tokens']} latency_ms={row['latency_ms']}")
        print(f"  answer: {run['answer']}")
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 600)
