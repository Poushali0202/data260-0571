import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import AGENT_FILE, MEMORY_FILE, MEMORY_MAX_AGE_HOURS, MEMORY_MAX_LINES
from memory import aux_model, short_term_window
from src.model_client import ModelClient

consolidation_model = ModelClient(num_ctx=8192, num_predict=1200)
STAMP = re.compile(r"<!--\s*last_consolidated:\s*(\S+)\s*-->")
HELP = (
    "/memory shows AGENT.md and MEMORY.md as they are loaded into the system prompt. "
    "/compact consolidates MEMORY.md and reports the line count before and after. "
    "/dream extracts durable facts from the recent conversation and adds them to MEMORY.md. "
    "/help lists these commands."
)
GROUPS = {"type": "array", "items": {"type": "array", "items": {"type": "integer"}}}
CONSOLIDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "duplicates": GROUPS,
        "related": GROUPS,
        "conflicts": {"type": "array", "items": {"type": "object", "properties": {
            "keep": {"type": "integer"}, "drop": {"type": "integer"}, "reason": {"type": "string"}},
            "required": ["keep", "drop", "reason"]}},
    },
    "required": ["duplicates", "related", "conflicts"],
}


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


def plain(line):
    return line[2:].strip() if line.startswith("- ") else line.strip()


def words(line):
    return {w.rstrip("sd") for w in re.findall(r"[a-z0-9]+", re.sub(r"\(noted [^)]*\)", "", plain(line).lower())) if len(w) > 2}


def similar(a, b):
    wa, wb = words(a), words(b)
    return len(wa & wb) / len(wa | wb) if wa | wb else 0.0


def consolidate():
    text = load_file(MEMORY_FILE)
    before = fact_lines(text)
    numbered = "\n".join(f"{i}. {plain(line)}" for i, line in enumerate(before, start=1))
    prompt = (
        "Below are numbered facts from the memory file of a grocery recall assistant. Return JSON with:\n"
        "'duplicates': groups of numbers whose facts say the same thing;\n"
        "'related': groups of numbers whose facts are about the same person, product or topic and can be "
        "written on one line;\n"
        "'conflicts': pairs of facts that contradict each other, as objects with 'keep', 'drop' and a short "
        "'reason' (prefer the later noted date or the more specific statement).\n"
        "A number may appear in at most one group or pair. Facts that stand alone are not listed.\n\n" + numbered
    )
    response = consolidation_model.complete([{"role": "user", "content": prompt}], response_format=CONSOLIDATION_SCHEMA)
    try:
        result = json.loads(response.text)
    except json.JSONDecodeError:
        result = {"duplicates": [], "related": [], "conflicts": []}
    valid = lambda i: isinstance(i, int) and 1 <= i <= len(before)
    used = set()
    output = []

    def take(group):
        group = [i for i in group if valid(i) and i not in used]
        used.update(group)
        return group

    resolved = []
    for item in result.get("conflicts", []):
        pair = take([item.get("keep"), item.get("drop")])
        if len(pair) != 2:
            used.difference_update(pair)
            continue
        line = (f"- Resolved: kept '{plain(before[pair[0] - 1])}'; dropped '{plain(before[pair[1] - 1])}' "
                f"({item.get('reason', '').strip()})")
        resolved.append(line)
        output.append((pair[0], line))
    for group in result.get("duplicates", []):
        group = take(group)
        if not group:
            continue
        first = before[group[0] - 1]
        if all(similar(first, before[i - 1]) >= 0.5 for i in group):
            output.append((group[0], max((before[i - 1] for i in group), key=len)))
        else:
            output.append((group[0], "- " + "; ".join(plain(before[i - 1]).rstrip(".") for i in group) + "."))
    for group in result.get("related", []):
        group = take(group)
        for start in range(0, len(group), 6):
            chunk = group[start:start + 6]
            output.append((chunk[0], "- " + "; ".join(plain(before[i - 1]).rstrip(".") for i in chunk) + "."))
    unassigned = [before[i - 1] for i in range(1, len(before) + 1) if i not in used]
    output += [(i, before[i - 1]) for i in range(1, len(before) + 1) if i not in used]
    after = [line for _, line in sorted(output, key=lambda item: item[0])]
    write_memory(after, datetime.now(timezone.utc))
    return {"lines_before": len(before), "lines_after": len(after), "resolved": resolved,
            "kept_unchanged": len(unassigned), "model_groups": result}


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
