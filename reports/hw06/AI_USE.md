# AI-use statement

1. I used an AI assistant for debugging and for preparing the report document
   (`report.md` / `report.pdf`). The debugging help covered the `collMod` call that
   re-applies a `$jsonSchema` validator to a collection that already exists, the
   `tz_aware` MongoClient option so that dates read back from MongoDB serialize with a
   time zone, the Ollama structured-output call (`format` with a JSON schema) behind the
   fact extraction and the consolidation, the slow first import of sentence-transformers
   inside the FastAPI process, and the PowerShell console capture used for the terminal
   screenshots. I designed the notice document and the three memory collections, wrote
   the routers, the memory logic, the file-memory commands, the probe file, the sweep
   and scoring scripts and the smoke test myself, ran every experiment on my laptop,
   reviewed the outputs and made the Canvas submission.

2. One model output that was wrong: the first `/compact` run on the 55-line MEMORY.md
   returned a file of 14 lines that ended in the middle of a sentence ("Recall paperwork
   is kept"), with no `Resolved:` line at all, and the command still reported "53 lines
   before, 14 lines after" as if it had succeeded (`raw/MEMORY_consolidated_attempt1.md`,
   `raw/part4_compact_attempt1.json`). The second run, with a larger output limit, gave
   48 lines: it merged three duplicates, wrote one explicit resolution (Listeria versus
   E. coli) and silently dropped the two other dated contradictions, the October 12
   delivery date and the two-year paperwork rule, while keeping both store codes and both
   contact preferences (`raw/MEMORY_consolidated_attempt2.md`).

3. I noticed the first problem by reading the consolidated file and comparing its length
   with the 220-token completion limit of the summary model client, which cut the answer
   off; the server log showed the output count at the limit. The second problem showed up
   when I diffed the original and the consolidated file line by line: facts had vanished
   without a `Resolved:` entry, which is exactly what the assignment forbids, and the
   count was still above 40.

4. I changed the consolidation so that the model no longer rewrites the file. A first
   rewrite with source numbers and a schema still ran into the output limit (the model
   produced 1,800 tokens of JSON and the code, finding nothing usable, kept all 53 lines,
   `raw/part4_compact_attempt3.json`). The final version asks the model only for index
   groups: duplicates, related facts and conflicting pairs with a reason, which is a few
   hundred tokens. The code then keeps the longest line of a duplicate group (and only if
   the lines really overlap), joins related facts into one line, writes one `Resolved:`
   line per conflict with both texts and the reason, and keeps every unmentioned line
   unchanged. A fact can now only leave the file through an explicit merge or an explicit
   resolution, the server runs with `OLLAMA_TIMEOUT=900` because the calls take minutes
   on this CPU, and the resulting counts and the resolutions I judged wrong are in the
   report and in `METRICS.md`.
