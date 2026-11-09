import hashlib
import re

from sqlalchemy import text

from database import engine

CODE = re.compile(r"RN-\d{6}")

NOTICE_SQL = text(
    "SELECT n.id, n.product_name, n.notice_source, n.affected_units, s.name, s.region "
    "FROM grocery_notices n JOIN suppliers s ON s.id = n.supplier_id WHERE n.notice_code = :code"
)
LOTS_SQL = text("SELECT lot_code, units_affected FROM notice_lots WHERE notice_id = :id ORDER BY id")


def notice_codes(question):
    return sorted(set(CODE.findall(question.upper())))


def facts_for(codes):
    lines = []
    with engine.connect() as conn:
        for code in codes:
            row = conn.execute(NOTICE_SQL, {"code": code}).first()
            if row is None:
                lines.append(f"{code}: no record in s0571_rel")
                continue
            lots = conn.execute(LOTS_SQL, {"id": row.id}).all()
            lot_text = ", ".join(f"{lot.lot_code} ({lot.units_affected} units)" for lot in lots) or "none"
            lines.append(
                f"{code}: product {row.product_name}; source {row.notice_source}; affected units {row.affected_units}; "
                f"supplier {row.name} ({row.region}); lots: {lot_text}"
            )
    return "\n".join(lines)


def data_version(facts):
    return hashlib.sha1(facts.encode()).hexdigest()[:12] if facts else "none"
