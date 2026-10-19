from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException

from doc_schemas import NoticeDocIn, NoticeDocOut, NoticeDocUpdate
from mongo_db import get_collection

router = APIRouter(prefix="/api/doc/notices")


def now():
    return datetime.now(timezone.utc)


def to_object_id(notice_id: str) -> ObjectId:
    try:
        return ObjectId(notice_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid notice id")


def serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


def find_notice(notice_id: str) -> dict:
    doc = get_collection("notices").find_one({"_id": to_object_id(notice_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Notice not found")
    return doc


@router.post("", response_model=NoticeDocOut, status_code=201)
def create_notice(data: NoticeDocIn):
    doc = data.model_dump()
    doc["createdAt"] = doc["updatedAt"] = now()
    result = get_collection("notices").insert_one(doc)
    return serialize(get_collection("notices").find_one({"_id": result.inserted_id}))


@router.get("", response_model=list[NoticeDocOut])
def list_notices():
    docs = get_collection("notices").find().sort("createdAt", -1)
    return [serialize(doc) for doc in docs]


@router.get("/{notice_id}", response_model=NoticeDocOut)
def get_notice(notice_id: str):
    return serialize(find_notice(notice_id))


@router.put("/{notice_id}", response_model=NoticeDocOut)
def update_notice(notice_id: str, data: NoticeDocUpdate):
    find_notice(notice_id)
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updatedAt"] = now()
    get_collection("notices").update_one({"_id": to_object_id(notice_id)}, {"$set": updates})
    return serialize(find_notice(notice_id))


@router.delete("/{notice_id}", status_code=204)
def delete_notice(notice_id: str):
    result = get_collection("notices").delete_one({"_id": to_object_id(notice_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notice not found")
