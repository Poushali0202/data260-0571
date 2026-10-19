import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from config import (CHAT_LOG, LIFETIME_EVERY_SUMMARIES, MAX_FACTS_PER_MESSAGE, SUMMARIZE_EVERY_USER_MSGS,
                    TOP_K_EPISODES)
from mongo_db import get_collection
from src.model_client import ModelClient

PRIMER = (
    "You are the recall assistant for a grocery store chain. You help store managers handle "
    "supply and recall notices (recall, shortage, contamination, distribution). Answer only the current "
    "message in one to three short sentences. Use the summaries and facts you are given when they are "
    "relevant, do not repeat earlier advice unless asked, and say so when you do not know something."
)
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
KEEP_VERBATIM = 4
COMPRESSED_CHARS = 100

chat_model = ModelClient(num_ctx=8192, num_predict=160)
aux_model = ModelClient(num_ctx=8192, num_predict=220)
_embedder = None


def now():
    return datetime.now(timezone.utc)


def save_message(user_id, session_id, role, content):
    doc = {"user_id": user_id, "session_id": session_id, "role": role, "content": content, "created_at": now()}
    get_collection("messages").insert_one(doc)
    return doc


def short_term_window(user_id, session_id, n, exclude_id=None):
    if n <= 0:
        return []
    query = {"user_id": user_id, "session_id": session_id}
    if exclude_id is not None:
        query["_id"] = {"$ne": exclude_id}
    docs = list(get_collection("messages").find(query).sort("created_at", -1).limit(n))
    return [{"role": d["role"], "content": d["content"]} for d in reversed(docs)]


def compress_old(window):
    recent = window[-KEEP_VERBATIM:]
    older = window[:-KEEP_VERBATIM] if len(window) > KEEP_VERBATIM else []
    compressed = []
    for message in older:
        text = message["content"]
        if len(text) > COMPRESSED_CHARS:
            text = text[:COMPRESSED_CHARS].rsplit(" ", 1)[0] + " ..."
        compressed.append({"role": message["role"], "content": text})
    return compressed + recent


def latest_summary(user_id, scope, session_id=None):
    query = {"user_id": user_id, "scope": scope}
    if scope == "session":
        query["session_id"] = session_id
    doc = get_collection("summaries").find_one(query, sort=[("created_at", -1)])
    return doc["text"] if doc else None


def embed(texts):
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer(EMBED_MODEL)
    vectors = _embedder.encode(list(texts), normalize_embeddings=True)
    return [[float(x) for x in vector] for vector in vectors]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def extract_episodes(user_id, session_id, message):
    prompt = (
        "Extract up to 3 short facts about the user, their store, people, products, lots, codes or "
        "preferences from the message below. Skip questions and small talk. Return JSON of the form "
        '{"facts": [{"fact": "...", "importance": 0.0}]} where importance is between 0 and 1.\n\n'
        f"Message: {message}"
    )
    schema = {
        "type": "object",
        "properties": {"facts": {"type": "array", "items": {
            "type": "object",
            "properties": {"fact": {"type": "string"}, "importance": {"type": "number"}},
            "required": ["fact", "importance"]}}},
        "required": ["facts"],
    }
    response = aux_model.complete([{"role": "user", "content": prompt}], response_format=schema)
    try:
        facts = json.loads(response.text).get("facts", [])
    except json.JSONDecodeError:
        facts = []
    facts = [f for f in facts if isinstance(f.get("fact"), str) and f["fact"].strip()][:MAX_FACTS_PER_MESSAGE]
    if facts:
        vectors = embed([f["fact"] for f in facts])
        docs = []
        for fact, vector in zip(facts, vectors):
            importance = min(1.0, max(0.0, float(fact.get("importance", 0.5))))
            docs.append({"user_id": user_id, "session_id": session_id, "fact": fact["fact"].strip()[:200],
                         "importance": importance, "embedding": vector, "created_at": now()})
        get_collection("episodes").insert_many(docs)
    return facts, response


def retrieve_episodes(user_id, message, k=TOP_K_EPISODES):
    docs = list(get_collection("episodes").find({"user_id": user_id}, {"fact": 1, "importance": 1, "embedding": 1}))
    if not docs or k <= 0:
        return []
    query = embed([message])[0]
    scored = [(cosine(query, d["embedding"]), d) for d in docs]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [{"fact": d["fact"], "importance": d["importance"], "score": round(score, 3)} for score, d in scored[:k]]


def build_prompt(session_summary, lifetime_summary, window, episodes, message, file_memory_text=None):
    parts = {"primer": PRIMER, "summary": "", "episodes": "", "window": "", "message": message, "file_memory": ""}
    system = PRIMER
    if file_memory_text:
        parts["file_memory"] = file_memory_text
        system += "\n\n" + file_memory_text
    long_term = ""
    if lifetime_summary:
        long_term += "What you know about this user from earlier sessions:\n" + lifetime_summary
    if session_summary:
        long_term += ("\n\n" if long_term else "") + "Summary of this session so far:\n" + session_summary
    if long_term:
        parts["summary"] = long_term
        system += "\n\n" + long_term
    if episodes:
        facts = "\n".join(f"- {e['fact']}" for e in episodes)
        parts["episodes"] = "Relevant facts from memory:\n" + facts
        system += "\n\n" + parts["episodes"]
    parts["window"] = "\n".join(f"{m['role']}: {m['content']}" for m in window)
    messages = [{"role": "system", "content": system}] + window + [{"role": "user", "content": message}]
    return messages, parts


def split_tokens(parts, prompt_tokens):
    total_chars = sum(len(text) for text in parts.values()) or 1
    return {f"{name}_tokens": round(prompt_tokens * len(text) / total_chars) for name, text in parts.items()}


def user_message_count(user_id, session_id):
    return get_collection("messages").count_documents({"user_id": user_id, "session_id": session_id, "role": "user"})


def summarize_session(user_id, session_id):
    previous = latest_summary(user_id, "session", session_id)
    recent = short_term_window(user_id, session_id, 2 * SUMMARIZE_EVERY_USER_MSGS)
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in recent)
    prompt = (
        "Update the running summary of this conversation. Keep names, stores, products, lot codes, "
        "notice codes, numbers, dates and preferences. Write at most 8 short bullets and nothing else.\n\n"
        f"Previous summary:\n{previous or '(none)'}\n\nNew messages:\n{transcript}"
    )
    response = aux_model.complete([{"role": "user", "content": prompt}])
    get_collection("summaries").insert_one({"user_id": user_id, "session_id": session_id, "scope": "session",
                                            "text": response.text, "created_at": now()})
    return response


def condense_lifetime(user_id):
    previous = latest_summary(user_id, "user")
    sessions = get_collection("summaries").find({"user_id": user_id, "scope": "session"}).sort("created_at", -1).limit(5)
    joined = "\n\n".join(doc["text"] for doc in sessions)
    prompt = (
        "Condense these session summaries into one lifetime profile of the user: who they are, their store, "
        "the people and suppliers they work with, and their standing preferences. Drop one-off details. "
        "Write at most 6 short bullets and nothing else.\n\n"
        f"Previous profile:\n{previous or '(none)'}\n\nSession summaries:\n{joined}"
    )
    response = aux_model.complete([{"role": "user", "content": prompt}])
    get_collection("summaries").insert_one({"user_id": user_id, "session_id": None, "scope": "user",
                                            "text": response.text, "created_at": now()})
    return response


def maybe_summarize(user_id, session_id):
    count = user_message_count(user_id, session_id)
    responses = []
    if count and count % SUMMARIZE_EVERY_USER_MSGS == 0:
        responses.append(summarize_session(user_id, session_id))
        session_summaries = get_collection("summaries").count_documents({"user_id": user_id, "scope": "session"})
        if session_summaries % LIFETIME_EVERY_SUMMARIES == 0:
            responses.append(condense_lifetime(user_id))
    return responses


def log_turn(row):
    path = Path(CHAT_LOG)
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        if new_file:
            writer.writeheader()
        writer.writerow(row)
