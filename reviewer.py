import asyncio
import json

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from kafka_common import BOOTSTRAP, DRAFTS, FINAL, PREFIX, encode, log, short
from src.model_client import ModelClient

SYSTEM = (
    "You are the Reviewer. Check that the draft answers the question, follows the plan and does not "
    'invent facts. Reply in JSON with status "approved" or "rejected" and a one sentence note.'
)
REVIEW_FORMAT = {
    "type": "object",
    "properties": {"status": {"type": "string", "enum": ["approved", "rejected"]}, "note": {"type": "string"}},
    "required": ["status", "note"],
}

llm = ModelClient(num_predict=120)


def review(draft):
    content = f"Question: {draft['question']}\n\nPlan:\n{draft['plan']}\n\nDraft:\n{draft['draft']}"
    if draft.get("facts"):
        content += f"\n\nNotice records from the database:\n{draft['facts']}"
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]
    return json.loads(llm.complete(messages, response_format=REVIEW_FORMAT).text)


async def main():
    consumer = AIOKafkaConsumer(
        DRAFTS, bootstrap_servers=BOOTSTRAP, group_id=f"{PREFIX}-reviewer", auto_offset_reset="earliest", enable_auto_commit=False
    )
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await consumer.start()
    await producer.start()
    log("REVIEWER", f"listening on {DRAFTS}")
    try:
        async for msg in consumer:
            draft = json.loads(msg.value)
            correlation_id = draft["correlation_id"]
            log(
                "REVIEWER",
                f"received from {DRAFTS} offset={msg.offset} correlation_id={correlation_id} draft={short(draft['draft'])}",
            )
            verdict = await asyncio.to_thread(review, draft)
            final = {
                "correlation_id": correlation_id,
                "status": verdict["status"],
                "answer": draft["draft"],
                "review_note": verdict["note"],
                "question": draft["question"],
            }
            sent = await producer.send_and_wait(FINAL, encode(final))
            log(
                "REVIEWER",
                f"sent {verdict['status']} to {FINAL} offset={sent.offset} correlation_id={correlation_id} "
                f"note={short(verdict['note'])}",
            )
            await consumer.commit()
    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
