import csv

from cached_ask import THRESHOLD, ask, cache

QUERIES = [
    ("new", "How many units are affected by recall notice RN-004870?"),
    ("new", "Which supplier is responsible for notice RN-005000?"),
    ("exact duplicate", "How many units are affected by recall notice RN-004870?"),
    ("paraphrase", "What is the number of affected units for notice RN-004870?"),
    ("new", "What lots are listed under notice RN-004822?"),
    ("paraphrase", "Who is the supplier behind recall RN-005000?"),
    ("exact duplicate", "What lots are listed under notice RN-004822?"),
    ("new", "What should a shopper do with a recalled product they already opened?"),
    ("paraphrase", "I already opened a recalled item, what should I do with it?"),
    ("exact duplicate", "Which supplier is responsible for notice RN-005000?"),
    ("new", "Where did the notice RN-000001 come from?"),
    ("paraphrase", "What is the source of recall notice RN-000001?"),
]
OUT = "reports/hw09/raw/p2_cache_test.csv"

cache.clear()
rows = []
for number, (kind, question) in enumerate(QUERIES, 1):
    result = ask(question)
    rows.append({"n": number, "kind": kind, **result})
    print(f"#{number:<2} {kind:<15} is_cached={result['is_cached']!s:<5} similarity={result['similarity']:.4f} "
          f"latency={result['latency_ms']:.1f} ms  {question}")
    print(f"    answer: {' '.join(result['answer'].split())[:160]}")

with open(OUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) + ["version_check_ms", "agent_ms"], extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)

hits = [r for r in rows if r["is_cached"]]
misses = [r for r in rows if not r["is_cached"]]
print(f"\nthreshold {THRESHOLD}: {len(hits)}/{len(rows)} served from cache, hit rate {100 * len(hits) / len(rows):.1f}%")
print(f"average latency cached {sum(r['latency_ms'] for r in hits) / len(hits):.1f} ms, "
      f"non-cached {sum(r['latency_ms'] for r in misses) / len(misses):.1f} ms")
