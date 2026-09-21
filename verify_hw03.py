from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "reports" / "hw03"
SID4 = "0571"
PORT_BASE = 8571
SEED = 571
VERIFY_SEED = 260571
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
IDLE_TIMEOUT = 5
BASE_URL = f"http://127.0.0.1:{PORT_BASE}"
USER = {"username": "inspector", "password": "recall2026"}

REQUIRED_FILES = [
    "RUN_LOG.txt",
    "METRICS.md",
    "AI_USE.md",
    "README.md",
    "SOURCES.md",
    "CORPUS_MANIFEST.json",
    "questions.yaml",
    "raw/retrieval_results.jsonl",
    "raw/chunk_stats.json",
    "raw/warmup_retrieval_results.jsonl",
]


def check(name: str, passed: bool, details: str) -> dict[str, object]:
    print(f"{'PASS' if passed else 'FAIL'} {name}: {details}")
    return {"check": name, "passed": bool(passed), "details": details}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


opener = urllib.request.build_opener(NoRedirect)


def request(method: str, path: str, form: dict | None = None, cookie: str | None = None):
    data = urllib.parse.urlencode(form).encode("utf-8") if form else None
    req = urllib.request.Request(BASE_URL + path, data=data, method=method)
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with opener.open(req, timeout=10) as response:
            return response.status, response.headers, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read().decode("utf-8")


def server_up() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", PORT_BASE), timeout=1):
            return True
    except OSError:
        return False


def check_auth() -> list[dict[str, object]]:
    checks = []
    if server_up():
        return [check("port_free_for_test_server", False, f"stop the app on port {PORT_BASE} and run again")]
    env = {**os.environ, "IDLE_TIMEOUT_SECONDS": str(IDLE_TIMEOUT)}
    server = subprocess.Popen(
        [sys.executable, "app.py"], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    for _ in range(40):
        if server_up():
            break
        time.sleep(0.5)
    try:
        status, _, body = request("GET", "/")
        checks.append(check("home_page_shows_login_link", status == 200 and 'href="/login"' in body, f"GET / returned {status}"))

        status, _, body = request("POST", "/login", {"username": "inspector", "password": "wrong"})
        ok = status == 401 and "alert-danger" in body and "Invalid username or password" in body
        checks.append(check("invalid_login_shows_alert", ok, f"POST /login with a wrong password returned {status}"))

        status, headers, _ = request("POST", "/login", USER)
        set_cookie = headers.get("Set-Cookie") or ""
        ok = status == 302 and headers.get("Location") == "/dashboard"
        checks.append(check("login_redirects_to_dashboard", ok, f"returned {status}, Location={headers.get('Location')}"))
        flags = ["httponly", "samesite=lax", "secure"]
        ok = all(flag in set_cookie.lower() for flag in flags)
        checks.append(check("session_cookie_has_three_flags", ok, set_cookie.split(";", 1)[-1].strip()))
        cookie = set_cookie.split(";")[0]

        status, _, body = request("GET", "/dashboard", cookie=cookie)
        checks.append(check("dashboard_with_session", status == 200 and "Welcome, Poushali" in body, f"returned {status}"))
        status, headers, _ = request("GET", "/dashboard")
        ok = status == 302 and headers.get("Location") == "/login"
        checks.append(check("dashboard_without_session_redirects", ok, f"returned {status}, Location={headers.get('Location')}"))

        status, headers, _ = request("GET", "/logout", cookie=cookie)
        checks.append(check("logout_redirects_home", status == 302 and headers.get("Location") == "/", f"returned {status}"))
        status, headers, _ = request("GET", "/dashboard", cookie=cookie)
        ok = status == 302 and headers.get("Location") == "/login"
        checks.append(check("logged_out_cookie_rejected", ok, f"old cookie on /dashboard returned {status}"))

        _, headers, _ = request("POST", "/login", USER)
        cookie = (headers.get("Set-Cookie") or "").split(";")[0]
        time.sleep(IDLE_TIMEOUT + 1)
        status, headers, _ = request("GET", "/dashboard", cookie=cookie)
        ok = status == 302 and headers.get("Location") == "/login"
        checks.append(check("idle_session_expires", ok, f"after {IDLE_TIMEOUT + 1} s idle /dashboard returned {status}"))
    finally:
        server.terminate()
    return checks


def check_retrieval() -> list[dict[str, object]]:
    checks = []
    manifest = json.loads((REPORT / "CORPUS_MANIFEST.json").read_text(encoding="utf-8"))
    total = sum(item["bytes"] for item in manifest)
    checks.append(check("corpus_at_least_200_kb", total >= 200_000, f"{len(manifest)} files, {total} bytes"))
    mismatched = [
        item["file"] for item in manifest
        if hashlib.sha256((ROOT / "corpus" / item["file"]).read_bytes()).hexdigest() != item["sha256"]
    ]
    checks.append(check("corpus_hashes_match_manifest", not mismatched, f"mismatched: {mismatched}" if mismatched else "all hashes match"))

    questions = yaml.safe_load((REPORT / "questions.yaml").read_text(encoding="utf-8"))["questions"]
    complete = all(q.get("expected_answer") and q.get("expected_source") for q in questions)
    checks.append(check("five_questions_with_expected_answers", len(questions) == 5 and complete, f"{len(questions)} questions"))
    single = [q["id"] for q in questions if q.get("single_source")]
    checks.append(check("at_least_two_single_source_questions", len(single) >= 2, f"single-source: {single}"))

    rows = [json.loads(line) for line in (REPORT / "raw" / "retrieval_results.jsonl").read_text(encoding="utf-8").splitlines()]
    expected = {"token", "semantic", "sentence_window"}
    ids = {q["id"] for q in questions}
    covered = all({row["question_id"] for row in rows if row["technique"] == name} == ids for name in expected)
    checks.append(check("raw_results_cover_three_techniques", {row["technique"] for row in rows} == expected and covered, f"{len(rows)} rows"))
    fields = ["store_score", "cosine_sim", "chunk_len", "latency_ms", "preview"]
    checks.append(check("raw_rows_have_required_fields", all(all(f in row for f in fields) for row in rows), ", ".join(fields)))

    summary = subprocess.run([sys.executable, "summarize_retrieval.py"], cwd=ROOT, capture_output=True, text=True)
    ok = summary.returncode == 0 and "| token |" in summary.stdout and "| sentence_window |" in summary.stdout
    checks.append(check("summary_script_recomputes_tables", ok, f"exit code {summary.returncode}"))
    return checks


def main() -> int:
    checks = check_auth() + check_retrieval()
    missing = [name for name in REQUIRED_FILES if not (REPORT / name).exists()]
    checks.append(check("report_files_present", not missing, f"missing: {missing}" if missing else "all files present"))

    result = {
        "homework": "DATA-260 HW3",
        "sid4": SID4,
        "commit_hash": git("rev-parse", "HEAD"),
        "tag": git("tag", "--points-at", "HEAD"),
        "embedding_model": EMBED_MODEL,
        "configuration": {"port_base": PORT_BASE, "idle_timeout_seconds_in_test": IDLE_TIMEOUT, "top_k": 5},
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
