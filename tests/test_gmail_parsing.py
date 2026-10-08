import base64

from api.services.gmail import _extract_body, _parse_message


def _b64(text):
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def test_extract_body_prefers_first_text_part():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/plain", "body": {"data": _b64("Order Total: $12.00")}},
            {"mimeType": "text/html", "body": {"data": _b64("<b>ignored</b>")}},
        ],
    }
    assert _extract_body(payload) == "Order Total: $12.00"


def test_extract_body_strips_html():
    payload = {"mimeType": "text/html", "body": {"data": _b64("<p>Order <b>#123456</b></p>\n<p>Total: $5.00</p>")}}
    assert _extract_body(payload) == "Order #123456 Total: $5.00"


def test_parse_message_falls_back_to_snippet():
    msg = {
        "id": "abc",
        "threadId": "t1",
        "snippet": "Your order from Chipotle",
        "labelIds": ["INBOX"],
        "payload": {
            "mimeType": "image/png",
            "headers": [
                {"name": "From", "value": "DoorDash <no-reply@doordash.com>"},
                {"name": "Subject", "value": "Order confirmed"},
                {"name": "Date", "value": "Sat, 21 Mar 2026 19:42:10 -0700"},
            ],
        },
    }
    parsed = _parse_message(msg)
    assert parsed["from"].startswith("DoorDash")
    assert parsed["subject"] == "Order confirmed"
    assert parsed["body"] == "Your order from Chipotle"
    assert parsed["date"] == "Sat, 21 Mar 2026 19:42:10 -0700"
