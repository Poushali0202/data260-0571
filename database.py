import os
from contextvars import ContextVar

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing. Copy .env.example to .env and fill in the MySQL password.")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
db_session_basede26 = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()

query_counter = ContextVar("query_counter", default=None)


@event.listens_for(engine, "before_cursor_execute")
def count_query(conn, cursor, statement, parameters, context, executemany):
    counter = query_counter.get()
    if counter is not None:
        counter[0] += 1


def start_counting():
    query_counter.set([0])


def queries_so_far():
    return query_counter.get()[0]


def get_db():
    db = db_session_basede26()
    try:
        yield db
    finally:
        db.close()
