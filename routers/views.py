from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth_session import get_current_user, get_current_user_optional
from templating import render, ANONYMOUS_USER

router = APIRouter()


@router.get("/", name="index")
def index(request: Request, user: User = Depends(get_current_user_optional)):
    return render(request, "index.html", {"current_user": user or ANONYMOUS_USER})


@router.get("/donor", name="donor_dashboard")
def donor_dashboard(request: Request, user: User = Depends(get_current_user_optional)):
    if user is None:
        return RedirectResponse(url=f"/login?role=donor", status_code=303)
    if user.role != "donor":
        return RedirectResponse(url="/role-redirect", status_code=303)
    return render(request, "donor.html", {"current_user": user})


@router.get("/volunteer", name="volunteer_dashboard")
def volunteer_dashboard(request: Request, user: User = Depends(get_current_user_optional)):
    if user is None:
        return RedirectResponse(url=f"/login?role=volunteer", status_code=303)
    if user.role != "volunteer":
        return RedirectResponse(url="/role-redirect", status_code=303)
    return render(request, "volunteer.html", {"current_user": user})


@router.get("/organization", name="organization_dashboard")
def organization_dashboard(request: Request, user: User = Depends(get_current_user_optional)):
    if user is None:
        return RedirectResponse(url=f"/login?role=organization", status_code=303)
    if user.role != "organization":
        return RedirectResponse(url="/role-redirect", status_code=303)
    return render(request, "organization.html", {"current_user": user})


@router.get("/role-redirect", name="role_redirect")
def role_redirect(user: User = Depends(get_current_user)):
    path = {
        "donor": "/donor",
        "volunteer": "/volunteer",
        "organization": "/organization",
    }.get(user.role, "/")
    return RedirectResponse(url=path, status_code=303)


# ---------- Lightweight admin panel for org verification ----------
# Demo-grade: any logged-in user can view this for the hackathon demo so judges
# can see the verification step working end-to-end. Lock this behind a real
# admin role before any non-demo deployment.
@router.get("/admin/organizations", name="admin_organizations")
def admin_organizations(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    orgs = db.query(User).filter_by(role="organization").order_by(User.created_at.desc()).all()
    return render(request, "admin_orgs.html", {"current_user": user}, orgs=orgs)


class DecisionBody(BaseModel):
    decision: str


@router.post("/api/admin/organizations/{org_id}/decide")
def decide_organization(
    org_id: int, body: DecisionBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    org = db.get(User, org_id)
    if org is None or org.role != "organization":
        return JSONResponse({"error": "Organization not found."}, status_code=404)
    if body.decision not in ("approved", "rejected"):
        return JSONResponse({"error": "Decision must be 'approved' or 'rejected'."}, status_code=400)

    org.verification_status = body.decision
    db.commit()
    return {"ok": True, "org": org.to_dict()}
