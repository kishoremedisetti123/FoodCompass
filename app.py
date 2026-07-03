from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from database import engine, Base
from routers import auth, donations, views


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Equivalent to Flask's `with app.app_context(): db.create_all()`
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="FoodCompass", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(views.router)
app.include_router(auth.router)
app.include_router(donations.router)
