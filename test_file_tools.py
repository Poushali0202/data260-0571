import csv
import json
import shutil
import sys
from pathlib import Path

import file_tools
from file_tools import FILE_TOOL_SPECS, SAFE_PREFIXES, confirm_bash, execute_file_tool, is_destructive

RAW = Path(__file__).resolve().parent / "reports" / "hw07" / "raw"
FILES = {
    "inventory.py": "def total_units(lots):\n    return sum(lot['units'] for lot in lots)\n",
    "notify.py": "import logging\n\nlogging.basicConfig(level=logging.DEBUG)\n\n\ndef send(msg):\n    logging.info(msg)\n",
    "report.py": "def title(name):\n    return name.upper()\n",
}
GATE_CASES = [
    ("ls -la", True),
    ("cat inventory.py", True),
    ("grep -rn total .", True),
    ("echo done > result.txt", True),
    ("git status", True),
    ("ls && rm -Rf ~/projects", False),
    ("sudo chown root:root notify.py", False),
    ("dd if=/dev/zero of=/dev/sda bs=1M", False),
    ("mkfs.ext4 /dev/sdb1", False),
    ("echo pwned > /etc/hosts", False),
]


def integration_test():
    from agent_loop import run_agent

    if file_tools.SANDBOX.exists():
        shutil.rmtree(file_tools.SANDBOX)
    file_tools.SANDBOX.mkdir(parents=True)
    for name, text in FILES.items():
        (file_tools.SANDBOX / name).write_text(text, encoding="utf-8")
    print(f"sandbox: {file_tools.SANDBOX} with {sorted(FILES)}")
    prompt = "List the Python files in the sandbox, find the one that contains DEBUG, and show me its full contents."
    print(f"instruction: {prompt}")
    system = "You work on files in a sandbox using the tools. Use the tools step by step and answer from their results."
    run = run_agent(prompt, execute=execute_file_tool, specs=FILE_TOOL_SPECS, system_prompt=system)
    order = [c["tool"] for c in run["tool_calls"]]
    found = any(c["tool"] == "read_file" and "notify.py" in json.dumps(c["args"]) for c in run["tool_calls"])
    print(f"tool order: {' -> '.join(order)}")
    print(f"answer:\n{run['answer']}")
    print(f"integration result: {'PASS' if found and 'DEBUG' in run['answer'] else 'FAIL'}")
    (RAW / "file_tools_integration.json").write_text(json.dumps(run, indent=2), encoding="utf-8")


def gate_test():
    print(f"SAFE_PREFIXES = {SAFE_PREFIXES}")
    rows = []
    for command, should_pass in GATE_CASES:
        gate = confirm_bash(command)
        if gate["allowed"] == should_pass:
            outcome = "ok"
        else:
            outcome = "FALSE ALLOW" if gate["allowed"] else "FALSE BLOCK"
        rows.append({"command": command, "expected": "allow" if should_pass else "block",
                     "is_destructive": is_destructive(command), "decision": "allow" if gate["allowed"] else "block",
                     "reason": gate["reason"], "outcome": outcome})
        print(f"{command:<38} expected={rows[-1]['expected']:<6} decision={rows[-1]['decision']:<6} "
              f"destructive={str(rows[-1]['is_destructive']):<5} {outcome:<11} {gate['reason']}")
    confirmed = confirm_bash("ls && rm -Rf ~/projects", auto_approve=True)
    print(f"with auto_approve=True: {confirmed}")
    wrong = [r for r in rows if r["outcome"] != "ok"]
    false_allows = [r["command"] for r in wrong if r["outcome"] == "FALSE ALLOW"]
    print(f"gate result: {10 - len(wrong)}/10 correct, false allows: {false_allows}")
    out = RAW / sys.argv[2] if len(sys.argv) > 2 else RAW / "safety_gate_results.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    if "--gate-only" not in sys.argv:
        integration_test()
    gate_test()
