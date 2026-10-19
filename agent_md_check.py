import ast
import json
import re
import subprocess
import sys
from pathlib import Path

from src.model_client import ModelClient

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reports" / "hw06" / "raw"
TASK = (
    "Implement the function notice_age_days(notice_date, today) that returns the number of whole days "
    "between a notice date and today, both datetime objects, and raises ValueError when today is earlier "
    "than the notice date. Follow every instruction in AGENT.md. Return only Python code with the imports, "
    "the function and its test function. No explanation and no markdown fences."
)
SNAKE = re.compile(r"^[a-z_][a-z0-9_]*$")


def generate():
    agent = (ROOT / "AGENT.md").read_text(encoding="utf-8")
    model = ModelClient(num_ctx=8192, num_predict=400)
    response = model.complete([{"role": "system", "content": agent}, {"role": "user", "content": TASK}])
    code = response.text
    if "```" in code:
        code = code.split("```")[1]
        code = code[len("python"):] if code.startswith("python") else code
    return code.strip() + "\n"


def check_rules(code):
    tree = ast.parse(code)
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    main = [f for f in functions if not f.name.startswith("test_")]
    tests = [f for f in functions if f.name.startswith("test_")]
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    raises = [node for node in ast.walk(tree) if isinstance(node, ast.Raise)]
    return {
        "function_notice_age_days_exists": any(f.name == "notice_age_days" for f in functions),
        "snake_case_names": all(SNAKE.match(f.name) for f in functions),
        "type_hints_on_parameters_and_return": all(
            f.returns is not None and all(arg.annotation is not None for arg in f.args.args) for f in main),
        "docstring_present": all(ast.get_docstring(f) for f in main),
        "no_print_calls": not any(isinstance(c.func, ast.Name) and c.func.id == "print" for c in calls),
        "raises_value_error": any("ValueError" in ast.dump(r) for r in raises),
        "test_function_with_assert": any(any(isinstance(n, ast.Assert) for n in ast.walk(t)) for t in tests),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    code = generate()
    path = OUT / "generated_function.py"
    path.write_text(code, encoding="utf-8")
    results = check_rules(code)
    run = subprocess.run([sys.executable, "-c", code + "\nimport sys\n"
                          + "\n".join(f"{f}()" for f in re.findall(r"^def (test_\w+)\(", code, re.M))],
                         capture_output=True, text=True, timeout=60)
    results["tests_run_and_pass"] = run.returncode == 0
    for name, passed in results.items():
        print(f"{'PASS' if passed else 'FAIL'} {name}")
    print(f"{sum(results.values())}/{len(results)} rules followed, code saved to {path}")
    if run.returncode != 0:
        print(run.stderr.strip()[-500:])
    (OUT / "agent_md_check.json").write_text(json.dumps({"task": TASK, "rules": results, "stderr": run.stderr[-500:]}, indent=2) + "\n", encoding="utf-8")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
