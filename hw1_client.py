from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.model_client import ModelClient


DEMO_TURNS = [
    "Review the HTML form for required-field accessibility issues.",
    "Review the JavaScript validation and identify one edge case.",
    "Suggest one small test for successful form submission.",
    "Explain whether the current submission counter is a closure.",
    "Give a final two-item priority list for improving this code.",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--agent-file", default="AGENT.md")
    parser.add_argument("--demo", action="store_true", help="run five sample turns")
    args = parser.parse_args()

    agent_instructions = Path(args.agent_file).read_text(encoding="utf-8")
    client = ModelClient(model=args.model, base_url=args.base_url)
    history: list[dict[str, str]] = [
        {"role": "system", "content": agent_instructions},
    ]
    prompts = DEMO_TURNS if args.demo else []
    print("Enter a message, /stats for statistics, or /quit to exit.")
    try:
        while True:
            prompt = prompts.pop(0) if prompts else input("you> ").strip()
            if not prompt:
                continue
            print(f"you> {prompt}")
            if prompt == "/stats":
                print(json.dumps(client.stats(history), indent=2))
                continue
            if prompt in {"/quit", "/exit"}:
                break
            history.append({"role": "user", "content": prompt})
            response = client.complete(history)
            history.append({"role": "assistant", "content": response.text})
            print(f"assistant> {response.text}")
            if args.demo and len(history) == 7:
                print("stats after turn 3:")
                print(json.dumps(client.stats(history), indent=2))
            if args.demo and not prompts:
                print("stats after turn 5:")
                print(json.dumps(client.stats(history), indent=2))
                break
    except (EOFError, KeyboardInterrupt):
        print()
    finally:
        client.print_cumulative_stats()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
