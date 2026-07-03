from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from werkzeug_security import generate_password_hash, check_password_hash
from database import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(160), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # donor | volunteer | organization
    phone = Column(String(30))
    address = Column(String(255))
    created_at = Column(DateTime, default=utcnow)

    # Organization-only fields
    org_type = Column(String(60))
    registration_note = Column(Text)
    verification_status = Column(String(20), default="not_applicable")
    # not_applicable | pending | approved | rejected

    donations = relationship(
        "Donation", foreign_keys="Donation.donor_id", back_populates="donor", lazy="dynamic"
    )
    claimed_donations = relationship(
        "Donation", foreign_keys="Donation.claimed_by_org_id", back_populates="claiming_org", lazy="dynamic"
    )
    assigned_pickups = relationship(
        "Donation", foreign_keys="Donation.assigned_volunteer_id", back_populates="volunteer", lazy="dynamic"
    )

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_authenticated(self):
        # Mirrors Flask-Login's User.is_authenticated so templates ported
        # verbatim (e.g. `current_user.is_authenticated`) keep working.
        return True

    @property
    def is_organization(self):
        return self.role == "organization"

    @property
    def is_verified_org(self):
        return self.role == "organization" and self.verification_status == "approved"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "org_type": self.org_type,
            "verification_status": self.verification_status,
        }


class Donation(Base):
    __tablename__ = "donations"

    id = Column(Integer, primary_key=True)
    donor_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    food_type = Column(String(160), nullable=False)
    quantity = Column(String(60), nullable=False)
    expiry_datetime = Column(DateTime, nullable=False)
    pickup_location = Column(String(255), nullable=False)
    notes = Column(String(500))

    status = Column(String(20), default="available")
    # available | claimed | picked_up | delivered | cancelled

    claimed_by_org_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_volunteer_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=utcnow)
    claimed_at = Column(DateTime, nullable=True)
    picked_up_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    donor = relationship("User", foreign_keys=[donor_id], back_populates="donations")
    claiming_org = relationship("User", foreign_keys=[claimed_by_org_id], back_populates="claimed_donations")
    volunteer = relationship("User", foreign_keys=[assigned_volunteer_id], back_populates="assigned_pickups")

    logs = relationship(
        "DonationLog", back_populates="donation", lazy="dynamic",
        order_by="DonationLog.timestamp", cascade="all, delete-orphan"
    )

    def hours_left(self):
        delta = self.expiry_datetime - utcnow()
        return round(delta.total_seconds() / 3600, 1)

    def is_expired(self):
        return self.hours_left() < 0

    def urgency(self):
        h = self.hours_left()
        if h < 0:
            return "expired"
        if h <= 2:
            return "urgent"
        if h <= 6:
            return "soon"
        return "fresh"

    def to_dict(self):
        return {
            "id": self.id,
            "food_type": self.food_type,
            "quantity": self.quantity,
            "expiry_datetime": self.expiry_datetime.isoformat(),
            "pickup_location": self.pickup_location,
            "notes": self.notes,
            "status": self.status,
            "hours_left": self.hours_left(),
            "urgency": self.urgency(),
            "donor_name": self.donor.name if self.donor else None,
            "claiming_org_name": self.claiming_org.name if self.claiming_org else None,
            "volunteer_name": self.volunteer.name if self.volunteer else None,
            "created_at": self.created_at.isoformat(),
        }


class DonationLog(Base):
    __tablename__ = "donation_logs"

    id = Column(Integer, primary_key=True)
    donation_id = Column(Integer, ForeignKey("donations.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=utcnow)

    donation = relationship("Donation", back_populates="logs")
