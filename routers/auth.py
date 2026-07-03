from fastapi import APIRouter, Request, Depends, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import User
from auth_session import (
    get_current_user_optional, set_login_cookie, clear_login_cookie, get_current_user,
)
from templating import render, ANONYMOUS_USER

router = APIRouter()

VALID_ROLES = {"donor", "volunteer", "organization"}


# ---------- Page routes ----------
@router.get("/signup", name="signup_page")
def signup_page(request: Request, role: str = "donor"):
    if role not in VALID_ROLES:
        role = "donor"
    return render(request, "signup.html", role=role)


@router.get("/login", name="login_page")
def login_page(request: Request, role: str = "donor"):
    if role not in VALID_ROLES:
        role = "donor"
    return render(request, "login.html", role=role)


# ---------- Request schemas ----------
class SignupBody(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=6)
    role: str
    phone: Optional[str] = ""
    address: Optional[str] = ""
    org_type: Optional[str] = None
    registration_note: Optional[str] = None


class LoginBody(BaseModel):
    email: EmailStr
    password: str


# ---------- API routes ----------
@router.post("/api/signup")
def api_signup(body: SignupBody, response: Response, db: Session = Depends(get_db)):
    if body.role not in VALID_ROLES:
        return JSONResponse({"error": "Invalid role."}, status_code=400)

    email = body.email.lower().strip()
    if db.query(User).filter_by(email=email).first():
        return JSONResponse({"error": "An account with this email already exists."}, status_code=409)

    user = User(
        name=body.name.strip(), email=email, role=body.role,
        phone=(body.phone or "").strip(), address=(body.address or "").strip(),
    )
    user.set_password(body.password)

    if body.role == "organization":
        note = (body.registration_note or "").strip()
        if not note:
            return JSONResponse(
                {"error": "Please describe your organization for verification review."}, status_code=400
            )
        user.org_type = body.org_type or "Other"
        user.registration_note = note
        user.verification_status = "pending"
    else:
        user.verification_status = "not_applicable"

    db.add(user)
    db.commit()
    db.refresh(user)

    set_login_cookie(response, user.id)
    return {"ok": True, "user": user.to_dict(), "redirect": _dashboard_path_for(body.role)}


@router.post("/api/login")
def api_login(body: LoginBody, response: Response, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    user = db.query(User).filter_by(email=email).first()
    if not user or not user.check_password(body.password):
        return JSONResponse({"error": "Incorrect email or password."}, status_code=401)

    set_login_cookie(response, user.id)
    return {"ok": True, "user": user.to_dict(), "redirect": _dashboard_path_for(user.role)}


@router.post("/api/logout")
def api_logout(response: Response, user: User = Depends(get_current_user)):
    clear_login_cookie(response)
    return {"ok": True, "redirect": "/"}


@router.get("/api/me")
def api_me(user=Depends(get_current_user_optional)):
    if user is None:
        return {"authenticated": False}
    return {"authenticated": True, "user": user.to_dict()}


def _dashboard_path_for(role: str) -> str:
    return {
        "donor": "/donor",
        "volunteer": "/volunteer",
        "organization": "/organization",
    }.get(role, "/")
