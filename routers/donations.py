from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import get_db
from models import Donation, DonationLog, User, utcnow as _utcnow
from auth_session import get_current_user, require_role

router = APIRouter(prefix="/api/donations")


def log_event(db: Session, donation: Donation, event: str, actor: Optional[User] = None):
    db.add(DonationLog(donation_id=donation.id, actor_id=actor.id if actor else None, event=event))


def _parse_datetime(raw: str):
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


class CreateDonationBody(BaseModel):
    food_type: str
    quantity: str
    expiry_datetime: str
    pickup_location: str
    notes: Optional[str] = ""


# ---------- Create (Donor) ----------
@router.post("")
def create_donation(
    body: CreateDonationBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("donor")),
):
    food_type = body.food_type.strip()
    quantity = body.quantity.strip()
    pickup_location = body.pickup_location.strip()

    if not food_type or not quantity or not body.expiry_datetime or not pickup_location:
        return JSONResponse({"error": "Food type, quantity, expiry and location are all required."}, status_code=400)

    expiry_dt = _parse_datetime(body.expiry_datetime)
    if expiry_dt is None:
        return JSONResponse({"error": "Could not understand the expiry date/time."}, status_code=400)

    donation = Donation(
        donor_id=user.id,
        food_type=food_type,
        quantity=quantity,
        expiry_datetime=expiry_dt,
        pickup_location=pickup_location,
        notes=(body.notes or "").strip() or None,
    )
    db.add(donation)
    db.flush()  # assigns donation.id before logging against it
    log_event(db, donation, f"Posted by {user.name}", actor=user)
    db.commit()
    db.refresh(donation)

    return JSONResponse({"ok": True, "donation": donation.to_dict()}, status_code=201)


# ---------- List ----------
@router.get("")
def list_donations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Returns donations scoped to what the current role should see:
      - donor: their own posted donations (any status)
      - organization: available donations + ones they've claimed
      - volunteer: claimed donations awaiting pickup + ones assigned to them
    """
    if user.role == "donor":
        items = (
            db.query(Donation)
            .filter(Donation.donor_id == user.id)
            .order_by(Donation.created_at.desc())
            .all()
        )

    elif user.role == "organization":
        items = (
            db.query(Donation)
            .filter(or_(Donation.status == "available", Donation.claimed_by_org_id == user.id))
            .order_by(Donation.expiry_datetime.asc())
            .all()
        )

    elif user.role == "volunteer":
        items = (
            db.query(Donation)
            .filter(
                or_(
                    (Donation.status == "claimed") & (Donation.assigned_volunteer_id.is_(None)),
                    Donation.assigned_volunteer_id == user.id,
                )
            )
            .order_by(Donation.expiry_datetime.asc())
            .all()
        )

    else:
        items = []

    return {"donations": [d.to_dict() for d in items]}


# ---------- Claim (Organization) ----------
@router.post("/{donation_id}/claim")
def claim_donation(
    donation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("organization")),
):
    if not user.is_verified_org:
        return JSONResponse(
            {"error": "Your organization is still pending verification. You can claim donations once approved."},
            status_code=403,
        )

    donation = db.get(Donation, donation_id)
    if donation is None:
        return JSONResponse({"error": "Donation not found."}, status_code=404)
    if donation.status != "available":
        return JSONResponse({"error": "This donation has already been claimed."}, status_code=409)
    if donation.is_expired():
        return JSONResponse({"error": "This donation has expired."}, status_code=410)

    donation.status = "claimed"
    donation.claimed_by_org_id = user.id
    donation.claimed_at = _utcnow()
    log_event(db, donation, f"Claimed by {user.name}", actor=user)
    db.commit()
    db.refresh(donation)

    return {"ok": True, "donation": donation.to_dict()}


# ---------- Assign self as pickup volunteer ----------
@router.post("/{donation_id}/assign-volunteer")
def assign_volunteer(
    donation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("volunteer")),
):
    donation = db.get(Donation, donation_id)
    if donation is None:
        return JSONResponse({"error": "Donation not found."}, status_code=404)
    if donation.status != "claimed":
        return JSONResponse({"error": "This donation isn't ready for pickup yet."}, status_code=409)
    if donation.assigned_volunteer_id is not None:
        return JSONResponse({"error": "A volunteer has already taken this pickup."}, status_code=409)

    donation.assigned_volunteer_id = user.id
    log_event(db, donation, f"Pickup taken by volunteer {user.name}", actor=user)
    db.commit()
    db.refresh(donation)

    return {"ok": True, "donation": donation.to_dict()}


# ---------- Mark picked up (Volunteer) ----------
@router.post("/{donation_id}/picked-up")
def mark_picked_up(
    donation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    donation = db.get(Donation, donation_id)
    if donation is None:
        return JSONResponse({"error": "Donation not found."}, status_code=404)
    if user.role != "volunteer" or donation.assigned_volunteer_id != user.id:
        return JSONResponse({"error": "Only the assigned volunteer can update this."}, status_code=403)
    if donation.status != "claimed":
        return JSONResponse({"error": "This donation isn't awaiting pickup."}, status_code=409)

    donation.status = "picked_up"
    donation.picked_up_at = _utcnow()
    log_event(db, donation, f"Picked up by {user.name}", actor=user)
    db.commit()
    db.refresh(donation)

    return {"ok": True, "donation": donation.to_dict()}


# ---------- Confirm delivery (Organization) ----------
@router.post("/{donation_id}/confirm-delivery")
def confirm_delivery(
    donation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    donation = db.get(Donation, donation_id)
    if donation is None:
        return JSONResponse({"error": "Donation not found."}, status_code=404)
    if user.role != "organization" or donation.claimed_by_org_id != user.id:
        return JSONResponse({"error": "Only the claiming organization can confirm delivery."}, status_code=403)
    if donation.status != "picked_up":
        return JSONResponse({"error": "This donation hasn't been picked up yet."}, status_code=409)

    donation.status = "delivered"
    donation.delivered_at = _utcnow()
    log_event(db, donation, f"Delivery confirmed by {user.name}", actor=user)
    db.commit()
    db.refresh(donation)

    return {"ok": True, "donation": donation.to_dict()}


# ---------- Cancel (Donor) ----------
@router.post("/{donation_id}/cancel")
def cancel_donation(
    donation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    donation = db.get(Donation, donation_id)
    if donation is None:
        return JSONResponse({"error": "Donation not found."}, status_code=404)
    if user.role != "donor" or donation.donor_id != user.id:
        return JSONResponse({"error": "Only the donor who posted this can cancel it."}, status_code=403)
    if donation.status in ("delivered", "cancelled"):
        return JSONResponse({"error": "This donation can no longer be cancelled."}, status_code=409)

    donation.status = "cancelled"
    donation.cancelled_at = _utcnow()
    log_event(db, donation, f"Cancelled by {user.name}", actor=user)
    db.commit()
    db.refresh(donation)

    return {"ok": True, "donation": donation.to_dict()}


# ---------- Activity log for one donation (transparency trail) ----------
@router.get("/{donation_id}/log")
def donation_log(donation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    donation = db.get(Donation, donation_id)
    if donation is None:
        return JSONResponse({"error": "Donation not found."}, status_code=404)
    entries = [{"event": e.event, "timestamp": e.timestamp.isoformat()} for e in donation.logs]
    return {"log": entries}
