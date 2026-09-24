from __future__ import annotations

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

from sqlalchemy.engine import make_url

from database import DATABASE_URL, db_session_basede26
from models import UserSession

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "reports" / "hw04"
SID4 = "0571"
PORT_BASE = 8571
SEED = 571
VERIFY_SEED = 260571
LLM_MODEL = "qwen3:8b"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BASE_URL = f"http://127.0.0.1:{PORT_BASE}"
LOGIN = {"email": "inspector@example.com", "password": "recall2026"}

REQUIRED_FILES = [
    "RUN_LOG.txt",
    "METRICS.md",
    "AI_USE.md",
    "README.md",
    "raw/n_plus_one_requests.csv",
    "raw/n_plus_one_summary.json",
    "raw/rag_chunks.jsonl",
    "raw/rag_retrievals.txt",
    "raw/rag_results.jsonl",
    "raw/rag_comparison.md",
    "raw/rag_k_sweep.md",
    "raw/rag_evaluation.md",
]


def check(name: str, passed: bool, details: str) -> dict[str, object]:
    print(f"{'PASS' if passed else 'FAIL'} {name}: {details}")
    return {"check": name, "passed": bool(passed), "details": details}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def request(method: str, path: str, body: dict | None = None, cookie: str | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, method=method, headers={"Content-Type": "application/json"})
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            text = response.read().decode("utf-8")
            return response.status, response.headers, json.loads(text) if text else None
    except urllib.error.HTTPError as error:
        text = error.read().decode("utf-8")
        return error.code, error.headers, json.loads(text) if text else None


def server_up() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", PORT_BASE), timeout=1):
            return True
    except OSError:
        return False


def check_app() -> list[dict[str, object]]:
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
        checks.append(check("backend_responds_on_port_base", status == 200 and body == {"status": "ok"}, f"GET /health on port {PORT_BASE} returned {status}"))

        status, _, _ = request("GET", "/api/notices")
        checks.append(check("list_requires_login", status == 401, f"GET /api/notices without a cookie returned {status}"))
        status, _, _ = request("POST", "/auth/login", {"email": LOGIN["email"], "password": "wrong"})
        checks.append(check("wrong_password_rejected", status == 401, f"POST /auth/login with a wrong password returned {status}"))

        status, headers, body = request("POST", "/auth/login", LOGIN)
        set_cookie = headers.get("Set-Cookie") or ""
        cookie = set_cookie.split(";")[0]
        token = cookie.split("=", 1)[1] if "=" in cookie else ""
        ok = status == 200 and cookie.startswith("session_id=") and "httponly" in set_cookie.lower()
        checks.append(check("login_sets_httponly_cookie", ok, set_cookie.split(";", 1)[-1].strip()))
        opaque = len(token) == 64 and all(c in "0123456789abcdef" for c in token) and LOGIN["email"] not in token
        checks.append(check("cookie_is_opaque_token", opaque, f"{len(token)} hex characters, no user data"))
        db = db_session_basede26()
        row = db.get(UserSession, token)
        db.close()
        ok = row is not None and row.user_id > 0 and row.expires_at > row.created_at
        checks.append(check("session_token_stored_in_mysql", ok, "sessions row found with user_id and expiry" if row else "no sessions row"))
        status, _, body = request("GET", "/auth/me", cookie=cookie)
        checks.append(check("me_returns_logged_in_user", status == 200 and body.get("email") == LOGIN["email"], f"GET /auth/me returned {status}"))

        status, _, created = request("POST", "/api/notices", {"productName": "Verify test product", "noticeSource": "verify_hw04"}, cookie=cookie)
        checks.append(check("create_record", status == 201 and isinstance(created.get("id"), int), f"POST returned {status}, id={created.get('id') if created else None}"))
        notice_id = created["id"]
        status, _, body = request("GET", f"/api/notices/{notice_id}", cookie=cookie)
        checks.append(check("read_record_by_id", status == 200 and body["productName"] == "Verify test product", f"GET /api/notices/{notice_id} returned {status}"))
        payload = {"productName": "Verify test product updated", "noticeSource": "verify_hw04"}
        status, _, body = request("PUT", f"/api/notices/{notice_id}", payload, cookie=cookie)
        checks.append(check("update_record", status == 200 and body["productName"] == payload["productName"], f"PUT returned {status}"))
        status, _, body = request("GET", "/api/notices", cookie=cookie)
        checks.append(check("list_returns_records", status == 200 and any(n["id"] == notice_id for n in body), f"{len(body)} records, test record present"))

        status, _, naive = request("GET", "/api/notices/naive?page_size=10", cookie=cookie)
        status2, _, fixed = request("GET", "/api/notices/fixed?page_size=10", cookie=cookie)
        ok = status == 200 and status2 == 200 and len(naive["notices"]) == 10 and len(fixed["notices"]) == 10
        ok = ok and all("lots" in n for n in naive["notices"] + fixed["notices"])
        checks.append(check("naive_and_fixed_lists_return_data", ok, "10 notices with a lots field from each version"))
        checks.append(check("naive_runs_n_plus_one_queries", naive["sql_queries"] == 11, f"naive sql_queries={naive['sql_queries']} for page_size 10"))
        checks.append(check("fixed_runs_fewer_queries", fixed["sql_queries"] < naive["sql_queries"], f"fixed sql_queries={fixed['sql_queries']}"))
        checks.append(check("both_versions_return_same_records", naive["notices"] == fixed["notices"], "same ids, fields and lots"))

        status, _, _ = request("DELETE", f"/api/notices/{notice_id}", cookie=cookie)
        status2, _, _ = request("GET", f"/api/notices/{notice_id}", cookie=cookie)
        checks.append(check("delete_record", status == 204 and status2 == 404, f"DELETE returned {status}, GET afterwards returned {status2}"))
        status, _, _ = request("POST", "/auth/logout", cookie=cookie)
        status2, _, _ = request("GET", "/auth/me", cookie=cookie)
        checks.append(check("logout_invalidates_session", status == 200 and status2 == 401, f"logout returned {status}, old cookie on /auth/me returned {status2}"))
    finally:
        if server:
            server.terminate()
    return checks


def check_results() -> list[dict[str, object]]:
    checks = []
    with (REPORT / "raw" / "n_plus_one_requests.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    combos = {(r["page_size"], r["version"]) for r in rows}
    counts = {combo: sum(1 for r in rows if (r["page_size"], r["version"]) == combo) for combo in combos}
    ok = len(rows) == 180 and len(combos) == 6 and all(n == 30 for n in counts.values())
    checks.append(check("raw_has_180_measured_requests", ok, f"{len(rows)} rows over {len(combos)} page size and version pairs"))
    expected = {("10", "naive"): 11, ("50", "naive"): 51, ("200", "naive"): 201}
    ok = all(int(r["sql_queries"]) == expected.get((r["page_size"], r["version"]), 2) for r in rows)
    checks.append(check("raw_query_counts_match_n_plus_one", ok, "naive = page_size + 1, fixed = 2 on every row"))

    summary = json.loads((REPORT / "raw" / "n_plus_one_summary.json").read_text(encoding="utf-8"))
    slower = []
    for page_size in (10, 50, 200):
        naive = next(s for s in summary if s["page_size"] == page_size and s["version"] == "naive")
        fixed = next(s for s in summary if s["page_size"] == page_size and s["version"] == "fixed")
        slower.append(naive["p50_ms"] > fixed["p50_ms"])
    checks.append(check("fixed_faster_at_every_page_size", all(slower), f"naive p50 > fixed p50 for page sizes 10, 50, 200: {slower}"))

    rag = [json.loads(line) for line in (REPORT / "raw" / "rag_results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    compare = [r for r in rag if r["stage"] == "compare"]
    sweep = [r for r in rag if r["stage"] == "sweep"]
    ok = len(compare) == 18 and {(r["question_id"], r["config"]) for r in compare} == {(f"Q{i}", c) for i in range(1, 7) for c in "ABC"}
    checks.append(check("rag_six_questions_three_configs", ok, f"{len(compare)} comparison rows"))
    checks.append(check("rag_k_sweep_present", sorted(r["k"] for r in sweep) == [1, 3, 5], f"sweep k values {sorted(r['k'] for r in sweep)}"))
    refused = [r["refused"] for r in compare if r["config"] == "C" and r["question_id"] in ("Q5", "Q6")]
    checks.append(check("rag_refuses_q5_q6_in_context_config", len(refused) == 2 and all(refused), f"Q5 and Q6 refused: {refused}"))
    return checks


def main() -> int:
    checks = check_app() + check_results()
    missing = [name for name in REQUIRED_FILES if not (REPORT / name).exists()]
    checks.append(check("report_files_present", not missing, f"missing: {missing}" if missing else "all files present"))

    result = {
        "homework": "DATA-260 HW4",
        "sid4": SID4,
        "commit_hash": git("rev-parse", "HEAD"),
        "tag": git("tag", "--points-at", "HEAD"),
        "model": {"llm": f"{LLM_MODEL} through Ollama", "embeddings": EMBED_MODEL},
        "configuration": {
            "port_base": PORT_BASE,
            "database_url": make_url(DATABASE_URL).render_as_string(hide_password=True),
            "chunk_size": 500,
            "chunk_overlap": 50,
            "top_k": 3,
        },
        "seed": SEED,
        "verify_seed": VERIFY_SEED,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
    }
    destination = REPORT / "verification.json"
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {destination} (passed={result['passed']})")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
