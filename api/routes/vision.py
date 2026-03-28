"""Vision endpoint — identify products from images using Gemini."""

import base64
from fastapi import APIRouter, UploadFile, File, HTTPException
from api.config import settings

router = APIRouter(tags=["vision"])


@router.post("/identify")
async def identify_product(file: UploadFile = File(...)):
    """Upload an image, Gemini identifies the product."""
    try:
        from google import genai
        client = genai.Client(api_key=settings.gemini_api_key)

        image_bytes = await file.read()
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite-preview",
            contents=[
                {
                    "parts": [
                        {"text": "Look at this image. Identify the main product or item shown. Return ONLY a short Amazon search query (2-5 words) that would find this exact product. No explanation, just the search query."},
                        {"inline_data": {"mime_type": file.content_type or "image/jpeg", "data": b64}},
                    ]
                }
            ],
        )

        search_query = response.text.strip().strip('"').strip("'")

        return {
            "identified_product": search_query,
            "amazon_search_url": f"https://www.amazon.com/s?k={search_query.replace(' ', '+')}",
            "message": f"I identified: '{search_query}'. Ready to add to your Amazon cart!",
        }
    except Exception as e:
        # Fallback — return the error but still give a usable response
        return {
            "identified_product": "product from image",
            "amazon_search_url": "https://www.amazon.com",
            "message": f"Could not identify product: {str(e)[:100]}",
        }
