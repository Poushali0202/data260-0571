import ast
import csv
import hashlib
import json
import math
import operator
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SNAPSHOTS = Path(__file__).resolve().parent / "reports" / "hw07" / "raw" / "pricing_snapshots"
MAX_ROWS = 40
READ_ONLY = True
UNTRUSTED_LABEL = False

CSV_SQL_SCHEMA = {
    "type": "object",
    "properties": {"sql": {"type": "string", "description": "one read-only SELECT over the table trips"}},
    "required": ["sql"],
}
POLICY_RETRIEVER_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "description": "pricing page URL"},
        "query": {"type": "string", "description": "what to look for, e.g. 'month pass price ebike per minute'"},
        "k": {"type": "integer", "description": "number of passages, default 3"},
    },
    "required": ["url", "query"],
}
CALCULATOR_SCHEMA = {
    "type": "object",
    "properties": {
        "expression": {"type": "string", "description": "arithmetic with numbers, + - * / and parentheses"},
        "units": {"type": "string"},
    },
    "required": ["expression"],
}

db = None
pages = {}


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def result(data=None, error=None, source=None):
    return {"success": error is None, "data": data, "error": error, "source": source, "ts": now()}


def load_trips(path):
    global db
    db = sqlite3.connect(":memory:", check_same_thread=False)
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    columns = list(rows[0])
    db.execute(f"CREATE TABLE trips ({', '.join(columns)}, duration_min INTEGER)")
    for row in rows:
        start = datetime.fromisoformat(row["started_at"][:19])
        end = datetime.fromisoformat(row["ended_at"][:19])
        minutes = math.ceil((end - start).total_seconds() / 60)
        db.execute(f"INSERT INTO trips VALUES ({', '.join('?' * (len(columns) + 1))})", [*row.values(), minutes])
    db.commit()
    return len(rows)


def check_select(sql):
    statement = sql.strip().rstrip(";").strip()
    if ";" in statement:
        return "only one statement is allowed"
    if not re.match(r"(?is)^(select|with)\b", statement):
        return "only read-only SELECT queries are allowed"
    return None


def csv_sql(sql):
    if READ_ONLY:
        problem = check_select(sql)
        if problem:
            return result(error=problem, source="uploaded.csv")
        db.execute("PRAGMA query_only = ON")
    try:
        cursor = db.execute(sql)
        names = [c[0] for c in cursor.description] if cursor.description else []
        rows = [dict(zip(names, r)) for r in cursor.fetchall()]
        db.commit()
    except sqlite3.Error as error:
        return result(error=f"SQL error: {error}", source="uploaded.csv")
    finally:
        db.execute("PRAGMA query_only = OFF")
    return result({"rows": rows[:MAX_ROWS], "row_count": len(rows), "source": "uploaded.csv"}, source="uploaded.csv")


def fetch_page(url):
    if url not in pages:
        response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        # each plan card repeats every plan's price; the page only shows the row label and its own column
        for tag in soup.find_all(attrs={"col": True, "idx": True}):
            if tag["idx"] not in ("0", tag["col"]):
                tag.decompose()
        text = soup.get_text("\n", strip=True)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        snapshot = {"url": url, "final_url": response.url, "accessed": now(), "sha256": digest, "file": f"{digest[:12]}.txt"}
        SNAPSHOTS.mkdir(parents=True, exist_ok=True)
        (SNAPSHOTS / snapshot["file"]).write_text(text, encoding="utf-8")
        with open(SNAPSHOTS / "index.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot) + "\n")
        pages[url] = (text, snapshot)
    return pages[url]


def passages(text, size=8):
    lines = text.splitlines()
    seen, chunks = set(), []
    for start in range(0, len(lines), size // 2):
        chunk = " | ".join(lines[start:start + size])
        if chunk not in seen:
            seen.add(chunk)
            chunks.append(chunk)
    return chunks


def policy_retriever(url, query, k=3):
    try:
        text, snapshot = fetch_page(url)
    except requests.RequestException as error:
        return result(error=f"could not fetch {url}: {error}", source=url)
    words = {w[:3] for w in re.findall(r"[a-z]+", query.lower()) if len(w) > 2}
    scored = []
    for chunk in passages(text):
        tokens = {w[:3] for w in re.findall(r"[a-z]+", chunk.lower())}
        score = len(words & tokens) + 0.25 * chunk.count("$")
        scored.append({"text": chunk, "source": url, "score": score})
    top = sorted(scored, key=lambda p: -p["score"])[:k]
    if UNTRUSTED_LABEL:
        for p in top:
            p["text"] = f"<untrusted_page_text>{p['text']}</untrusted_page_text>"
    return result({"passages": top, "accessed": snapshot["accessed"], "sha256": snapshot["sha256"]}, source=url)


OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
             ast.USub: operator.neg, ast.UAdd: operator.pos}


def evaluate(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        return OPERATORS[type(node.op)](evaluate(node.left), evaluate(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
        return OPERATORS[type(node.op)](evaluate(node.operand))
    raise ValueError("unsupported expression")


def calculator(expression, units=None):
    if not re.fullmatch(r"[0-9+\-*/().\s]+", expression):
        return result(error="only numbers, + - * / and parentheses are allowed")
    try:
        value = evaluate(ast.parse(expression, mode="eval").body)
    except (SyntaxError, ValueError, ZeroDivisionError) as error:
        return result(error=f"cannot evaluate: {error}")
    data = {"value": round(value, 4)}
    if units:
        data["units"] = units
    return result(data)
