import json
from datetime import datetime

BOOTSTRAP = "localhost:9092"
PREFIX = "s0571"
INBOX = f"{PREFIX}_inbox"
TASKS = f"{PREFIX}_tasks"
DRAFTS = f"{PREFIX}_drafts"
FINAL = f"{PREFIX}_final"
DEAD_LETTER = f"{PREFIX}_dead_letter"


def log(agent, text):
    print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} [{agent}] {text}", flush=True)


def encode(message):
    return json.dumps(message).encode()


def short(text, size=90):
    text = " ".join(str(text).split())
    return text if len(text) <= size else text[:size] + "..."
