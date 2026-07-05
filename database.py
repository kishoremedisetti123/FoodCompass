import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# On Render, the project root is read-only — SQLite must live in /tmp.
# If DATABASE_URL is set (e.g. Render Postgres), that takes priority.
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    # Local development — use instance/ folder next to app.py
    # On Render without DATABASE_URL — fall back to /tmp (writable)
    if os.environ.get("RENDER"):
        db_path = "/tmp/foodcompass.db"
    else:
        instance_dir = os.path.join(BASE_DIR, "instance")
        os.makedirs(instance_dir, exist_ok=True)
        db_path = os.path.join(instance_dir, "foodcompass.db")
    DATABASE_URL = f"sqlite:///{db_path}"

# Render/Heroku-style URLs sometimes use postgres:// — SQLAlchemy 2.x wants postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a request-scoped DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()