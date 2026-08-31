"""Planner -> Reviewer -> Finalizer demo for the assigned grocery-notice domain.

The domain is supplied as input; no domain vocabulary is embedded in the agent
logic. Ollama is used for every normal run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from src.model_client import ModelClient

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "into", "is", "it", "of", "on", "or", "that", "the", "this",
    "to", "was", "were", "with", "will", "your", "our", "their", "about",
}


def strip_code_and_md(value: Any) -> str:
    """Remove common formatting artifacts from an LLM response."""
    text = str(value or "")
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "").replace("`", "")
    return " ".join(text.split()).strip()


def extract_json_block(text: str) -> str:
    """Extract the first balanced JSON object from possibly noisy text."""
    cleaned = strip_code_and_md(text)
    start = cleaned.find("{")
    if start < 0:
        return cleaned
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(cleaned)):
        char = cleaned[index]
        if char == '"' and not escaped:
            in_string = not in_string
        escaped = char == "\\" and not escaped
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return cleaned[start : index + 1]
    return cleaned[start:]


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'-]+", text.lower())


def phrase_candidates(title: str, content: str, max_count: int = 12) -> list[str]:
    """Rank multi-word phrases and useful unigrams found in the input only."""
    source_words = [word for word in words(f"{title} {content}") if word not in STOP_WORDS]
    candidates: list[tuple[str, int, int]] = []
    for size in (3, 2):
        for index in range(len(source_words) - size + 1):
            phrase_words = source_words[index : index + size]
            phrase = " ".join(phrase_words)
            candidates.append((phrase, len(phrase_words), index))
    counts = Counter(phrase for phrase, _, _ in candidates)
    ranked = sorted(
        counts,
        key=lambda phrase: (-counts[phrase], -len(phrase.split()), phrase),
    )
    ranked += [word for word in source_words if word not in ranked]
    result: list[str] = []
    for candidate in ranked:
        if candidate not in result:
            result.append(candidate)
        if len(result) >= max_count:
            break
    return result or ["important topic", "reported details", "next steps"]


def fallback_summary(title: str, content: str) -> str:
    """Create a concise input-derived summary if a model response is malformed."""
    sentence = " ".join(f"{title} {content}".split())
    summary_words = sentence.rstrip(".!?").split()[:25]
    return (" ".join(summary_words).rstrip(".!?") + ".") if summary_words else "A submitted item requires review."


def normalize_tags(value: Any, title: str, content: str) -> list[str]:
    candidates = phrase_candidates(title, content)
    requested = value if isinstance(value, list) else []
    tags: list[str] = []
    for tag in requested + candidates:
        cleaned = strip_code_and_md(tag).lower().strip(" ,.;:")
        if cleaned and cleaned not in tags and cleaned not in STOP_WORDS:
            tags.append(cleaned)
        if len(tags) == 3:
            break
    while len(tags) < 3:
        tags.append(candidates[len(tags)] if len(candidates) > len(tags) else f"topic {len(tags) + 1}")
    return tags[:3]


def coerce_reply(raw: Any, title: str, content: str) -> dict[str, Any]:
    """Coerce arbitrary output to the assignment's strict JSON shape."""
    obj = raw if isinstance(raw, dict) else {}
    data = obj.get("data") if isinstance(obj.get("data"), dict) else obj
    summary = strip_code_and_md(data.get("summary", "")) if isinstance(data, dict) else ""
    summary_words = summary.rstrip(".!?").split()
    if not summary_words:
        summary = fallback_summary(title, content)
    else:
        summary = " ".join(summary_words[:25]).rstrip(".!?") + "."
    message = strip_code_and_md(obj.get("message", "")) or "Proposal reviewed."
    return {
        "thought": strip_code_and_md(obj.get("thought", "")),
        "message": " ".join(message.split()[:60]),
        "data": {
            "tags": normalize_tags(data.get("tags") if isinstance(data, dict) else [], title, content),
            "summary": summary,
            "issues": data.get("issues", []) if isinstance(data, dict) and isinstance(data.get("issues", []), list) else [],
        },
    }


def parse_reply(text: str, title: str, content: str) -> dict[str, Any]:
    try:
        raw = json.loads(extract_json_block(text))
    except (json.JSONDecodeError, TypeError):
        raw = {}
    return coerce_reply(raw, title, content)


def ask_agent(
    client: ModelClient,
    role: str,
    instruction: str,
    title: str,
    content: str,
    transcript: list[dict[str, str]],
    temperature: float,
) -> tuple[dict[str, Any], int]:
    history = "\n".join(f'{entry["role"]}: {entry["content"]}' for entry in transcript) or "(empty)"
    response = client.complete(
        [
            {
                "role": "system",
                "content": (
                    f"You are the {role} agent. {instruction} "
                    "Return ONLY one JSON object with thought, message, and data keys. "
                    "data.tags must have exactly three topical strings; data.summary must be "
                    "at most 25 words and end with a period; data.issues must be an array."
                ),
            },
            {
                "role": "user",
                "content": (
                    f'Title: {title}\nContent: {content}\n'
                    f"Prior Planner/Reviewer transcript:\n{history}"
                ),
            },
        ],
        temperature=temperature,
        response_format="json",
    )
    result = parse_reply(response.text, title, content)
    return result, response.total_tokens


def run_pipeline(
    title: str,
    content: str,
    email: str,
    model: str = "qwen3:8b",
    base_url: str = "http://localhost:11434",
    temperature: float = 0.0,
) -> dict[str, Any]:
    client = ModelClient(model=model, base_url=base_url, temperature=temperature)
    transcript: list[dict[str, str]] = []
    stages = [
        ("Planner", "Propose three distinct, topical tags and a one-sentence summary."),
        ("Reviewer", "Check topical relevance, remove generic tags, and flag or repair issues."),
        ("Finalizer", "Use the transcript to publish the strongest three tags and final summary."),
    ]
    stage_results: dict[str, dict[str, Any]] = {}
    latencies: dict[str, int] = {}
    for role, instruction in stages:
        started = time.perf_counter()
        result, _ = ask_agent(client, role, instruction, title, content, transcript, temperature)
        latencies[role] = round((time.perf_counter() - started) * 1000)
        stage_results[role] = result
        transcript.append({"role": role, "content": json.dumps(result["data"], ensure_ascii=False)})
    return {
        "title": title,
        "email": email,
        "content": content,
        "agents": {"transcript": transcript, "stages": stage_results, "final": stage_results["Finalizer"]["data"]},
        "latencies_ms": latencies,
        "submissionDate": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument("--email", default="poushali@example.com")
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        result = run_pipeline(
            args.title, args.content, args.email, args.model, args.base_url, args.temperature
        )
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 2

    for role in ("Planner", "Reviewer"):
        stage = result["agents"]["stages"][role]
        print(f"\n--- {role} ({result['latencies_ms'][role]} ms) ---")
        print(json.dumps(stage, indent=2, ensure_ascii=False))
    print("\n--- Finalized Output ---")
    print(json.dumps(result["agents"]["stages"]["Finalizer"], indent=2, ensure_ascii=False))
    print("\n--- Publish Output JSON ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
