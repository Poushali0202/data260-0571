# HW3 measurements

Retrieval only, no LLM. Embeddings from `sentence-transformers/all-MiniLM-L6-v2`
(384 dimensions, 256 wordpiece input window) on the CPU of the laptop described in
the report. Corpus: 21 files, 393,964 bytes (388,095 characters). k = 5 for every
query. Raw rows: `raw/retrieval_results.jsonl` (one row per technique, question and
rank, with store score, cosine, chunk length, latency, preview, source file and the
full chunk text and window) and `raw/chunk_stats.json`; the warm-up run is in
`raw/warmup_*`. `python summarize_retrieval.py` rebuilds every table below from
those files. Console output with timestamps: `RUN_LOG.txt`.

Definitions used in the tables:

- Retrieval latency is the wall-clock time of `retriever.retrieve()` with a
  precomputed query embedding, so it measures the similarity search over the
  in-memory `SimpleVectorStore` only (one query, no repetitions).
- `cosine_sim` is recomputed explicitly from the chunk and query embeddings; it
  equals the retriever's `store_score` in every row.
- Top-1 cosine and Mean@5 cosine in the summary are averaged over the five questions.
- Recall@5 is the share of questions with at least one top-5 chunk that contains the
  answer phrases from `questions.yaml` (whole-phrase match; for the sentence-window
  index the check runs on the stored window, which is what a reader model would get).

| Technique | Settings |
|---|---|
| token | `TokenTextSplitter(chunk_size=200, chunk_overlap=40)` |
| semantic | `SemanticSplitterNodeParser(buffer_size=1, breakpoint_percentile_threshold=95, embed_model=MiniLM)` |
| sentence_window | `SentenceWindowNodeParser(window_size=3)`, single sentences, window in metadata |

## Retrieval quality, five questions, k=5

| Technique | Chunks | Avg chunk length (chars) | Top-1 cosine | Mean@5 cosine | Recall@5 | Mean retrieval latency (ms) |
|---|---|---|---|---|---|---|
| token | 557 | 865.9 | 0.7368 | 0.6388 | 1.0 | 21.55 |
| semantic | 157 | 2471.9 | 0.7088 | 0.5787 | 1.0 | 6.41 |
| sentence_window | 2618 | 148.2 | 0.7836 | 0.6867 | 0.8 | 71.23 |

Build cost from `raw/chunk_stats.json`: token 0.9 s chunking + 22.1 s index build,
semantic 67.1 s + 7.3 s (the splitter embeds every sentence to find boundaries),
sentence window 0.2 s + 33.2 s.

## Chunk sizes against the 256 wordpiece window of the embedding model

| Technique | Chunks | Wordpieces min / median / max | Chunks longer than 256 wordpieces |
|---|---|---|---|
| token | 557 | 56 / 192 / 218 | 0 (0.0%) |
| semantic | 157 | 6 / 304 / 5923 | 86 (54.8%) |
| sentence_window | 2618 | 4 / 28 / 693 | 6 (0.2%) |

Over half of the semantic chunks are longer than the model can read, so their
embedding only represents the first 256 wordpieces (roughly the first 1,000
characters).

## Per question

| Question | Technique | Top-1 cosine | Mean@5 | Answer found at rank | Expected source in top-k | Latency (ms) |
|---|---|---|---|---|---|---|
| q1_listeriosis_plant | token | 0.8777 | 0.6654 | 1 | yes | 16.25 |
| q2_ecoli_sprouts | token | 0.7582 | 0.7225 | 1 | yes | 19.56 |
| q3_formula_plant | token | 0.6724 | 0.5654 | 1 | yes | 23.84 |
| q4_recall_classes | token | 0.5988 | 0.5146 | 1 | yes | 28.73 |
| q5_traceability_deadline | token | 0.7767 | 0.7258 | 1 | yes | 19.39 |
| q1_listeriosis_plant | semantic | 0.8778 | 0.619 | 1 | yes | 7.61 |
| q2_ecoli_sprouts | semantic | 0.7316 | 0.6486 | 1 | yes | 6.16 |
| q3_formula_plant | semantic | 0.6494 | 0.5314 | 1 | yes | 5.71 |
| q4_recall_classes | semantic | 0.6086 | 0.4594 | 1 | yes | 5.24 |
| q5_traceability_deadline | semantic | 0.6765 | 0.635 | 2 | yes | 7.34 |
| q1_listeriosis_plant | sentence_window | 0.8798 | 0.7002 | 1 | yes | 62.58 |
| q2_ecoli_sprouts | sentence_window | 0.8702 | 0.7601 | 1 | yes | 71.87 |
| q3_formula_plant | sentence_window | 0.6535 | 0.5695 | 1 | yes | 76.67 |
| q4_recall_classes | sentence_window | 0.7091 | 0.645 | none | no | 73.03 |
| q5_traceability_deadline | sentence_window | 0.8054 | 0.7585 | 1 | yes | 72.0 |

## Confidently scored retrievals that do not contain the answer

| Question | Technique | Rank | Cosine | Source file | What the chunk says |
|---|---|---|---|---|---|
| q5_traceability_deadline | semantic | 1 | 0.6765 | fda_fsma_preventive_controls_human_food.txt | A 2,400 character chunk about the FSMA preventive controls rule: its Federal Register docket, "requires food facilities to have a food safety plan", "Compliance dates are staggered, based on the size of the business". No mention of the traceability rule or of January 20, 2026. |
| q4_recall_classes | sentence_window | 1 | 0.7091 | ecfr_21_cfr_part_7_subpart_c_recalls.txt | 21 CFR 7.41(b): "the Food and Drug Administration will assign the recall a classification, i.e., Class I, Class II, or Class III, to indicate the relative degree of health hazard". It names the classes but never defines them; the window around it lists hazard evaluation factors. |
| q4_recall_classes | sentence_window | 2 to 5 | 0.6336 to 0.6152 | openfda_food_enforcement_reports.txt | Lines such as "Classification: Class II" from individual enforcement records. |
| q5_traceability_deadline | token | 2 to 5 | 0.7257 to 0.7000 | fda_fsma_food_traceability_rule.txt | Paragraphs about the traceability rule (benefits, public meetings, related tools) that do not contain the compliance date. |

Why the embedding considered them similar: the q5 semantic miss shares almost all
of the question's vocabulary (FDA, FSMA, rule, compliance date) and the model has
no way to tell the preventive controls rule from the traceability rule when the
one distinguishing word, "traceability", is absent from the chunk head that was
embedded; the traceability chunk that holds the date is 4,525 characters long, the
date sits far past the 256 wordpiece cut-off, and its embedded head is about
critical tracking events and key data elements, so it landed at rank 2 (0.6491).
The q4 sentence-window miss is the opposite case: a single sentence that lists
"Class I, Class II, or Class III" next to "recall" and "health hazard" is an almost
perfect lexical match for a question that lists the same three names, while the
actual definitions on the FDA page are written as a label line ("Class I recall:")
followed by the definition on the next line, so the sentence splitter stores the
label and the definition as separate short nodes and neither one alone scores well.

## Observations

The sentence-window index has the highest top-1 and mean@5 cosines and put the exact
answer sentence first for four of the five questions (for example "The original
compliance date for all persons subject to the recordkeeping requirements of the
Food Traceability Rule was Tuesday, January 20, 2026" at 0.8054, and the Bartor
Road sentence at 0.8798). A one-sentence node is the closest thing to a one-sentence
question, so the scores are high and the three-sentence window carries the context
that the node itself lacks. The cost is 2,618 vectors instead of 557, which makes
the linear search about three times slower than the token index (71 ms against
22 ms), and the q4 failure above, where a sentence that names the topic beats the
sentences that answer the question. Token chunks of 200 tokens with a 40 token
overlap were the most robust: the answer was at rank 1 for every question, every
chunk fits inside the model window, and each hit brings roughly 870 characters of
surrounding text with it. Its cosines are lower than the sentence-window ones
because each chunk also contains material unrelated to the query.

The semantic splitter found coherent boundaries (the q1 chunk is exactly the
"Origin of the outbreak" section) but produced chunks that average 2,472 characters,
and 55% of them are longer than the 256 wordpieces MiniLM reads, so most of a long
chunk never influences its embedding. That is why it has the lowest mean@5 (0.5787),
why the q5 answer dropped to rank 2, and why one retrieved chunk is 9,827 characters
long. It is the fastest at query time (157 vectors, 6.4 ms) and the slowest to
build (67 s of sentence embeddings for boundary detection). The best technique does
change with the query: sentence window had the highest top-1 cosine on q1, q2, q4
and q5 and token on q3, but on q4 only token and semantic actually returned the
definitions.

## Conclusion

For this corpus I judge token chunking (200 tokens, 40 overlap) the best of the
three: it is the only technique that returned a chunk containing the answer at rank
1 for all five questions, none of its 557 chunks exceeds the embedding window, and
each hit carries enough context to answer from, at 22 ms per search. Sentence-window
chunking scores highest on cosine (0.7836 top-1, 0.6867 mean@5) and is the better
choice when a question maps to a single sentence, but it missed the recall class
definitions entirely and needs three times the search time and the window
post-processing step. Semantic chunking gave the lowest scores here because its
oversized chunks are truncated by the 256 token model; it would need a smaller
breakpoint threshold or a longer-context embedding model to compete.

The four AI-use answers are in `AI_USE.md`.
