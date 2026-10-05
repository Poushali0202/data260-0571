from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from database import get_db, queries_so_far, start_counting
from models import GroceryNotice, Supplier
from routers.auth import require_login
from routers.suppliers import commit_or_409
from schemas import NoticeIn, NoticeOut, NoticePage, NoticeWithLots

router = APIRouter(prefix="/api/notices", dependencies=[Depends(require_login)])


def find_notice(db: Session, notice_id: int) -> GroceryNotice:
    notice = db.get(GroceryNotice, notice_id)
    if notice is None:
        raise HTTPException(status_code=404, detail="Notice not found")
    return notice


def check_supplier(db: Session, supplier_id: int):
    if db.get(Supplier, supplier_id) is None:
        raise HTTPException(status_code=409, detail=f"supplierId {supplier_id} does not exist")


@router.get("", response_model=list[NoticeOut])
def list_notices(q: str = "", page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200), db: Session = Depends(get_db)):
    query = db.query(GroceryNotice)
    if q.strip():
        term = q.strip()
        query = query.filter(GroceryNotice.productName.contains(term) | GroceryNotice.noticeSource.contains(term))
    return query.order_by(GroceryNotice.id.desc()).offset((page - 1) * page_size).limit(page_size).all()


@router.get("/naive", response_model=NoticePage)
def list_naive(page_size: int = 10, db: Session = Depends(get_db)):
    start_counting()
    notices = db.query(GroceryNotice).order_by(GroceryNotice.id.desc()).limit(page_size).all()
    items = [NoticeWithLots.model_validate(notice) for notice in notices]
    return NoticePage(version="naive", page_size=page_size, sql_queries=queries_so_far(), notices=items)


@router.get("/fixed", response_model=NoticePage)
def list_fixed(page_size: int = 10, db: Session = Depends(get_db)):
    start_counting()
    notices = (
        db.query(GroceryNotice)
        .options(selectinload(GroceryNotice.lots))
        .order_by(GroceryNotice.id.desc())
        .limit(page_size)
        .all()
    )
    items = [NoticeWithLots.model_validate(notice) for notice in notices]
    return NoticePage(version="fixed", page_size=page_size, sql_queries=queries_so_far(), notices=items)


@router.get("/{notice_id}", response_model=NoticeOut)
def get_notice(notice_id: int, db: Session = Depends(get_db)):
    return find_notice(db, notice_id)


@router.post("", response_model=NoticeOut, status_code=201)
def create_notice(data: NoticeIn, db: Session = Depends(get_db)):
    check_supplier(db, data.supplierId)
    notice = GroceryNotice(**data.model_dump())
    db.add(notice)
    commit_or_409(db, "A notice with this noticeCode already exists")
    db.refresh(notice)
    return notice


@router.put("/{notice_id}", response_model=NoticeOut)
def update_notice(notice_id: int, data: NoticeIn, db: Session = Depends(get_db)):
    notice = find_notice(db, notice_id)
    check_supplier(db, data.supplierId)
    for field, value in data.model_dump().items():
        setattr(notice, field, value)
    commit_or_409(db, "A notice with this noticeCode already exists")
    db.refresh(notice)
    return notice


@router.delete("/highest", status_code=204)
def delete_highest(db: Session = Depends(get_db)):
    notice = db.query(GroceryNotice).order_by(GroceryNotice.id.desc()).first()
    if notice is None:
        raise HTTPException(status_code=404, detail="There are no notices to delete")
    db.delete(notice)
    db.commit()


@router.delete("/{notice_id}", status_code=204)
def delete_notice(notice_id: int, db: Session = Depends(get_db)):
    db.delete(find_notice(db, notice_id))
    db.commit()
