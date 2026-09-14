from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Annotated, Any, Dict, List, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, StringConstraints, ValidationError, field_validator

from src.model_client import ModelClient


class AgentState(TypedDict):
    title: str
    content: str
    email: str
    strict: bool
    task: str
    llm: Any
    planner_proposal: Dict[str, Any]
    reviewer_feedback: Dict[str, Any]
    turn_count: int
    max_turns: int
    validation_errors: List[str]
    force_issue: bool


Tag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=30)]


class PlannerOutput(BaseModel):
    tags: List[Tag] = Field(min_length=3, max_length=3)
    summary: str

    @field_validator("summary")
    @classmethod
    def at_most_25_words(cls, summary: str) -> str:
        count = len(summary.split())
        if count > 25:
            raise ValueError(f"summary has {count} words, the limit is 25")
        return summary


def describe(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in item['loc']) or 'output'}: {item['msg']}"
        for item in error.errors()
    )


def planner_node(state: AgentState) -> Dict[str, Any]:
    print("--- NODE: Planner ---")
    request = f"Title: {state['title']}\nContent: {state['content']}"
    if not state["planner_proposal"] and state["validation_errors"]:
        request += (
            "\n\nYour previous reply was rejected by the schema validator: "
            f"{state['validation_errors'][-1]}. Fix that problem and reply again."
        )
    issues = state["reviewer_feedback"].get("issues", [])
    if issues:
        request += (
            f"\n\nYour previous proposal was {json.dumps(state['planner_proposal'])}. "
            "The Reviewer found these issues:\n- " + "\n- ".join(issues)
            + "\nRevise the proposal to fix them."
        )
    response = state["llm"].complete(
        [
            {
                "role": "system",
                "content": (
                    f"You are the Planner agent. {state['task']} Reply with one JSON object of the form "
                    '{"tags": ["...", "...", "..."], "summary": "..."}: exactly three tags, each 3 to 30 '
                    "characters, and a one-sentence summary of at most 25 words. No other keys."
                ),
            },
            {"role": "user", "content": request},
        ],
        response_format="json",
    )
    try:
        proposal = PlannerOutput.model_validate_json(response.text).model_dump()
    except ValidationError as error:
        print(f"Planner output rejected: {describe(error)}")
        return {
            "planner_proposal": {},
            "reviewer_feedback": {},
            "validation_errors": state["validation_errors"] + [describe(error)],
        }
    return {"planner_proposal": proposal, "reviewer_feedback": {}}


def reviewer_node(state: AgentState) -> Dict[str, Any]:
    print("--- NODE: Reviewer ---")
    if state["force_issue"]:
        return {"reviewer_feedback": {"issues": ["Forced issue to exercise the correction loop."]}}
    rules = (
        "Flag a tag only when the content does not support it, and flag the summary "
        "only when it misstates the content."
    )
    if state["strict"]:
        rules += " Also flag generic tags such as 'food' or 'news' that do not name the product or event."
    response = state["llm"].complete(
        [
            {
                "role": "system",
                "content": (
                    f"You are the Reviewer agent for grocery supply and recall notices. {rules} "
                    'Reply with one JSON object of the form {"issues": ["short description of each problem"]}. '
                    "Use an empty list when the proposal is acceptable."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Title: {state['title']}\nContent: {state['content']}\n"
                    f"Planner proposal: {json.dumps(state['planner_proposal'])}"
                ),
            },
        ],
        response_format="json",
    )
    try:
        issues = json.loads(response.text).get("issues", [])
    except (json.JSONDecodeError, AttributeError):
        issues = []
    if not isinstance(issues, list):
        issues = [issues]
    return {"reviewer_feedback": {"issues": [str(issue) for issue in issues]}}


def supervisor_node(state: AgentState) -> Dict[str, Any]:
    turn = state["turn_count"] + 1
    print(f"--- NODE: Supervisor (turn {turn}, ceiling {state['max_turns']}) ---")
    return {"turn_count": turn}


def router_logic(state: AgentState) -> str:
    proposal = state["planner_proposal"]
    feedback = state["reviewer_feedback"]
    if proposal and feedback and not feedback["issues"]:
        print("Router: reviewer approved the proposal, finishing")
        return END
    if state["turn_count"] > state["max_turns"]:
        print("Router: turn ceiling reached, giving up")
        return END
    if not proposal:
        print("Router: no valid proposal, sending to planner")
        return "planner"
    if not feedback:
        print("Router: proposal not reviewed yet, sending to reviewer")
        return "reviewer"
    print("Router: reviewer found issues, sending back to planner")
    return "planner"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("planner", planner_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        router_logic,
        {"planner": "planner", "reviewer": "reviewer", END: END},
    )
    graph.add_edge("planner", "supervisor")
    graph.add_edge("reviewer", "supervisor")
    return graph.compile()


def run_graph(
    title: str,
    content: str,
    email: str,
    model: str = "qwen3:8b",
    base_url: str = "http://localhost:11434",
    temperature: float = 0.7,
    max_turns: int = 6,
    strict: bool = False,
    force_issue: bool = False,
) -> dict[str, Any]:
    llm = ModelClient(model=model, base_url=base_url, temperature=temperature)
    state: AgentState = {
        "title": title,
        "content": content,
        "email": email,
        "strict": strict,
        "task": "Propose three topical tags and a one-sentence summary for a grocery supply or recall notice.",
        "llm": llm,
        "planner_proposal": {},
        "reviewer_feedback": {},
        "turn_count": 0,
        "max_turns": max_turns,
        "validation_errors": [],
        "force_issue": force_issue,
    }
    node_calls: Counter[str] = Counter()
    started = time.perf_counter()
    for step in build_graph().stream(state, config={"recursion_limit": 100}, stream_mode="updates"):
        for node, update in step.items():
            node_calls[node] += 1
            state.update(update)
            print(f"[{node}] {json.dumps(update, ensure_ascii=False)}")
    feedback = state["reviewer_feedback"]
    approved = bool(state["planner_proposal"]) and bool(feedback) and not feedback["issues"]
    return {
        "title": title,
        "email": email,
        "content": content,
        "outcome": "done" if approved else "ceiling",
        "planner_proposal": state["planner_proposal"],
        "reviewer_feedback": feedback,
        "turn_count": state["turn_count"],
        "max_turns": max_turns,
        "planner_calls": node_calls["planner"],
        "reviewer_calls": node_calls["reviewer"],
        "validation_failures": len(state["validation_errors"]),
        "validation_errors": state["validation_errors"],
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "input_tokens": llm.input_tokens,
        "output_tokens": llm.output_tokens,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument("--email", default="poushali@example.com")
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-turns", type=int, default=6)
    parser.add_argument("--strict", action="store_true", help="reviewer also rejects generic tags")
    parser.add_argument("--force-issue", action="store_true", help="reviewer always reports an issue")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        result = run_graph(
            args.title, args.content, args.email, args.model, args.base_url,
            args.temperature, args.max_turns, args.strict, args.force_issue,
        )
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 2
    print("\n--- Final result ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
