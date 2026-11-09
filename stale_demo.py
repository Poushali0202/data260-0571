from sqlalchemy import text

from cached_ask import ask
from database import engine

QUESTION = "Which supplier is responsible for notice RN-005000?"
CODE = "RN-005000"
NEW_SUPPLIER = "Acme Foods"

SUPPLIER_SQL = text(
    "SELECT s.name FROM grocery_notices n JOIN suppliers s ON s.id = n.supplier_id WHERE n.notice_code = :c"
)


def supplier():
    with engine.connect() as conn:
        return conn.execute(SUPPLIER_SQL, {"c": CODE}).scalar()


def show(step, result):
    print(f"\n{step}\n  is_cached={result['is_cached']} similarity={result['similarity']} latency={result['latency_ms']} ms")
    print(f"  answer: {' '.join(result['answer'].split())}")


print(f"{CODE} supplier in s0571_rel = {supplier()}")
show("1. Ask once so the answer is in the cache", ask(QUESTION))

with engine.begin() as conn:
    conn.execute(
        text("UPDATE grocery_notices SET supplier_id = (SELECT id FROM suppliers WHERE name = :s) WHERE notice_code = :c"),
        {"s": NEW_SUPPLIER, "c": CODE},
    )
print(f"\n2. Updated {CODE}: supplier in s0571_rel is now {supplier()}")

show("3. Same question with the version check turned off (stale hit)", ask(QUESTION, check_version=False))
show("4. Same question with the version check on (marker differs, entry deleted, agent rerun)", ask(QUESTION))
show("5. Same question again (fresh answer now served from the cache)", ask(QUESTION))
