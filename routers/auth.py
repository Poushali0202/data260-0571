import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from config import JWT_ALGORITHM, JWT_SECRET, TOKEN_MINUTES
from database import get_db
from models import User
from schemas import Token, UserOut

router = APIRouter(prefix="/auth")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return salt + "$" + digest


def check_password(password: str, stored: str) -> bool:
    salt, digest = stored.split("$")
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return hmac.compare_digest(candidate, digest)


def create_token(user: User, minutes: int = TOKEN_MINUTES) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    claims = {"sub": user.username, "role": user.role, "exp": expires}
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)


def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status_code=401, detail="Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError:
        raise unauthorized
    user = db.query(User).filter(User.username == claims.get("sub")).first()
    if user is None:
        raise unauthorized
    return user


def require_role(*roles):
    def check(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail=f"Role '{user.role}' is not allowed; needs one of {list(roles)}")
        return user

    return check


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if user is None or not check_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password", headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": create_token(user), "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user
