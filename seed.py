"""
Quick demo seed script — creates a donor, an approved org, a volunteer,
and a couple of donations so the app has something to show immediately.

Run with:  python3 seed.py
"""
from datetime import timedelta
from database import engine, Base, SessionLocal
from models import User, Donation, DonationLog, utcnow

Base.metadata.create_all(bind=engine)
db = SessionLocal()

try:
    if db.query(User).filter_by(email="donor@demo.com").first():
        print("Demo data already exists — skipping. Delete instance/foodcompass.db to reseed.")
    else:
        donor = User(name="Anita Rao", email="donor@demo.com", role="donor",
                     phone="9999999999", address="MG Road, Vijayawada")
        donor.set_password("demo1234")

        org = User(name="Hope NGO", email="org@demo.com", role="organization",
                   org_type="NGO", phone="8888888888", address="City Center",
                   registration_note="Registered since 2015. Serves 3 shelters across the city.",
                   verification_status="approved")
        org.set_password("demo1234")

        volunteer = User(name="Ravi Kumar", email="volunteer@demo.com", role="volunteer",
                          phone="7777777777", address="Downtown")
        volunteer.set_password("demo1234")

        pending_org = User(name="New Hands Shelter", email="pendingorg@demo.com", role="organization",
                            org_type="Shelter", phone="6666666666", address="Riverside",
                            registration_note="Recently registered, awaiting document review.",
                            verification_status="pending")
        pending_org.set_password("demo1234")

        db.add_all([donor, org, volunteer, pending_org])
        db.commit()

        now = utcnow()
        d1 = Donation(donor_id=donor.id, food_type="Vegetable Biryani", quantity="25 servings",
                       expiry_datetime=now + timedelta(hours=1, minutes=30),
                       pickup_location="Downtown Community Hall", notes="Ring the back gate bell")
        d2 = Donation(donor_id=donor.id, food_type="Mixed Fruit Basket", quantity="5 kg",
                       expiry_datetime=now + timedelta(hours=4),
                       pickup_location="City Mall, Gate 2")
        d3 = Donation(donor_id=donor.id, food_type="Bread & Dairy", quantity="12 packs",
                       expiry_datetime=now + timedelta(hours=9),
                       pickup_location="Riverside Bakery")
        db.add_all([d1, d2, d3])
        db.commit()

        for d in (d1, d2, d3):
            db.add(DonationLog(donation_id=d.id, actor_id=donor.id, event=f"Posted by {donor.name}"))
        db.commit()

        print("Seeded demo accounts (all passwords: demo1234):")
        print("  Donor:         donor@demo.com")
        print("  Organization:  org@demo.com  (approved)")
        print("  Organization:  pendingorg@demo.com  (pending verification)")
        print("  Volunteer:     volunteer@demo.com")
finally:
    db.close()
