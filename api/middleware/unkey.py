"""Unkey API key verification middleware for rate limiting and access control."""

import httpx
from fastapi import Request, HTTPException
from api.config import settings


async def verify_api_key(request: Request):
    """Verify API key via Unkey. Skip if no root key configured or if it's a browser page."""
    # Skip verification if Unkey isn't configured
    if not settings.unkey_root_key:
        return

    # Skip for static files, OAuth callbacks, and health checks
    path = request.url.path
    skip_paths = ["/", "/auth/", "/api/health", "/identify"]
    if any(path.startswith(p) for p in skip_paths) or path.endswith(".html") or path.endswith(".css") or path.endswith(".js"):
        return

    # Check for API key in header
    api_key = request.headers.get("x-api-key") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not api_key:
        return  # Allow unauthenticated for now (browser UI doesn't send keys)

    # Verify with Unkey
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.unkey.com/v2/keys.verifyKey",
                headers={
                    "Authorization": f"Bearer {settings.unkey_root_key}",
                    "Content-Type": "application/json",
                },
                json={"key": api_key},
            )
            data = resp.json()
            if not data.get("valid", False):
                raise HTTPException(status_code=403, detail=f"Invalid API key: {data.get('code', 'unknown')}")
    except HTTPException:
        raise
    except Exception:
        pass  # Don't block if Unkey is down
