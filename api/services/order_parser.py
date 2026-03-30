"""Parse order confirmation emails into structured data.

Each order extracts: order_id, date, name/restaurant, items, platform, amount
Uses regex first, falls back to Gemini for complex emails.
"""

import re
import json
from datetime import datetime, timezone
from typing import Optional


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
    """Detect platform from sender, subject, body, snippet."""
    sender = email.get("from", "")
    subject = email.get("subject", "")
    body = email.get("body", "")[:1500]
    snippet = email.get("snippet", "")
    text = f"{sender} {subject} {body} {snippet}"
    for platform, pattern in PLATFORM_PATTERNS.items():
        if pattern.search(text):
            return platform
    text_lower = text.lower()
    if any(kw in text_lower for kw in ["has shipped", "order total", "amazon.com/dp", "amazon.com/gp"]):
        return "amazon"
    if any(kw in text_lower for kw in ["order from", "delivery to", "delivery fee", "reorder from"]):
        return "doordash"
    return None


def is_order_email(email: dict) -> bool:
    """Check if email is an order confirmation."""
    text = f"{email.get('subject', '')} {email.get('body', '')} {email.get('snippet', '')}".lower()
    keywords = ["order confirm", "your order", "order receipt", "order placed", "has shipped",
                 "order #", "your receipt", "order summary", "order total", "delivery confirm"]
    return any(kw in text for kw in keywords)


def extract_order_number(text: str) -> str:
    """Extract order ID/number."""
    patterns = [
        r"#(\d{3}-\d{7}-\d{7})",           # Amazon: #112-1234567-8901234
        r"order\s*#?\s*:?\s*(\d{3}-\d{7}-\d{7})",  # Order #112-...
        r"order\s*#\s*([\w-]{6,30})",        # Order #ABC123
        r"order\s+(\d{3}-\d{7}-\d{7})",     # Order 112-...
        r"confirmation\s*#?\s*:?\s*([\w-]{6,})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1)
    return ""


def extract_total(text: str) -> float:
    """Extract order total amount."""
    # Look for "Order Total: $X" or "Total: $X" patterns
    patterns = [
        r"order\s*total[:\s]*\$?([\d,]+\.?\d*)",
        r"total[:\s]*\$?([\d,]+\.?\d*)",
        r"charged[:\s]*\$?([\d,]+\.?\d*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            try:
                val = float(match.group(1).replace(",", ""))
                if val > 0:
                    return val
            except ValueError:
                continue
    # Fallback: find the largest dollar amount
    amounts = re.findall(r"\$\s*([\d,]+\.\d{2})", text)
    if amounts:
        try:
            return max(float(a.replace(",", "")) for a in amounts)
        except ValueError:
            pass
    return 0.0


def extract_items(text: str) -> list[dict]:
    """Extract item list with name, qty, price."""
    items = []
    seen = set()

    # Pattern 1: "1x Product Name $price" or "1x Product Name - $price"
    for match in re.finditer(r"(\d+)\s*x\s+(.+?)\s*[-–]?\s*\$?([\d.]+)", text):
        name = match.group(2).strip().rstrip("-– ")
        if name and name not in seen and len(name) > 2 and len(name) < 120:
            items.append({"name": name, "qty": int(match.group(1)), "price": float(match.group(3))})
            seen.add(name)

    # Pattern 2: "Product Name - $price" (no qty prefix)
    if not items:
        for match in re.finditer(r"(?:^|\n)\s*(.+?)\s*[-–]\s*\$(\d+\.?\d*)", text):
            name = match.group(1).strip()
            if name and name not in seen and len(name) > 2 and len(name) < 120 and not re.match(r"^(subtotal|tax|tip|delivery|shipping|total|order)", name, re.I):
                items.append({"name": name, "qty": 1, "price": float(match.group(2))})
                seen.add(name)

    # Pattern 3: "Product Name $price" (space separated)
    if not items:
        for match in re.finditer(r"(?:^|\n)\s*(?:\d+x\s+)?(.{5,80}?)\s+\$([\d.]+)", text):
            name = match.group(1).strip()
            if name and name not in seen and not re.match(r"^(subtotal|tax|tip|delivery|shipping|total|order|free)", name, re.I):
                items.append({"name": name, "qty": 1, "price": float(match.group(2))})
                seen.add(name)

    return items[:20]


def extract_restaurant(email: dict) -> str:
    """Extract restaurant name from food order email."""
    subject = email.get("subject", "")
    body = email.get("body", "")

    # "order from [Restaurant]" in subject or body
    for text in [subject, body[:500]]:
        match = re.search(r"order from\s+(.+?)(?:\s+is|\s*[-|!]|\s+Estimated|\s+Items)", text, re.I)
        if match:
            return match.group(1).strip()

    # "Your order from [Restaurant]" pattern
    match = re.search(r"your .+ order from (.+?)(?:\s*[-|!]|\n)", subject, re.I)
    if match:
        return match.group(1).strip()

    # Bold restaurant name in body
    match = re.search(r"from\s+(.+?)(?:\s*[-–]|\s+\d|\n)", body[:300], re.I)
    if match:
        name = match.group(1).strip()
        if len(name) > 2 and len(name) < 60:
            return name

    return ""


def parse_date(text: str) -> Optional[datetime]:
    """Extract date from email text or headers."""
    patterns = [
        r"(\w+ \d{1,2},?\s*\d{4})",
        r"(\d{1,2}/\d{1,2}/\d{2,4})",
        r"(\d{4}-\d{2}-\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            for fmt in ["%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
    return None


def extract_with_gemini(email: dict) -> Optional[dict]:
    """Use Gemini to extract structured order data from complex emails."""
    try:
        import os
        from google import genai
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            return None

        client = genai.Client(api_key=api_key)
        body = email.get("body", "")[:2000]
        subject = email.get("subject", "")

        prompt = f"""Extract order data from this email. Return ONLY valid JSON, no other text.

Subject: {subject}
Body: {body}

Return JSON with these exact fields:
{{"order_id": "string", "platform": "string (amazon/doordash/ubereats/walmart/target)", "name": "string (restaurant name for food, or 'Amazon Order' for shopping)", "items": [{{"name": "string", "qty": 1, "price": 0.00}}], "total": 0.00, "date": "YYYY-MM-DD"}}"""

        response = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
        text = response.text.strip()
        # Extract JSON from response
        if "```" in text:
            text = text.split("```")[1].replace("json", "").strip()
        return json.loads(text)
    except Exception:
        return None


def parse_food_order(email: dict) -> Optional[dict]:
    """Parse a food delivery order email. Extracts: order_id, date, restaurant, items, platform, total."""
    platform = detect_platform(email)
    if not platform or platform not in FOOD_PLATFORMS:
        return None
    if not is_order_email(email):
        return None

    body = email.get("body", "")
    subject = email.get("subject", "")
    full_text = f"{subject} {body}"

    order_id = extract_order_number(full_text)
    restaurant = extract_restaurant(email)
    items = extract_items(body)
    total = extract_total(body)
    date = parse_date(email.get("date", "")) or parse_date(full_text)

    # If regex failed to get key fields, try Gemini
    if not restaurant or not items or total == 0:
        gemini_data = extract_with_gemini(email)
        if gemini_data:
            if not restaurant:
                restaurant = gemini_data.get("name", "")
            if not items:
                items = gemini_data.get("items", [])
            if total == 0:
                total = gemini_data.get("total", 0)
            if not order_id:
                order_id = gemini_data.get("order_id", "")
            if not date:
                try:
                    date = datetime.strptime(gemini_data.get("date", ""), "%Y-%m-%d")
                except (ValueError, TypeError):
                    pass

    return {
        "gmail_message_id": email["id"],
        "platform": platform,
        "restaurant_name": restaurant,
        "order_date": date or datetime.now(timezone.utc),
        "items": items,
        "total": total,
        "status": "confirmed",
        "raw_snippet": email.get("snippet", "")[:500],
    }


def parse_shopping_order(email: dict) -> Optional[dict]:
    """Parse a shopping order email. Extracts: order_id, date, items, platform, total."""
    platform = detect_platform(email)
    if not platform or platform not in SHOPPING_PLATFORMS:
        return None
    if not is_order_email(email):
        return None

    body = email.get("body", "")
    subject = email.get("subject", "")
    full_text = f"{subject} {body}"

    order_number = extract_order_number(full_text)
    items = extract_items(body)
    total = extract_total(body)
    date = parse_date(email.get("date", "")) or parse_date(full_text)

    # If regex failed, try Gemini
    if not items or total == 0:
        gemini_data = extract_with_gemini(email)
        if gemini_data:
            if not items:
                items = gemini_data.get("items", [])
            if total == 0:
                total = gemini_data.get("total", 0)
            if not order_number:
                order_number = gemini_data.get("order_id", "")
            if not date:
                try:
                    date = datetime.strptime(gemini_data.get("date", ""), "%Y-%m-%d")
                except (ValueError, TypeError):
                    pass

    return {
        "gmail_message_id": email["id"],
        "platform": platform,
        "order_number": order_number,
        "order_date": date or datetime.now(timezone.utc),
        "items": items,
        "total": total,
        "status": "confirmed",
        "raw_snippet": email.get("snippet", "")[:500],
    }
