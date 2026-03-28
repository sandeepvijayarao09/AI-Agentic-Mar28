"""Agent management endpoints — trigger and monitor scheduled agents."""

from fastapi import APIRouter
from api.agents.scheduled import run_email_sync, run_favourites_validation, run_daily_maintenance

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/sync")
async def trigger_email_sync():
    """Trigger the Email Sync Agent to pull orders from Gmail."""
    result = await run_email_sync()
    return {"agent": "EmailSyncAgent", "result": str(result)}


@router.post("/validate")
async def trigger_favourites_validation():
    """Trigger the Favourites Accuracy Agent to revalidate data."""
    result = await run_favourites_validation()
    return {"agent": "FavouritesValidator", "result": result}


@router.post("/daily")
async def trigger_daily_maintenance():
    """Trigger full daily maintenance: email sync + favourites validation."""
    result = await run_daily_maintenance()
    return {"agents": ["EmailSyncAgent", "FavouritesValidator"], "result": result}


@router.get("/status")
def agent_status():
    """List all registered agents and their capabilities."""
    return {
        "agents": [
            {
                "name": "SecondBrain",
                "type": "chat",
                "tools": 13,
                "description": "Main conversational agent with 13 tools for food, shopping, favourites, bio, Gmail sync, and autonomous browser shopping",
            },
            {
                "name": "EmailSyncAgent",
                "type": "scheduled",
                "schedule": "daily",
                "description": "Autonomously checks Gmail for new order confirmations and updates the database",
            },
            {
                "name": "FavouritesValidator",
                "type": "scheduled",
                "schedule": "daily",
                "description": "Recomputes favourites from actual order data, removes stale entries, ensures accuracy",
            },
        ]
    }
