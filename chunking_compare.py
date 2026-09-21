import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yaml
from llama_index.core import Document, QueryBundle, Settings, VectorStoreIndex
from llama_index.core.node_parser import SemanticSplitterNodeParser, SentenceWindowNodeParser, TokenTextSplitter
from llama_index.core.schema import MetadataMode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "reports" / "hw03" / "raw"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
WARMUP_URL = "https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt"
WARMUP_FILE = ROOT / "corpus_warmup" / "tinyshakespeare.txt"
WARMUP_QUESTION = {
    "id": "warmup",
    "question": "Why do the citizens want to kill Caius Marcius?",
    "expected_source": "tinyshakespeare.txt",
    "answer_keywords": ["Marcius", "enemy to the people"],
}


def make_document(text, name):
    return Document(
        text=text,
        metadata={"source_file": name},
        excluded_embed_metadata_keys=["source_file"],
        excluded_llm_metadata_keys=["source_file"],
    )


def load_corpus(folder):
    return [make_document(path.read_text(encoding="utf-8"), path.name) for path in sorted(folder.glob("*.txt"))]


def load_warmup():
    if not WARMUP_FILE.exists():
        WARMUP_FILE.parent.mkdir(exist_ok=True)
        WARMUP_FILE.write_text(requests.get(WARMUP_URL, timeout=60).text, encoding="utf-8")
    return [make_document(WARMUP_FILE.read_text(encoding="utf-8")[:100000], WARMUP_FILE.name)]


def build_chunkers(embed_model):
    return {
        "token": TokenTextSplitter(chunk_size=200, chunk_overlap=40),
        "semantic": SemanticSplitterNodeParser(buffer_size=1, breakpoint_percentile_threshold=95, embed_model=embed_model),
        "sentence_window": SentenceWindowNodeParser.from_defaults(
            window_size=3, window_metadata_key="window", original_text_metadata_key="original_text"
        ),
    }


def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def contains_all(text, keywords):
    return all(re.search(r"(?<!\w)" + re.escape(keyword) + r"(?!\w)", text, re.IGNORECASE) for keyword in keywords)


def retrieve(technique, index, embed_model, question, k):
    query_vec = np.array(embed_model.get_query_embedding(question["question"]))
    print(f"query embedding: dim={query_vec.shape[0]} first8={np.round(query_vec[:8], 4).tolist()}")
    retriever = index.as_retriever(similarity_top_k=k)
    start = time.perf_counter()
    hits = retriever.retrieve(QueryBundle(query_str=question["question"], embedding=query_vec.tolist()))
    latency_ms = (time.perf_counter() - start) * 1000
    doc_vecs = np.array([embed_model.get_text_embedding(hit.node.get_content(metadata_mode=MetadataMode.EMBED)) for hit in hits])
    print(f"query vector shape {query_vec.shape}, stacked doc vectors shape {doc_vecs.shape}")
    rows = []
    for rank, (hit, doc_vec) in enumerate(zip(hits, doc_vecs), start=1):
        text = hit.node.get_content(metadata_mode=MetadataMode.NONE)
        window = hit.node.metadata.get("window")
        rows.append({
            "technique": technique,
            "question_id": question["id"],
            "question": question["question"],
            "expected_source": question["expected_source"],
            "rank": rank,
            "store_score": round(float(hit.score), 4),
            "cosine_sim": round(cosine(query_vec, doc_vec), 4),
            "chunk_len": len(text),
            "preview": text[:160].replace("\n", " "),
            "source_file": hit.node.metadata.get("source_file"),
            "source_hit": hit.node.metadata.get("source_file") == question["expected_source"],
            "contains_answer": contains_all(window or text, question["answer_keywords"]),
            "latency_ms": round(latency_ms, 2),
            "text": text,
            "window": window,
        })
    table = pd.DataFrame(rows)[["rank", "store_score", "cosine_sim", "chunk_len", "preview"]]
    print(table.to_string(index=False))
    print(f"retrieval latency: {latency_ms:.2f} ms")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--warmup", action="store_true", help="run on the first 100 KB of Tiny Shakespeare instead of the corpus")
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)
    Settings.embed_model = embed_model
    if args.warmup:
        documents, questions, prefix = load_warmup(), [WARMUP_QUESTION], "warmup_"
    else:
        documents = load_corpus(ROOT / "corpus")
        questions = yaml.safe_load((ROOT / "reports" / "hw03" / "questions.yaml").read_text(encoding="utf-8"))["questions"]
        prefix = ""
    print(f"{len(documents)} documents, {sum(len(d.text) for d in documents)} characters, k={args.k}")

    RAW.mkdir(parents=True, exist_ok=True)
    stats = {}
    with (RAW / f"{prefix}retrieval_results.jsonl").open("w", encoding="utf-8") as out:
        for name, chunker in build_chunkers(embed_model).items():
            start = time.perf_counter()
            nodes = chunker.get_nodes_from_documents(documents)
            chunking_s = time.perf_counter() - start
            start = time.perf_counter()
            index = VectorStoreIndex(nodes, embed_model=embed_model)
            index_s = time.perf_counter() - start
            lengths = [len(node.get_content(metadata_mode=MetadataMode.NONE)) for node in nodes]
            stats[name] = {
                "chunks": len(nodes),
                "avg_chunk_len": round(sum(lengths) / len(lengths), 1),
                "chunking_s": round(chunking_s, 2),
                "index_build_s": round(index_s, 2),
            }
            print(f"\n=== Technique: {name} | {len(nodes)} chunks, avg {stats[name]['avg_chunk_len']} chars, "
                  f"chunking {chunking_s:.1f} s, index build {index_s:.1f} s ===")
            for question in questions:
                print(f"\n--- {name} | {question['id']}: {question['question']}")
                for row in retrieve(name, index, embed_model, question, args.k):
                    out.write(json.dumps(row) + "\n")
    (RAW / f"{prefix}chunk_stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {RAW / (prefix + 'retrieval_results.jsonl')} and {RAW / (prefix + 'chunk_stats.json')}")


if __name__ == "__main__":
    main()
