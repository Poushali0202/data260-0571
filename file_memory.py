import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import AGENT_FILE, MEMORY_FILE, MEMORY_MAX_AGE_HOURS, MEMORY_MAX_LINES
from memory import aux_model, short_term_window

STAMP = re.compile(r"<!--\s*last_consolidated:\s*(\S+)\s*-->")
HELP = (
    "/memory shows AGENT.md and MEMORY.md as they are loaded into the system prompt. "
    "/compact consolidates MEMORY.md and reports the line count before and after. "
    "/dream extracts durable facts from the recent conversation and adds them to MEMORY.md. "
    "/help lists these commands."
)


def load_file(name):
    path = Path(name)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def fact_lines(text):
    return [line for line in text.splitlines() if line.strip() and not line.strip().startswith(("#", "<!--"))]


def read_last_consolidated(text):
    match = STAMP.search(text)
    return datetime.fromisoformat(match.group(1)) if match else None


def needs_consolidation(text):
    stamp = read_last_consolidated(text)
    too_long = len(fact_lines(text)) > MEMORY_MAX_LINES
    too_old = stamp is None or datetime.now(timezone.utc) - stamp > timedelta(hours=MEMORY_MAX_AGE_HOURS)
    return too_long or too_old


def system_prompt_block():
    return (
        "Project instructions (AGENT.md):\n" + load_file(AGENT_FILE).strip()
        + "\n\nDurable facts from earlier conversations (MEMORY.md):\n" + "\n".join(fact_lines(load_file(MEMORY_FILE)))
    )


def write_memory(lines, stamp):
    header = f"# MEMORY.md\n<!-- last_consolidated: {stamp.isoformat(timespec='seconds')} -->\n\n"
    Path(MEMORY_FILE).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def bullets(text):
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(("- ", "* ")):
            lines.append("- " + line[2:].strip())
    return lines


def consolidate():
    text = load_file(MEMORY_FILE)
    before = fact_lines(text)
    prompt = (
        "You maintain the memory file of a grocery recall assistant. Rewrite the facts below.\n"
        "1. Merge lines that state the same fact into one line.\n"
        "2. When two lines contradict each other, keep ONE line that starts with 'Resolved:' and states "
        "which version you kept, which version you dropped, and why (prefer the later date or the more "
        "specific statement). Never drop a conflicting line without such a note.\n"
        "3. Keep every other fact. Do not invent facts.\n"
        "Return only bullet lines that start with '- ', at most 30 lines.\n\n" + "\n".join(before)
    )
    response = aux_model.complete([{"role": "user", "content": prompt}])
    after = bullets(response.text) or before
    write_memory(after, datetime.now(timezone.utc))
    return {"lines_before": len(before), "lines_after": len(after), "resolved": [l for l in after if "Resolved:" in l]}


def dream(user_id, session_id):
    recent = short_term_window(user_id, session_id, 20)
    if not recent:
        return []
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in recent)
    prompt = (
        "From the conversation below, list the facts worth remembering in future sessions: who the user is, "
        "their store, people, suppliers, codes and standing preferences. Skip questions and one-off chatter. "
        "Return at most 5 bullet lines starting with '- ', or the single word NONE.\n\n" + transcript
    )
    response = aux_model.complete([{"role": "user", "content": prompt}])
    text = load_file(MEMORY_FILE)
    existing = set(fact_lines(text))
    added = [line for line in bullets(response.text) if line not in existing]
    if added:
        stamp = read_last_consolidated(text) or datetime.now(timezone.utc)
        write_memory(fact_lines(text) + added, stamp)
    return added


def handle_command(message, user_id, session_id):
    command = message.strip().split()[0].lower()
    if command == "/help":
        return {"command": "help", "reply": HELP}
    if command == "/memory":
        text = load_file(MEMORY_FILE)
        stamp = read_last_consolidated(text)
        return {"command": "memory", "reply": system_prompt_block(), "fact_lines": len(fact_lines(text)),
                "last_consolidated": stamp.isoformat() if stamp else None, "needs_consolidation": needs_consolidation(text)}
    if command == "/compact":
        result = consolidate()
        reply = f"MEMORY.md consolidated: {result['lines_before']} lines before, {result['lines_after']} lines after."
        return {"command": "compact", "reply": reply, **result}
    if command == "/dream":
        added = dream(user_id, session_id)
        reply = ("Added to MEMORY.md:\n" + "\n".join(added)) if added else "Nothing new worth remembering."
        return {"command": "dream", "reply": reply, "added": added}
    return None
