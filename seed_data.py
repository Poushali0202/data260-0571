import random

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from database import DATABASE_URL, Base, db_session_basede26, engine
from models import GroceryNotice, NoticeLot, User
from routers.auth import hash_password

SEED = 571
NOTICE_COUNT = 5000
LOT_COUNT = 200

USERS = [
    ("Poushali", "inspector@example.com", "recall2026"),
    ("Store Manager", "manager@example.com", "shelf2026"),
]

FORMS = ["Organic", "Frozen", "Fresh", "Canned", "Dried", "Bagged", "Store brand", "Family size"]
PRODUCTS = [
    "baby spinach", "romaine lettuce", "mixed berries", "ground beef", "whole milk", "cheddar cheese",
    "peanut butter", "infant formula", "chicken thighs", "smoked salmon", "bean sprouts", "cantaloupe",
    "ice cream", "almond flour", "orange juice", "deli ham", "tomato sauce", "hummus", "oat cereal",
    "eggs", "shredded coconut", "tahini", "sliced mushrooms", "queso fresco",
]
SIZES = ["5 oz", "8 oz", "12 oz", "1 lb", "2 lb", "1 gallon", "6 pack", "family pack"]
SOURCES = [
    "FDA recall bulletin", "USDA FSIS notice", "CDC outbreak notice", "CFIA advisory", "Acme Foods",
    "Dairy Fresh Co-op", "Green Valley Farms", "Pacific Seafood Supply", "Sunrise Bakery", "Harvest Fresh Produce",
    "Blue Ridge Creamery", "Golden State Growers", "Northern Meats", "Riverbend Foods", "Maple Leaf Foods",
    "Natural Selection Foods", "Abbott Nutrition", "Peanut Corporation of America", "Bay Area Grocers",
    "Mission Organics", "Summit Frozen Foods", "Coastal Distributors", "Prairie Grain Mills", "Evergreen Market",
]


def create_database():
    url = make_url(DATABASE_URL)
    server = create_engine(url.set(database=None))
    with server.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {url.database}"))
    server.dispose()


def main():
    random.seed(SEED)
    create_database()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = db_session_basede26()
    db.add_all([User(name=name, email=email, password_hash=hash_password(password)) for name, email, password in USERS])
    notices = []
    for _ in range(NOTICE_COUNT):
        product = f"{random.choice(FORMS)} {random.choice(PRODUCTS)} {random.choice(SIZES)}"
        notices.append(GroceryNotice(productName=product, noticeSource=random.choice(SOURCES)))
    db.add_all(notices)
    db.commit()

    lots = []
    for _ in range(LOT_COUNT):
        lots.append(NoticeLot(
            notice_id=random.randint(NOTICE_COUNT - 199, NOTICE_COUNT),
            lotCode=f"LOT-{random.randint(100000, 999999)}",
            unitsAffected=random.randint(10, 5000),
        ))
    db.add_all(lots)
    db.commit()

    print(f"seed {SEED}: {db.query(User).count()} users, {db.query(GroceryNotice).count()} notices, {db.query(NoticeLot).count()} lots")
    db.close()


if __name__ == "__main__":
    main()
