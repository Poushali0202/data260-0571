import csv
import json
import time
from pathlib import Path

import yaml

from cached_ask import ask, cache
from notice_facts import data_version, facts_for

THRESHOLDS = [0.75, 0.80, 0.85, 0.90, 0.95]
MISS_COST = 1
FALSE_HIT_COST = 20
RAW = Path("reports/hw09/raw")
SEEDS_FILE = RAW / "sweep_seeds.json"
RUNS_FILE = RAW / "sweep_agent_runs.json"
ROWS_FILE = RAW / "sweep_rows.csv"


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


cases = yaml.safe_load(open("cache_cases.yaml", encoding="utf-8"))
seed_by_query = {s["query"]: s["id"] for s in cases["seeds"]}

# 1. seed the cache with the agent answers of the 10 seed queries
seeds = load(SEEDS_FILE)
if not seeds:
    cache.clear()
for seed in cases["seeds"]:
    if seed["id"] not in seeds:
        result = ask(seed["query"], threshold=2.0)
        seeds[seed["id"]] = result
        save(SEEDS_FILE, seeds)

# 2. agent answer for every case that can miss at some threshold (run once, reused at every threshold)
runs = load(RUNS_FILE)
for case in cases["cases"]:
    match = cache.nearest(cache.embed(case["query"]))
    if case["id"] not in runs and (case["expected"] == "miss" or match["similarity"] < max(THRESHOLDS)):
        runs[case["id"]] = ask(case["query"], threshold=2.0, store=False)
        save(RUNS_FILE, runs)

# 3. the sweep itself
rows = []
for threshold in THRESHOLDS:
    for case in cases["cases"]:
        t0 = time.perf_counter()
        match = cache.nearest(cache.embed(case["query"]))
        hit = match["similarity"] >= threshold
        if hit:
            data_version(facts_for(match["codes"]))
        lookup_ms = (time.perf_counter() - t0) * 1000
        latency = lookup_ms if hit else lookup_ms + runs[case["id"]]["agent_ms"]
        matched_seed = seed_by_query.get(match["query"])
        false_hit = hit and (case["expected"] == "miss" or matched_seed != case.get("cached_id"))
        rows.append({
            "threshold": threshold, "id": case["id"], "category": case["category"], "expected": case["expected"],
            "similarity": round(match["similarity"], 4), "matched_seed": matched_seed, "hit": hit,
            "false_hit": false_hit, "latency_ms": round(latency, 1),
        })

with open(ROWS_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print("| Threshold | Hit rate | False-hit rate | Mean latency (ms) | Total cost |")
print("|---|---|---|---|---|")
for threshold in THRESHOLDS:
    part = [r for r in rows if r["threshold"] == threshold]
    hits = sum(r["hit"] for r in part)
    false_hits = sum(r["false_hit"] for r in part)
    misses = len(part) - hits
    mean = sum(r["latency_ms"] for r in part) / len(part)
    cost = misses * MISS_COST + false_hits * FALSE_HIT_COST
    print(f"| {threshold:.2f} | {hits}/40 = {100 * hits / 40:.1f}% | {false_hits}/40 = {100 * false_hits / 40:.1f}% "
          f"| {mean:.1f} | {misses} x {MISS_COST} + {false_hits} x {FALSE_HIT_COST} = {cost} |")
