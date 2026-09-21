# AI-use statement

1. I used an AI assistant for debugging and for preparing the report document
   (`report.md` / `report.pdf`). The debugging help covered the login flow (why a
   replayed cookie still opened the dashboard, why the smoke test looked slow),
   the Wikipedia rate limit that broke the first corpus download, a console
   encoding error on a narrow no-break space in the FDA text, and the reportlab
   layout. I wrote and ran the application code, the chunking comparison, the
   corpus fetch script and the smoke test myself, chose the corpus sources, wrote
   the five questions before running the comparison, reviewed every output file,
   and made the Canvas submission.

2. One thing I verified myself was the logout. The first version of the logout
   route only cleared the session, so the browser dropped the cookie, but a copy
   of the signed cookie stayed valid until its `Max-Age` ran out: replaying it
   with curl after `/logout` still returned `200 OK` from `/dashboard`. A second
   unsuitable result was my own answer check in the retrieval script: it counted
   "Class I" as present inside "Class II" and "Class III", so openFDA records that
   only say "Classification: Class II" were reported as containing the definition
   of the recall classes. I also checked that the `store_score` returned by the
   LlamaIndex retriever is the cosine similarity by recomputing the chunk
   embeddings explicitly.

3. I found the replay problem with the curl sequence in `RUN_LOG.txt` (log in,
   log out, send the old cookie again) against a server started with
   `IDLE_TIMEOUT_SECONDS=20`. An earlier check with a 3 second timeout had hidden
   it, because every request to `localhost` on this laptop takes about 2 seconds
   (IPv6 is tried first), so the cookie had already expired by the time it was
   replayed; timing requests against `localhost` and `127.0.0.1` showed the
   difference (2.1 s versus 0.015 s). I found the answer-check problem by reading
   the per-question rows for q4: four openFDA chunks at ranks 2 to 5 were flagged
   as containing the answer although their text is a single classification line.
   The cosine check is the `cosine_sim` column next to `store_score` in every
   table: the values match to four decimals.

4. `routers/auth.py` now keeps a set of active session ids. Login creates a
   random id, stores it in the session and in the set; logout removes it from
   the set before clearing the session; `current_user()` rejects any cookie whose
   id is not in the set or whose `last_seen` is older than the idle timeout, so a
   replayed cookie is refused with a redirect to `/login` even though its
   signature is still valid. `verify_hw03.py` and the run log use `127.0.0.1`
   and a 5 second timeout, so the checks measure the application and not the
   name lookup. The answer check now matches whole phrases with a regular
   expression, and q4 uses the two defining phrases from the FDA page; the
   questions and expected answers in `questions.yaml` were not changed. With
   that fix the sentence-window index shows a real miss on q4 (Recall@5 of 0.8),
   which is discussed in `METRICS.md`.
