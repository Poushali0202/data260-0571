import asyncio
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from aiokafka import AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient

from kafka_common import BOOTSTRAP, DEAD_LETTER, DRAFTS, FINAL, INBOX, TASKS

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "reports" / "hw08"
SID4 = "0571"
PORT_BASE = 8571
SEED = 571
VERIFY_SEED = 260571
MODEL = "qwen3:8b through Ollama, temperature 0 (planner, writer, reviewer)"
API_URL = f"http://127.0.0.1:{PORT_BASE}/notices"
TOPICS = {"s0571_notice_requests": 1, "s0571_notice_responses": 1, INBOX: 1, TASKS: 2, DRAFTS: 1, FINAL: 1, DEAD_LETTER: 1}
REQUIRED_FILES = [
    "RUN_LOG.txt",
    "METRICS.md",
    "AI_USE.md",
    "raw/ordering_nokey.csv",
    "raw/ordering_keyed.csv",
    "raw/p3_dead_letter_topic.txt",
]


def check(name, passed, details):
    print(f"{'PASS' if passed else 'FAIL'} {name}: {details}", flush=True)
    return {"check": name, "passed": bool(passed), "details": details}


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def read_topic(topic):
    async def read():
        consumer = AIOKafkaConsumer(topic, bootstrap_servers=BOOTSTRAP, auto_offset_reset="earliest")
        await consumer.start()
        values = []
        try:
            while batch := await consumer.getmany(timeout_ms=3000):
                for messages in batch.values():
                    values += [m.value for m in messages]
        finally:
            await consumer.stop()
        return values

    return asyncio.run(read())


def json_values(topic):
    out = []
    for value in read_topic(topic):
        try:
            out.append(json.loads(value))
        except ValueError:
            pass
    return out


def topic_partitions():
    async def describe():
        admin = AIOKafkaAdminClient(bootstrap_servers=BOOTSTRAP)
        await admin.start()
        try:
            return {t["topic"]: len(t["partitions"]) for t in await admin.describe_topics(list(TOPICS))}
        finally:
            await admin.close()

    return asyncio.run(describe())


def call_api(operation, data, correlation_id):
    body = {"correlation_id": correlation_id, "operation": operation, "data": data}
    return requests.post(API_URL, json=body, timeout=20).json()


def check_request_response():
    checks = []
    notice = {
        "productName": "Verify spinach 5 oz",
        "noticeCode": "RN-260571",
        "noticeSource": "Smoke test",
        "noticeCategory": "recall",
        "affectedUnits": 3,
    }
    created = call_api("CREATE_NOTICE", notice, "verify-create")
    notice_id = created.get("notice_id", "")
    fetched = call_api("GET_NOTICE", {"notice_id": notice_id}, "verify-get")
    stored = fetched.get("notice", {})
    round_trip = (
        created.get("success")
        and len(notice_id) == 36
        and fetched.get("success")
        and all(stored.get(k) == v for k, v in notice.items())
    )
    checks.append(check("create_then_get_round_trip", round_trip, f"notice_id {notice_id}, fields match {round_trip}"))
    ids = [created.get("correlation_id"), fetched.get("correlation_id")]
    checks.append(check("correlation_id_preserved", ids == ["verify-create", "verify-get"], f"{ids}"))

    unknown = call_api("DELETE_NOTICE", {}, "verify-unknown")
    missing = call_api("GET_NOTICE", {"notice_id": "no-such-id"}, "verify-missing")
    invalid = call_api("CREATE_NOTICE", {**notice, "productName": ""}, "verify-invalid")
    errors = [unknown, missing, invalid]
    clean = all(not r.get("success") and r.get("error") for r in errors)
    echoed = [r.get("correlation_id") for r in errors] == ["verify-unknown", "verify-missing", "verify-invalid"]
    checks.append(check("errors_clean_and_keep_correlation_id", clean and echoed, f"{[r.get('error') for r in errors]}"))
    return checks


def wait_for(path, text, seconds):
    end = time.time() + seconds
    while time.time() < end:
        if path.exists() and text in path.read_text(errors="replace"):
            return True
        time.sleep(2)
    return False


def check_pipeline(tmp):
    checks = []
    logs = {name: tmp / f"{name}.log" for name in ("planner", "writer", "reviewer")}
    files = [path.open("w") for path in logs.values()]
    procs = [
        subprocess.Popen([sys.executable, "-u", f"{name}.py"], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
        for name, f in zip(logs, files)
    ]
    try:
        ready = all(wait_for(path, "listening", 60) for path in logs.values())
        checks.append(check("agents_start", ready, "planner, writer and reviewer are listening"))
        time.sleep(10)

        out = subprocess.run(
            [sys.executable, "-u", "send_question.py", "Should a store keep selling recalled milk?"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=600,
        ).stdout
        correlation_id = out.split("correlation_id=")[1].split()[0]
        final = json.loads(out[out.index("{") :])
        journey = (
            final["correlation_id"] == correlation_id
            and final["status"] in ("approved", "rejected")
            and len(final["answer"]) > 20
        )
        checks.append(check("inbox_to_final_journey", journey, f"status {final['status']}, correlation_id kept"))

        subprocess.run([sys.executable, "replay_task.py", correlation_id], cwd=ROOT, capture_output=True, timeout=60)
        skipped = wait_for(logs["writer"], f"duplicate correlation_id={correlation_id}", 120)
        drafts = sum(d.get("correlation_id") == correlation_id for d in json_values(DRAFTS))
        checks.append(check("replay_is_idempotent", skipped and drafts == 1, f"replay skipped, {drafts} draft"))

        dead_before = len(read_topic(DEAD_LETTER))
        out = subprocess.run([sys.executable, "send_poison.py"], cwd=ROOT, capture_output=True, text=True).stdout
        good_id = out.split("correlation_id=")[1].split()[0]
        unblocked = wait_for(logs["writer"], f"correlation_id={good_id} draft=", 240)
        dead_after = len(read_topic(DEAD_LETTER))
        tries = logs["writer"].read_text(errors="replace").count("failed:")
        checks.append(
            check(
                "poison_retried_then_dead_lettered",
                dead_after == dead_before + 1 and tries == 3,
                f"{tries} failed attempts, dead letter count {dead_before} -> {dead_after}",
            )
        )
        checks.append(check("poison_does_not_block", unblocked, "next message on the same partition was processed"))
    finally:
        for p, f in zip(procs, files):
            p.terminate()
            p.wait()
            f.close()
    return checks


def main():
    found = topic_partitions()
    checks = [check("topics_and_partitions", found == TOPICS, f"{found}")]
    checks += check_request_response()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        checks += check_pipeline(Path(tmp))
    missing = [f for f in REQUIRED_FILES if not (REPORT / f).exists()]
    checks.append(check("report_files_present", not missing, f"missing: {missing}" if missing else "all present"))
    result = {
        "homework": 8,
        "sid4": SID4,
        "port_base": PORT_BASE,
        "commit": git("rev-parse", "HEAD"),
        "tag_hw8": git("rev-list", "-n", "1", "hw8") or None,
        "model": MODEL,
        "seed": SEED,
        "verify_seed": VERIFY_SEED,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "checks": checks,
        "passed": sum(c["passed"] for c in checks),
        "total": len(checks),
    }
    (REPORT / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"{result['passed']}/{result['total']} checks passed, written to reports/hw08/verification.json")


if __name__ == "__main__":
    main()
