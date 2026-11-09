import asyncio
import json

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from kafka_common import BOOTSTRAP, INBOX, PREFIX, TASKS, encode, log, short
from src.model_client import ModelClient

SYSTEM = (
    "You are the Planner for a grocery recall notice help desk. Write a plan of 2 to 4 short "
    "numbered steps that a writer should follow to answer the question. Do not answer it yourself."
)

llm = ModelClient(num_predict=150)


def make_plan(question):
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    return llm.complete(messages).text


async def main():
    consumer = AIOKafkaConsumer(
        INBOX, bootstrap_servers=BOOTSTRAP, group_id=f"{PREFIX}-planner", auto_offset_reset="earliest", enable_auto_commit=False
    )
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await consumer.start()
    await producer.start()
    log("PLANNER", f"listening on {INBOX}")
    try:
        async for msg in consumer:
            question = json.loads(msg.value)
            correlation_id = question["correlation_id"]
            log(
                "PLANNER",
                f"received from {INBOX} offset={msg.offset} correlation_id={correlation_id} "
                f"question={short(question['question'])}",
            )
            plan = await asyncio.to_thread(make_plan, question["question"])
            task = {**question, "plan": plan}
            sent = await producer.send_and_wait(TASKS, encode(task))
            log(
                "PLANNER",
                f"sent plan to {TASKS} partition={sent.partition} offset={sent.offset} "
                f"correlation_id={correlation_id} plan={short(plan)}",
            )
            await consumer.commit()
    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
