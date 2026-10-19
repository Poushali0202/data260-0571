from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["open", "investigating", "closed"]
Category = Literal["recall", "shortage", "contamination", "distribution"]


class NoticeDocIn(BaseModel):
    productName: str = Field(min_length=1, max_length=100)
    noticeDescription: str | None = Field(default=None, max_length=1000)
    status: Status = "open"
    noticeCategory: Category
    noticeDate: datetime


class NoticeDocUpdate(BaseModel):
    productName: str | None = Field(default=None, min_length=1, max_length=100)
    noticeDescription: str | None = Field(default=None, max_length=1000)
    status: Status | None = None
    noticeCategory: Category | None = None
    noticeDate: datetime | None = None


class NoticeDocOut(NoticeDocIn):
    id: str
    createdAt: datetime
    updatedAt: datetime


class ChatIn(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    session_id: str | None = Field(default=None, max_length=100)
    message: str = Field(min_length=1, max_length=4000)
    short_term_n: int | None = Field(default=None, ge=0, le=100)
    policy: Literal["none", "compress_old"] = "none"
    file_memory: bool = False


class ChatOut(BaseModel):
    reply: str
    session_id: str
    used: dict
    usage: dict
