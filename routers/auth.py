import os
import secrets
import time
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")

USERS = {
    "inspector": {"password": "recall2026", "name": "Poushali"},
    "manager": {"password": "shelf2026", "name": "Store Manager"},
}
IDLE_TIMEOUT = int(os.getenv("IDLE_TIMEOUT_SECONDS", "600"))
ACTIVE_SESSIONS = set()


def current_user(request: Request):
    user = request.session.get("user")
    session_id = request.session.get("id")
    idle = time.time() - request.session.get("last_seen", 0)
    if not user or session_id not in ACTIVE_SESSIONS or idle > IDLE_TIMEOUT:
        ACTIVE_SESSIONS.discard(session_id)
        request.session.clear()
        return None
    request.session["last_seen"] = time.time()
    return user


@router.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {"user": current_user(request)})


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"user": current_user(request), "error": None})


@router.post("/login")
def login(request: Request, username: str = Form(), password: str = Form()):
    account = USERS.get(username)
    if account is None or account["password"] != password:
        context = {"user": None, "error": "Invalid username or password."}
        return templates.TemplateResponse(request, "login.html", context, status_code=401)
    session_id = secrets.token_hex(16)
    ACTIVE_SESSIONS.add(session_id)
    request.session["id"] = session_id
    request.session["user"] = {"username": username, "name": account["name"]}
    request.session["last_seen"] = time.time()
    return RedirectResponse("/dashboard", status_code=302)


@router.get("/dashboard")
def dashboard(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request, "dashboard.html", {"user": user})


@router.get("/logout")
def logout(request: Request):
    ACTIVE_SESSIONS.discard(request.session.get("id"))
    request.session.clear()
    return RedirectResponse("/", status_code=302)
