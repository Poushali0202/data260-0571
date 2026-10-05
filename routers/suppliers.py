from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import GroceryNotice, Supplier
from routers.auth import require_login
from schemas import NoticeOut, SupplierIn, SupplierOut

router = APIRouter(prefix="/api/suppliers", dependencies=[Depends(require_login)])


def find_supplier(db: Session, supplier_id: int) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


def commit_or_409(db: Session, message: str):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=message)


@router.get("", response_model=list[SupplierOut])
def list_suppliers(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200), db: Session = Depends(get_db)):
    return db.query(Supplier).order_by(Supplier.id).offset((page - 1) * page_size).limit(page_size).all()


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    return find_supplier(db, supplier_id)


@router.get("/{supplier_id}/notices", response_model=list[NoticeOut])
def notices_of_supplier(supplier_id: int, db: Session = Depends(get_db)):
    find_supplier(db, supplier_id)
    return db.query(GroceryNotice).filter(GroceryNotice.supplierId == supplier_id).order_by(GroceryNotice.id.desc()).all()


@router.post("", response_model=SupplierOut, status_code=201)
def create_supplier(data: SupplierIn, db: Session = Depends(get_db)):
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    commit_or_409(db, "A supplier with this email already exists")
    db.refresh(supplier)
    return supplier


@router.put("/{supplier_id}", response_model=SupplierOut)
def update_supplier(supplier_id: int, data: SupplierIn, db: Session = Depends(get_db)):
    supplier = find_supplier(db, supplier_id)
    supplier.name = data.name
    supplier.region = data.region
    supplier.email = data.email
    commit_or_409(db, "A supplier with this email already exists")
    db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = find_supplier(db, supplier_id)
    count = db.query(GroceryNotice).filter(GroceryNotice.supplierId == supplier_id).count()
    if count:
        raise HTTPException(status_code=409, detail=f"Supplier still has {count} notices; delete or reassign them first")
    db.delete(supplier)
    db.commit()
