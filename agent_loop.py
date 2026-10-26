import json
import time

from domain_tools import TOOL_SPECS, execute_tool

SYSTEM_PROMPT = (
    "You are an assistant for grocery supply and recall notices. Use the tools to look up data and answer only "
    "from tool results. Notice ids and supplier ids are integers. When the question needs several lookups, make "
    "all of them before answering. When you have what you need, answer in two to four plain sentences."
)
TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "object": dict, "array": list}


def check_call(name, args, specs):
    spec = next((s["function"] for s in specs if s["function"]["name"] == name), None)
    if spec is None:
        names = [s["function"]["name"] for s in specs]
        return "unknown_tool", f"There is no tool called '{name}'. Use one of {names}."
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return "malformed_arguments", f"The arguments for {name} are not valid JSON: {args[:100]}"
    if not isinstance(args, dict):
        return "malformed_arguments", f"The arguments for {name} must be a JSON object."
    params = spec["parameters"]
    missing = [key for key in params.get("required", []) if key not in args]
    if missing:
        return "malformed_arguments", f"{name} is missing the required argument(s) {missing}."
    for key, value in args.items():
        prop = params["properties"].get(key)
        if prop is None:
            return "malformed_arguments", f"{name} has no argument '{key}'. Allowed: {list(params['properties'])}."
        expected = TYPES[prop["type"]]
        if not isinstance(value, expected) or (isinstance(value, bool) and prop["type"] != "boolean"):
            return "malformed_arguments", f"Argument '{key}' of {name} must be of type {prop['type']}, got {value!r}."
    return None, None


def run_agent(user_input, model=None, execute=execute_tool, specs=TOOL_SPECS, system_prompt=SYSTEM_PROMPT,
              max_steps=8, max_repairs=2, max_tool_calls=None, max_tokens=None, extra_messages=(), log=print):
    if model is None:
        from src.model_client import ModelClient
        model = ModelClient(temperature=0.7, num_ctx=4096, num_predict=400)
    messages = [{"role": "system", "content": system_prompt}, *extra_messages, {"role": "user", "content": user_input}]
    calls, failures = [], []
    tokens = 0
    answer, stop_reason = "", "max_steps"
    started = time.perf_counter()

    for step in range(1, max_steps + 1):
        response = model.complete(messages, tools=specs)
        tokens += response.total_tokens
        if max_tokens and tokens > max_tokens:
            stop_reason = "budget_exhausted"
            break
        message = response.raw.get("message", {})
        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            if "<tool_call>" in response.text:
                problem = ("malformed_arguments", "Your tool call could not be parsed. Send it again as a proper tool call.")
            elif not calls:
                problem = ("text_instead_of_tool", "Answer only from tool results. Call a tool first.")
            else:
                answer, stop_reason = response.text, "final_answer"
                break
            failures.append({"step": step, "kind": problem[0], "detail": problem[1]})
            log(f"  repair: {problem[0]}: {problem[1]}")
            if len(failures) > max_repairs:
                stop_reason = "repair_failed"
                break
            messages.append({"role": "assistant", "content": response.text})
            messages.append({"role": "user", "content": problem[1]})
            continue

        messages.append({"role": "assistant", "content": message.get("content", ""), "tool_calls": tool_calls})
        for call in tool_calls:
            if max_tool_calls and len(calls) >= max_tool_calls:
                stop_reason = "budget_exhausted"
                break
            name = call["function"]["name"]
            args = call["function"].get("arguments") or {}
            kind, problem = check_call(name, args, specs)
            if kind:
                failures.append({"step": step, "kind": kind, "detail": problem, "tool": name, "args": args})
                log(f"  repair: {kind}: {problem}")
                error = json.dumps({"error": problem + " Fix it and call again."})
                messages.append({"role": "tool", "tool_name": name, "content": error})
                continue
            if isinstance(args, str):
                args = json.loads(args)
            result = execute(name, args)
            calls.append({"step": step, "tool": name, "args": args, "result": result})
            log(f"  tool #{len(calls)} {name} {json.dumps(args)} -> {result[:160]}")
            messages.append({"role": "tool", "tool_name": name, "content": result})

        if stop_reason == "budget_exhausted":
            break
        if len(failures) > max_repairs:
            stop_reason = "repair_failed"
            break

    log(f"  total tool calls: {len(calls)}, stop: {stop_reason}")
    return {
        "input": user_input,
        "answer": answer,
        "stop_reason": stop_reason,
        "tool_calls": calls,
        "failures": failures,
        "tokens": tokens,
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "model_calls": step,
    }


if __name__ == "__main__":
    import sys

    run = run_agent(" ".join(sys.argv[1:]))
    print(run["answer"])
