import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from domain_tools import TOOL_SPECS, execute_tool

LOG_PATH = Path(__file__).resolve().parent / "reports" / "hw05" / "raw" / "agent_runs.jsonl"
SYSTEM_PROMPT = (
    "You are an assistant for grocery supply and recall notices (database s0571_rel). "
    "Use the tools to look up data and answer only from tool results. Notice ids and supplier ids are integers. "
    "When you have what you need, reply to the user in two or three plain sentences without calling more tools."
)


def run_agent(user_input, model=None, max_steps=5, store=None, log_path=LOG_PATH):
    if model is None:
        from src.model_client import ModelClient
        model = ModelClient(num_ctx=4096, num_predict=300)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_input}]
    steps = []
    answer = ""
    stop_reason = "max_steps"
    started = time.perf_counter()
    for step in range(1, max_steps + 1):
        response = model.complete(messages, tools=TOOL_SPECS)
        message = response.raw.get("message", {})
        calls = message.get("tool_calls") or []
        if not calls:
            answer = response.text
            steps.append({"step": step, "assistant": answer})
            stop_reason = "completed"
            break
        messages.append({"role": "assistant", "content": message.get("content", ""), "tool_calls": calls})
        blocked = None
        for call in calls:
            name = call["function"]["name"]
            inputs = call["function"].get("arguments") or {}
            result = execute_tool(name, inputs, store)
            parsed = json.loads(result)
            steps.append({"step": step, "tool": name, "inputs": inputs, "result": parsed})
            messages.append({"role": "tool", "content": result, "tool_name": name})
            if parsed["error"] and parsed["error"].startswith("Safety rule"):
                blocked = parsed["error"]
        if blocked:
            answer = blocked
            stop_reason = "safety_block"
            break
    run = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "model": getattr(model, "model", type(model).__name__),
        "user_input": user_input,
        "max_steps": max_steps,
        "steps_used": steps[-1]["step"] if steps else 0,
        "tool_calls": sum(1 for s in steps if "tool" in s),
        "stop_reason": stop_reason,
        "answer": answer,
        "seconds": round(time.perf_counter() - started, 1),
        "steps": steps,
    }
    if log_path:
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(run, default=str) + "\n")
    return run


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("user_input")
    parser.add_argument("--max-steps", type=int, default=5)
    args = parser.parse_args()
    run = run_agent(args.user_input, max_steps=args.max_steps)
    for step in run["steps"]:
        if "tool" in step:
            print(f"step {step['step']}: {step['tool']}({json.dumps(step['inputs'])}) -> {json.dumps(step['result'])[:300]}")
        else:
            print(f"step {step['step']}: answer")
    print(f"stop_reason={run['stop_reason']} steps_used={run['steps_used']} tool_calls={run['tool_calls']} seconds={run['seconds']}")
    print(run["answer"])
