"""Master-Slave Agent Architecture — Google ADK

Architecture:
  Master Agent (Orchestrator) → routes to specialized sub-agents
  ├── Food Agent (4 tools)
  ├── Shopping Agent (5 tools)
  ├── Email Agent (3 tools)
  ├── Profile Agent (3 tools)
  └── General Agent (no tools)

  Verifier Agent → validates every response before returning to user
"""

import os
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

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


# ═══════════════════════════════════════════════════════════════════════════════
# SUB-AGENTS (Slaves)
# ═══════════════════════════════════════════════════════════════════════════════

food_agent = Agent(
    name="FoodAgent",
    model="gemini-2.5-flash-lite",
    description="Handles all food-related requests: ordering food, suggesting restaurants, showing food order history, opening DoorDash.",
    instruction="""You are the Food Specialist agent. You handle ALL food-related requests.

Your tools:
- suggest_food_from_history: ALWAYS call this first when user wants food. It picks from their most-ordered restaurants.
- get_food_orders: Show order history with restaurant names, items, amounts, dates.
- search_food_to_order: Get search links for DoorDash/UberEats/Grubhub.
- autonomous_order_food: Open a real browser to DoorDash. Use when user says "order" or "open DoorDash".

RULES:
- Always suggest a SPECIFIC restaurant, never ask "what do you want?"
- Include clickable markdown links: [text](url)
- Show order amounts and dates when displaying history
- Be concise and action-oriented.""",
    tools=[get_food_orders, suggest_food_from_history, search_food_to_order, autonomous_order_food],
)

shopping_agent = Agent(
    name="ShoppingAgent",
    model="gemini-2.5-flash-lite",
    description="Handles all shopping requests: buying products, reordering past purchases, searching Amazon/Walmart, opening browser to add to cart.",
    instruction="""You are the Shopping Specialist agent. You handle ALL shopping/buying requests.

Your tools:
- suggest_product_from_history: Search past purchases. Use when user mentions something they bought before.
- find_product_in_gmail: Search Gmail for order confirmations. Use when user says "that thing I bought last month".
- get_shopping_orders: Show purchase history with items, amounts, platforms, dates.
- search_product_to_buy: Get Amazon/Walmart/Target search links.
- autonomous_shop_amazon: Open real browser, search Amazon, add to cart. Use when user says "buy" or "add to cart".

RULES:
- When user mentions a past purchase, SEARCH for it immediately — don't ask for more details.
- Include product names, prices, and clickable links.
- For reorders, find the exact product from history first.
- Be concise and action-oriented.""",
    tools=[get_shopping_orders, suggest_product_from_history, search_product_to_buy, autonomous_shop_amazon, find_product_in_gmail],
)

email_agent = Agent(
    name="EmailAgent",
    model="gemini-2.5-flash-lite",
    description="Handles all email requests: sending emails, searching inbox, syncing order confirmations from Gmail.",
    instruction="""You are the Email Specialist agent. You handle ALL email-related requests.

Your tools:
- send_email_for_user: Compose and send emails. Extract to/subject/body from user's message.
- search_emails_for_user: Search Gmail inbox. Use for "find emails about X" or "check my inbox".
- sync_emails_to_db: Pull order confirmations from Gmail into the database. Use when user says "sync".

RULES:
- When sending email, confirm what was sent (to, subject).
- When searching, show matching email subjects and senders.
- Be concise.""",
    tools=[send_email_for_user, search_emails_for_user, sync_emails_to_db],
)

profile_agent = Agent(
    name="ProfileAgent",
    model="gemini-2.5-flash-lite",
    description="Handles user profile, bio, preferences, and favourites data.",
    instruction="""You are the Profile Specialist agent. You manage user data.

Your tools:
- get_user_bio: Read profile (name, email, location, bio).
- update_user_bio: Update profile fields. Extract info from user's message.
- get_favourites: Show most-ordered restaurants, food items, products.

RULES:
- When user shares personal info ("I'm Sandeep, I live in Boston"), update bio immediately.
- When showing favourites, include order counts.
- Be friendly and concise.""",
    tools=[get_user_bio, update_user_bio, get_favourites],
)

general_agent = Agent(
    name="GeneralAgent",
    model="gemini-2.5-flash-lite",
    description="Handles general knowledge questions, greetings, and anything not related to food, shopping, email, or profile.",
    instruction="""You are the General Knowledge agent. You answer questions that don't fit other specialists.

Handle: greetings, general knowledge, explanations, recommendations, advice.
Do NOT handle: food ordering, shopping, email, profile updates — those go to other agents.

Be helpful, concise, and friendly.""",
    tools=[],
)


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFIER AGENT
# ═══════════════════════════════════════════════════════════════════════════════

verifier_agent = Agent(
    name="VerifierAgent",
    model="gemini-2.5-flash-lite",
    description="Validates agent responses for accuracy and completeness.",
    instruction="""You are the Verifier Agent. You receive a user's original question and a sub-agent's response.

Your job: Check the response and return a VERIFIED version.

CHECKS:
1. Does the response actually answer the user's question?
2. Are markdown links properly formatted? [text](url) — fix if broken.
3. Are product/restaurant names specific (not generic)?
4. Is important data included (prices, dates, order numbers)?
5. Is the response concise and actionable?

RULES:
- If the response is good, return it as-is (don't add unnecessary text).
- If there are issues, FIX them and return the corrected version.
- NEVER add disclaimers like "as a verifier" — just return the clean response.
- Keep the same tone and style as the original response.
- Return ONLY the final response text, nothing else.""",
    tools=[],
)

_verifier_session = InMemorySessionService()
_verifier_runner = Runner(agent=verifier_agent, app_name="Verifier", session_service=_verifier_session)


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER AGENT (Orchestrator)
# ═══════════════════════════════════════════════════════════════════════════════

master_agent = Agent(
    name="MasterAgent",
    model="gemini-2.5-flash",
    description="Master orchestrator that routes user requests to specialized sub-agents.",
    instruction="""You are the Master Agent — the brain's orchestrator. You NEVER answer questions directly.
Your ONLY job is to route the user's request to the correct specialist agent.

ROUTING RULES:
- Food/hungry/eat/restaurant/order food/DoorDash → transfer_to_agent: FoodAgent
- Buy/shop/purchase/reorder/Amazon/product/cart → transfer_to_agent: ShoppingAgent
- Email/send/inbox/sync/Gmail → transfer_to_agent: EmailAgent
- Name/bio/profile/preferences/favourites/location → transfer_to_agent: ProfileAgent
- Everything else (greetings, general knowledge, questions) → transfer_to_agent: GeneralAgent

IMPORTANT:
- ALWAYS delegate. NEVER answer directly.
- Route based on the PRIMARY intent of the message.
- If unclear, route to GeneralAgent.""",
    sub_agents=[food_agent, shopping_agent, email_agent, profile_agent, general_agent],
)

# Session and Runner for Master
session_service = InMemorySessionService()
runner = Runner(
    agent=master_agent,
    app_name="SecondBrain",
    session_service=session_service,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CHAT FUNCTION (Master → Sub-agent → Verifier pipeline)
# ═══════════════════════════════════════════════════════════════════════════════

async def chat(message: str, history: list[dict] | None = None) -> str:
    """Master-Slave-Verifier pipeline:
    1. Master routes to correct sub-agent
    2. Sub-agent executes with tools
    3. Verifier validates the response
    4. Return verified response to user
    """
    # Build context with history
    context_msg = message
    if history:
        conv = "\n".join([f"{m['role']}: {m['content']}" for m in history[-8:]])
        context_msg = f"Previous conversation:\n{conv}\n\nUser's latest message: {message}"

    # Create fresh session per request to avoid cross-contamination
    import time
    session_id = f"chat-{int(time.time() * 1000)}"
    session = await session_service.create_session(
        app_name="SecondBrain", user_id="user", session_id=session_id
    )

    # Step 1: Master routes to sub-agent, sub-agent executes
    content = types.Content(role="user", parts=[types.Part.from_text(text=context_msg)])

    sub_response = ""
    async for event in runner.run_async(
        user_id="user", session_id=session_id, new_message=content,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                sub_response = event.content.parts[0].text or ""

    if not sub_response:
        return "I couldn't process that request. Please try again."

    # Step 2: Verifier validates the response
    verified = await _verify_response(message, sub_response)
    return verified


async def _verify_response(user_message: str, agent_response: str) -> str:
    """Run the Verifier Agent on the sub-agent's response."""
    try:
        verify_prompt = f"""User asked: "{user_message}"

Agent responded: "{agent_response}"

Verify this response and return the final version."""

        session = await _verifier_session.create_session(
            app_name="Verifier", user_id="system", session_id=f"verify-{hash(user_message) % 10000}"
        )

        content = types.Content(role="user", parts=[types.Part.from_text(text=verify_prompt)])

        verified_text = ""
        async for event in _verifier_runner.run_async(
            user_id="system",
            session_id=f"verify-{hash(user_message) % 10000}",
            new_message=content,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    verified_text = event.content.parts[0].text or ""

        return verified_text or agent_response
    except Exception:
        # If verifier fails, return original response
        return agent_response
