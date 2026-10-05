import json

from agent import run_agent

SCENARIOS = [
    ("Is there a recall notice for baby spinach? Give me the newest one.", 5),
    ("Show me the details of notice 4990 and tell me which supplier it belongs to.", 5),
    ("How many notices does supplier 3 have and how many units are affected in total?", 5),
    ("Has ibuprofen been recalled recently?", 5),
    ("Find milk notices, open the newest one, then summarise its supplier.", 2),
]

for user_input, max_steps in SCENARIOS:
    print(f"\n=== {user_input} (max_steps={max_steps}) ===")
    run = run_agent(user_input, max_steps=max_steps)
    for step in run["steps"]:
        if "tool" in step:
            print(f"step {step['step']}: {step['tool']}({json.dumps(step['inputs'])}) -> {json.dumps(step['result'])[:200]}")
    print(f"stop_reason={run['stop_reason']} steps_used={run['steps_used']} tool_calls={run['tool_calls']} seconds={run['seconds']}")
    print("answer:", run["answer"])
