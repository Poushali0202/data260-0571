import csv
import json
from pathlib import Path
from statistics import mean

import yaml

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "reports" / "hw06" / "raw"
INPUT_PRICE = 1.0 / 1_000_000
OUTPUT_PRICE = 5.0 / 1_000_000
CONVERSATIONS = 10_000
QUALITY_MARGIN = 0.5


def score_reply(reply, expected):
    text = reply.lower()
    found = sum(1 for options in expected if any(phrase.lower() in text for phrase in options))
    return found, len(expected), 1 + round(4 * found / len(expected))


def main():
    probes = {p["id"]: p for p in yaml.safe_load((ROOT / "memory_probes.yaml").read_text(encoding="utf-8"))["probes"]}
    with (RAW / "sweep_turns.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    settings = []
    for row in rows:
        if row["setting"] not in settings:
            settings.append(row["setting"])

    scores = []
    for row in rows:
        if row["kind"] != "probe":
            continue
        found, total, score = score_reply(row["reply"], probes[row["probe_id"]]["expected"])
        scores.append({"setting": row["setting"], "probe_id": row["probe_id"], "question": row["message"],
                       "reply": row["reply"], "found": found, "total": total, "score": score})
    if scores:
        with (RAW / "probe_scores.csv").open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(scores[0]))
            writer.writeheader()
            writer.writerows(scores)

    summary = {}
    for setting in settings:
        turns = [r for r in rows if r["setting"] == setting and r["kind"] == "conversation"]
        probe_rows = [s for s in scores if s["setting"] == setting]
        prompt = sum(int(r["prompt_tokens"]) for r in turns)
        completion = sum(int(r["completion_tokens"]) for r in turns)
        aux_prompt = sum(int(r["aux_prompt_tokens"]) for r in turns)
        aux_completion = sum(int(r["aux_completion_tokens"]) for r in turns)
        chat_cost = prompt * INPUT_PRICE + completion * OUTPUT_PRICE
        full_cost = chat_cost + aux_prompt * INPUT_PRICE + aux_completion * OUTPUT_PRICE
        summary[setting] = {
            "short_term_n": int(turns[0]["short_term_n"]),
            "policy": turns[0]["policy"],
            "turns": len(turns),
            "mean_prompt_tokens": round(mean(int(r["prompt_tokens"]) for r in turns), 1),
            "mean_completion_tokens": round(mean(int(r["completion_tokens"]) for r in turns), 1),
            "mean_window_tokens": round(mean(int(r["window_tokens"]) for r in turns), 1),
            "mean_summary_tokens": round(mean(int(r["summary_tokens"]) for r in turns), 1),
            "mean_episodes_tokens": round(mean(int(r["episodes_tokens"]) for r in turns), 1),
            "mean_primer_tokens": round(mean(int(r["primer_tokens"]) for r in turns), 1),
            "mean_latency_ms": round(mean(int(r["latency_ms"]) for r in turns)),
            "mean_model_latency_ms": round(mean(int(r["model_latency_ms"]) for r in turns)),
            "probe_scores": {s["probe_id"]: s["score"] for s in probe_rows},
            "mean_probe_score": round(mean(s["score"] for s in probe_rows), 2) if probe_rows else None,
            "prompt_tokens_per_conversation": prompt,
            "completion_tokens_per_conversation": completion,
            "aux_prompt_tokens_per_conversation": aux_prompt,
            "aux_completion_tokens_per_conversation": aux_completion,
            "chat_cost_per_conversation_usd": round(chat_cost, 6),
            "chat_cost_10k_usd": round(chat_cost * CONVERSATIONS, 2),
            "full_cost_per_conversation_usd": round(full_cost, 6),
            "full_cost_10k_usd": round(full_cost * CONVERSATIONS, 2),
        }

    scored = {k: v for k, v in summary.items() if v["mean_probe_score"] is not None} or summary
    best_quality = max(v["mean_probe_score"] or 0 for v in scored.values())
    candidates = [k for k, v in scored.items() if (v["mean_probe_score"] or 0) >= best_quality - QUALITY_MARGIN]
    best = min(candidates, key=lambda k: scored[k]["chat_cost_10k_usd"])
    worst = max(scored, key=lambda k: scored[k]["chat_cost_10k_usd"])
    base = summary.get("n30")
    policy = summary.get("n30_compress")
    savings = None
    if base and policy and base["mean_probe_score"] is not None and policy["mean_probe_score"] is not None:
        savings = {
            "prompt_tokens_saved_per_conversation": base["prompt_tokens_per_conversation"] - policy["prompt_tokens_per_conversation"],
            "prompt_tokens_saved_percent": round(100 * (1 - policy["prompt_tokens_per_conversation"] / base["prompt_tokens_per_conversation"]), 1),
            "probe_score_change": round(policy["mean_probe_score"] - base["mean_probe_score"], 2),
        }
    result = {"settings": summary, "best_setting": best, "worst_setting": worst,
              "selection_rule": f"worst = highest chat cost; best = lowest chat cost among settings whose mean probe score is within {QUALITY_MARGIN} of the highest score",
              "policy_vs_n30": savings, "pricing": {"input_per_million_usd": 1, "output_per_million_usd": 5, "conversations": CONVERSATIONS}}
    (RAW / "sweep_summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print("| Setting | Mean prompt tokens/turn | Mean latency (ms) | Probe quality (1-5) |")
    print("|---|---|---|---|")
    for name, v in summary.items():
        print(f"| {name} (N={v['short_term_n']}, policy {v['policy']}) | {v['mean_prompt_tokens']} | {v['mean_latency_ms']} | {v['mean_probe_score']} |")
    print()
    print("| Setting | Prompt tokens / conversation | Completion tokens / conversation | Cost / conversation | Cost for 10,000 | With extraction and summaries |")
    print("|---|---|---|---|---|---|")
    for name, v in summary.items():
        print(f"| {name} | {v['prompt_tokens_per_conversation']} | {v['completion_tokens_per_conversation']} | ${v['chat_cost_per_conversation_usd']:.4f} | ${v['chat_cost_10k_usd']:.2f} | ${v['full_cost_10k_usd']:.2f} |")
    print()
    print(f"best: {best}, worst: {worst}, policy vs n30: {savings}")
    for s in scores:
        print(f"{s['setting']} {s['probe_id']} score={s['score']} ({s['found']}/{s['total']}): {s['reply'][:160]}")


if __name__ == "__main__":
    main()
