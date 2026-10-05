from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
NOTICE_CODE_PATTERN = r"^RN-\d{6}$"


class SupplierIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    region: str = Field(min_length=1, max_length=200)
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)


class SupplierOut(SupplierIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    createdAt: datetime
    updatedAt: datetime


class NoticeIn(BaseModel):
    productName: str = Field(min_length=1, max_length=200)
    noticeCode: str = Field(pattern=NOTICE_CODE_PATTERN)
    noticeSource: str = Field(min_length=1, max_length=200)
    affectedUnits: int = Field(default=0, ge=0)
    supplierId: int = Field(gt=0)


class NoticeOut(NoticeIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    createdAt: datetime
    updatedAt: datetime


class LotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lotCode: str
    unitsAffected: int


class NoticeWithLots(NoticeOut):
    lots: list[LotOut]


class NoticePage(BaseModel):
    version: str
    page_size: int
    sql_queries: int
    notices: list[NoticeWithLots]


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
