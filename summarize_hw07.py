import csv
import json
from collections import Counter
from pathlib import Path

RAW = Path(__file__).resolve().parent / "reports" / "hw07" / "raw"
KINDS = ["malformed_arguments", "unknown_tool", "text_instead_of_tool", "lost_chain"]


def load(name):
    return [json.loads(line) for line in (RAW / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def correct_on_review(task, answer):
    text = answer.replace(",", "")
    if task == "B":
        example = "4770" in text or ("Organic baby spinach 5 oz" in answer and "2399" in text)
        return "266" in text and "214685" in text and example and "00470" not in text
    if task == "A":
        return "4970" in text and "Prairie Grain Mills" in answer and "2335" in text
    return all(v in text for v in ("4985", "4967", "2196", "Northern Meats", "Green Valley Farms"))


def write_csv(name, rows):
    with open(RAW / name, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def reliability(attempts):
    calls = sum(a["tool_calls"] + len([f for f in a["failure_details"] if "tool" in f]) for a in attempts)
    bad_calls = sum(len([f for f in a["failure_details"] if "tool" in f]) for a in attempts)
    kinds = Counter(k for a in attempts for k in a["failures"])
    rows = []
    for task in ["A", "B", "C", "all"]:
        mine = [a for a in attempts if task in ("all", a["task"])]
        rows.append({
            "task": task,
            "attempts": len(mine),
            "tool_calls": sum(a["tool_calls"] for a in mine),
            "well_formed_before_repair": f"{sum(a['well_formed_before_repair'] for a in mine)}/{len(mine)}",
            "well_formed_after_repair": f"{sum(a['well_formed_after_repair'] for a in mine)}/{len(mine)}",
            **{k: sum(a["failures"].count(k) for a in mine) for k in KINDS},
        })
    write_csv("reliability_summary.csv", rows)
    print(f"call level: {calls - bad_calls}/{calls} calls well formed on first emission; failure kinds {dict(kinds)}")
    return rows


def comparison(attempts, runs):
    original_rejected = [a for a in attempts if not a["verifier_ok"]]
    original_false = [a for a in original_rejected if correct_on_review(a["task"], a["answer"])]
    reflections = load("reflections.jsonl")
    rejected_answers = [(r["task"], r["evidence"]["answer"]) for r in reflections]
    rejected_answers += [(r["task"], r["answer"]) for r in runs if r["stop"] != "success"]
    reflexion_false = [t for t, answer in rejected_answers if correct_on_review(t, answer)]

    def mean(values):
        return round(sum(values) / len(values))

    def claims(items):
        return f"{sum(bool(i['unsupported_claims']) for i in items)} / {sum(len(i['unsupported_claims']) for i in items)}"

    rows = [
        {"metric": "Task success", "original": f"{sum(a['verifier_ok'] for a in attempts)}/{len(attempts)}",
         "reflexion": f"{sum(r['stop'] == 'success' for r in runs)}/{len(runs)}"},
        {"metric": "Unsupported claims (final answers with any / total claims)",
         "original": claims(attempts), "reflexion": claims(runs)},
        {"metric": "Retry rate (runs that retried / mean retries)", "original": "0/21 / 0",
         "reflexion": f"{sum(r['retries'] > 0 for r in runs)}/{len(runs)} / {sum(r['retries'] for r in runs) / len(runs):.2f}"},
        {"metric": "Tool calls per run (mean)", "original": f"{sum(a['tool_calls'] for a in attempts) / len(attempts):.2f}",
         "reflexion": f"{sum(r['tool_calls'] for r in runs) / len(runs):.2f}"},
        {"metric": "Tokens per run (mean)", "original": mean([a["tokens"] for a in attempts]),
         "reflexion": mean([r["tokens"] for r in runs])},
        {"metric": "Latency per run (mean ms)", "original": mean([a["latency_ms"] for a in attempts]),
         "reflexion": mean([r["latency_ms"] for r in runs])},
        {"metric": "Verifier false rejections", "original": f"{len(original_false)} of {len(original_rejected)} rejections",
         "reflexion": f"{len(reflexion_false)} of {len(rejected_answers)} rejections"},
    ]
    write_csv("comparison.csv", rows)
    per_task = []
    for task in ["A", "B", "C"]:
        a = [x for x in attempts if x["task"] == task]
        r = [x for x in runs if x["task"] == task]
        per_task.append({"task": task, "original_success": f"{sum(x['verifier_ok'] for x in a)}/{len(a)}",
                         "reflexion_success": f"{sum(x['stop'] == 'success' for x in r)}/{len(r)}",
                         "reflexion_stops": dict(Counter(x["stop"] for x in r)),
                         "reflexion_mean_attempts": round(sum(x["attempts"] for x in r) / len(r), 2),
                         "original_mean_tokens": mean([x["tokens"] for x in a]),
                         "reflexion_mean_tokens": mean([x["tokens"] for x in r])})
    write_csv("comparison_by_task.csv", per_task)
    return rows, per_task


if __name__ == "__main__":
    attempts = load("reliability_attempts.jsonl")
    for row in reliability(attempts):
        print(row)
    if (RAW / "reflexion_runs.jsonl").exists():
        rows, per_task = comparison(attempts, load("reflexion_runs.jsonl"))
        for row in rows + per_task:
            print(row)
