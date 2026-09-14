from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

PORT_BASE = 8571
ROOT = Path(__file__).resolve().parent

app = FastAPI(title="Grocery supply and recall notices")


class NoticeCreate(BaseModel):
    productName: str = Field(min_length=1)
    noticeSource: str = Field(min_length=1)
    submitterEmail: str
    noticeDescription: str
    noticeCategory: str


class NoticeUpdate(BaseModel):
    productName: str = Field(min_length=1)
    noticeSource: str = Field(min_length=1)


class Notice(NoticeCreate):
    id: int


notices = [
    Notice(
        id=1,
        productName="Organic baby spinach 5 oz",
        noticeSource="FDA recall bulletin",
        submitterEmail="poushali@example.com",
        noticeDescription="Possible listeria contamination in bags packed between March 2 and March 6.",
        noticeCategory="recall",
    ),
    Notice(
        id=2,
        productName="Frozen mixed berries",
        noticeSource="Acme Foods",
        submitterEmail="poushali@example.com",
        noticeDescription="Supplier reported possible hepatitis A contamination in selected lots.",
        noticeCategory="contamination",
    ),
    Notice(
        id=3,
        productName="Whole milk 1 gallon",
        noticeSource="Dairy Fresh Co-op",
        submitterEmail="poushali@example.com",
        noticeDescription="Deliveries delayed for two weeks because of a regional trucking shortage.",
        noticeCategory="shortage",
    ),
]


@app.get("/")
def home():
    return FileResponse(ROOT / "index.html")


@app.get("/feedback.js")
def script():
    return FileResponse(ROOT / "feedback.js")


@app.get("/api/notices")
def list_notices(q: str = ""):
    term = q.strip().lower()
    if not term:
        return notices
    return [
        notice for notice in notices
        if term in notice.productName.lower() or term in notice.noticeSource.lower()
    ]


@app.post("/api/notices", status_code=201)
def add_notice(data: NoticeCreate):
    new_id = max((notice.id for notice in notices), default=0) + 1
    notice = Notice(id=new_id, **data.model_dump())
    notices.append(notice)
    return notice


@app.put("/api/notices/{notice_id}")
def update_notice(notice_id: int, data: NoticeUpdate):
    for notice in notices:
        if notice.id == notice_id:
            notice.productName = data.productName
            notice.noticeSource = data.noticeSource
            return notice
    raise HTTPException(status_code=404, detail="Notice not found")


@app.delete("/api/notices/highest", status_code=204)
def delete_highest():
    if not notices:
        raise HTTPException(status_code=404, detail="There are no notices to delete")
    notices.remove(max(notices, key=lambda notice: notice.id))


if __name__ == "__main__":
    uvicorn.run(app, port=PORT_BASE)
