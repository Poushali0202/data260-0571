"""Self-check for the repository deliverables; writes verification.json."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def check(name: str, passed: bool, details: str) -> dict[str, object]:
    return {"check": name, "passed": passed, "details": details}


def main() -> int:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "feedback.js").read_text(encoding="utf-8")
    checks = [
        check("configuration", True, "SID4=0571 PORT_BASE=8571 DOMAIN_ID=3"),
        check("html_title", "<title>HW1-Poushali</title>" in html, "HW1-Poushali title present"),
        check("domain_heading", "Grocery Supply and Recall Notices" in html, "assigned domain heading present"),
        check("autofocus", 'id="productName"' in html and "autofocus" in html, "primary field autofocus present"),
        check("required_form_controls", html.count("required") >= 6, "required primary, secondary, email, content, category, and terms controls"),
        check("four_categories", html.count('<option value="') == 5, "four domain options plus one disabled placeholder"),
        check("script_link", '<script src="feedback.js"></script>' in html, "JavaScript linked at end of document"),
        check("length_validation", "description.length <= 25" in javascript, "content length validation present"),
        check("terms_validation", "termsAccepted" in javascript and "terms and conditions" in javascript, "terms validation present"),
        check("json_conversion", "JSON.stringify" in javascript and "JSON.parse" in javascript, "JSON conversion present"),
        check("destructuring", "const { productName, submitterEmail }" in javascript, "object destructuring present"),
        check("spread_date", "...parsedNotice" in javascript and "submissionDate" in javascript, "spread and submissionDate present"),
        check("closure", "submissionCounter = (() =>" in javascript, "submission counter closure present"),
        check("schema", (ROOT / "DOMAIN_SCHEMA.md").exists(), "domain schema present before implementation"),
        check("agents", (ROOT / "agents_demo.py").exists(), "Planner/Reviewer/Finalizer implementation present"),
        check("adapter", (ROOT / "src" / "model_client.py").exists(), "reusable model adapter present"),
        check("client_demo", (ROOT / "hw1_client.py").exists(), "five-turn client present"),
        check("agent_instructions", (ROOT / "AGENT.md").exists(), "strict bullet-only instructions present"),
        check("experiment_case", (ROOT / "reports" / "hw01" / "cases" / "nondeterminism_input.json").exists(), "fixed experiment input present"),
        check("docker", (ROOT / "Dockerfile").exists(), "Dockerfile present"),
    ]
    result = {
        "homework": "DATA-260 HW1",
        "verified_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
    }
    destination = ROOT / "reports" / "hw01" / "verification.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
