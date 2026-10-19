import csv
import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import yaml

BASE_URL = "http://127.0.0.1:8571"
RAW = Path(__file__).resolve().parent / "reports" / "hw06" / "raw"
TURNS_CSV = RAW / "sweep_turns.csv"
SETTINGS = [("n4", 4, "none"), ("n12", 12, "none"), ("n30", 30, "none"), ("n30_compress", 30, "compress_old")]
FIELDS = ["setting", "short_term_n", "policy", "kind", "turn", "probe_id", "message", "reply", "prompt_tokens",
          "completion_tokens", "primer_tokens", "summary_tokens", "window_tokens", "episodes_tokens",
          "message_tokens", "latency_ms", "model_latency_ms", "aux_prompt_tokens", "aux_completion_tokens",
          "summaries_written", "short_term_count", "episodes_retrieved"]

CONVERSATION = [
    "Hi, I am Maya Chen and I manage the Willow Glen Market in San Jose.",
    "We got a recall notice this morning for organic baby spinach from Green Valley Farms, lot GV-2291.",
    "The notice code is RN-004410 and the source is the FDA recall bulletin.",
    "What should I do with the affected bags first?",
    "We have 48 bags on the shelf and 120 more in the back room.",
    "Please remember that I prefer to get follow-ups by email, not by phone.",
    "Our produce supplier contact is Luis at Green Valley Farms, his number ends in 7781.",
    "Which categories of notices does the system track?",
    "There is also a shortage of whole milk from Dairy Fresh Co-op this week.",
    "They said the milk shortage should be over by Friday.",
    "Can you explain the difference between a recall and a contamination warning?",
    "My assistant manager is Daniel, he handles the night shift.",
    "We set the spinach notice status to investigating for now.",
    "How long should I keep the recall paperwork?",
    "Our store code is WG-17, you may need it for reports.",
    "Customers asked whether frozen berries are affected too. They are not, right?",
    "The spinach lot GV-2291 was delivered on October 12.",
    "I also want a weekly summary of open notices every Monday.",
    "What is a good way to tell staff about a new recall quickly?",
    "We pulled all 168 spinach bags and moved them to the quarantine cage.",
    "How do I record the destroyed units?",
    "Update from Green Valley Farms: the contamination was Listeria.",
    "Should we notify customers who bought spinach last week?",
    "We use a loyalty card system, so we can find the buyers.",
    "What should the customer notice say?",
    "Daniel will post the notice at the entrance tonight.",
    "One more thing: the frozen berries shortage from last month is resolved.",
    "Can you list the notices we discussed today?",
    "Which one is the most urgent?",
    "Thanks. Mark the milk shortage as closed.",
]


def post_chat(body):
    data = json.dumps(body).encode()
    request = urllib.request.Request(BASE_URL + "/api/chat", data=data, method="POST",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=900) as response:
        return json.loads(response.read().decode())


def load_rows():
    if not TURNS_CSV.exists():
        return []
    with TURNS_CSV.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def append_row(row):
    new_file = not TURNS_CSV.exists()
    with TURNS_CSV.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def run_turn(setting, n, policy, kind, turn, probe_id, message):
    body = {"user_id": f"sweep_{setting}", "session_id": f"{setting}-session", "message": message,
            "short_term_n": n, "policy": policy}
    started = time.perf_counter()
    result = post_chat(body)
    usage = result["usage"]
    row = {"setting": setting, "short_term_n": n, "policy": policy, "kind": kind, "turn": turn, "probe_id": probe_id,
           "message": message, "reply": result["reply"], "short_term_count": result["used"]["short_term"]["count"],
           "episodes_retrieved": len(result["used"]["episodes"])}
    for field in FIELDS:
        if field in usage:
            row[field] = usage[field]
    append_row(row)
    print(f"{datetime.now().isoformat(timespec='seconds')} {setting} {kind} {turn} {probe_id or ''} "
          f"prompt={usage['prompt_tokens']} completion={usage['completion_tokens']} "
          f"latency={usage['latency_ms']}ms wall={time.perf_counter() - started:.1f}s", flush=True)


def main():
    probes = yaml.safe_load((Path(__file__).resolve().parent / "memory_probes.yaml").read_text(encoding="utf-8"))["probes"]
    RAW.mkdir(parents=True, exist_ok=True)
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 1e9
    deadline = time.time() + budget * 60
    done = {(r["setting"], r["kind"], r["turn"], r["probe_id"]) for r in load_rows()}
    for setting, n, policy in SETTINGS:
        for turn, message in enumerate(CONVERSATION, start=1):
            if (setting, "conversation", str(turn), "") in done:
                continue
            if time.time() > deadline:
                print("time budget used, rerun to continue")
                return
            run_turn(setting, n, policy, "conversation", turn, "", message)
        for index, probe in enumerate(probes, start=1):
            if (setting, "probe", str(index), probe["id"]) in done:
                continue
            if time.time() > deadline:
                print("time budget used, rerun to continue")
                return
            run_turn(setting, n, policy, "probe", index, probe["id"], probe["question"])
    print("sweep complete")


if __name__ == "__main__":
    main()
