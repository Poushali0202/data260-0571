import json
import subprocess
import time
import uuid
from datetime import datetime

import requests

API_URL = "http://127.0.0.1:8571/notices"
CONTAINERS = ["s0571-notice-api", "s0571-notice-worker"]


def stamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def service_logs(correlation_id, since):
    lines = []
    for name in CONTAINERS:
        out = subprocess.run(["docker", "logs", "-t", "--since", since, name], capture_output=True, text=True)
        lines += [line for line in (out.stdout + out.stderr).splitlines() if correlation_id in line]
    return [line.split(" ", 1)[1] for line in sorted(lines)]


def call(operation, data):
    correlation_id = str(uuid.uuid4())
    body = {"correlation_id": correlation_id, "operation": operation, "data": data}
    print(f"{stamp()} [CLIENT] created correlation_id={correlation_id} for {operation}")
    print(f"{stamp()} [CLIENT] POST {API_URL}")
    since = str(int(time.time()) - 1)
    response = requests.post(API_URL, json=body, timeout=15).json()
    received = f"{stamp()} [CLIENT] received response success={response['success']} correlation_id={response['correlation_id']}"
    time.sleep(1)
    for line in service_logs(correlation_id, since):
        print(line)
    print(received)
    same = response.get("correlation_id") == correlation_id
    print(f"{stamp()} [CLIENT] correlation_id preserved: {same}")
    return response, same


print("=== CREATE_NOTICE ===")
notice = {
    "productName": "Organic baby spinach 5 oz",
    "noticeCode": "RN-000571",
    "noticeSource": "FDA recall bulletin",
    "noticeCategory": "recall",
    "affectedUnits": 1200,
}
created, create_ok = call("CREATE_NOTICE", notice)
notice_id = created["notice_id"]
print(f"{stamp()} [CLIENT] generated notice_id={notice_id}")

print("\n=== GET_NOTICE ===")
fetched, get_ok = call("GET_NOTICE", {"notice_id": notice_id})
print("\nRetrieved notice:")
print(json.dumps(fetched["notice"]))
print(
    f"CREATE success={created['success']} GET success={fetched['success']} "
    f"correlation_id preserved on both requests: {create_ok and get_ok}"
)
