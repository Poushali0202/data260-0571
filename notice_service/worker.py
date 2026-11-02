import asyncio
import json
import os
import re
import uuid
from datetime import datetime

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
PREFIX = "s0571"
REQUEST_TOPIC = f"{PREFIX}_notice_requests"
CATEGORIES = {"recall", "shortage", "contamination", "distribution"}

notices = {}


def log(text):
    print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} [WORKER] {text}", flush=True)


def validate_notice(data):
    for field in ("productName", "noticeCode", "noticeSource", "noticeCategory"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            return f"{field} is required"
    if not re.fullmatch(r"RN-\d{6}", data["noticeCode"]):
        return "noticeCode must look like RN-123456"
    if data["noticeCategory"] not in CATEGORIES:
        return "noticeCategory must be one of: " + ", ".join(sorted(CATEGORIES))
    units = data.get("affectedUnits")
    if not isinstance(units, int) or isinstance(units, bool) or units < 0:
        return "affectedUnits must be a whole number 0 or more"
    return None


def process(operation, data):
    if not isinstance(data, dict):
        return {"success": False, "error": "data must be an object"}

    if operation == "CREATE_NOTICE":
        error = validate_notice(data)
        if error:
            return {"success": False, "error": error}
        notice_id = str(uuid.uuid4())
        notices[notice_id] = {
            "notice_id": notice_id,
            "productName": data["productName"].strip(),
            "noticeCode": data["noticeCode"],
            "noticeSource": data["noticeSource"].strip(),
            "noticeCategory": data["noticeCategory"],
            "affectedUnits": data["affectedUnits"],
        }
        return {"success": True, "notice_id": notice_id, "message": "Notice created"}

    if operation == "GET_NOTICE":
        notice = notices.get(data.get("notice_id"))
        if notice is None:
            return {"success": False, "error": "Notice not found"}
        return {"success": True, "notice": notice}

    return {"success": False, "error": "Unknown operation"}


async def main():
    consumer = AIOKafkaConsumer(
        REQUEST_TOPIC,
        bootstrap_servers=BOOTSTRAP,
        group_id=f"{PREFIX}-notice-worker",
        auto_offset_reset="earliest",
    )
    producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
    await consumer.start()
    await producer.start()
    log("Consumer is ready and listening...")

    try:
        async for msg in consumer:
            try:
                request = json.loads(msg.value)
            except ValueError:
                log(f"skipped bad JSON at offset {msg.offset}")
                continue
            correlation_id = request.get("correlation_id")
            reply_to = request.get("reply_to") or f"{PREFIX}_notice_responses"
            operation = request.get("operation")
            log(
                f"received from {msg.topic} partition={msg.partition} offset={msg.offset} "
                f"correlation_id={correlation_id} operation={operation}"
            )

            result = process(operation, request.get("data"))
            log(f"processed {operation} correlation_id={correlation_id} success={result['success']}")

            response = {"correlation_id": correlation_id, **result}
            sent = await producer.send_and_wait(reply_to, json.dumps(response).encode())
            log(
                f"sent to {sent.topic} partition={sent.partition} offset={sent.offset} "
                f"correlation_id={correlation_id} message={json.dumps(response)}"
            )
    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
