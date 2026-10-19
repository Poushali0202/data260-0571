import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

import memory
from config import MEMORY_FILE, SHORT_TERM_N
from doc_schemas import ChatIn, ChatOut
from file_memory import consolidate, handle_command, load_file, needs_consolidation, system_prompt_block
from mongo_db import get_collection

router = APIRouter(prefix="/api")


def clean(doc):
    doc.pop("_id", None)
    doc.pop("embedding", None)
    return doc


@router.post("/chat", response_model=ChatOut)
def chat(data: ChatIn):
    started = time.perf_counter()
    session_id = data.session_id or uuid.uuid4().hex[:12]
    if data.message.startswith("/"):
        result = handle_command(data.message, data.user_id, session_id)
        if result:
            return ChatOut(reply=result.pop("reply"), session_id=session_id, used={"command": result}, usage={})

    n = SHORT_TERM_N if data.short_term_n is None else data.short_term_n
    user_doc = memory.save_message(data.user_id, session_id, "user", data.message)
    window = memory.short_term_window(data.user_id, session_id, n, exclude_id=user_doc["_id"])
    if data.policy == "compress_old":
        window = memory.compress_old(window)
    session_summary = memory.latest_summary(data.user_id, "session", session_id)
    lifetime_summary = memory.latest_summary(data.user_id, "user")
    episodes = memory.retrieve_episodes(data.user_id, data.message)

    file_text = None
    consolidated = False
    if data.file_memory:
        if needs_consolidation(load_file(MEMORY_FILE)):
            consolidate()
            consolidated = True
        file_text = system_prompt_block()

    messages, parts = memory.build_prompt(session_summary, lifetime_summary, window, episodes, data.message, file_text)
    model_started = time.perf_counter()
    response = memory.chat_model.complete(messages)
    model_ms = round((time.perf_counter() - model_started) * 1000)
    memory.save_message(data.user_id, session_id, "assistant", response.text)

    facts, extraction = memory.extract_episodes(data.user_id, session_id, data.message)
    aux_calls = [extraction] + memory.maybe_summarize(data.user_id, session_id)

    usage = {
        "prompt_tokens": response.input_tokens,
        "completion_tokens": response.output_tokens,
        **memory.split_tokens(parts, response.input_tokens),
        "model_latency_ms": model_ms,
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "aux_prompt_tokens": sum(r.input_tokens for r in aux_calls),
        "aux_completion_tokens": sum(r.output_tokens for r in aux_calls),
        "summaries_written": len(aux_calls) - 1,
    }
    memory.log_turn({"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "user_id": data.user_id,
                     "session_id": session_id, "short_term_n": n, "policy": data.policy,
                     "file_memory": data.file_memory, **usage})
    used = {
        "short_term": {"count": len(window), "messages": window},
        "long_term": {"session_summary": session_summary, "lifetime_summary": lifetime_summary},
        "episodes": episodes,
        "new_facts": facts,
        "file_memory": {"included": data.file_memory, "consolidated": consolidated},
    }
    return ChatOut(reply=response.text, session_id=session_id, used=used, usage=usage)


@router.get("/memory/{user_id}")
def get_memory(user_id: str):
    messages = list(get_collection("messages").find({"user_id": user_id}).sort("created_at", -1).limit(16))
    session = get_collection("summaries").find_one({"user_id": user_id, "scope": "session"}, sort=[("created_at", -1)])
    lifetime = get_collection("summaries").find_one({"user_id": user_id, "scope": "user"}, sort=[("created_at", -1)])
    episodes = list(get_collection("episodes").find({"user_id": user_id}).sort("created_at", -1).limit(20))
    return {
        "user_id": user_id,
        "messages": [clean(m) for m in reversed(messages)],
        "session_summary": clean(session) if session else None,
        "lifetime_summary": clean(lifetime) if lifetime else None,
        "episodes": [clean(e) for e in episodes],
    }


@router.get("/aggregate/{user_id}")
def aggregate(user_id: str):
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "messages": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    daily = [{"date": row["_id"], "messages": row["messages"]} for row in get_collection("messages").aggregate(pipeline)]
    summaries = get_collection("summaries").find({"user_id": user_id}).sort("created_at", -1).limit(5)
    return {"user_id": user_id, "daily_message_counts": daily, "recent_summaries": [clean(s) for s in summaries]}
