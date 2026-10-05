import asyncio
import csv
import json
import random
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "reports" / "hw05"
SID4 = "0571"
PORT_BASE = 8571
SEED = 571
VERIFY_SEED = 260571
MODEL = "qwen3:8b"
BASE_URL = f"http://127.0.0.1:{PORT_BASE}"
LOGIN = {"email": "inspector@example.com", "password": "recall2026"}
REQUIRED_FILES = ["RUN_LOG.txt", "METRICS.md", "AI_USE.md", "REFLECTION.md", "raw/fault_injection_calls.csv",
                  "raw/fault_injection_summary.json", "raw/agent_runs.jsonl", "raw/inspector/meals_tools_list.json"]


def check(name, passed, details):
    print(f"{'PASS' if passed else 'FAIL'} {name}: {details}")
    return {"check": name, "passed": bool(passed), "details": details}


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def request(method, path, body=None, cookie=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, method=method, headers={"Content-Type": "application/json"})
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            text = response.read().decode()
            return response.status, response.headers, json.loads(text) if text else None
    except urllib.error.HTTPError as error:
        text = error.read().decode()
        return error.code, error.headers, json.loads(text) if text else None


def server_up():
    try:
        with socket.create_connection(("127.0.0.1", PORT_BASE), timeout=1):
            return True
    except OSError:
        return False


def check_app():
    checks = []
    server = None
    if not server_up():
        server = subprocess.Popen([sys.executable, "app.py"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            if server_up():
                break
            time.sleep(0.5)
    try:
        status, _, body = request("GET", "/health")
        checks.append(check("backend_responds_on_port_base", status == 200 and body == {"status": "ok"}, f"GET /health returned {status}"))
        status, headers, _ = request("POST", "/auth/login", LOGIN)
        cookie = (headers.get("Set-Cookie") or "").split(";")[0]
        checks.append(check("login_works", status == 200 and cookie.startswith("session_id="), f"login returned {status}"))

        supplier = {"name": "Verify Farms", "region": "Nevada", "email": f"verify{int(time.time())}@example.com"}
        status, _, created = request("POST", "/api/suppliers", supplier, cookie)
        checks.append(check("create_supplier", status == 201 and isinstance(created.get("id"), int), f"POST /api/suppliers returned {status}"))
        supplier_id = created["id"]
        status, _, _ = request("POST", "/api/suppliers", supplier, cookie)
        checks.append(check("duplicate_email_is_409", status == 409, f"second POST returned {status}"))
        status, _, _ = request("POST", "/api/suppliers", dict(supplier, email="bad"), cookie)
        checks.append(check("bad_email_is_422", status == 422, f"POST with email 'bad' returned {status}"))
        status, _, page = request("GET", "/api/suppliers?page=1&page_size=5", cookie=cookie)
        checks.append(check("suppliers_paginated", status == 200 and len(page) == 5, f"{len(page)} rows for page_size 5"))

        notice = {"productName": "Verify spinach", "noticeCode": "RN-999999", "noticeSource": "verify_hw05", "affectedUnits": 5, "supplierId": supplier_id}
        status, _, created = request("POST", "/api/notices", notice, cookie)
        checks.append(check("create_notice_with_fk", status == 201 and created.get("supplierId") == supplier_id, f"POST /api/notices returned {status}"))
        notice_id = created["id"]
        status, _, _ = request("POST", "/api/notices", dict(notice, noticeCode="XYZ"), cookie)
        checks.append(check("bad_notice_code_is_422", status == 422, f"POST with noticeCode XYZ returned {status}"))
        status, _, _ = request("POST", "/api/notices", dict(notice, supplierId=999999), cookie)
        checks.append(check("unknown_supplier_is_409", status == 409, f"POST with supplierId 999999 returned {status}"))
        status, _, rows = request("GET", f"/api/suppliers/{supplier_id}/notices", cookie=cookie)
        checks.append(check("relationship_query", status == 200 and [r["id"] for r in rows] == [notice_id], f"{len(rows)} notices for supplier {supplier_id}"))
        status, _, body = request("PUT", f"/api/notices/{notice_id}", dict(notice, affectedUnits=9), cookie)
        checks.append(check("update_notice", status == 200 and body["affectedUnits"] == 9, f"PUT returned {status}"))
        status, _, _ = request("DELETE", f"/api/suppliers/{supplier_id}", cookie=cookie)
        checks.append(check("supplier_with_notices_not_deletable", status == 409, f"DELETE supplier returned {status}"))
        status, _, _ = request("DELETE", f"/api/notices/{notice_id}", cookie=cookie)
        status2, _, _ = request("DELETE", f"/api/suppliers/{supplier_id}", cookie=cookie)
        status3, _, _ = request("GET", f"/api/suppliers/{supplier_id}", cookie=cookie)
        checks.append(check("delete_notice_then_supplier", status == 204 and status2 == 204 and status3 == 404, f"deletes returned {status}, {status2}; GET afterwards {status3}"))
    finally:
        if server:
            server.terminate()
    return checks


async def call_tool(script, tool, arguments):
    params = StdioServerParameters(command=sys.executable, args=[script], cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = [t.name for t in (await session.list_tools()).tools]
            result = await session.call_tool(tool, arguments)
            return tools, result.structured_content or json.loads(result.content[0].text)


def check_mcp():
    checks = []
    tools, result = asyncio.run(call_tool("domain_server.py", "notice_detail_tool", {"notice_id": 1}))
    ok = sorted(tools) == ["notice_detail_tool", "search_notices_tool", "supplier_summary_tool"]
    checks.append(check("domain_server_has_three_tools", ok, f"tools {sorted(tools)}"))
    data = result.get("result", result)
    checks.append(check("domain_server_answers_tool_call", data.get("ok") is True and data["data"]["id"] == 1 and data["error"] is None, "notice_detail_tool(1) returned ok envelope"))
    tools, result = asyncio.run(call_tool("domain_server.py", "supplier_summary_tool", {"supplier_id": 0}))
    data = result.get("result", result)
    checks.append(check("domain_server_rejects_invalid_input", data.get("ok") is False and data["data"] is None and data["error"], f"error: {data.get('error')}"))
    try:
        tools, result = asyncio.run(call_tool("meals_server.py", "search_meals_by_name", {"query": "Arrabiata", "limit": 2}))
        meals = result.get("result", result)
        ok = len(tools) == 4 and isinstance(meals, list) and {"id", "name", "area", "category", "thumb"} <= set(meals[0])
        checks.append(check("meals_server_answers_tool_call", ok, f"{len(tools)} tools, search returned {len(meals) if isinstance(meals, list) else meals}"))
    except Exception as error:
        checks.append(check("meals_server_answers_tool_call", False, f"{type(error).__name__}: {error}"))
    return checks


def check_results():
    checks = []
    with (REPORT / "raw" / "fault_injection_calls.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    per_rate = {rate: [r for r in rows if r["failure_rate"] == rate] for rate in ("0.0", "0.2", "0.5")}
    checks.append(check("fault_injection_has_150_calls", len(rows) == 150 and all(len(v) == 50 for v in per_rate.values()), f"{len(rows)} rows, {[len(v) for v in per_rate.values()]} per rate"))
    reproduced = True
    for rate, calls in per_rate.items():
        rng = random.Random(VERIFY_SEED)
        for row in calls:
            draws = ""
            for _ in range(3):
                draws += "F" if rng.random() < float(rate) else "S"
                if draws[-1] == "S":
                    break
            reproduced = reproduced and draws == row["draws"] and (row["ok"] == "True") == draws.endswith("S")
    checks.append(check("failure_sequence_reproduces_from_verify_seed", reproduced, "draw strings regenerated from random.Random(260571) match every row"))
    runs = [json.loads(line) for line in (REPORT / "raw" / "agent_runs.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    reasons = {r["stop_reason"] for r in runs}
    checks.append(check("agent_runs_logged", len(runs) >= 4 and all(r["steps_used"] <= r["max_steps"] for r in runs), f"{len(runs)} runs, stop reasons {sorted(reasons)}"))
    proc = subprocess.run([sys.executable, "test_tools.py"], cwd=ROOT, capture_output=True, text=True)
    checks.append(check("offline_tests_pass", proc.returncode == 0, proc.stdout.strip().splitlines()[-1] if proc.stdout else proc.stderr[-200:]))
    missing = [name for name in REQUIRED_FILES if not (REPORT / name).exists()]
    checks.append(check("report_files_present", not missing, f"missing: {missing}" if missing else "all files present"))
    return checks


def main():
    checks = check_app() + check_mcp() + check_results()
    result = {
        "homework": "DATA-260 HW5",
        "sid4": SID4,
        "commit_hash": git("rev-parse", "HEAD"),
        "tag": git("tag", "--points-at", "HEAD"),
        "model": f"{MODEL} through Ollama",
        "configuration": {"port_base": PORT_BASE, "prefix": "s0571", "retry": {"attempts": 3, "base_delay_s": 0.2, "max_delay_s": 1.0}, "db_timeouts_s": 5},
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
