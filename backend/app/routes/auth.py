from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User, UserSession
from app.schemas.auth import AuthUser, LoginRequest, SignUpRequest

router = APIRouter(prefix="/auth", tags=["authentication"])
COOKIE_NAME = "civicpulse_session"
SESSION_DAYS = 14
PBKDF2_ITERATIONS = 310_000


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _password_matches(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _set_session(response: Response, db: Session, user: User):
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    db.add(UserSession(user_id=user.id, token_hash=_token_hash(token), expires_at=expires_at))
    db.commit()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        path="/",
    )


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    session = db.scalar(select(UserSession).where(UserSession.token_hash == _token_hash(token)))
    if not session:
        return None
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        return None
    return db.get(User, session.user_id)


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue")
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user


@router.post("/signup", response_model=AuthUser, status_code=status.HTTP_201_CREATED)
def signup(payload: SignUpRequest, response: Response, db: Session = Depends(get_db)):
    user = User(full_name=payload.full_name, email=payload.email, password_hash=_hash_password(payload.password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with that email already exists") from exc
    _set_session(response, db, user)
    return user


@router.post("/login", response_model=AuthUser)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not _password_matches(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    _set_session(response, db, user)
    return user


@router.post("/admin-login", response_model=AuthUser)
def admin_login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not _password_matches(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="This account does not have administrator access")
    _set_session(response, db, user)
    return user


@router.get("/me")
def me(user: User | None = Depends(get_optional_user)):
    return {"user": AuthUser.model_validate(user).model_dump() if user else None}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        session = db.scalar(select(UserSession).where(UserSession.token_hash == _token_hash(token)))
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=os.getenv("COOKIE_SECURE", "false").lower() == "true", samesite="lax")
