# AI-use statement

1. I used an AI assistant for debugging and for preparing the report document (`report.md` and the PDF).
   The debugging help covered the Kafka listener settings so that both the containers and the host
   scripts can reach the broker, the Git Bash path conversion that broke `docker exec` on Windows, and
   the PowerShell quirks in the screenshot commands. I chose the topic layout, the message schemas and
   the notice validation rules, wrote the worker, the FastAPI wrapper, the three agents and the failure
   fixes (idempotency file, commit after processing, bounded retries with a dead-letter topic, entity
   keys), ran every experiment on my laptop and checked the results against the Kafka consumer group
   offsets.

2. One output that was wrong: when I asked for help merging the client lines and the container log lines
   in `homework_demo.py`, the suggestion was to sort all lines by their printed timestamp. The first
   output then showed the client receiving the CREATE_NOTICE response at 11:54:56.208, before the worker
   had sent it at 11:54:56.209. That order is impossible.

3. I found it by reading the demo output line by line and checking that every step happened after the step
   that caused it. The cause was clock skew of a few milliseconds between Windows and the Docker Desktop VM,
   plus lines in the same millisecond being sorted alphabetically. I also did not trust the agent logs alone
   for the consumer-death test: I checked `kafka-consumer-groups.sh --describe` right after each kill to see
   which offset was really committed.

4. The demo now prints its own lines before and after the request, and sorts only the container lines,
   using the nanosecond timestamps that `docker logs -t` adds. Both containers share the Docker VM clock,
   so that order is reliable, and the output follows the real send, receive, process, reply sequence.
