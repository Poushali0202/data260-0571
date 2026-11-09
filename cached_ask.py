import asyncio
import json
import sys
import time

from kafka_common import log
from notice_facts import data_version, facts_for, notice_codes
from semantic_cache import SemanticCache
from send_question import ask_pipeline

THRESHOLD = 0.85

cache = SemanticCache()


def ms(start, end):
    return round((end - start) * 1000, 1)


def ask(question, threshold=THRESHOLD, check_version=True, store=True):
    t0 = time.perf_counter()
    embedding = cache.embed(question)
    t1 = time.perf_counter()
    match = cache.nearest(embedding)
    t2 = time.perf_counter()
    timings = {"embed_ms": ms(t0, t1), "search_ms": ms(t1, t2)}
    similarity = round(match["similarity"], 4) if match else 0.0

    if match and similarity >= threshold:
        stale = False
        if check_version:
            stale = data_version(facts_for(match["codes"])) != match["data_version"]
            timings["version_check_ms"] = ms(t2, time.perf_counter())
        if not stale:
            log("CACHE", f"HIT similarity={similarity} cached_query={match['query']!r}")
            return {
                "question": question, "answer": match["answer"], "is_cached": True, "similarity": similarity,
                "cached_query": match["query"], "latency_ms": ms(t0, time.perf_counter()), **timings,
            }
        log("CACHE", f"STALE similarity={similarity} data version changed, deleting {match['key']}")
        cache.delete(match["key"])

    log("CACHE", f"MISS best similarity={similarity}, running the HW8 agent pipeline")
    t3 = time.perf_counter()
    codes = notice_codes(question)
    facts = facts_for(codes)
    final = asyncio.run(ask_pipeline(question, facts))
    t4 = time.perf_counter()
    timings["agent_ms"] = ms(t3, t4)
    if store:
        cache.store(question, embedding, final["answer"], codes, data_version(facts))
    return {
        "question": question, "answer": final["answer"], "is_cached": False, "similarity": similarity,
        "cached_query": None, "latency_ms": ms(t0, time.perf_counter()), **timings,
    }


if __name__ == "__main__":
    print(json.dumps(ask(sys.argv[1]), indent=2))
