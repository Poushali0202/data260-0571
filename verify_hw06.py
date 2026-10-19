import csv
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import WriteError

from config import MONGO_DB, MONGO_URI, SHORT_TERM_N, SUMMARIZE_EVERY_USER_MSGS, TOP_K_EPISODES

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "reports" / "hw06"
SID4 = "0571"
PORT_BASE = 8571
SEED = 571
VERIFY_SEED = 260571
MODEL = "qwen3:8b"
BASE_URL = f"http://127.0.0.1:{PORT_BASE}"
TEST_USER = "verify_hw06"
REQUIRED_FILES = ["RUN_LOG.txt", "METRICS.md", "AI_USE.md", "raw/chat_log.csv", "raw/sweep_turns.csv",
                  "raw/sweep_summary.json", "raw/probe_scores.csv", "raw/MEMORY_original.md",
                  "raw/MEMORY_consolidated.md", "raw/generated_function.py", "raw/agent_md_check.json"]


def check(name, passed, details):
    print(f"{'PASS' if passed else 'FAIL'} {name}: {details}")
    return {"check": name, "passed": bool(passed), "details": details}


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def request(method, path, body=None, timeout=600):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            text = response.read().decode()
            return response.status, json.loads(text) if text else None
    except urllib.error.HTTPError as error:
        text = error.read().decode()
        return error.code, json.loads(text) if text else None


def server_up():
    try:
        with socket.create_connection(("127.0.0.1", PORT_BASE), timeout=1):
            return True
    except OSError:
        return False


def check_document_api():
    checks = []
    status, body = request("GET", "/health")
    checks.append(check("backend_responds_on_port_base", status == 200 and body == {"status": "ok"}, f"GET /health returned {status}"))
    notice = {"productName": "Verify spinach", "noticeDescription": "smoke test", "noticeCategory": "recall", "noticeDate": "2026-10-18T09:00:00Z"}
    status, created = request("POST", "/api/doc/notices", notice)
    checks.append(check("doc_create_201", status == 201 and created.get("status") == "open", f"POST returned {status}, default status {created.get('status')}"))
    notice_id = created["id"]
    status, rows = request("GET", "/api/doc/notices")
    checks.append(check("doc_list", status == 200 and any(r["id"] == notice_id for r in rows), f"{len(rows)} documents listed"))
    status, body = request("GET", f"/api/doc/notices/{notice_id}")
    checks.append(check("doc_get_by_id", status == 200 and body["productName"] == "Verify spinach", f"GET returned {status}"))
    status, body = request("PUT", f"/api/doc/notices/{notice_id}", {"status": "closed"})
    checks.append(check("doc_update", status == 200 and body["status"] == "closed" and body["updatedAt"] != body["createdAt"], f"PUT returned {status}"))
    status, _ = request("POST", "/api/doc/notices", {"noticeCategory": "recall", "noticeDate": "2026-10-18T09:00:00Z"})
    status2, _ = request("POST", "/api/doc/notices", dict(notice, noticeCategory="rumor"))
    status3, _ = request("POST", "/api/doc/notices", dict(notice, noticeDate="next week"))
    checks.append(check("doc_validation_422", (status, status2, status3) == (422, 422, 422), f"missing field {status}, bad enum {status2}, bad date {status3}"))
    status, _ = request("GET", "/api/doc/notices/not-an-id")
    status2, _ = request("GET", "/api/doc/notices/000000000000000000000000")
    checks.append(check("doc_bad_id_400_and_unknown_404", (status, status2) == (400, 404), f"malformed id {status}, unknown id {status2}"))
    status, _ = request("DELETE", f"/api/doc/notices/{notice_id}")
    status2, _ = request("GET", f"/api/doc/notices/{notice_id}")
    checks.append(check("doc_delete_then_404", (status, status2) == (204, 404), f"DELETE {status}, GET afterwards {status2}"))
    db = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)[MONGO_DB]
    try:
        db.notices.insert_one({"productName": "x" * 120, "status": "open", "noticeCategory": "recall",
                               "noticeDate": datetime.now(timezone.utc), "createdAt": datetime.now(timezone.utc), "updatedAt": datetime.now(timezone.utc)})
        rejected = False
    except WriteError as error:
        rejected = error.code == 121
    checks.append(check("mongo_schema_validator_rejects_bad_document", rejected, "direct insert with a 120 character productName raised WriteError 121"))
    return checks


def check_chat_api():
    checks = []
    db = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)[MONGO_DB]
    try:
        body = {"user_id": TEST_USER, "session_id": "verify-session", "message": "Hi, I am Maya from Willow Glen Market. Our store code is WG-17."}
        status, reply = request("POST", "/api/chat", body)
        ok = status == 200 and isinstance(reply.get("reply"), str) and reply["reply"].strip() != ""
        checks.append(check("chat_returns_reply", ok, f"POST /api/chat returned {status}, {len(reply.get('reply', ''))} characters"))
        used = reply.get("used", {})
        ok = {"short_term", "long_term", "episodes"} <= set(used) and reply["usage"]["prompt_tokens"] > 0
        checks.append(check("chat_reports_memory_used_and_tokens", ok, f"used keys {sorted(used)}, prompt tokens {reply['usage'].get('prompt_tokens')}"))
        status, mem = request("GET", f"/api/memory/{TEST_USER}")
        ok = status == 200 and {"messages", "session_summary", "lifetime_summary", "episodes"} <= set(mem) and len(mem["messages"]) == 2
        checks.append(check("memory_endpoint", ok, f"{len(mem.get('messages', []))} messages, {len(mem.get('episodes', []))} episodes"))
        status, agg = request("GET", f"/api/aggregate/{TEST_USER}")
        ok = status == 200 and agg["daily_message_counts"] and agg["daily_message_counts"][-1]["messages"] == 2 and "recent_summaries" in agg
        checks.append(check("aggregate_endpoint", ok, f"daily counts {agg.get('daily_message_counts')}"))
        status, helped = request("POST", "/api/chat", dict(body, message="/help"))
        ok = status == 200 and all(cmd in helped["reply"] for cmd in ("/memory", "/compact", "/dream", "/help"))
        checks.append(check("help_command", ok, "reply lists the four commands"))
        status, shown = request("POST", "/api/chat", dict(body, message="/memory"))
        info = shown["used"].get("command", {})
        ok = status == 200 and isinstance(info.get("fact_lines"), int) and "AGENT.md" in shown["reply"]
        checks.append(check("memory_command", ok, f"{info.get('fact_lines')} fact lines, last consolidated {info.get('last_consolidated')}"))
    finally:
        for name in ("messages", "summaries", "episodes"):
            db[name].delete_many({"user_id": TEST_USER})
    return checks


def check_files():
    checks = []
    agent = (ROOT / "AGENT.md").read_text(encoding="utf-8")
    headings = [line for line in agent.splitlines() if line.startswith("## ")]
    rules = [line for line in agent.splitlines() if line.startswith("- ")]
    checks.append(check("agent_md_has_rules", len(rules) >= 5 and len(headings) >= 3, f"{len(rules)} instructions under {len(headings)} headings"))
    memory_lines = [l for l in (ROOT / "MEMORY.md").read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith(("#", "<!--"))]
    original = [l for l in (REPORT / "raw" / "MEMORY_original.md").read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith(("#", "<!--"))]
    checks.append(check("memory_md_consolidated_under_40_lines", len(memory_lines) < 40 < len(original), f"{len(original)} fact lines before, {len(memory_lines)} after"))
    with (REPORT / "raw" / "sweep_turns.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    per_setting = {}
    for row in rows:
        per_setting.setdefault(row["setting"], {"conversation": 0, "probe": 0})[row["kind"]] += 1
    ok = len(per_setting) == 4 and all(v == {"conversation": 30, "probe": 5} for v in per_setting.values())
    checks.append(check("sweep_has_four_settings_of_30_turns_and_5_probes", ok, f"{per_setting}"))
    summary = json.loads((REPORT / "raw" / "sweep_summary.json").read_text(encoding="utf-8"))
    ok = summary["best_setting"] in summary["settings"] and summary["worst_setting"] in summary["settings"]
    checks.append(check("cost_summary_names_best_and_worst", ok, f"best {summary.get('best_setting')}, worst {summary.get('worst_setting')}"))
    rules = json.loads((REPORT / "raw" / "agent_md_check.json").read_text(encoding="utf-8"))["rules"]
    checks.append(check("generated_function_follows_agent_md", all(rules.values()), f"{sum(rules.values())}/{len(rules)} rules"))
    missing = [name for name in REQUIRED_FILES if not (REPORT / name).exists()] + ([] if (ROOT / "memory_probes.yaml").exists() else ["memory_probes.yaml"])
    checks.append(check("report_files_present", not missing, f"missing: {missing}" if missing else "all files present"))
    return checks


def main():
    server = None
    if not server_up():
        server = subprocess.Popen([sys.executable, "app.py"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(120):
            if server_up():
                break
            time.sleep(0.5)
    try:
        checks = check_document_api() + check_chat_api() + check_files()
    finally:
        if server:
            server.terminate()
    result = {
        "homework": "DATA-260 HW6",
        "sid4": SID4,
        "commit_hash": git("rev-parse", "HEAD"),
        "tag": git("tag", "--points-at", "HEAD"),
        "model": f"{MODEL} through Ollama, embeddings all-MiniLM-L6-v2",
        "configuration": {"port_base": PORT_BASE, "prefix": "s0571", "mongo_db": MONGO_DB, "short_term_n": SHORT_TERM_N,
                          "summarize_every_user_msgs": SUMMARIZE_EVERY_USER_MSGS, "top_k_episodes": TOP_K_EPISODES},
        "seed": SEED,
        "verify_seed": VERIFY_SEED,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": all(c["passed"] for c in checks),
        "checks": checks,
    }
    destination = REPORT / "verification.json"
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {destination} (passed={result['passed']})")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
