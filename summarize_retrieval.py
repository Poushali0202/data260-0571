import argparse
import json
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parent / "reports" / "hw03" / "raw"


def markdown(frame):
    lines = ["| " + " | ".join(frame.columns) + " |", "|" + "---|" * len(frame.columns)]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="", help="use warmup_ for the Tiny Shakespeare run")
    args = parser.parse_args()
    rows = pd.read_json(RAW / f"{args.prefix}retrieval_results.jsonl", lines=True)
    stats = json.loads((RAW / f"{args.prefix}chunk_stats.json").read_text(encoding="utf-8"))
    k = int(rows["rank"].max())

    summary = []
    for technique, group in rows.groupby("technique", sort=False):
        per_question = group.groupby("question_id", sort=False)
        summary.append({
            "Technique": technique,
            "Chunks": stats[technique]["chunks"],
            "Avg chunk length (chars)": stats[technique]["avg_chunk_len"],
            "Top-1 cosine": round(per_question["cosine_sim"].max().mean(), 4),
            f"Mean@{k} cosine": round(group["cosine_sim"].mean(), 4),
            f"Recall@{k}": round(per_question["contains_answer"].any().mean(), 2),
            "Mean retrieval latency (ms)": round(per_question["latency_ms"].first().mean(), 2),
        })
    print(f"## Summary over {rows['question_id'].nunique()} questions, k={k}\n")
    print(markdown(pd.DataFrame(summary)))

    detail = []
    for (question_id, technique), group in rows.groupby(["question_id", "technique"], sort=False):
        hits = group[group["contains_answer"]]
        detail.append({
            "Question": question_id,
            "Technique": technique,
            "Top-1 cosine": round(group["cosine_sim"].max(), 4),
            f"Mean@{k}": round(group["cosine_sim"].mean(), 4),
            "Answer found at rank": int(hits["rank"].min()) if len(hits) else "none",
            "Expected source in top-k": "yes" if group["source_hit"].any() else "no",
            "Latency (ms)": round(group["latency_ms"].iloc[0], 2),
        })
    print("\n## Per question\n")
    print(markdown(pd.DataFrame(detail)))

    misses = rows[(rows["rank"] == 1) & (~rows["contains_answer"])].round({"cosine_sim": 4})
    print("\n## Rank-1 chunks that do not contain the answer\n")
    print(markdown(misses[["question_id", "technique", "cosine_sim", "source_file", "preview"]]))


if __name__ == "__main__":
    main()
