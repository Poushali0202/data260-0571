import redis
from sqlalchemy import update

from database import db_session_basede26
from models import GroceryNotice

PREFIX = "s0571"
SYNC_EVERY = 10


class NoticeCache:
    def __init__(self, host="localhost", port=6379):
        self.redis_client = redis.Redis(host=host, port=port, decode_responses=True)

    def increment_notice_views(self, notice_id):
        key = f"{PREFIX}:views:notice:{notice_id}"
        count = self.redis_client.incr(key)
        if count % SYNC_EVERY == 0:
            with db_session_basede26() as db:
                db.execute(
                    update(GroceryNotice)
                    .where(GroceryNotice.id == notice_id)
                    .values(viewCount=count, updatedAt=GroceryNotice.updatedAt)
                )
                db.commit()
            print("✓ Synced views to database")
        return count
