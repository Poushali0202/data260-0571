import argparse
import json
import re
import sys
from pathlib import Path

import faiss
import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

from src.model_client import ModelClient

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "corpus"
RAW = ROOT / "reports" / "hw04" / "raw"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 3
SWEEP_KS = [1, 3, 5]
MIN_SCORE = 0.35
DUPLICATE_OVERLAP = 0.6
REFUSAL = "I cannot answer this question from the provided documents"

QUESTIONS = [
    {
        "id": "Q1",
        "kind": "answer in one chunk",
        "question": "Which Maple Leaf Foods facility was the source of the 2008 listeriosis outbreak in Canada?",
        "expected_sources": ["wikipedia_2008_canadian_listeriosis_outbreak.txt"],
        "keywords_all": ["Bartor Road"],
        "refuse": False,
    },
    {
        "id": "Q2",
        "kind": "answer needs two chunks",
        "question": "When was the Food Safety Modernization Act signed into law, and what was the original compliance date of the Food Traceability Rule?",
        "expected_sources": ["wikipedia_fda_food_safety_modernization_act.txt", "fda_fsma_food_traceability_rule.txt"],
        "keywords_all": ["January 4, 2011", "January 20, 2026"],
        "refuse": False,
    },
    {
        "id": "Q3",
        "kind": "similar information across documents",
        "question": "Which company was responsible for the 2008 to 2009 Salmonella outbreak linked to peanut butter, and what happened to the company afterwards?",
        "expected_sources": ["wikipedia_peanut_corporation_of_america.txt", "wikipedia_product_recall.txt"],
        "keywords_all": ["Peanut Corporation of America|PCA"],
        "keywords_any": ["Chapter 7", "liquidation", "bankrupt", "defunct", "ceased", "closed"],
        "refuse": False,
    },
    {
        "id": "Q4",
        "kind": "ambiguous",
        "question": "What caused the outbreak?",
        "expected_sources": [],
        "keywords_any": ["which outbreak", "more context", "depends on", "clarify", "specify", "cannot answer"],
        "refuse": False,
    },
    {
        "id": "Q5",
        "kind": "answer not in the documents",
        "question": "What is the FDA's toll-free phone number for reporting a problem with a recalled food?",
        "expected_sources": [],
        "refuse": True,
    },
    {
        "id": "Q6",
        "kind": "unrelated",
        "question": "Who won the 2018 FIFA World Cup?",
        "expected_sources": [],
        "refuse": True,
    },
]

NO_RAG_PROMPT = "You are a helpful assistant. Answer the question in at most three sentences."
BASIC_PROMPT = "Use the context to answer the question in at most three sentences."
CONTEXT_PROMPT = (
    "Answer the question using only the numbered sources below, in at most three sentences. "
    "Cite the source number after each fact, like [Source 2]. "
    f"If the sources do not contain the answer, reply exactly: {REFUSAL}"
)
SOFT_REFUSALS = [
    "cannot answer", "does not contain", "doesn't contain", "not mentioned", "does not mention", "doesn't mention",
    "no information", "not provided", "not available", "unable to", "don't have", "do not have", "not specified",
    "does not include", "doesn't include", "not include",
]


def load_chunks():
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = []
    for path in sorted(CORPUS.glob("*.txt")):
        for text in splitter.split_text(path.read_text(encoding="utf-8")):
            chunks.append({"chunk_id": len(chunks), "source": path.name, "text": text})
    return chunks


def build_index(chunks, embedder):
    vectors = embedder.encode([chunk["text"] for chunk in chunks], normalize_embeddings=True, batch_size=64)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(np.asarray(vectors, dtype="float32"))
    return index


def retrieve(question, k, chunks, index, embedder):
    vector = embedder.encode([question], normalize_embeddings=True)
    scores, ids = index.search(np.asarray(vector, dtype="float32"), k)
    return [dict(chunks[i], score=round(float(score), 4)) for score, i in zip(scores[0], ids[0])]


def show_hits(label, hits):
    lines = [f"--- {label}: top-{len(hits)} retrieved chunks ---"]
    for rank, hit in enumerate(hits, 1):
        preview = " ".join(hit["text"].split())[:140]
        lines.append(f"  {rank}. score={hit['score']:.4f}  source={hit['source']}  chunk_id={hit['chunk_id']}  {preview}")
    text = "\n".join(lines)
    print(text)
    with (RAW / "rag_retrievals.txt").open("a", encoding="utf-8") as f:
        f.write(text + "\n\n")


def words(text):
    return set(re.findall(r"\w+", text.lower()))


def overlap(a, b):
    return len(words(a) & words(b)) / len(words(a) | words(b))


def engineer_context(hits):
    kept, dropped = [], []
    for hit in hits:
        if hit["score"] < MIN_SCORE:
            dropped.append({"chunk_id": hit["chunk_id"], "reason": f"score {hit['score']:.4f} below {MIN_SCORE}"})
        elif any(overlap(hit["text"], other["text"]) > DUPLICATE_OVERLAP for other in kept):
            dropped.append({"chunk_id": hit["chunk_id"], "reason": "duplicate of a kept chunk"})
        else:
            kept.append(hit)
    return kept, dropped


def basic_prompt(question, hits):
    context = "\n\n".join(hit["text"] for hit in hits)
    return f"Context:\n{context}\n\nQuestion: {question}"


def engineered_prompt(question, kept):
    parts = [f"[Source {i}] {hit['source']}, chunk {hit['chunk_id']}\n{hit['text']}" for i, hit in enumerate(kept, 1)]
    return "Sources:\n\n" + "\n\n".join(parts) + f"\n\nQuestion: {question}"


def ask(llm, system, user):
    reply = llm.complete([{"role": "system", "content": system}, {"role": "user", "content": user}])
    return reply.text, reply.input_tokens, reply.output_tokens


def looks_refused(answer):
    lower = answer.lower()
    return REFUSAL.lower() in lower or any(phrase in lower for phrase in SOFT_REFUSALS)


def has_keyword(text, keyword):
    return any(alternative.lower() in text.lower() for alternative in keyword.split("|"))


def contains_keywords(text, q):
    all_ok = all(has_keyword(text, k) for k in q.get("keywords_all", []))
    any_ok = not q.get("keywords_any") or any(has_keyword(text, k) for k in q["keywords_any"])
    return all_ok and any_ok


def supported(answer, q, support):
    if not q.get("keywords_all"):
        return None
    used = [k for k in q["keywords_all"] + q.get("keywords_any", []) if has_keyword(answer, k)]
    text = "\n".join(hit["text"] for hit in support)
    return bool(used) and all(has_keyword(text, k) for k in used)


def evaluate(q, config, answer, retrieved, context):
    refused = looks_refused(answer)
    sources = {hit["source"] for hit in retrieved}
    cited = [int(n) for n in re.findall(r"\[Source (\d+)\]", answer)]
    support = [context[n - 1] for n in cited if 0 < n <= len(context)] or context
    row = {
        "correct_retrieval": None if not q["expected_sources"] else all(s in sources for s in q["expected_sources"]),
        "refused": refused,
        "refusal_ok": refused == q["refuse"],
        "cited_sources": cited,
    }
    if q["refuse"]:
        row["correct_answer"] = refused
        row["grounded"] = None if refused else False
    else:
        row["correct_answer"] = not refused and contains_keywords(answer, q)
        if refused or not context:
            row["grounded"] = None
        else:
            row["grounded"] = supported(answer, q, support)
    if config == "A":
        row["grounded"] = None
    if config == "C":
        row["format_ok"] = (REFUSAL in answer) if refused else bool(cited)
    else:
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", answer.strip()) if s]
        row["format_ok"] = len(sentences) <= 3
    return row


def answer_question(llm, q, config, k, chunks, index, embedder):
    retrieved, context, dropped = [], [], []
    if config == "A":
        answer, prompt_tokens, output_tokens = ask(llm, NO_RAG_PROMPT, q["question"])
    elif config == "B":
        retrieved = retrieve(q["question"], k, chunks, index, embedder)
        show_hits(f"{q['id']} config B k={k}", retrieved)
        context = retrieved
        answer, prompt_tokens, output_tokens = ask(llm, BASIC_PROMPT, basic_prompt(q["question"], context))
    else:
        retrieved = retrieve(q["question"], k, chunks, index, embedder)
        show_hits(f"{q['id']} config C k={k}", retrieved)
        context, dropped = engineer_context(retrieved)
        for item in dropped:
            print(f"  dropped chunk {item['chunk_id']}: {item['reason']}")
        print(f"  context after filtering: {[hit['chunk_id'] for hit in context]}")
        answer, prompt_tokens, output_tokens = ask(llm, CONTEXT_PROMPT, engineered_prompt(q["question"], context))
    print(f"[{q['id']} {config} k={k}] {answer}\n")
    row = {
        "question_id": q["id"],
        "kind": q["kind"],
        "question": q["question"],
        "config": config,
        "k": k,
        "retrieved": [{"chunk_id": h["chunk_id"], "source": h["source"], "score": h["score"]} for h in retrieved],
        "context_chunk_ids": [h["chunk_id"] for h in context],
        "dropped": dropped,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "answer": answer,
    }
    row.update(evaluate(q, config, answer, retrieved, context))
    return row


def load_rows():
    path = RAW / "rag_results.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def save_row(row):
    with (RAW / "rag_results.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def reevaluate(rows):
    chunks = {c["chunk_id"]: c for c in (json.loads(l) for l in (RAW / "rag_chunks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}
    questions = {q["id"]: q for q in QUESTIONS}
    for row in rows:
        retrieved = [dict(chunks[h["chunk_id"]], score=h["score"]) for h in row["retrieved"]]
        context = [chunks[i] for i in row["context_chunk_ids"]]
        row.update(evaluate(questions[row["question_id"]], row["config"], row["answer"], retrieved, context))
    (RAW / "rag_results.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return rows


def run_all():
    RAW.mkdir(parents=True, exist_ok=True)
    chunks = load_chunks()
    (RAW / "rag_chunks.jsonl").write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in chunks) + "\n", encoding="utf-8")
    sources = len({c["source"] for c in chunks})
    print(f"{sources} documents, {len(chunks)} chunks (chunk_size={CHUNK_SIZE}, chunk_overlap={CHUNK_OVERLAP})")
    embedder = SentenceTransformer(EMBED_MODEL)
    index = build_index(chunks, embedder)
    print(f"FAISS index built with {index.ntotal} vectors of dimension {index.d}")

    llm = ModelClient(temperature=0.0, num_ctx=4096, num_predict=200)
    rows = load_rows()
    done = {(r["stage"], r["question_id"], r["config"], r["k"]) for r in rows}
    for q in QUESTIONS:
        for config in ["A", "B", "C"]:
            if ("compare", q["id"], config, TOP_K) in done:
                continue
            row = answer_question(llm, q, config, TOP_K, chunks, index, embedder)
            save_row({"stage": "compare", **row})
    sweep_question = QUESTIONS[1]
    for k in SWEEP_KS:
        if ("sweep", sweep_question["id"], "C", k) in done:
            continue
        row = answer_question(llm, sweep_question, "C", k, chunks, index, embedder)
        save_row({"stage": "sweep", **row})
    write_summaries(load_rows())


def cell(text):
    return " ".join(str(text).split()).replace("|", "/")


def flag(value):
    return "n/a" if value is None else ("yes" if value else "no")


def write_summaries(rows):
    compare = [r for r in rows if r["stage"] == "compare"]
    sweep = [r for r in rows if r["stage"] == "sweep"]
    header = f"Model qwen3:8b (temperature 0), embeddings {EMBED_MODEL}, chunk_size={CHUNK_SIZE}, chunk_overlap={CHUNK_OVERLAP}, top_k={TOP_K}.\n\n"

    lines = ["# Three-configuration comparison\n", header]
    for q in QUESTIONS:
        lines.append(f"## {q['id']} ({q['kind']}): {q['question']}\n")
        lines.append("| Config | Context chunks (source, chunk_id, score) | Answer | Correct | Grounded | Refused |")
        lines.append("|---|---|---|---|---|---|")
        for r in compare:
            if r["question_id"] != q["id"]:
                continue
            ctx = "; ".join(f"{h['source']} #{h['chunk_id']} ({h['score']})" for h in r["retrieved"] if h["chunk_id"] in r["context_chunk_ids"]) or "none"
            lines.append(f"| {r['config']} | {cell(ctx)} | {cell(r['answer'])} | {flag(r['correct_answer'])} | {flag(r['grounded'])} | {flag(r['refused'])} |")
        lines.append("")
    (RAW / "rag_comparison.md").write_text("\n".join(lines), encoding="utf-8")

    lines = ["# top_k sweep\n", header]
    if sweep:
        lines.append(f"Question {sweep[0]['question_id']}: {sweep[0]['question']}\n")
    lines.append("| k | Retrieved (source, chunk_id, score) | Kept after filtering | Answer | Correct | Cited |")
    lines.append("|---|---|---|---|---|---|")
    for r in sweep:
        hits = "; ".join(f"{h['source']} #{h['chunk_id']} ({h['score']})" for h in r["retrieved"])
        lines.append(f"| {r['k']} | {cell(hits)} | {r['context_chunk_ids']} | {cell(r['answer'])} | {flag(r['correct_answer'])} | {r['cited_sources']} |")
    (RAW / "rag_k_sweep.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    lines = ["# Evaluation\n", header]
    lines.append("| Question | Config | Correct retrieval | Correct answer | Grounded | Refused when needed | Format OK |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in compare:
        lines.append(f"| {r['question_id']} | {r['config']} | {flag(r['correct_retrieval'])} | {flag(r['correct_answer'])} | {flag(r['grounded'])} | {flag(r['refusal_ok'])} | {flag(r['format_ok'])} |")
    lines.append("\n| Config | Accuracy (correct answers / 6) | Faithfulness (grounded / answered with context) | Format compliance | Robustness (Q5, Q6 refused) |")
    lines.append("|---|---|---|---|---|")
    for config in ["A", "B", "C"]:
        subset = [r for r in compare if r["config"] == config]
        if not subset:
            continue
        correct = sum(r["correct_answer"] for r in subset)
        answered = [r for r in subset if r["grounded"] is not None]
        grounded = sum(r["grounded"] for r in answered)
        formatted = sum(r["format_ok"] for r in subset)
        robust = sum(r["refused"] for r in subset if r["question_id"] in ("Q5", "Q6"))
        faith = f"{grounded}/{len(answered)}" if answered else "n/a (no context)"
        lines.append(f"| {config} | {correct}/6 | {faith} | {formatted}/6 | {robust}/2 |")
    (RAW / "rag_evaluation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote rag_comparison.md, rag_k_sweep.md, rag_evaluation.md")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="re-evaluate the saved answers and rebuild the markdown tables")
    args = parser.parse_args()
    if args.summary:
        write_summaries(reevaluate(load_rows()))
    else:
        run_all()
