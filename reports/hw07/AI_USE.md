# AI-use statement

1. I used an AI assistant for debugging and for preparing the report document (`report.md` and the PDF).
   The debugging help covered the PyJWT expired-token handling, the Ruff line-length setting for this
   repository, the Windows console encoding error that stopped one Reflexion batch, the HTML of the Bay
   Wheels pricing page, and the LangChain `create_agent` stream format. I chose the JWT design and the
   role rules, wrote the agent loop, the verifiers, the Reflexion bounds, the bike-share tools and UI, the
   hostile fixture and the safety gate, built the two trip scenarios from the public Bay Wheels data, ran
   every experiment on my laptop and checked the results.

2. One output that was wrong: when I asked for help reading the pricing page, the suggested extraction
   used the page text as a flat list. The page repeats every plan's price inside every plan card, so the
   flat text put "$1.00 to unlock, then $0.19/min" (the single ride price) directly under "Month pass
   $29/month". An agent reading it would have charged the single ride rate to members.

3. I found it by printing the extracted lines next to the page in a browser and by computing the two
   plan totals by hand for both scenarios before trusting any agent output (commuter: $4,559.19 pay per
   use against $1,657.37 with the month pass; occasional rider: $886.98 against $1,073.00). I also saw
   the same kind of problem in the agent itself: one trial run multiplied per-minute charges by the
   number of months and recommended pay per use for the commuter.

4. In the page HTML each plan card marks its cells with `col` and `idx` attributes, and the browser only
   shows the row label (`idx` 0) and the card's own column. `fetch_page` now drops the hidden cells, so
   every passage has one plan with its own classic and ebike price. For the agent I wrote the cost
   formula into the system prompt in general terms (the prices still come from the retriever) and
   compared its totals with my hand calculation in the report.
