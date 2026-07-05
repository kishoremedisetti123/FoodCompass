import os
from contextlib import asynccontextmanager
from datetime import timedelta
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from database import engine, Base, SessionLocal
from models import User, Donation, DonationLog, utcnow
from routers import auth, donations, views

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def seed_demo_data():
    """Auto-seed demo accounts on startup if they don't exist yet."""
    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(User).filter_by(email="donor@demo.com").first():
            return  # already seeded, skip

        donor = User(name="Anita Rao", email="donor@demo.com", role="donor",
                     phone="9999999999", address="MG Road, Vijayawada",
                     verification_status="not_applicable")
        donor.set_password("demo1234")

        org = User(name="Hope NGO", email="org@demo.com", role="organization",
                   org_type="NGO", phone="8888888888", address="City Center",
                   registration_note="Registered since 2015. Serves 3 shelters.",
                   verification_status="approved")
        org.set_password("demo1234")

        volunteer = User(name="Ravi Kumar", email="volunteer@demo.com", role="volunteer",
                         phone="7777777777", address="Downtown",
                         verification_status="not_applicable")
        volunteer.set_password("demo1234")

        pending_org = User(name="New Hands Shelter", email="pendingorg@demo.com",
                           role="organization", org_type="Shelter",
                           phone="6666666666", address="Riverside",
                           registration_note="Recently registered, awaiting review.",
                           verification_status="pending")
        pending_org.set_password("demo1234")

        db.add_all([donor, org, volunteer, pending_org])
        db.commit()

        now = utcnow()
        d1 = Donation(donor_id=donor.id, food_type="Vegetable Biryani",
                      quantity="25 servings",
                      expiry_datetime=now + timedelta(hours=6),
                      pickup_location="Downtown Community Hall",
                      notes="Ring the back gate bell")
        d2 = Donation(donor_id=donor.id, food_type="Mixed Fruit Basket",
                      quantity="5 kg",
                      expiry_datetime=now + timedelta(hours=10),
                      pickup_location="City Mall, Gate 2")
        d3 = Donation(donor_id=donor.id, food_type="Bread & Dairy",
                      quantity="12 packs",
                      expiry_datetime=now + timedelta(hours=18),
                      pickup_location="Riverside Bakery")
        db.add_all([d1, d2, d3])
        db.commit()

        for d in (d1, d2, d3):
            db.add(DonationLog(donation_id=d.id, actor_id=donor.id,
                               event=f"Posted by {donor.name}"))
        db.commit()
        print("✓ Demo data seeded successfully.")

    except Exception as e:
        db.rollback()
        print(f"Seeding skipped or failed: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables then seed demo data on every cold start
    Base.metadata.create_all(bind=engine)
    seed_demo_data()
    yield


app = FastAPI(title="FoodCompass", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

app.include_router(views.router)
app.include_router(auth.router)
app.include_router(donations.router)