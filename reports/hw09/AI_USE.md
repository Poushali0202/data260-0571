# AI-use statement

1. I used an AI assistant for debugging and for preparing the report document (`report.md` and the PDF).
   The debugging help covered Docker Desktop stopping all containers with exit code 255, Ollama failing to
   load qwen3:8b with "unable to allocate CPU buffer", and the module path of `IndexDefinition` in
   redis-py 8. I chose the cache design (key
   names, vector index, data-version marker and the version check on every hit), wrote the counter, the
   semantic cache, the ingress in front of the HW8 Kafka agents, the labeled cases, the sweep, the cost
   model, the two Part 4 agents, the lesson rules and the validation step, ran every experiment on my
   laptop and checked the results.

2. One output that was wrong: when qwen3:8b would not load, the suggestion was that the WSL VM was holding
   the memory as page cache, and to drop the cache inside the Docker VM. After dropping it the VM gave back
   about 1 GB, but the model still failed with the same allocation error.

3. I found it by retrying the model right after the fix and then looking at the Windows commit charge
   instead of free RAM: 63.6 GB of the 65.3 GB commit limit was in use. Sorting processes by private bytes
   showed two WinZip background helper processes (WzBGTools64) holding about 38.6 GB, running since
   November 4. The WSL VM was not the cause.

4. I stopped the two WinZip helper processes. The commit charge dropped to about 50 GB and qwen3:8b loaded
   on the next request. I also turned off the restart policy of the two HW8 notice containers, because
   their restart loop while Kafka was down was what made Docker Desktop stop every container.
