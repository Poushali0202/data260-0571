import difflib
import json
import re
import subprocess
import tempfile
from pathlib import Path

SANDBOX = Path(tempfile.gettempdir()) / "data260_sandbox"
SAFE_PREFIXES = ("ls", "cat", "echo", "pwd", "head", "tail", "wc", "grep", "find", "git status", "git log", "git diff")
DESTRUCTIVE = [
    ("recursive deletion", r"\brm\s+(-[a-zA-Z]*[rR]|--recursive)|\bfind\b.*\s-delete\b"),
    ("privilege escalation", r"\bsudo\b|\bsu\s"),
    ("permission or ownership change", r"\bchmod\b|\bchown\b"),
    ("raw device write", r"\bof=/dev/"),
    ("filesystem creation", r"\bmkfs"),
    ("redirection to a root path", r">\s*/(?!tmp/|dev/null)"),
]


def inside_sandbox(path):
    full = (SANDBOX / path).resolve()
    if not full.is_relative_to(SANDBOX.resolve()):
        raise ValueError(f"{path} is outside the sandbox")
    return full


def read_file(path, max_lines=None):
    lines = inside_sandbox(path).read_text(encoding="utf-8").splitlines()
    shown = lines[:max_lines] if max_lines else lines
    return {"path": path, "lines": len(lines), "content": "\n".join(shown), "truncated": len(shown) < len(lines)}


def write_file(path, content):
    full = inside_sandbox(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return {"path": path, "bytes": len(content.encode())}


def edit_file(path, old, new):
    full = inside_sandbox(path)
    before = full.read_text(encoding="utf-8")
    if before.count(old) != 1:
        raise ValueError(f"old text must appear exactly once in {path}, found {before.count(old)}")
    after = before.replace(old, new)
    full.write_text(after, encoding="utf-8")
    diff = difflib.unified_diff(before.splitlines(), after.splitlines(), path, path, n=0, lineterm="")
    return {"path": path, "diff": "\n".join(diff)}


def glob_files(pattern, root="."):
    base = inside_sandbox(root)
    return {"matches": sorted(str(p.relative_to(SANDBOX.resolve())).replace("\\", "/") for p in base.glob(pattern))}


def search_in_files(pattern, root=".", file_pattern="*"):
    hits = []
    for file in sorted(inside_sandbox(root).rglob(file_pattern)):
        if file.is_file():
            for number, line in enumerate(file.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if re.search(pattern, line):
                    hits.append(f"{file.relative_to(SANDBOX.resolve()).as_posix()}:{number}: {line.strip()}")
    return {"pattern": pattern, "hits": hits}


def is_destructive(command):
    return any(re.search(pattern, command) for _, pattern in DESTRUCTIVE)


def confirm_bash(command, auto_approve=False):
    reasons = [name for name, pattern in DESTRUCTIVE if re.search(pattern, command)]
    if reasons:
        if auto_approve:
            return {"allowed": True, "reason": f"destructive ({', '.join(reasons)}) but explicitly confirmed"}
        return {"allowed": False, "reason": f"blocked: {', '.join(reasons)} needs explicit confirmation"}
    if command.strip().startswith(SAFE_PREFIXES):
        return {"allowed": True, "reason": "matches SAFE_PREFIXES"}
    if auto_approve:
        return {"allowed": True, "reason": "not in SAFE_PREFIXES but explicitly confirmed"}
    return {"allowed": False, "reason": "not in SAFE_PREFIXES, needs confirmation"}


def bash(command, auto_approve=False):
    gate = confirm_bash(command, auto_approve)
    if not gate["allowed"]:
        return {"command": command, "ran": False, "reason": gate["reason"]}
    done = subprocess.run(command, shell=True, cwd=SANDBOX, capture_output=True, text=True, timeout=30)
    return {"command": command, "ran": True, "exit_code": done.returncode, "output": (done.stdout + done.stderr)[-2000:]}


FILE_TOOLS = {"read_file": read_file, "write_file": write_file, "edit_file": edit_file, "glob_files": glob_files,
              "search_in_files": search_in_files, "bash": bash}


def spec(name, description, properties, required):
    return {"type": "function", "function": {"name": name, "description": description, "parameters": {
        "type": "object", "required": required, "properties": properties}}}


FILE_TOOL_SPECS = [
    spec("read_file", "Read a text file in the sandbox.",
         {"path": {"type": "string"}, "max_lines": {"type": "integer"}}, ["path"]),
    spec("write_file", "Create or overwrite a file in the sandbox.",
         {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
    spec("edit_file", "Replace one exact occurrence of old with new in a file. Returns a short diff.",
         {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}}, ["path", "old", "new"]),
    spec("glob_files", "List sandbox files matching a glob pattern such as '**/*.py'.",
         {"pattern": {"type": "string"}, "root": {"type": "string"}}, ["pattern"]),
    spec("search_in_files", "Search file contents for a regex. file_pattern limits which files are searched, e.g. '*.py'.",
         {"pattern": {"type": "string"}, "root": {"type": "string"}, "file_pattern": {"type": "string"}}, ["pattern"]),
    spec("bash", "Run a shell command in the sandbox. Only safe commands run without confirmation.",
         {"command": {"type": "string"}}, ["command"]),
]


def execute_file_tool(name, args):
    try:
        return json.dumps({"ok": True, "data": FILE_TOOLS[name](**args), "error": None})
    except Exception as error:
        return json.dumps({"ok": False, "data": None, "error": f"{type(error).__name__}: {error}"})
