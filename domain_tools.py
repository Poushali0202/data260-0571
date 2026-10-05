import json

from sqlalchemy import func
from sqlalchemy.exc import OperationalError

from retry import retry_call

MAX_LIMIT = 50
RETRY_ON = (OperationalError, ConnectionError, TimeoutError, OSError)
MEDICATION_TERMS = ("tablet", "capsule", "ibuprofen", "insulin", "prescription", "medication", "vaccine", "drug")


def envelope(data=None, error=None):
    return {"ok": error is None, "data": data, "error": error}


def notice_row(notice):
    return {
        "id": notice.id,
        "productName": notice.productName,
        "noticeCode": notice.noticeCode,
        "noticeSource": notice.noticeSource,
        "affectedUnits": notice.affectedUnits,
        "supplierId": notice.supplierId,
    }


class MySQLStore:
    def __init__(self):
        from database import db_session_basede26
        from models import GroceryNotice, Supplier
        self.session = db_session_basede26
        self.Notice = GroceryNotice
        self.Supplier = Supplier

    def search(self, term, limit):
        with self.session() as db:
            rows = (db.query(self.Notice)
                    .filter(self.Notice.productName.contains(term) | self.Notice.noticeSource.contains(term))
                    .order_by(self.Notice.id.desc()).limit(limit).all())
            return [notice_row(n) for n in rows]

    def get(self, notice_id):
        with self.session() as db:
            notice = db.get(self.Notice, notice_id)
            if notice is None:
                return None
            row = notice_row(notice)
            row["supplierName"] = notice.supplier.name
            row["createdAt"] = notice.createdAt.isoformat()
            return row

    def summary(self, supplier_id):
        with self.session() as db:
            supplier = db.get(self.Supplier, supplier_id)
            if supplier is None:
                return None
            count, units = (db.query(func.count(self.Notice.id), func.coalesce(func.sum(self.Notice.affectedUnits), 0))
                            .filter(self.Notice.supplierId == supplier_id).one())
            return {"supplierId": supplier.id, "supplierName": supplier.name, "region": supplier.region,
                    "noticeCount": int(count), "totalAffectedUnits": int(units)}


class MemoryStore:
    def __init__(self, notices, suppliers):
        self.notices = notices
        self.suppliers = suppliers

    def search(self, term, limit):
        hits = [n for n in self.notices if term in n["productName"] or term in n["noticeSource"]]
        return sorted(hits, key=lambda n: -n["id"])[:limit]

    def get(self, notice_id):
        return next((n for n in self.notices if n["id"] == notice_id), None)

    def summary(self, supplier_id):
        supplier = next((s for s in self.suppliers if s["id"] == supplier_id), None)
        if supplier is None:
            return None
        mine = [n for n in self.notices if n["supplierId"] == supplier_id]
        return {"supplierId": supplier["id"], "supplierName": supplier["name"], "region": supplier["region"],
                "noticeCount": len(mine), "totalAffectedUnits": sum(n["affectedUnits"] for n in mine)}


def positive_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def search_notices(inputs, store):
    query = inputs.get("query")
    limit = inputs.get("limit", 5)
    if not isinstance(query, str) or not query.strip():
        return envelope(error="query must be a non-empty string")
    if not positive_int(limit) or limit > MAX_LIMIT:
        return envelope(error=f"limit must be an integer between 1 and {MAX_LIMIT}")
    try:
        rows = retry_call(lambda: store.search(query.strip(), limit), retry_on=RETRY_ON)
    except Exception as error:
        return envelope(error=f"storage error: {error}")
    return envelope({"query": query.strip(), "count": len(rows), "notices": rows})


def notice_detail(inputs, store):
    notice_id = inputs.get("notice_id")
    if not positive_int(notice_id):
        return envelope(error="notice_id must be a positive integer")
    try:
        notice = retry_call(lambda: store.get(notice_id), retry_on=RETRY_ON)
    except Exception as error:
        return envelope(error=f"storage error: {error}")
    if notice is None:
        return envelope(error=f"notice {notice_id} not found")
    return envelope(notice)


def supplier_summary(inputs, store):
    supplier_id = inputs.get("supplier_id")
    if not positive_int(supplier_id):
        return envelope(error="supplier_id must be a positive integer")
    try:
        summary = retry_call(lambda: store.summary(supplier_id), retry_on=RETRY_ON)
    except Exception as error:
        return envelope(error=f"storage error: {error}")
    if summary is None:
        return envelope(error=f"supplier {supplier_id} not found")
    return envelope(summary)


TOOLS = {"search_notices": search_notices, "notice_detail": notice_detail, "supplier_summary": supplier_summary}

TOOL_SPECS = [
    {"type": "function", "function": {
        "name": "search_notices",
        "description": "Search grocery recall notices by product name or notice source. Returns id, productName, noticeCode, affectedUnits and supplierId.",
        "parameters": {"type": "object", "required": ["query"], "properties": {
            "query": {"type": "string", "description": "text to look for in the product name or source"},
            "limit": {"type": "integer", "description": "max rows, 1 to 50, default 5"}}}}},
    {"type": "function", "function": {
        "name": "notice_detail",
        "description": "Full detail of one recall notice by numeric id, including the supplier name.",
        "parameters": {"type": "object", "required": ["notice_id"], "properties": {
            "notice_id": {"type": "integer"}}}}},
    {"type": "function", "function": {
        "name": "supplier_summary",
        "description": "Aggregate for one supplier by numeric supplierId: notice count and total affected units.",
        "parameters": {"type": "object", "required": ["supplier_id"], "properties": {
            "supplier_id": {"type": "integer"}}}}},
]


def safety_violation(name, inputs):
    if name != "search_notices":
        return None
    query = str(inputs.get("query", "")).lower()
    hit = next((term for term in MEDICATION_TERMS if term in query), None)
    if hit:
        return (f"Safety rule: '{hit}' looks like a medication. This dataset only covers grocery recalls, "
                "so a 'no matches' answer would be misleading; use the FDA drug recall database instead.")
    return None


def execute_tool(name, inputs, store=None):
    try:
        if name not in TOOLS:
            result = envelope(error=f"unknown tool '{name}'; expected one of {sorted(TOOLS)}")
        elif not isinstance(inputs, dict):
            result = envelope(error="inputs must be a JSON object")
        elif safety_violation(name, inputs):
            result = envelope(error=safety_violation(name, inputs))
        else:
            result = TOOLS[name](inputs, store or MySQLStore())
    except Exception as error:
        result = envelope(error=f"{type(error).__name__}: {error}")
    return json.dumps(result, default=str)
