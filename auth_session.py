"""
Cookie-based session auth for FastAPI — a small hand-rolled replacement for
Flask-Login (which doesn't exist in the FastAPI world).

How it works:
- On login/signup we sign the user's id with itsdangerous and set it as an
  HttpOnly cookie called "session".
- `get_current_user_optional` reads + verifies that cookie on every request
  and loads the User row (or returns None).
- `get_current_user` wraps that and raises 401 if nobody's logged in —
  use this as a route dependency for anything that requires login.
- `require_role(...)` is a small dependency factory for role-gating routes.
"""
import os
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import User

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
SESSION_COOKIE_NAME = "session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 14  # 14 days

_serializer = URLSafeTimedSerializer(SECRET_KEY, salt="foodcompass-session")


def create_session_cookie_value(user_id: int) -> str:
    return _serializer.dumps({"user_id": user_id})


def _read_user_id_from_cookie(cookie_value: str):
    try:
        data = _serializer.loads(cookie_value, max_age=SESSION_MAX_AGE_SECONDS)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None


def get_current_user_optional(request: Request, db: Session = Depends(get_db)):
    cookie_value = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie_value:
        return None
    user_id = _read_user_id_from_cookie(cookie_value)
    if user_id is None:
        return None
    return db.get(User, user_id)


def get_current_user(user: User = Depends(get_current_user_optional)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required.")
    return user


def require_role(*roles: str):
    """Dependency factory: require_role("donor") or require_role("donor", "volunteer")."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this action.")
        return user

    return dependency


def set_login_cookie(response, user_id: int):
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_cookie_value(user_id),
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
    )


def clear_login_cookie(response):
    response.delete_cookie(SESSION_COOKIE_NAME)
