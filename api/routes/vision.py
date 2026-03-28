"""Vision endpoint — specialized product identification agent using Gemini."""

import base64
from fastapi import APIRouter, UploadFile, File
from api.config import settings

router = APIRouter(tags=["vision"])

IDENTIFY_PROMPT = """You are a product identification specialist. Analyze this image carefully.

Step 1: Identify the EXACT product — brand, model name, model number, color, size if visible.
Step 2: Look for any text, logos, branding, or design cues that reveal the specific model.
Step 3: Consider the latest models available. If it looks like a very recent/unreleased product, identify it as the latest known model.

Return your answer in this EXACT format (nothing else):
PRODUCT: [exact product name with brand and model]
SEARCH: [Amazon search query 3-6 words to find this exact product]

Examples:
PRODUCT: Apple iPhone 15 Pro Max Natural Titanium
SEARCH: iPhone 15 Pro Max Natural Titanium

PRODUCT: Nike Air Max 1 '86 OG Big Bubble
SEARCH: Nike Air Max 1 86 OG

Be precise. Do NOT guess a generic name. Identify the EXACT model."""

VERIFY_PROMPT = """You are a product verification agent. I identified a product from an image as: "{product}"

The user wants to buy this exact product on Amazon. Verify and refine:
1. Is this identification specific enough to find the RIGHT product on Amazon?
2. If the model is wrong or too generic, correct it based on visual details.
3. Return the BEST Amazon search query (3-8 words) that will find this EXACT product as the #1 result.

Return ONLY the Amazon search query, nothing else."""


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
