"""Parse order confirmation emails into structured data."""

import re
from datetime import datetime
from typing import Optional


# Platform detection patterns
PLATFORM_PATTERNS = {
    "doordash": re.compile(r"doordash", re.I),
    "ubereats": re.compile(r"uber\s*eats|uber\.com", re.I),
    "grubhub": re.compile(r"grubhub", re.I),
    "amazon": re.compile(r"amazon", re.I),
    "walmart": re.compile(r"walmart", re.I),
    "target": re.compile(r"target\.com", re.I),
    "instacart": re.compile(r"instacart", re.I),
}

FOOD_PLATFORMS = {"doordash", "ubereats", "grubhub", "instacart"}
SHOPPING_PLATFORMS = {"amazon", "walmart", "target"}


def detect_platform(email: dict) -> Optional[str]:
    """Detect which platform sent this email."""
    sender = email.get("from", "")
    subject = email.get("subject", "")
    text = f"{sender} {subject}"
    for platform, pattern in PLATFORM_PATTERNS.items():
        if pattern.search(text):
            return platform
    return None


def is_order_email(email: dict) -> bool:
    """Check if email looks like an order confirmation."""
    subject = email.get("subject", "").lower()
    body = email.get("body", "").lower()
    text = f"{subject} {body}"
    order_keywords = [
        "order confirm", "your order", "order receipt",
        "order placed", "delivery confirm", "order #",
        "your receipt", "order summary", "thank you for your order",
    ]
    return any(kw in text for kw in order_keywords)


def extract_total(text: str) -> float:
    """Extract total amount from email text."""
    patterns = [
        r"total[:\s]*\$?([\d,]+\.?\d*)",
        r"charged[:\s]*\$?([\d,]+\.?\d*)",
        r"amount[:\s]*\$?([\d,]+\.?\d*)",
        r"\$\s*([\d,]+\.\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                continue
    return 0.0


def extract_items(text: str) -> list[dict]:
    """Extract item list from email text."""
    items = []
    # Common patterns: "1x Item Name $9.99" or "Item Name - $9.99" or "Item Name  $9.99"
    patterns = [
        r"(\d+)\s*x\s+(.+?)\s+\$?([\d.]+)",
        r"(.+?)\s+-\s+\$?([\d.]+)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if len(match) == 3:
                items.append({"name": match[1].strip(), "qty": int(match[0]), "price": float(match[2])})
            elif len(match) == 2:
                items.append({"name": match[0].strip(), "qty": 1, "price": float(match[1])})
    return items[:20]  # cap at 20 items


def extract_order_number(text: str) -> str:
    """Extract order number from email."""
    patterns = [
        r"order\s*#?\s*:?\s*([\w-]{5,})",
        r"#(\d{3}-\d{7}-\d{7})",  # Amazon format
        r"confirmation\s*#?\s*:?\s*([\w-]{5,})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1)
    return ""


def extract_restaurant(email: dict) -> str:
    """Extract restaurant name from food order email."""
    subject = email.get("subject", "")
    body = email.get("body", "")

    # DoorDash: "Your DoorDash order from [Restaurant] is confirmed"
    match = re.search(r"order from (.+?)(?:\s+is|\s*-|\s*\|)", subject, re.I)
    if match:
        return match.group(1).strip()

    # Uber Eats: often has restaurant in subject
    match = re.search(r"your .+ order from (.+)", subject, re.I)
    if match:
        return match.group(1).strip()

    # Try body
    match = re.search(r"(?:restaurant|from)[:\s]+(.+?)(?:\n|\r|$)", body, re.I)
    if match:
        return match.group(1).strip()[:100]

    return ""


def parse_date(text: str) -> Optional[datetime]:
    """Try to extract a date from email text."""
    date_str = ""
    # Look for "Date" header value from email
    patterns = [
        r"(\w+ \d{1,2},?\s*\d{4})",
        r"(\d{1,2}/\d{1,2}/\d{2,4})",
        r"(\d{4}-\d{2}-\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            break

    if not date_str:
        return None

    for fmt in ["%B %d, %Y", "%B %d %Y", "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def parse_food_order(email: dict) -> Optional[dict]:
    """Parse a food delivery order email into structured data."""
    platform = detect_platform(email)
    if not platform or platform not in FOOD_PLATFORMS:
        return None
    if not is_order_email(email):
        return None

    body = email.get("body", "")
    return {
        "gmail_message_id": email["id"],
        "platform": platform,
        "restaurant_name": extract_restaurant(email),
        "order_date": parse_date(email.get("date", "")) or datetime.utcnow(),
        "items": extract_items(body),
        "total": extract_total(body),
        "status": "confirmed",
        "raw_snippet": email.get("snippet", "")[:500],
    }


def parse_shopping_order(email: dict) -> Optional[dict]:
    """Parse a shopping order email into structured data."""
    platform = detect_platform(email)
    if not platform or platform not in SHOPPING_PLATFORMS:
        return None
    if not is_order_email(email):
        return None

    body = email.get("body", "")
    return {
        "gmail_message_id": email["id"],
        "platform": platform,
        "order_number": extract_order_number(f"{email.get('subject', '')} {body}"),
        "order_date": parse_date(email.get("date", "")) or datetime.utcnow(),
        "items": extract_items(body),
        "total": extract_total(body),
        "status": "confirmed",
        "raw_snippet": email.get("snippet", "")[:500],
    }
