"""Gmail service — read, search, and send emails. No delete operations."""

import base64
import email as email_lib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from googleapiclient.discovery import build

from api.auth.gmail import get_credentials


def _get_service():
    creds = get_credentials()
    if not creds:
        raise RuntimeError("Not authenticated. Visit /auth/gmail to authorize.")
    return build("gmail", "v1", credentials=creds)


def list_emails(max_results: int = 20, query: str = "") -> list[dict]:
    """List emails from inbox. Optionally filter with Gmail search query."""
    service = _get_service()
    result = (
        service.users()
        .messages()
        .list(userId="me", maxResults=max_results, q=query)
        .execute()
    )
    messages = result.get("messages", [])
    return [get_email(msg["id"]) for msg in messages]


def get_email(message_id: str) -> dict:
    """Fetch a single email by ID and return parsed fields."""
    service = _get_service()
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )
    return _parse_message(msg)


def search_emails(query: str, max_results: int = 20) -> list[dict]:
    """Search emails using Gmail search syntax (e.g. 'from:boss@co.com subject:urgent')."""
    return list_emails(max_results=max_results, query=query)


def send_email(to: str, subject: str, body: str, html: bool = False) -> dict:
    """Send an email. Set html=True for HTML body."""
    service = _get_service()

    if html:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body, "html"))
    else:
        msg = MIMEText(body)

    msg["to"] = to
    msg["subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"message_id": result["id"], "status": "sent"}


def mark_as_read(message_id: str) -> dict:
    """Mark an email as read."""
    service = _get_service()
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()
    return {"message_id": message_id, "status": "marked_read"}


def _parse_message(msg: dict) -> dict:
    headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
    body = _extract_body(msg["payload"])
    return {
        "id": msg["id"],
        "thread_id": msg.get("threadId"),
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", ""),
        "date": headers.get("Date", ""),
        "snippet": msg.get("snippet", ""),
        "body": body,
        "labels": msg.get("labelIds", []),
    }


def _extract_body(payload: dict) -> str:
    """Recursively extract plain text body from message payload."""
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    if mime_type.startswith("multipart/"):
        for part in payload.get("parts", []):
            text = _extract_body(part)
            if text:
                return text

    return ""
