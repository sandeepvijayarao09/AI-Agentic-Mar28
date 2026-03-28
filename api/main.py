"""Agentic Second Brain — FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.gmail import router as gmail_router

app = FastAPI(
    title="Agentic Second Brain",
    description="AI-powered knowledge base, task manager, and agent memory layer.",
    version="0.1.0",
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

# /auth/gmail/authorize  → start OAuth
# /auth/gmail/callback   → OAuth callback
# /auth/gmail/status     → check auth
# /auth/gmail/emails     → list emails
# /auth/gmail/emails/search → search
# /auth/gmail/emails/{id}   → single email
# /auth/gmail/emails/send   → send email


@app.get("/")
def root():
    return {"status": "ok", "app": "Agentic Second Brain", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
