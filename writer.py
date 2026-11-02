import argparse
import asyncio
import json
from pathlib import Path

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, TopicPartition

from kafka_common import BOOTSTRAP, DEAD_LETTER, DRAFTS, PREFIX, TASKS, encode, log, short
from src.model_client import ModelClient

SYSTEM = "You are the Writer. Follow the plan and answer the question in at most 120 words."
MAX_ATTEMPTS = 3
DONE_FILE = Path("state/writer_done.txt")

parser = argparse.ArgumentParser()
parser.add_argument("--name", default="writer-1")
parser.add_argument("--auto-commit", action="store_true", help="before fix: offsets committed in the background")
parser.add_argument("--no-dedupe", action="store_true", help="before fix: replays are processed again")
parser.add_argument("--no-dlq", action="store_true", help="before fix: a failing message crashes the writer")
args = parser.parse_args()
NAME = args.name.upper()

llm = ModelClient(num_predict=200)


def load_done():
    if not DONE_FILE.exists():
        return set()
    return set(DONE_FILE.read_text().split())


def mark_done(correlation_id):
    DONE_FILE.parent.mkdir(exist_ok=True)
    with DONE_FILE.open("a") as f:
        f.write(correlation_id + "\n")


def write_draft(raw):
    task = json.loads(raw)
    if not task.get("question") or not task.get("plan"):
        raise ValueError("task is missing question or plan")
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Question: {task['question']}\n\nPlan:\n{task['plan']}"},
    ]
    return task, llm.complete(messages).text


async def main():
    consumer = AIOKafkaConsumer(
        TASKS,
        bootstrap_servers=BOOTSTRAP,
        group_id=f"{PREFIX}-writer",
        auto_offset_reset="earliest",
        enable_auto_commit=args.auto_commit,
    )
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await consumer.start()
    await producer.start()
    done = set() if args.no_dedupe else load_done()
    log(
        NAME, f"listening on {TASKS} (auto_commit={args.auto_commit}, dedupe={not args.no_dedupe}, dead_letter={not args.no_dlq})"
    )
    try:
        async for msg in consumer:
            log(NAME, f"received from {TASKS} partition={msg.partition} offset={msg.offset} key={msg.key}")
            correlation_id = None
            try:
                correlation_id = json.loads(msg.value).get("correlation_id")
            except ValueError:
                pass

            if correlation_id in done:
                log(NAME, f"duplicate correlation_id={correlation_id}, already processed, skipped")
            else:
                for attempt in range(1, MAX_ATTEMPTS + 1):
                    try:
                        log(NAME, f"writing draft correlation_id={correlation_id} attempt {attempt}/{MAX_ATTEMPTS}")
                        task, draft = await asyncio.to_thread(write_draft, msg.value)
                        break
                    except Exception as error:
                        last_error = str(error)
                        log(NAME, f"attempt {attempt}/{MAX_ATTEMPTS} failed: {last_error}")
                        if args.no_dlq:
                            raise
                        await asyncio.sleep(1)
                else:
                    record = {
                        "correlation_id": correlation_id,
                        "source_topic": TASKS,
                        "partition": msg.partition,
                        "offset": msg.offset,
                        "error": last_error,
                        "attempts": MAX_ATTEMPTS,
                        "raw": msg.value.decode(errors="replace"),
                    }
                    sent = await producer.send_and_wait(DEAD_LETTER, encode(record))
                    log(NAME, f"gave up after {MAX_ATTEMPTS} attempts, moved to {DEAD_LETTER} offset={sent.offset}")
                    task = None

                if task:
                    out = {
                        **task,
                        "draft": draft,
                        "writer": args.name,
                        "task_partition": msg.partition,
                        "task_offset": msg.offset,
                    }
                    sent = await producer.send_and_wait(DRAFTS, encode(out))
                    log(NAME, f"sent draft to {DRAFTS} offset={sent.offset} correlation_id={correlation_id} draft={short(draft)}")
                    if not args.no_dedupe:
                        done.add(correlation_id)
                        mark_done(correlation_id)

            if not args.auto_commit:
                await consumer.commit({TopicPartition(msg.topic, msg.partition): msg.offset + 1})
                log(NAME, f"committed partition={msg.partition} offset={msg.offset + 1}")
    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
