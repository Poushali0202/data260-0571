from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import CollectionInvalid

from config import MONGO_DB, MONGO_URI

STATUS_VALUES = ["open", "investigating", "closed"]
CATEGORY_VALUES = ["recall", "shortage", "contamination", "distribution"]

NOTICE_SCHEMA = {
    "bsonType": "object",
    "required": ["productName", "status", "noticeCategory", "noticeDate", "createdAt", "updatedAt"],
    "properties": {
        "productName": {"bsonType": "string", "minLength": 1, "maxLength": 100},
        "noticeDescription": {"bsonType": ["string", "null"], "maxLength": 1000},
        "status": {"enum": STATUS_VALUES},
        "noticeCategory": {"enum": CATEGORY_VALUES},
        "noticeDate": {"bsonType": "date"},
        "createdAt": {"bsonType": "date"},
        "updatedAt": {"bsonType": "date"},
    },
}

MESSAGE_SCHEMA = {
    "bsonType": "object",
    "required": ["user_id", "session_id", "role", "content", "created_at"],
    "properties": {
        "user_id": {"bsonType": "string"},
        "session_id": {"bsonType": "string"},
        "role": {"enum": ["user", "assistant"]},
        "content": {"bsonType": "string"},
        "created_at": {"bsonType": "date"},
    },
}

SUMMARY_SCHEMA = {
    "bsonType": "object",
    "required": ["user_id", "session_id", "scope", "text", "created_at"],
    "properties": {
        "user_id": {"bsonType": "string"},
        "session_id": {"bsonType": ["string", "null"]},
        "scope": {"enum": ["session", "user"]},
        "text": {"bsonType": "string"},
        "created_at": {"bsonType": "date"},
    },
}

EPISODE_SCHEMA = {
    "bsonType": "object",
    "required": ["user_id", "session_id", "fact", "importance", "embedding", "created_at"],
    "properties": {
        "user_id": {"bsonType": "string"},
        "session_id": {"bsonType": "string"},
        "fact": {"bsonType": "string", "maxLength": 200},
        "importance": {"bsonType": "double", "minimum": 0, "maximum": 1},
        "embedding": {"bsonType": "array", "items": {"bsonType": "double"}},
        "created_at": {"bsonType": "date"},
    },
}

SCHEMAS = {
    "notices": NOTICE_SCHEMA,
    "messages": MESSAGE_SCHEMA,
    "summaries": SUMMARY_SCHEMA,
    "episodes": EPISODE_SCHEMA,
}

client = MongoClient(MONGO_URI, tz_aware=True, serverSelectionTimeoutMS=5000)
db = client[MONGO_DB]


def setup_collections():
    for name, schema in SCHEMAS.items():
        try:
            db.create_collection(name, validator={"$jsonSchema": schema})
        except CollectionInvalid:
            db.command("collMod", name, validator={"$jsonSchema": schema})
    db.notices.create_index([("createdAt", DESCENDING)])
    db.messages.create_index([("user_id", ASCENDING), ("session_id", ASCENDING), ("created_at", ASCENDING)])
    db.summaries.create_index([("user_id", ASCENDING), ("scope", ASCENDING), ("created_at", DESCENDING)])
    db.episodes.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])


def get_collection(name):
    return db[name]
