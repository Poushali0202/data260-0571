import csv
import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import requests

BASE_URL = "http://127.0.0.1:8571"
PAGE_SIZES = [10, 50, 200]
VERSIONS = ["naive", "fixed"]
REQUESTS_PER_CASE = 30
WARMUP = 2
RAW = Path(__file__).resolve().parent / "reports" / "hw04" / "raw"
LOGIN = {"email": "inspector@example.com", "password": "recall2026"}


def timed_get(session, version, page_size):
    start = time.perf_counter()
    response = session.get(f"{BASE_URL}/api/notices/{version}", params={"page_size": page_size})
    latency_ms = (time.perf_counter() - start) * 1000
    response.raise_for_status()
    return response.json(), latency_ms


def main():
    session = requests.Session()
    session.post(f"{BASE_URL}/auth/login", json=LOGIN).raise_for_status()

    rows = []
    for page_size in PAGE_SIZES:
        for version in VERSIONS:
            for _ in range(WARMUP):
                timed_get(session, version, page_size)
            for number in range(1, REQUESTS_PER_CASE + 1):
                body, latency_ms = timed_get(session, version, page_size)
                rows.append({
                    "page_size": page_size,
                    "version": version,
                    "request": number,
                    "sql_queries": body["sql_queries"],
                    "notices_returned": len(body["notices"]),
                    "lots_returned": sum(len(notice["lots"]) for notice in body["notices"]),
                    "latency_ms": round(latency_ms, 3),
                    "timestamp": datetime.now().isoformat(timespec="milliseconds"),
                })
            print(f"page_size={page_size} {version}: {REQUESTS_PER_CASE} requests done, sql_queries={rows[-1]['sql_queries']}")

    RAW.mkdir(parents=True, exist_ok=True)
    with (RAW / "n_plus_one_requests.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = []
    for page_size in PAGE_SIZES:
        for version in VERSIONS:
            latencies = [r["latency_ms"] for r in rows if r["page_size"] == page_size and r["version"] == version]
            queries = {r["sql_queries"] for r in rows if r["page_size"] == page_size and r["version"] == version}
            summary.append({
                "page_size": page_size,
                "version": version,
                "sql_queries_per_request": sorted(queries),
                "p50_ms": round(float(np.percentile(latencies, 50)), 2),
                "p95_ms": round(float(np.percentile(latencies, 95)), 2),
                "p99_ms": round(float(np.percentile(latencies, 99)), 2),
                "mean_ms": round(float(np.mean(latencies)), 2),
            })
    for page_size in PAGE_SIZES:
        naive, fixed = [s for s in summary if s["page_size"] == page_size]
        naive["speedup_p50"] = round(naive["p50_ms"] / fixed["p50_ms"], 2)
        naive["saved_ms_p50"] = round(naive["p50_ms"] - fixed["p50_ms"], 2)
    (RAW / "n_plus_one_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("\n| Page size | Version | SQL stmts/req | p50 (ms) | p95 (ms) | p99 (ms) |")
    print("|---|---|---|---|---|---|")
    for s in summary:
        queries = "/".join(str(q) for q in s["sql_queries_per_request"])
        print(f"| {s['page_size']} | {s['version']} | {queries} | {s['p50_ms']} | {s['p95_ms']} | {s['p99_ms']} |")
    print()
    for s in summary:
        if s["version"] == "naive":
            print(f"page_size={s['page_size']}: fixed is {s['speedup_p50']}x faster at p50 ({s['saved_ms_p50']} ms saved per request)")
    print(f"wrote {RAW / 'n_plus_one_requests.csv'} ({len(rows)} rows) and n_plus_one_summary.json")


if __name__ == "__main__":
    main()
