"""Vision endpoint — identify products from images using Gemini."""

import base64
from fastapi import APIRouter, UploadFile, File, HTTPException
from google import genai

from api.config import settings

router = APIRouter(tags=["vision"])

client = genai.Client(api_key=settings.gemini_api_key)


@router.post("/identify")
async def identify_product(file: UploadFile = File(...)):
    """Upload an image, Gemini identifies the product, returns a search query for Amazon."""
    try:
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
        raise HTTPException(status_code=500, detail=str(e))
