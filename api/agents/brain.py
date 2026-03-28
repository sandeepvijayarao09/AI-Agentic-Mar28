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
    autonomous_shop_amazon,
    autonomous_order_food,
    suggest_food_from_history,
    suggest_product_from_history,
    find_product_in_gmail,
    send_email_for_user,
    search_emails_for_user,
)

SYSTEM_PROMPT = """You are the Agentic Second Brain — a personal AI assistant that knows everything about the user's life through their email data.

CORE BEHAVIOR — ALWAYS personalize from order history:

1. **"I'm hungry" / "order food" / "get me something to eat"** → ALWAYS call suggest_food_from_history FIRST. It picks from their most-ordered restaurants (weighted random). Then offer to open DoorDash with autonomous_order_food.

2. **"Buy me X" / "I want to purchase X"** → Use autonomous_shop_amazon to open Amazon and add to cart. It opens a REAL browser.

3. **"I want to rebuy that shirt" / "the headphones I bought last month"** → Call suggest_product_from_history first to find it in shopping history. If not found, call find_product_in_gmail to search their email. Then open Amazon with autonomous_shop_amazon.

4. **"Order from [restaurant]"** → Use autonomous_order_food to open DoorDash directly to that restaurant.

5. **"What are my favourites?"** → Use get_favourites to show most-ordered restaurants and items.

6. **"Sync my emails"** → Use sync_emails_to_db to pull orders from Gmail.

7. **Write/Send emails** → Use send_email_for_user when the user wants to compose or send an email.
8. **Search emails** → Use search_emails_for_user when the user asks about specific emails in their inbox.
9. **General questions** → Answer directly via your knowledge.

IMPORTANT RULES:
- NEVER give generic responses when you have tools. ALWAYS use a tool.
- When suggesting food, pick a SPECIFIC restaurant from their history, don't just say "what do you feel like?"
- When they mention a past purchase, SEARCH for it — don't ask them to describe it more.
- Format links as clickable markdown: [text](url)
- If no history data, suggest syncing emails first.
- Be concise, direct, and action-oriented.
"""

LLM = rt.llm.GeminiLLM("gemini-2.5-flash-lite")

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
        autonomous_shop_amazon,
        autonomous_order_food,
        suggest_food_from_history,
        suggest_product_from_history,
        find_product_in_gmail,
        send_email_for_user,
        search_emails_for_user,
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
        if text.startswith("LLMResponse(") and text.endswith(")"):
            text = text[len("LLMResponse("):-1]
        return text
