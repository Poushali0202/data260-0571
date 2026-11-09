import json
import re
from pathlib import Path

REFERENCE = json.loads((Path(__file__).parent / "reference_data.json").read_text())

NO_RECORD_PHRASES = [
    "no record", "not found", "not in the", "no information", "does not exist", "doesn't exist",
    "could not find", "couldn't find", "no notice", "not available", "no data", "no details",
]

FEEDBACK = {
    "lot_total": "The total across all lots of {code} is missing or wrong. Add the units of every lot in the record.",
    "lot_gap": "The difference between the lot total and the affected units of {code} is missing or wrong. "
               "Add all lot units first, then subtract.",
    "lot_average": "The average units per lot of {code} is missing or wrong. "
                   "Add all lot units, then divide by the number of lots.",
    "largest_lot": "The lot with the most units for {code} is missing or wrong. Compare the units of every lot.",
    "affected_units": "The affected units for {code} are missing or wrong. "
                      "Use the affected units field of the notice, not the lot units.",
    "supplier": "The supplier name for {code} is missing or wrong. Use the supplier in the record.",
    "region": "The supplier region for {code} is missing or wrong. Use the region in brackets after the supplier.",
    "source": "The notice source for {code} is missing or wrong. Use the source field of the record.",
    "product": "The product for {code} is missing or wrong. Use the product field of the record.",
    "no_record": "{code} is not in the reference data. Say the notice has no record and do not give any details.",
}


def clean(text):
    return re.sub(r"(?<=\d),(?=\d{3})", "", text).lower()


def evaluate(question_id, answer):
    item = REFERENCE["questions"][question_id]
    code = item["notice"]
    facts = REFERENCE["notices"].get(code)
    text = clean(answer)
    failed = []
    for field in item["check"]:
        if field == "no_record":
            ok = any(p in text for p in NO_RECORD_PHRASES) and "lot-" not in text
        elif isinstance(facts[field], int):
            ok = re.search(rf"(?<![\d.]){facts[field]}(?!\d)", text) is not None
        else:
            ok = str(facts[field]).lower() in text
        if not ok:
            failed.append(field)

    if not failed:
        explanation = f"The answer matches the reference facts for {code}."
        return {"result": "PASS", "explanation": explanation, "feedback": None, "failed": []}
    expected = "no record" if facts is None else ", ".join(f"{f} = {facts[f]}" for f in failed)
    return {
        "result": "REVISE",
        "explanation": f"Checked against the reference for {code}: expected {expected}.",
        "feedback": " ".join(FEEDBACK[f].format(code=code) for f in failed),
        "failed": failed,
    }
