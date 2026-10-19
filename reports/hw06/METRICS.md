# HW6 measurements

Machine: Intel Core i5-1135G7, 15.8 GB RAM, Windows 11 Home, CPU only, with about 1 GB of RAM free
while `qwen3:8b` (Q4_K_M, 6.7 GB) was loaded. Ollama `qwen3:8b` with temperature 0 and thinking off
for every model call, `all-MiniLM-L6-v2` for the embeddings, MongoDB 7.0 in the Docker container
`s0571-mongo`, FastAPI on port 8571. Console output with timestamps: `RUN_LOG.txt`.

## Part 3: what memory costs

### Logging

`routers/chat.py` records for every `POST /api/chat` the prompt and completion tokens reported by
Ollama (`prompt_eval_count`, `eval_count`), the request latency (whole request, including the fact
extraction call and any summary calls that follow the reply) and the model latency (chat call only),
and appends a row to `raw/chat_log.csv` (145 rows: 5 smoke turns and the 140 sweep turns). The
tokens of the system primer, the long-term summaries, the short-term window, the episodic facts and
the current message are the measured prompt tokens split in proportion to the character count of
each part (`memory.split_tokens`), because Ollama only reports the total. The sweep runner
(`run_memory_cost.py`) stores the same numbers per turn with the setting, the message and the reply
in `raw/sweep_turns.csv` (140 rows).

### Probes

`memory_probes.yaml` holds the five questions, the expected items and the 1 to 5 rubric.
A reply is scored automatically: an item counts as found when one of its phrases appears in the
reply, and `score = 1 + round(4 * found / total)`. Per-probe results: `raw/probe_scores.csv`.

### Short-term memory sizes and the compression policy

Same 30-message conversation (store manager Maya Chen, spinach recall RN-004410, lot GV-2291,
milk shortage, store code WG-17, assistant manager Daniel) in a fresh user and session per setting,
`SUMMARIZE_EVERY_USER_MSGS=5`, `TOP_K_EPISODES=4`, then the five probes in the same session.
Means are over the 30 conversation turns; probe quality is the mean of the five probe scores.

| Setting | Mean prompt tokens/turn | Mean latency (ms) | Probe quality (1-5) |
|---|---|---|---|
| SHORT_TERM_N=4 | 483.4 | 58084 | 5.0 |
| SHORT_TERM_N=12 | 709.3 | 82279 | 5.0 |
| SHORT_TERM_N=30 | 1083.4 | 108547 | 5.0 |
| Eviction/compression policy (N=30, `compress_old`) | 900.0 | 82594 | 4.6 |

Where the prompt tokens go (mean per turn, proportional split):

| Setting | Primer | Long-term summaries | Short-term window | Episodic facts | Model latency only (ms) | Mean completion tokens |
|---|---|---|---|---|---|---|
| N=4 | 92.1 | 184.9 | 131.0 | 61.0 | 25688 | 44.2 |
| N=12 | 91.6 | 174.8 | 367.9 | 60.5 | 47044 | 45.4 |
| N=30 | 92.2 | 175.4 | 740.5 | 61.0 | 77720 | 44.0 |
| N=30 + compress_old | 95.1 | 181.7 | 545.4 | 63.0 | 53899 | 42.4 |

The window is the only part that grows with N; summaries and facts stay at about 240 tokens
together. All three plain settings answered every probe correctly (5 of 5) because the facts asked
for (turns 1, 2 to 3, 6, 12, 15 and 20) were outside the window by the time the probes were asked
and were served by the session summary and the retrieved episodes in every setting. The bigger
window therefore bought nothing on the probes and cost 2.2 times the prompt tokens and 1.9 times
the latency of N=4 on this CPU.

Policy (`memory.compress_old`): keep the last 4 messages of the window verbatim and cut every
older message in the window to its first 100 characters. Applied to N=30 it saved 5,502 prompt
tokens per conversation (16.9%, 183 tokens per turn) and 26 s of latency per turn, and probe
quality fell from 5.0 to 4.6: probe p5 answered with store code "WG-037" instead of WG-17. In that
run the session summary written at message 30 had dropped the store code, the retrieved facts for
the two-part question were the spinach-bag facts, and the compressed window no longer held the
turn-15 message, so the model guessed. The other four probes were unaffected.

### Cost of 10,000 30-turn conversations

Input $1 per million tokens, output $5 per million tokens. "Chat calls" counts the 30 chat
completions; "with memory maintenance" adds the 30 fact-extraction calls and the 6 session summary
plus 3 lifetime summary calls of a conversation, which a hosted deployment would also pay for.
Raw numbers: `raw/sweep_summary.json`.

| Setting | Prompt tokens / conversation | Completion tokens / conversation | Chat calls, per conversation | Chat calls, 10,000 conversations | With memory maintenance, 10,000 |
|---|---|---|---|---|---|
| N=4 (best) | 14,501 | 1,326 | $0.0211 | $211.31 | $405.10 |
| N=12 | 21,279 | 1,363 | $0.0281 | $280.94 | $473.39 |
| N=30 (worst) | 32,501 | 1,320 | $0.0391 | $391.01 | $587.42 |
| N=30 + compress_old | 26,999 | 1,271 | $0.0334 | $333.54 | $524.79 |

Selection rule (`summarize_memory_cost.py`): the worst setting is the one with the highest chat
cost, N=30. The best setting is the cheapest one among those whose probe quality is within 0.5 of
the best score; all four qualify, so the best is N=4. The worst setting costs 1.85 times the best
for the same probe quality; the maintenance calls (fact extraction and summaries) are a fixed
$194 per 10,000 conversations in every setting and are what makes the small window work.

## Part 4: file-based memory

| Step | Result |
|---|---|
| `MEMORY.md` before `/compact` | 55 lines (53 fact lines, 6 duplicated lines, 5 contradicting pairs), `raw/MEMORY_original.md` |
| `MEMORY.md` after `/compact` | 27 lines (24 fact lines), `raw/MEMORY_consolidated.md`; 6 duplicate pairs merged, 12 topic groups joined, 1 line kept unchanged |
| Contradictions resolved explicitly | 5 "Resolved:" lines (delivery date, paperwork retention, contact preference, contamination type, and one pair that was not a contradiction) |
| Resolved incorrectly | 2: the contact preference (email dropped although "phone after 6 pm" only adds an evening rule, and the undated email line survived, so the file now says both) and the pair "answer in one to three sentences" vs "milk deliveries resumed on October 17", which do not contradict each other. Not detected: store code WG-17 vs WG-71 (no dates), both lines remain. The three dated conflicts (October 12 vs 14, two vs five years, E. coli vs Listeria) were resolved by the later date, which is correct. |
| `/dream` after the 10-message chat session | 5 facts added (user, store, lettuce lot and notice code, email preference, Rohan's shift, oat milk shortage); MEMORY.md now 32 lines |
| Generated function vs AGENT.md | 8 of 8 rules followed (`raw/agent_md_check.json`), tests pass |
