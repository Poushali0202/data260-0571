# HW8 metrics

SID4 0571, PREFIX s0571, SEED 571, VERIFY_SEED 260571. qwen3:8b through Ollama on CPU (Intel Core i5-1135G7).
All runs on 2026-11-02, local time (PST). Raw logs are in `raw/`, the full console output is in `RUN_LOG.txt`.

## Part 1: request/response over Kafka (homework_demo.py, 12:34)

| Operation | correlation_id | Result | Request offset | Response offset | API sent to API returned |
|---|---|---|---:|---:|---:|
| CREATE_NOTICE | 258eb3bc-d7ec-4a59-b04b-07bf48d7692f | success, notice_id 1308825e-e252-4f10-b009-0a76a60ad44d | 32 | 32 | 10 ms |
| GET_NOTICE | 615159cc-9fe6-4613-af10-dbd904fe798c | success, all five fields match | 33 | 33 | 2 ms |

| Error case | correlation_id kept | Error returned |
|---|---|---|
| Unknown operation DELETE_NOTICE | err-test-1 | Unknown operation |
| GET_NOTICE with unknown id | err-test-2 | Notice not found |
| Empty productName | err-test-3 | productName is required |
| noticeCode "RN-12" | err-test-4 | noticeCode must look like RN-123456 |
| noticeCategory "flood" | err-test-5 | noticeCategory must be one of: contamination, distribution, recall, shortage |
| affectedUnits -3 | err-test-6 | affectedUnits must be a whole number 0 or more |

## Part 2: one message journey (correlation_id 8c340cdd-1777-4a77-8a2c-9b8dfa9b5995)

| Stage | Reads | Sends to | Started | Finished | Time |
|---|---|---|---|---|---:|
| send_question.py | - | s0571_inbox offset 1 | 12:12:34.306 | 12:12:34.306 | 0 s |
| Planner | s0571_inbox offset 1 | s0571_tasks partition 1 offset 0 | 12:12:34.306 | 12:13:08.653 | 34.3 s |
| Writer | s0571_tasks partition 1 offset 0 | s0571_drafts offset 1 | 12:13:08.660 | 12:13:28.476 | 19.8 s |
| Reviewer | s0571_drafts offset 1 | s0571_final offset 1 (approved) | 12:13:28.478 | 12:13:44.661 | 16.2 s |
| send_question.py | s0571_final offset 1 | - | 12:13:44.662 | 12:13:44.662 | 0 s |
| Total | | | | | 70.4 s |

## Part 3: failure table

| Failure scenario | Before fix | After fix |
|---|---|---|
| Duplicate delivery | `writer.py --no-dedupe`. Task 60b8fbaf replayed unchanged (partition 0 offset 1 sent again as offset 2). Writer called the model twice and wrote 2 drafts, reviewer approved both, `s0571_final` has 2 messages (offsets 2 and 3) with the same correlation_id. | Processed correlation_ids are kept in `state/writer_done.txt`. Task cb207d2f replayed (partition 1 offset 1 sent again as offset 2): writer logged "duplicate ... already processed, skipped" and committed offset 3. 1 model call, 1 draft, 1 final message (offset 4). |
| Consumer killed mid-work | `writer.py --auto-commit`. Writer killed 8 s into the draft for partition 0 offset 3. Committed offset was already 4 (lag 0). Restarted writer received nothing in 100 s, 0 drafts for c3a07346, the question never got an answer. Message lost. | Manual commit after the draft is sent. Writer killed 8 s into the draft for partition 0 offset 4. Committed offset stayed 4 (lag 1). Restarted writer received offset 4 again at start, sent the draft, committed 5. Answer (approved) arrived 73 s after the question. |
| Poison message | `writer.py --no-dlq`. Malformed JSON at partition 1 offset 3: writer crashed with JSONDecodeError, crashed again on the same offset after restart. Partition 1 lag 2, the normal task at offset 4 was never processed. | 3 attempts 1 s apart, then the message went to `s0571_dead_letter` (offset 0, with the error, source offset and raw text) and offset 4 was committed. The normal task behind it was processed straight away (draft offset 6). Lag 0 on both partitions. |
| Two partitions/two consumers | No key: each of the 4 products landed in both partitions, so both writers worked on the same product at once. Spinach processed as seq 1, 3, 2, 4 and smoked salmon as 1, 2, 3, 4, 6, 5, 7, 8. 2 of 4 products out of order. | Key = product name: spinach and chicken nuggets in partition 0 (writer-1), peanut butter and smoked salmon in partition 1 (writer-2). Every product stayed in one partition and 4 of 4 kept their order. |

## Part 3 IV: ordering detail (20 messages from VERIFY_SEED 260571)

| Product | Messages | No key: partitions | No key: processed order | Keyed: partition | Keyed: processed order |
|---|---:|---|---|---|---|
| Organic baby spinach 5 oz | 4 | 0, 1 | 1, 3, 2, 4 | 0 | 1, 2, 3, 4 |
| Creamy peanut butter 16 oz | 4 | 0, 1 | 1, 2, 3, 4 | 1 | 1, 2, 3, 4 |
| Frozen chicken nuggets 2 lb | 4 | 0, 1 | 1, 2, 3, 4 | 0 | 1, 2, 3, 4 |
| Smoked salmon 12 oz | 8 | 0, 1 | 1, 2, 3, 4, 6, 5, 7, 8 | 1 | 1, 2, 3, 4, 5, 6, 7, 8 |

Both runs took about 2.5 minutes for 20 drafts (no key 12:27:32 to 12:29:55, keyed 12:30:48 to 12:32:50).
Per-message rows are in `raw/ordering_nokey.csv` and `raw/ordering_keyed.csv`.
