from sqlalchemy import text

from database import engine
from notice_cache import NoticeCache

NOTICE_ID = 4870

cache = NoticeCache()
cache.redis_client.delete(f"s0571:views:notice:{NOTICE_ID}")

print("=== Testing Counter ===\n")
for i in range(1, 26):
    total = cache.increment_notice_views(NOTICE_ID)
    print(f"Access #{i}: Total = {total}")

with engine.connect() as conn:
    stored = conn.execute(text("SELECT view_count FROM grocery_notices WHERE id = :id"), {"id": NOTICE_ID}).scalar()
print(f"\nRedis {cache.redis_client.get(f's0571:views:notice:{NOTICE_ID}')}, MySQL view_count {stored}")
