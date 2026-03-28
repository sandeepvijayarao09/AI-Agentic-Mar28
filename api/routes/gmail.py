"""Gmail API routes."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from api.auth.gmail import get_authorization_url, exchange_code_for_token, get_credentials
from api.services.gmail import list_emails, get_email, search_emails, send_email, mark_as_read

router = APIRouter(prefix="/gmail", tags=["gmail"])


# ── Auth ──────────────────────────────────────────────────────────────────────

@router.get("/authorize")
def authorize():
    """Redirect user to Google OAuth consent screen."""
    auth_url, state = get_authorization_url()
    return RedirectResponse(auth_url)


@router.get("/callback")
def oauth_callback(code: str, state: str):
    """Handle OAuth callback and store token."""
    try:
        exchange_code_for_token(code, state)
        return {"status": "authenticated", "message": "Gmail connected successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status")
def auth_status():
    """Check if Gmail is authenticated."""
    creds = get_credentials()
    return {"authenticated": creds is not None}


# ── Read ──────────────────────────────────────────────────────────────────────

@router.get("/emails")
def get_emails(
    max_results: int = Query(20, ge=1, le=100),
    query: str = Query("", description="Gmail search query"),
):
    """List emails from inbox."""
    try:
        return list_emails(max_results=max_results, query=query)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/emails/search")
def search(
    q: str = Query(..., description="Gmail search query e.g. 'from:boss@co.com'"),
    max_results: int = Query(20, ge=1, le=100),
):
    """Search emails using Gmail search syntax."""
    try:
        return search_emails(query=q, max_results=max_results)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/emails/{message_id}")
def get_single_email(message_id: str):
    """Fetch a single email by ID."""
    try:
        return get_email(message_id)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))


# ── Write ─────────────────────────────────────────────────────────────────────

class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    html: bool = False


@router.post("/emails/send")
def send(payload: SendEmailRequest):
    """Send an email."""
    try:
        return send_email(payload.to, payload.subject, payload.body, payload.html)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.patch("/emails/{message_id}/read")
def mark_read(message_id: str):
    """Mark an email as read."""
    try:
        return mark_as_read(message_id)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
