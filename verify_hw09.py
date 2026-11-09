import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml
from sqlalchemy import text

from cached_ask import ask, cache
from database import engine
from notice_cache import NoticeCache
from notice_facts import data_version, facts_for
from self_improving.evaluator_agent import REFERENCE, evaluate

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "reports" / "hw09"
PART4 = ROOT / "self_improving"
SID4 = "0571"
SEED = 571
VERIFY_SEED = 260571
MODEL = "qwen3:8b through Ollama, temperature 0; all-MiniLM-L6-v2 embeddings; Redis Stack 7.4.0"
TEST_NOTICE = 4999
REQUIRED_FILES = [
    "RUN_LOG.txt", "METRICS.md", "AI_USE.md", "raw/p1_counter.txt", "raw/p2_cache_test.csv",
    "raw/sweep_rows.csv", "raw/p3_stale_demo.txt", "raw/p4_train.json", "raw/p4_validate.json",
    "raw/p4_test_baseline.json", "raw/p4_test_repair.json", "raw/p4_test_memory.json", "raw/p4_test_validated.json",
]


def check(name, passed, details):
    print(f"{'PASS' if passed else 'FAIL'} {name}: {details}", flush=True)
    return {"check": name, "passed": bool(passed), "details": details}


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def check_counter():
    counter = NoticeCache()
    key = f"s0571:views:notice:{TEST_NOTICE}"
    counter.redis_client.delete(key)
    counts = [counter.increment_notice_views(TEST_NOTICE) for _ in range(12)]
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT view_count FROM grocery_notices WHERE id = :id"), {"id": TEST_NOTICE}).scalar()
    counter.redis_client.delete(key)
    return [
        check("counter_increments", counts == list(range(1, 13)), f"returned {counts[0]}..{counts[-1]}"),
        check("counter_syncs_every_10", stored == 10, f"MySQL view_count after 12 views = {stored}"),
    ]


def check_cache():
    keys = [k.decode() for k in cache.redis_client.scan_iter("*")]
    indexes = [i.decode() for i in cache.redis_client.execute_command("FT._LIST")]
    seed = yaml.safe_load(open(ROOT / "cache_cases.yaml", encoding="utf-8"))["seeds"][1]["query"]
    result = ask(seed)
    match = cache.nearest(cache.embed(seed))
    fresh = data_version(facts_for(match["codes"])) == match["data_version"]
    return [
        check("redis_keys_use_prefix", keys and all(k.startswith("s0571:") for k in keys),
              f"{len(keys)} keys, indexes {indexes}"),
        check("exact_duplicate_is_cache_hit", result["is_cached"] and result["similarity"] >= 0.999,
              f"is_cached={result['is_cached']} similarity={result['similarity']} latency={result['latency_ms']} ms"),
        check("stored_data_version_matches_db", fresh, f"{match['codes']} marker {match['data_version']}"),
    ]


def check_cases():
    cases = yaml.safe_load(open(ROOT / "cache_cases.yaml", encoding="utf-8"))["cases"]
    counts = Counter(c["category"] for c in cases)
    return [check("cache_cases_40_labeled", len(cases) == 40 and set(counts.values()) == {10}, dict(counts))]


def check_part4():
    checks = []
    ids = []
    for name in ["training_data.json", "validation_data.json", "test_data.json"]:
        rows = json.loads((PART4 / name).read_text())
        ids += [r["id"] for r in rows]
        checks.append(check(f"{name}_inputs_only", all(set(r) == {"id", "question"} for r in rows), f"{len(rows)} questions"))
    checks.append(check("every_question_in_reference", all(i in REFERENCE["questions"] for i in ids), f"{len(ids)} ids"))
    facts = REFERENCE["notices"]["RN-004803"]
    good = evaluate("t01", f"The lots add up to {facts['lot_total']} units.")["result"]
    bad = evaluate("t01", "The lots add up to 7000 units.")
    checks.append(check("evaluator_pass_and_revise", good == "PASS" and bad["result"] == "REVISE" and bad["feedback"],
                        f"correct -> {good}, wrong -> {bad['result']}"))
    lessons = json.loads((PART4 / "lessons.json").read_text())
    fields = {"lesson_id", "failure_pattern", "correction", "created_at", "use_count"}
    checks.append(check("lessons_have_required_fields", lessons and all(fields <= set(lesson) for lesson in lessons),
                        [f"{lesson['lesson_id']} {lesson['status']}" for lesson in lessons]))
    return checks


def main():
    checks = check_counter() + check_cache() + check_cases() + check_part4()
    missing = [f for f in REQUIRED_FILES if not (REPORT / f).exists()]
    checks.append(check("report_files_present", not missing, f"missing: {missing}" if missing else "all present"))
    result = {
        "homework": 9,
        "sid4": SID4,
        "commit": git("rev-parse", "HEAD"),
        "tag_hw9": git("rev-list", "-n", "1", "hw9") or None,
        "model": MODEL,
        "seed": SEED,
        "verify_seed": VERIFY_SEED,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "checks": checks,
        "passed": sum(c["passed"] for c in checks),
        "total": len(checks),
    }
    (REPORT / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"{result['passed']}/{result['total']} checks passed, written to reports/hw09/verification.json")


if __name__ == "__main__":
    main()
