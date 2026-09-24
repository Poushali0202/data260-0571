from pydantic import BaseModel, ConfigDict, Field


class NoticeIn(BaseModel):
    productName: str = Field(min_length=1)
    noticeSource: str = Field(min_length=1)


class NoticeOut(NoticeIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


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
