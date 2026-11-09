import asyncio
import json
import sys
import uuid

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, TopicPartition

from kafka_common import BOOTSTRAP, FINAL, INBOX, encode, log

DEFAULT_QUESTION = (
    "A shopper bought spinach that is now under a recall notice. What should they check and what should they do with it?"
)


async def ask_pipeline(question, facts=""):
    correlation_id = str(uuid.uuid4())

    consumer = AIOKafkaConsumer(bootstrap_servers=BOOTSTRAP)
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await consumer.start()
    await producer.start()
    final_partition = TopicPartition(FINAL, 0)
    consumer.assign([final_partition])
    await consumer.seek_to_end(final_partition)

    try:
        message = {"correlation_id": correlation_id, "question": question, "facts": facts}
        sent = await producer.send_and_wait(INBOX, encode(message))
        log("YOU", f"sent question to {INBOX} offset={sent.offset} correlation_id={correlation_id}")
        log("YOU", f"waiting for the answer on {FINAL}")
        async for msg in consumer:
            final = json.loads(msg.value)
            if final.get("correlation_id") == correlation_id:
                log("YOU", f"received from {FINAL} offset={msg.offset} correlation_id={correlation_id}")
                return final
    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUESTION
    print(json.dumps(asyncio.run(ask_pipeline(question)), indent=2))
