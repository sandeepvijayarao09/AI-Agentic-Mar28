"""Gmail OAuth 2.0 flow — handles authorization and token management."""

import json
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow

from api.config import settings

# Scopes: read + send mail, NO delete
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",  # labels/read status, no delete
]

TOKEN_PATH = Path(".token.json")


def get_oauth_flow() -> Flow:
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.oauth_redirect_uri],
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=settings.oauth_redirect_uri,
    )
    return flow


def get_authorization_url() -> tuple[str, str]:
    """Returns (authorization_url, state)."""
    flow = get_oauth_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url, state


def exchange_code_for_token(code: str, state: str) -> Credentials:
    """Exchange authorization code for credentials and persist to disk."""
    flow = get_oauth_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
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
