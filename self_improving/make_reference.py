import json
from pathlib import Path

from sqlalchemy import text

from database import engine

HERE = Path(__file__).parent

CHECKS = {
    "t01": ("RN-004803", ["lot_total"]), "t02": ("RN-004840", ["supplier", "region"]),
    "t03": ("RN-009120", ["no_record"]), "t04": ("RN-004826", ["affected_units"]),
    "t05": ("RN-004850", ["largest_lot"]), "t06": ("RN-009377", ["no_record"]),
    "t07": ("RN-004877", ["affected_units"]), "t08": ("RN-004822", ["lot_total"]),
    "t09": ("RN-004860", ["affected_units"]), "t10": ("RN-004870", ["lot_total"]),
    "t11": ("RN-004850", ["lot_gap"]), "t12": ("RN-004870", ["lot_average"]),
    "t13": ("RN-004855", ["lot_gap"]), "t14": ("RN-004815", ["lot_average"]),
    "t15": ("RN-004805", ["lot_average"]),
    "v01": ("RN-004830", ["lot_total"]), "v02": ("RN-004835", ["affected_units"]),
    "v03": ("RN-004845", ["supplier"]), "v04": ("RN-004890", ["affected_units"]),
    "v05": ("RN-009555", ["no_record"]), "v06": ("RN-004803", ["largest_lot"]),
    "v07": ("RN-004866", ["source"]), "v08": ("RN-004881", ["affected_units"]),
    "v09": ("RN-004840", ["lot_gap"]), "v10": ("RN-004822", ["lot_average"]),
    "v11": ("RN-004830", ["lot_average"]),
    "x01": ("RN-004805", ["lot_total"]), "x02": ("RN-004850", ["lot_total"]),
    "x03": ("RN-004881", ["supplier", "region"]), "x04": ("RN-004840", ["affected_units"]),
    "x05": ("RN-009804", ["no_record"]), "x06": ("RN-004810", ["affected_units"]),
    "x07": ("RN-004877", ["largest_lot"]), "x08": ("RN-009231", ["no_record"]),
}

notices = {}
with engine.connect() as conn:
    for code, _ in CHECKS.values():
        row = conn.execute(text(
            "SELECT n.id, n.product_name, n.notice_source, n.affected_units, s.name, s.region "
            "FROM grocery_notices n JOIN suppliers s ON s.id = n.supplier_id WHERE n.notice_code = :c"), {"c": code}).first()
        if row is None:
            continue
        lots = conn.execute(text("SELECT lot_code, units_affected FROM notice_lots WHERE notice_id = :id"), {"id": row.id}).all()
        lot_total = sum(lot.units_affected for lot in lots)
        notices[code] = {
            "product": row.product_name,
            "source": row.notice_source,
            "affected_units": row.affected_units,
            "supplier": row.name,
            "region": row.region,
            "lots": {lot.lot_code: lot.units_affected for lot in lots},
            "lot_total": lot_total,
            "lot_gap": abs(lot_total - row.affected_units),
            "lot_average": lot_total // len(lots) if lots else None,
            "largest_lot": max(lots, key=lambda lot: lot.units_affected).lot_code if lots else None,
        }

questions = {qid: {"notice": code, "check": check} for qid, (code, check) in CHECKS.items()}
(HERE / "reference_data.json").write_text(json.dumps({"notices": notices, "questions": questions}, indent=2))
print(f"{len(notices)} notices, {len(questions)} questions")
