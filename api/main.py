"""Agentic Second Brain — FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from api.config import settings  # noqa — triggers env var setup
from api.db.base import init_db
from api.routes.gmail import router as gmail_router
from api.routes.chat import router as chat_router
from api.routes.sync import router as sync_router
from api.routes.bio import router as bio_router
from api.routes.vision import router as vision_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create DB tables
    init_db()
    yield


app = FastAPI(
    title="Agentic Second Brain",
    description="AI-powered personal assistant — knows your orders, favourites, and life through email.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(gmail_router, prefix="/auth")
app.include_router(chat_router)
app.include_router(sync_router)
app.include_router(bio_router)
app.include_router(vision_router)

@app.get("/api/health")
def health():
    from api.db.base import SessionLocal
    from api.models.food_order import FoodOrder
    from api.models.shopping import Shopping
    db = SessionLocal()
    try:
        return {
            "status": "healthy",
            "food_orders": db.query(FoodOrder).count(),
            "shopping_orders": db.query(Shopping).count(),
        }
    finally:
        db.close()


# Serve the chat UI at root — must be last (catches all unmatched routes)
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
