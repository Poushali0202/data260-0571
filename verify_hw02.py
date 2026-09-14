from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SID4 = "0571"
PORT_BASE = 8571
SEED = 571
VERIFY_SEED = 260571
MODEL = "qwen3:8b"
TURN_CEILING = 6
BASE_URL = f"http://localhost:{PORT_BASE}"

REQUIRED_FILES = [
    "reports/hw02/RUN_LOG.txt",
    "reports/hw02/METRICS.md",
    "reports/hw02/AI_USE.md",
    "reports/hw02/cases/schema_input.json",
    "reports/hw02/cases/adversarial_input.json",
    "reports/hw02/raw/schema_validation_runs.json",
    "reports/hw02/raw/ceiling_2_runs.json",
    "reports/hw02/raw/ceiling_10_runs.json",
    "reports/hw02/raw/adversarial_runs.json",
]


def check(name: str, passed: bool, details: str) -> dict[str, object]:
    print(f"{'PASS' if passed else 'FAIL'} {name}: {details}")
    return {"check": name, "passed": bool(passed), "details": details}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def request(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        BASE_URL + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8")
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as error:
        return error.code, None


def server_up() -> bool:
    try:
        with socket.create_connection(("localhost", PORT_BASE), timeout=1):
            return True
    except OSError:
        return False


def check_backend() -> list[dict[str, object]]:
    checks = []
    server = None
    if not server_up():
        server = subprocess.Popen(
            [sys.executable, "app.py"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        for _ in range(40):
            if server_up():
                break
            time.sleep(0.5)
    try:
        status, _ = request("GET", "/")
        checks.append(check("backend_responds_on_port_base", status == 200, f"GET / on port {PORT_BASE} returned {status}"))

        status, before = request("GET", "/api/notices")
        ok = status == 200 and isinstance(before, list)
        checks.append(check("list_notices", ok, f"GET /api/notices returned {status} with {len(before or [])} records"))
        before = before or []

        status, created = request("POST", "/api/notices", {
            "productName": "Smoke test crackers",
            "noticeSource": "Smoke test bakery",
            "submitterEmail": "smoke@example.com",
            "noticeDescription": "Temporary record created by verify_hw02.py.",
            "noticeCategory": "distribution",
        })
        ok = status == 201 and isinstance(created, dict) and isinstance(created.get("id"), int)
        checks.append(check("add_notice", ok, f"POST /api/notices returned {status}"))

        status, after = request("GET", "/api/notices")
        after = after or []
        checks.append(check("list_grows_after_add", len(after) == len(before) + 1, f"{len(before)} records before, {len(after)} after"))

        status, updated = request("PUT", "/api/notices/1", {"productName": "Smoke test product", "noticeSource": "Smoke test source"})
        ok = status == 200 and isinstance(updated, dict) and updated.get("productName") == "Smoke test product"
        checks.append(check("update_notice_1", ok, f"PUT /api/notices/1 returned {status}"))

        status, found = request("GET", "/api/notices?q=smoke%20test%20source")
        ids = [notice["id"] for notice in (found or [])]
        checks.append(check("search_by_secondary_field", status == 200 and ids == [1], f"search returned ids {ids}"))

        highest = max((notice["id"] for notice in after), default=0)
        status, _ = request("DELETE", "/api/notices/highest")
        _, remaining = request("GET", "/api/notices")
        ok = status == 204 and all(notice["id"] != highest for notice in (remaining or []))
        checks.append(check("delete_highest_id", ok, f"DELETE returned {status}, id {highest} removed"))
    finally:
        if server:
            server.terminate()
    return checks


def check_graph() -> list[dict[str, object]]:
    checks = []
    case = json.loads((ROOT / "reports/hw02/cases/schema_input.json").read_text(encoding="utf-8"))
    result: dict = {}
    with tempfile.TemporaryDirectory() as folder:
        result_file = Path(folder) / "graph_result.json"
        command = [
            sys.executable, "agent_graph.py",
            "--title", case["title"], "--content", case["content"],
            "--temperature", "0", "--max-turns", str(TURN_CEILING), "--output", str(result_file),
        ]
        try:
            completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=900)
            finished = completed.returncode == 0 and result_file.exists()
            details = f"exit code {completed.returncode}"
        except subprocess.TimeoutExpired:
            finished, details = False, "still running after 900 seconds"
        checks.append(check("graph_finishes", finished, details))
        if finished:
            result = json.loads(result_file.read_text(encoding="utf-8"))

    proposal = result.get("planner_proposal", {})
    tags = proposal.get("tags", [])
    words = proposal.get("summary", "").split()
    checks.append(check("graph_reviewer_approved", result.get("outcome") == "done", f"outcome={result.get('outcome')} turns={result.get('turn_count')}"))
    checks.append(check("exactly_three_tags", len(tags) == 3 and all(3 <= len(tag) <= 30 for tag in tags), f"tags={tags}"))
    checks.append(check("summary_at_most_25_words", 0 < len(words) <= 25, f"{len(words)} words"))
    return checks


def main() -> int:
    checks = check_backend() + check_graph()
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).exists()]
    checks.append(check("report_files_present", not missing, f"missing: {missing}" if missing else "all files present"))

    result = {
        "homework": "DATA-260 HW2",
        "sid4": SID4,
        "commit_hash": git("rev-parse", "HEAD"),
        "tag": git("tag", "--points-at", "HEAD"),
        "model": MODEL,
        "configuration": {"port_base": PORT_BASE, "smoke_test_temperature": 0.0, "turn_ceiling": TURN_CEILING},
        "seed": SEED,
        "verify_seed": VERIFY_SEED,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
    }
    destination = ROOT / "reports" / "hw02" / "verification.json"
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {destination} (passed={result['passed']})")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
