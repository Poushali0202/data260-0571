import asyncio
import json
import sys

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from kafka_common import BOOTSTRAP, TASKS, log


async def main():
    correlation_id = sys.argv[1]
    consumer = AIOKafkaConsumer(TASKS, bootstrap_servers=BOOTSTRAP, auto_offset_reset="earliest")
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await consumer.start()
    await producer.start()
    try:
        original = None
        while original is None:
            batch = await consumer.getmany(timeout_ms=3000)
            if not batch:
                break
            for messages in batch.values():
                for msg in messages:
                    try:
                        if json.loads(msg.value).get("correlation_id") == correlation_id:
                            original = msg
                    except ValueError:
                        pass
        if original is None:
            log("REPLAY", f"no task with correlation_id={correlation_id} in {TASKS}")
            return
        sent = await producer.send_and_wait(TASKS, original.value, key=original.key, partition=original.partition)
        log(
            "REPLAY",
            f"original at {TASKS} partition={original.partition} offset={original.offset}, "
            f"replayed unchanged as offset={sent.offset} correlation_id={correlation_id}",
        )
    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
