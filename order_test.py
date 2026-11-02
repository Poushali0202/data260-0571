import asyncio
import csv
import json
import random
import sys
import uuid
from datetime import datetime
from pathlib import Path

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, TopicPartition

from kafka_common import BOOTSTRAP, DRAFTS, TASKS, encode, log

VERIFY_SEED = 260571
PRODUCTS = ["Organic baby spinach 5 oz", "Creamy peanut butter 16 oz", "Frozen chicken nuggets 2 lb", "Smoked salmon 12 oz"]
EVENTS = ["recall opened", "affected lots listed", "stores notified", "shelves cleared", "refunds started", "recall closed"]
OUT_DIR = Path("reports/hw08/raw")


def build_messages():
    rng = random.Random(VERIFY_SEED)
    counts = {p: 0 for p in PRODUCTS}
    messages = []
    for _ in range(20):
        product = rng.choice(PRODUCTS)
        counts[product] += 1
        seq = counts[product]
        event = EVENTS[(seq - 1) % len(EVENTS)]
        messages.append(
            {
                "correlation_id": str(uuid.uuid4()),
                "entity": product,
                "seq": seq,
                "question": f"Write one sentence telling stores: {product}, update {seq}, {event}.",
                "plan": "1. Write one short sentence with the product and the update.",
            }
        )
    return messages


async def main():
    keyed = "--keyed" in sys.argv
    run = "keyed" if keyed else "nokey"
    messages = build_messages()
    wanted = {m["correlation_id"] for m in messages}

    consumer = AIOKafkaConsumer(bootstrap_servers=BOOTSTRAP)
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await consumer.start()
    await producer.start()
    drafts_partition = TopicPartition(DRAFTS, 0)
    consumer.assign([drafts_partition])
    await consumer.seek_to_end(drafts_partition)

    for m in messages:
        key = m["entity"].encode() if keyed else None
        sent = await producer.send_and_wait(TASKS, encode(m), key=key)
        log("ORDER", f"sent {m['entity']} seq={m['seq']} key={key} partition={sent.partition} offset={sent.offset}")

    rows = []
    async for msg in consumer:
        draft = json.loads(msg.value)
        if draft["correlation_id"] not in wanted:
            continue
        rows.append(
            {
                "processed_order": len(rows) + 1,
                "entity": draft["entity"],
                "seq": draft["seq"],
                "task_partition": draft["task_partition"],
                "task_offset": draft["task_offset"],
                "writer": draft["writer"],
                "finished_at": datetime.now().isoformat(timespec="milliseconds"),
                "correlation_id": draft["correlation_id"],
            }
        )
        r = rows[-1]
        log("ORDER", f"#{r['processed_order']} {r['entity']} seq={r['seq']} partition={r['task_partition']} by {r['writer']}")
        if len(rows) == len(messages):
            break
    await consumer.stop()
    await producer.stop()

    with open(OUT_DIR / f"ordering_{run}.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSummary ({run}):")
    for product in PRODUCTS:
        seqs = [r["seq"] for r in rows if r["entity"] == product]
        parts = sorted({r["task_partition"] for r in rows if r["entity"] == product})
        print(f"  {product:28} processed seq order {seqs}  partitions {parts}  in order: {seqs == sorted(seqs)}")


if __name__ == "__main__":
    asyncio.run(main())
