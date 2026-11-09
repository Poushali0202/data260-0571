import json
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

from self_improving.answer_agent import answer, relevant_lessons
from self_improving.evaluator_agent import evaluate

HERE = Path(__file__).parent
LESSONS_FILE = HERE / "lessons.json"
RAW = Path("reports/hw09/raw")

FIELD_LESSON = (
    "The answer leaves out or changes the exact value that was asked for.",
    "Copy the exact value of the field asked for (supplier, region, source or product) from the record.",
    ["supplier", "source", "product", "region", "located"],
)
LESSON_TEXT = {
    "affected_units": (
        "The answer gives the sum of the lot units when the question asks for the notice's affected units.",
        "When asked how many units a notice affects, give the affected units field of the notice record, even if it is 0. "
        "Do not replace it with the lot units.",
        ["units are affected", "affected units", "units does", "units affected"],
    ),
    "lot_total": (
        "The answer gives a wrong total, or no total, when the question asks to add lot units.",
        "For a total over lots, list each lot's units from the record, add them one at a time and state the final sum.",
        ["total", "add up", "combined", "sum"],
    ),
    "lot_gap": (
        "The answer gets the difference between the lot total and the affected units wrong.",
        "For a difference, first add all lot units and write the total, then subtract the smaller number from the "
        "larger one and show the subtraction.",
        ["difference"],
    ),
    "lot_average": (
        "The answer gets the average units per lot wrong.",
        "For an average per lot, write each lot's units, add them, count the lots, then divide the total by the count "
        "and show each step.",
        ["average"],
    ),
    "largest_lot": (
        "The answer names the wrong lot when asked which lot has the most units.",
        "Compare the units of every lot in the record and name the lot code with the highest number.",
        ["most units", "largest", "biggest"],
    ),
    "no_record": (
        "The answer gives details for a notice that has no record.",
        "If the record says a notice has no record, say it is not in the database and give no other details.",
        ["notice", "rn-"],
    ),
    "field_value": FIELD_LESSON,
}
LESSON_AFTER = 1
FIELD_TYPES = {"supplier", "region", "source", "product"}


def load_lessons():
    return json.loads(LESSONS_FILE.read_text()) if LESSONS_FILE.exists() else []


def save_lessons(lessons):
    LESSONS_FILE.write_text(json.dumps(lessons, indent=2))


def failure_type(field):
    return "field_value" if field in FIELD_TYPES else field


def run_question(item, attempts, lessons, controlled=False):
    start = time.perf_counter()
    used = relevant_lessons(item["question"], lessons)
    print(f"\n[{item['id']}] {item['question']}")
    if used:
        print(f"  loaded lessons: {', '.join(lesson['lesson_id'] for lesson in used)}")
    history = []
    reply, verdict = None, None
    for attempt in range(1, attempts + 1):
        if attempt == 1:
            reply = answer(item["question"], used, with_record=not controlled)
        else:
            reply = answer(item["question"], used, previous=reply, feedback=verdict["feedback"])
        verdict = evaluate(item["id"], reply)
        history.append({"attempt": attempt, "answer": reply, **verdict})
        print(f"  attempt {attempt}: {' '.join(reply.split())[:200]}")
        print(f"  evaluator: {verdict['result']} - {verdict['explanation']}")
        if verdict["feedback"]:
            print(f"  feedback: {verdict['feedback']}")
        if verdict["result"] == "PASS":
            break
    return {
        "id": item["id"], "question": item["question"], "result": verdict["result"], "attempts": len(history),
        "final_answer": reply, "lessons_used": [lesson["lesson_id"] for lesson in used],
        "latency_s": round(time.perf_counter() - start, 1), "history": history,
    }


def train():
    counts = Counter()
    results = []
    for item in json.loads((HERE / "training_data.json").read_text()):
        lessons = load_lessons()
        result = run_question(item, 2, lessons)
        for lesson in lessons:
            if lesson["lesson_id"] in result["lessons_used"]:
                lesson["use_count"] += 1
        for step in result["history"]:
            counts.update(failure_type(f) for f in step["failed"])
        for kind, count in counts.items():
            if count >= LESSON_AFTER and not any(lesson["failure_type"] == kind for lesson in lessons):
                pattern, correction, keywords = LESSON_TEXT[kind]
                lesson = {
                    "lesson_id": f"lesson_{len(lessons) + 1:03d}", "failure_pattern": pattern, "correction": correction,
                    "created_at": date.today().isoformat(), "use_count": 0,
                    "failure_type": kind, "keywords": keywords, "status": "candidate",
                }
                lessons.append(lesson)
                print(f"  NEW LESSON {lesson['lesson_id']} ({kind} seen {count} times): {correction}")
        save_lessons(lessons)
        results.append(result)
    return results


def demo():
    item = json.loads((HERE / "training_data.json").read_text())[0]
    print("Controlled case: the first answer is written without the notice record, so it cannot be complete.")
    return [run_question(item, 2, [], controlled=True)]


def first_attempt_results(lessons):
    items = json.loads((HERE / "validation_data.json").read_text())
    return {item["id"]: run_question(item, 1, lessons) for item in items}


def validate():
    lessons = load_lessons()
    report = []
    for candidate in [lesson for lesson in lessons if lesson["status"] == "candidate"]:
        kept = [lesson for lesson in lessons if lesson["status"] == "kept"]
        print(f"\n=== validating {candidate['lesson_id']} ({candidate['failure_type']}) ===\n--- before")
        before = first_attempt_results(kept)
        print("--- after")
        after = first_attempt_results(kept + [candidate])
        fails_before = [q for q, r in before.items() if r["result"] != "PASS"]
        fails_after = [q for q, r in after.items() if r["result"] != "PASS"]
        broken = [q for q in before if before[q]["result"] == "PASS" and after[q]["result"] != "PASS"]
        keep = len(fails_after) <= len(fails_before) and not broken
        candidate["status"] = "kept" if keep else "removed"
        report.append({
            "lesson_id": candidate["lesson_id"], "fails_before": fails_before, "fails_after": fails_after,
            "regressions": broken, "decision": candidate["status"], "before": before, "after": after,
        })
        print(f"{candidate['lesson_id']}: failures before {fails_before}, after {fails_after}, "
              f"regressions {broken} -> {candidate['status']}")
        save_lessons(lessons)
    return report


VARIANTS = {
    "baseline": (1, lambda lessons: []),
    "repair": (2, lambda lessons: []),
    "memory": (2, lambda lessons: lessons),
    "validated": (2, lambda lessons: [lesson for lesson in lessons if lesson["status"] == "kept"]),
}


def test(variant):
    attempts, pick = VARIANTS[variant]
    lessons = pick(load_lessons())
    print(f"variant {variant}: attempts {attempts}, lessons {[lesson['lesson_id'] for lesson in lessons]}")
    return [run_question(item, attempts, lessons) for item in json.loads((HERE / "test_data.json").read_text())]


def table():
    print("| Variant | Correct answers | Incorrect answers | Average attempts | Average latency (s) |")
    print("|---|---|---|---|---|")
    for variant in VARIANTS:
        rows = json.loads((RAW / f"p4_test_{variant}.json").read_text())
        correct = sum(r["result"] == "PASS" for r in rows)
        print(f"| {variant} | {correct}/{len(rows)} | {len(rows) - correct}/{len(rows)} | "
              f"{sum(r['attempts'] for r in rows) / len(rows):.2f} | {sum(r['latency_s'] for r in rows) / len(rows):.1f} |")


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "table":
        table()
    else:
        output = {"train": train, "demo": demo, "validate": validate}.get(command)
        result = output() if output else test(sys.argv[2])
        name = f"p4_test_{sys.argv[2]}" if command == "test" else f"p4_{command}"
        (RAW / f"{name}.json").write_text(json.dumps(result, indent=2))
