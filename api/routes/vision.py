"""Vision endpoint — specialized product identification agent using Gemini."""

import base64
from fastapi import APIRouter, UploadFile, File
from api.config import settings

router = APIRouter(tags=["vision"])

IDENTIFY_PROMPT = """You are an Amazon shopping assistant. A user wants to BUY the product in this image.

Your ONLY job: identify what product this is so they can find it on Amazon.

Rules:
- Return the REAL, PURCHASABLE product name (brand + model + color)
- NEVER say "mockup", "concept", "rendering", "prototype", or "unreleased"
- If the product looks like an iPhone, identify the CLOSEST available iPhone model (e.g., iPhone 16 Pro, iPhone 15 Pro)
- Always assume the user wants to BUY it — give a name that EXISTS on Amazon RIGHT NOW
- Focus on: brand, model, color, key variant

Return in this EXACT format:
PRODUCT: [purchasable product name]
SEARCH: [Amazon search query 3-5 words]

Examples:
PRODUCT: Apple iPhone 16 Pro Natural Titanium
SEARCH: iPhone 16 Pro Natural Titanium

PRODUCT: Nike Air Max 1 White Red
SEARCH: Nike Air Max 1 White Red"""

VERIFY_PROMPT = """The user wants to BUY this product on Amazon. First identification: "{product}"

Your job: return the BEST Amazon search query (3-6 words) to find this EXACT product.

Rules:
- The query must find a REAL product you can BUY on Amazon
- Remove words like "mockup", "concept", "rendering" — only real product names
- Keep brand + model + color/variant
- Return ONLY the search query, nothing else"""


@router.post("/identify")
async def identify_product(file: UploadFile = File(...)):
    """Two-pass product identification: identify then verify."""
    try:
        from google import genai
        client = genai.Client(api_key=settings.gemini_api_key)

        image_bytes = await file.read()
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        mime = file.content_type or "image/jpeg"

        # Pass 1: Identify product
        resp1 = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[{"parts": [
                {"text": IDENTIFY_PROMPT},
                {"inline_data": {"mime_type": mime, "data": b64}},
            ]}],
        )

        text1 = resp1.text.strip()
        product_name = ""
        search_query = ""

        for line in text1.split("\n"):
            line = line.strip()
            if line.startswith("PRODUCT:"):
                product_name = line.replace("PRODUCT:", "").strip()
            elif line.startswith("SEARCH:"):
                search_query = line.replace("SEARCH:", "").strip()

        if not product_name:
            product_name = text1.split("\n")[0].strip()
        if not search_query:
            search_query = product_name

        # Pass 2: Verify and refine with the image again
        resp2 = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[{"parts": [
                {"text": VERIFY_PROMPT.format(product=product_name)},
                {"inline_data": {"mime_type": mime, "data": b64}},
            ]}],
        )

        refined_query = resp2.text.strip().strip('"').strip("'")
        if refined_query and len(refined_query) > 3:
            search_query = refined_query

        amazon_url = f"https://www.amazon.com/s?k={search_query.replace(' ', '+')}"

        return {
            "identified_product": product_name,
            "search_query": search_query,
            "amazon_search_url": amazon_url,
            "message": f"Identified: **{product_name}**. [Buy on Amazon]({amazon_url})",
        }
    except Exception as e:
        return {
            "identified_product": "product from image",
            "search_query": "product",
            "amazon_search_url": "https://www.amazon.com",
            "message": f"Could not identify product: {str(e)[:100]}",
        }
