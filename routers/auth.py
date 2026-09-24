import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserSession
from schemas import LoginIn, UserOut

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")

COOKIE = "session_id"
SESSION_MINUTES = 30


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return salt + "$" + digest


def check_password(password: str, stored: str) -> bool:
    salt, digest = stored.split("$")
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return hmac.compare_digest(candidate, digest)


def find_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if user and check_password(password, user.password_hash):
        return user
    return None


def open_session(db: Session, user: User, response: Response):
    token = secrets.token_hex(32)
    now = datetime.now()
    expires = now + timedelta(minutes=SESSION_MINUTES)
    db.add(UserSession(id=token, user_id=user.id, created_at=now, expires_at=expires))
    db.commit()
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=SESSION_MINUTES * 60)


def close_session(db: Session, request: Request, response: Response):
    token = request.cookies.get(COOKIE)
    if token:
        db.query(UserSession).filter(UserSession.id == token).delete()
        db.commit()
    response.delete_cookie(COOKIE)


def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    session = db.get(UserSession, token)
    if session is None:
        return None
    if session.expires_at < datetime.now():
        db.delete(session)
        db.commit()
        return None
    return session.user


def require_login(user=Depends(current_user)):
    if user is None:
        raise HTTPException(status_code=401, detail="Login required")
    return user


@router.post("/auth/login", response_model=UserOut)
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = find_user(db, data.email, data.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    open_session(db, user, response)
    return user


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    close_session(db, request, response)
    return {"message": "logged out"}


@router.get("/auth/me", response_model=UserOut)
def me(user=Depends(require_login)):
    return user


@router.get("/")
def home(request: Request, user=Depends(current_user)):
    return templates.TemplateResponse(request, "index.html", {"user": user})


@router.get("/login")
def login_page(request: Request, user=Depends(current_user)):
    return templates.TemplateResponse(request, "login.html", {"user": user, "error": None})


@router.post("/login")
def login_form(request: Request, email: str = Form(), password: str = Form(), db: Session = Depends(get_db)):
    user = find_user(db, email, password)
    if user is None:
        context = {"user": None, "error": "Invalid email or password."}
        return templates.TemplateResponse(request, "login.html", context, status_code=401)
    response = RedirectResponse("/dashboard", status_code=302)
    open_session(db, user, response)
    return response


@router.get("/dashboard")
def dashboard(request: Request, user=Depends(current_user)):
    if user is None:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request, "dashboard.html", {"user": user})


@router.get("/logout")
def logout_page(request: Request, db: Session = Depends(get_db)):
    response = RedirectResponse("/", status_code=302)
    close_session(db, request, response)
    return response
