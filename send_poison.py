import asyncio
import uuid

from aiokafka import AIOKafkaProducer

from kafka_common import BOOTSTRAP, TASKS, encode, log

KEY = b"poison-test"


async def main():
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await producer.start()
    try:
        bad = b'{"correlation_id": "poison-' + uuid.uuid4().hex[:8].encode() + b'", "question": "Which lots are'
        sent = await producer.send_and_wait(TASKS, bad, key=KEY)
        log("POISON", f"sent malformed task to {TASKS} partition={sent.partition} offset={sent.offset}")

        good = {
            "correlation_id": str(uuid.uuid4()),
            "question": "Which peanut butter lots should a store pull from the shelf after a recall notice?",
            "plan": "1. Say the lot codes are listed on the recall notice.\n2. Tell the store to pull every matching jar.",
        }
        sent = await producer.send_and_wait(TASKS, encode(good), key=KEY)
        log(
            "POISON",
            f"sent normal task behind it partition={sent.partition} offset={sent.offset} correlation_id={good['correlation_id']}",
        )
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
