"""Main Agentic Second Brain — powered by Railtracks + Gemini."""

import railtracks as rt
from api.agents.tools import (
    get_food_orders,
    get_shopping_orders,
    get_favourites,
    get_user_bio,
    update_user_bio,
    sync_emails_to_db,
    search_food_to_order,
    search_product_to_buy,
)

SYSTEM_PROMPT = """You are the Agentic Second Brain — a personal AI assistant that knows everything about the user's life through their email data.

You have access to the user's:
- Food delivery order history (DoorDash, Uber Eats, Grubhub, Instacart)
- Shopping order history (Amazon, Walmart, Target)
- Favourite restaurants, food items, and products (auto-analyzed from orders)
- Personal bio and preferences

Your capabilities:
1. **General Questions**: Answer any general knowledge question naturally.
2. **Food Orders**: When the user talks about food, ordering, or eating — use get_food_orders and get_favourites to check their history, then use search_food_to_order to provide direct ordering links.
3. **Shopping**: When the user talks about buying/shopping — use get_shopping_orders to check history, then use search_product_to_buy to provide direct purchase links.
4. **Favourites**: Use get_favourites to show what they order most frequently.
5. **Profile**: Use get_user_bio and update_user_bio to view/edit their profile.
6. **Email Sync**: Use sync_emails_to_db to sync their latest orders from Gmail.

IMPORTANT BEHAVIORS:
- Be conversational, helpful, and proactive.
- If they mention wanting food, immediately check favourites and suggest top restaurants with ordering links.
- When providing links, format them as clickable markdown links.
- Always personalize based on their order history and favourites.
- If data seems empty, suggest syncing emails first with sync_emails_to_db.
- Keep responses concise but helpful.
"""

# Use Gemini as the LLM (reads GEMINI_API_KEY from env)
LLM = rt.llm.GeminiLLM("gemini-2.5-flash-lite")

# Create the main agent using Railtracks
SecondBrainAgent = rt.agent_node(
    name="SecondBrain",
    llm=LLM,
    system_message=SYSTEM_PROMPT,
    tool_nodes=[
        get_food_orders,
        get_shopping_orders,
        get_favourites,
        get_user_bio,
        update_user_bio,
        sync_emails_to_db,
        search_food_to_order,
        search_product_to_buy,
    ],
)


async def chat(message: str, history: list[dict] | None = None) -> str:
    """Send a message to the Second Brain agent and get a response."""
    with rt.Session(
        context={"prompt": message},
        save_state=False,
        timeout=60.0,
    ):
        result = await rt.call(SecondBrainAgent, message)
        text = str(result)
        # Strip LLMResponse wrapper from Railtracks output
        if text.startswith("LLMResponse(") and text.endswith(")"):
            text = text[len("LLMResponse("):-1]
        return text
