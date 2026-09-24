from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class GroceryNotice(Base):
    __tablename__ = "grocery_notices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    productName = Column("product_name", String(200), nullable=False)
    noticeSource = Column("notice_source", String(200), nullable=False)
    lots = relationship("NoticeLot", cascade="all, delete-orphan")


class NoticeLot(Base):
    __tablename__ = "notice_lots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    notice_id = Column(Integer, ForeignKey("grocery_notices.id", ondelete="CASCADE"), nullable=False)
    lotCode = Column("lot_code", String(50), nullable=False)
    unitsAffected = Column("units_affected", Integer, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)


class UserSession(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    expires_at = Column(DateTime, nullable=False)
    user = relationship("User", lazy="joined")
