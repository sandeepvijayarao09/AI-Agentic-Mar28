"""Gmail OAuth 2.0 flow — handles authorization and token management."""

import json
from pathlib import Path
from urllib.parse import urlencode

import httpx
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from api.config import settings

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
]

TOKEN_PATH = Path(".token.json")
SCOPE_STRING = " ".join(SCOPES)


def get_authorization_url() -> tuple[str, str]:
    """Returns (authorization_url, state). No PKCE — simple OAuth."""
    import secrets
    state = secrets.token_urlsafe(16)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.oauth_redirect_uri,
        "response_type": "code",
        "scope": SCOPE_STRING,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    url = "https://accounts.google.com/o/oauth2/auth?" + urlencode(params)
    return url, state


def exchange_code_for_token(code: str) -> Credentials:
    """Exchange authorization code for credentials using direct HTTP POST."""
    resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.oauth_redirect_uri,
            "grant_type": "authorization_code",
        },
    )
    resp.raise_for_status()
    token_data = resp.json()

    creds = Credentials(
        token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )
    _save_token(creds)
    return creds


def get_credentials() -> Credentials | None:
    """Load credentials from disk, refresh if expired."""
    if not TOKEN_PATH.exists():
        return None

    creds = Credentials.from_authorized_user_info(
        json.loads(TOKEN_PATH.read_text()), SCOPES
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_token(creds)

    return creds if creds.valid else None


def _save_token(creds: Credentials) -> None:
    TOKEN_PATH.write_text(creds.to_json())
