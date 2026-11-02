import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import FastAPI

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
PORT = 8571
PREFIX = "s0571"
REQUEST_TOPIC = f"{PREFIX}_notice_requests"
RESPONSE_TOPIC = f"{PREFIX}_notice_responses"
TIMEOUT_SECONDS = 10

producer = AIOKafkaProducer(bootstrap_servers=BOOTSTRAP)
consumer = AIOKafkaConsumer(RESPONSE_TOPIC, bootstrap_servers=BOOTSTRAP, auto_offset_reset="latest")
pending = {}


def log(text):
    print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} [API] {text}", flush=True)


async def read_responses():
    async for msg in consumer:
        response = json.loads(msg.value)
        correlation_id = response.get("correlation_id")
        log(
            f"received from {msg.topic} partition={msg.partition} offset={msg.offset} "
            f"correlation_id={correlation_id} success={response.get('success')}"
        )
        future = pending.pop(correlation_id, None)
        if future and not future.done():
            future.set_result(response)


@asynccontextmanager
async def lifespan(app):
    await producer.start()
    await consumer.start()
    task = asyncio.create_task(read_responses())
    log(f"FastAPI server started at http://127.0.0.1:{PORT}")
    yield
    task.cancel()
    await consumer.stop()
    await producer.stop()


app = FastAPI(title="s0571 notice service", lifespan=lifespan)


@app.post("/notices")
async def notice_operation(body: dict):
    correlation_id = body.get("correlation_id") or str(uuid.uuid4())
    message = {
        "correlation_id": correlation_id,
        "reply_to": RESPONSE_TOPIC,
        "operation": body.get("operation"),
        "data": body.get("data", {}),
    }
    future = asyncio.get_running_loop().create_future()
    pending[correlation_id] = future

    sent = await producer.send_and_wait(REQUEST_TOPIC, json.dumps(message).encode())
    log(
        f"sent to {sent.topic} partition={sent.partition} offset={sent.offset} "
        f"correlation_id={correlation_id} message={json.dumps(message)}"
    )
    try:
        response = await asyncio.wait_for(future, TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        pending.pop(correlation_id, None)
        response = {"correlation_id": correlation_id, "success": False, "error": "Timed out waiting for worker"}
    log(f"returned response to caller correlation_id={correlation_id}")
    return response
