"""Agent management endpoints — trigger and monitor all agents."""

from fastapi import APIRouter
from api.agents.scheduled import run_email_sync, run_favourites_validation, run_daily_maintenance

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/sync")
async def trigger_email_sync():
    result = await run_email_sync()
    return {"agent": "EmailSyncAgent", "result": str(result)}


@router.post("/validate")
async def trigger_favourites_validation():
    result = await run_favourites_validation()
    return {"agent": "FavouritesValidator", "result": result}


@router.post("/daily")
async def trigger_daily_maintenance():
    result = await run_daily_maintenance()
    return {"agents": ["EmailSyncAgent", "FavouritesValidator"], "result": result}


@router.get("/status")
def agent_status():
    """Master-Slave architecture — 7 chat agents + 2 scheduled agents."""
    return {
        "architecture": "Master-Slave with Verifier",
        "agents": [
            {"name": "MasterAgent", "type": "orchestrator", "model": "gemini-2.5-flash", "role": "Routes requests to specialized sub-agents", "sub_agents": ["FoodAgent", "ShoppingAgent", "EmailAgent", "ProfileAgent", "GeneralAgent"]},
            {"name": "FoodAgent", "type": "sub-agent", "model": "gemini-2.5-flash-lite", "tools": 4, "role": "Food ordering, restaurant suggestions, DoorDash"},
            {"name": "ShoppingAgent", "type": "sub-agent", "model": "gemini-2.5-flash-lite", "tools": 5, "role": "Product buying, reordering, Amazon cart"},
            {"name": "EmailAgent", "type": "sub-agent", "model": "gemini-2.5-flash-lite", "tools": 3, "role": "Send/search emails, sync Gmail orders"},
            {"name": "ProfileAgent", "type": "sub-agent", "model": "gemini-2.5-flash-lite", "tools": 3, "role": "User bio, preferences, favourites"},
            {"name": "GeneralAgent", "type": "sub-agent", "model": "gemini-2.5-flash-lite", "tools": 0, "role": "General knowledge, greetings"},
            {"name": "VerifierAgent", "type": "post-processor", "model": "gemini-2.5-flash-lite", "role": "Validates accuracy, completeness, links before returning to user"},
            {"name": "EmailSyncAgent", "type": "scheduled", "schedule": "daily", "tools": 1, "role": "Auto-syncs Gmail orders to database"},
            {"name": "FavouritesValidator", "type": "scheduled", "schedule": "daily", "tools": 0, "role": "Recomputes favourites from order data"},
        ],
        "total_agents": 9,
        "total_tools": 15,
    }
