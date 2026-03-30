"""Master-Slave Agent Architecture — Google ADK

Master Agent:
  1. THINKS — analyzes user intent, plans execution strategy
  2. DEPLOYS — dispatches one or more sub-agents
  3. CHAINS — sequences multiple agents for complex tasks
  4. VERIFIES — runs Verifier on every output before returning

Architecture:
  User → Master (Think → Plan → Deploy → Chain → Verify) → User
           │
           ├── FoodAgent (4 tools)
           ├── ShoppingAgent (5 tools)
           ├── EmailAgent (3 tools)
           ├── ProfileAgent (3 tools)
           ├── GeneralAgent (0 tools)
           └── VerifierAgent (post-processor)
"""

import time
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from api.agents.tools import (
    get_food_orders, get_shopping_orders, get_favourites,
    get_user_bio, update_user_bio, sync_emails_to_db,
    search_food_to_order, search_product_to_buy,
    autonomous_shop_amazon, autonomous_order_food,
    suggest_food_from_history, suggest_product_from_history,
    find_product_in_gmail, send_email_for_user, search_emails_for_user,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SUB-AGENTS (Workers)
# ═══════════════════════════════════════════════════════════════════════════════

food_agent = Agent(
    name="FoodAgent",
    model="gemini-2.5-flash-lite",
    description="Food specialist — ordering, suggestions, history, DoorDash. Deploy for: hungry, food, eat, restaurant, order food, DoorDash, meal.",
    instruction="""You are the Food Specialist. Execute the food task given to you.
- suggest_food_from_history: Call FIRST for vague requests ("I'm hungry")
- get_food_orders: Show order history (restaurant, items, amount, date)
- search_food_to_order: Get DoorDash/UberEats links
- autonomous_order_food: Open real DoorDash browser
Always give SPECIFIC restaurant names and markdown links [text](url).""",
    tools=[get_food_orders, suggest_food_from_history, search_food_to_order, autonomous_order_food],
)

shopping_agent = Agent(
    name="ShoppingAgent",
    model="gemini-2.5-flash-lite",
    description="Shopping specialist — buying, reordering, Amazon cart. Deploy for: buy, shop, purchase, reorder, Amazon, product, cart, headphones, shirt.",
    instruction="""You are the Shopping Specialist. Execute the shopping task given to you.
- suggest_product_from_history: Search past purchases to rebuy
- find_product_in_gmail: Search Gmail for order emails
- get_shopping_orders: Show purchase history (items, amount, platform, date)
- search_product_to_buy: Get Amazon/Walmart/Target links
- autonomous_shop_amazon: Open real Amazon browser + add to cart
Always include product names, prices, and markdown links.""",
    tools=[get_shopping_orders, suggest_product_from_history, search_product_to_buy, autonomous_shop_amazon, find_product_in_gmail],
)

email_agent = Agent(
    name="EmailAgent",
    model="gemini-2.5-flash-lite",
    description="Email specialist — send, search, sync Gmail. Deploy for: email, send, inbox, sync, Gmail, message.",
    instruction="""You are the Email Specialist. Execute the email task given to you.
- send_email_for_user: Send emails (extract to/subject/body)
- search_emails_for_user: Search inbox
- sync_emails_to_db: Sync order emails to database
Confirm actions taken. Be concise.""",
    tools=[send_email_for_user, search_emails_for_user, sync_emails_to_db],
)

profile_agent = Agent(
    name="ProfileAgent",
    model="gemini-2.5-flash-lite",
    description="Profile specialist — bio, preferences, favourites. Deploy for: name, bio, profile, favourites, location, preferences, who am I.",
    instruction="""You are the Profile Specialist. Execute the profile task given to you.
- get_user_bio: Read user profile
- update_user_bio: Update profile (extract info from message)
- get_favourites: Show top restaurants/items by order count
Include order counts for favourites. Be friendly.""",
    tools=[get_user_bio, update_user_bio, get_favourites],
)

general_agent = Agent(
    name="GeneralAgent",
    model="gemini-2.5-flash-lite",
    description="General knowledge — greetings, questions, advice. Deploy for anything that doesn't fit other agents.",
    instruction="Answer general questions helpfully and concisely. You are part of the Second Brain AI assistant.",
    tools=[],
)


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFIER AGENT (Quality Gate)
# ═══════════════════════════════════════════════════════════════════════════════

verifier_agent = Agent(
    name="VerifierAgent",
    model="gemini-2.5-flash-lite",
    description="Validates and corrects agent responses.",
    instruction="""You are the Verifier. You receive a task execution result and validate it.

CHECKS:
1. Does it answer the user's actual question?
2. Are markdown links valid? [text](url) — fix broken ones
3. Are names specific (not generic)?
4. Is data complete (prices, dates, order IDs)?
5. Is it concise and actionable?

ACTIONS:
- If GOOD: return the response as-is
- If ISSUES: fix and return corrected version
- If INCOMPLETE: add "[Note: some data may be missing]"

NEVER add meta-commentary. Return ONLY the clean final response.""",
    tools=[],
)


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER AGENT (Thinking Orchestrator)
# ═══════════════════════════════════════════════════════════════════════════════

# The Master uses a planning tool to think and decide
def _plan_execution(user_message: str, conversation_context: str = "") -> dict:
    """Master Agent's thinking tool. Analyzes user intent and creates an execution plan.

    Args:
        user_message: The user's current message.
        conversation_context: Recent conversation history for context.

    Returns a plan with agents to deploy and whether to chain them.
    """
    msg = f"{conversation_context} {user_message}".lower()

    plan = {
        "thinking": "",
        "agents_to_deploy": [],
        "chain": False,
        "chain_reason": "",
    }

    # ── Think: Analyze intent ──
    food_signals = any(w in msg for w in ["hungry", "food", "eat", "restaurant", "order food", "doordash", "pizza", "burrito", "meal", "lunch", "dinner", "breakfast"])
    shop_signals = any(w in msg for w in ["buy", "shop", "purchase", "reorder", "amazon", "product", "cart", "headphone", "shirt", "jacket", "shoe", "nike", "macbook"])
    email_signals = any(w in msg for w in ["email", "send", "inbox", "sync", "gmail", "message to"])
    profile_signals = any(w in msg for w in ["name", "bio", "profile", "favourit", "favorit", "location", "who am i", "my info", "preferences"])
    rebuy_signals = any(w in msg for w in ["reorder", "buy again", "that thing i bought", "bought last", "i bought", "rebuy"])

    # ── Plan: Decide agents and chaining ──

    # Complex: Rebuy requires chaining Shopping → Email (search history, then Gmail)
    if rebuy_signals:
        plan["thinking"] = "User wants to rebuy something. Chain: ShoppingAgent searches history, if not found chain to EmailAgent to search Gmail, then back to ShoppingAgent to open Amazon."
        plan["agents_to_deploy"] = ["ShoppingAgent", "EmailAgent"]
        plan["chain"] = True
        plan["chain_reason"] = "Search purchase history first, fall back to Gmail search, then buy"

    # Complex: "Order my usual" requires Profile (get favs) → Food (order it)
    elif food_signals and ("usual" in msg or "regular" in msg or "same as last" in msg):
        plan["thinking"] = "User wants their usual order. Chain: ProfileAgent gets favourites, then FoodAgent orders from top restaurant."
        plan["agents_to_deploy"] = ["ProfileAgent", "FoodAgent"]
        plan["chain"] = True
        plan["chain_reason"] = "Get favourites first, then order from top restaurant"

    # Complex: "Sync and show my orders" requires Email (sync) → Profile (show)
    elif email_signals and (food_signals or shop_signals or profile_signals):
        plan["thinking"] = "User wants to sync AND view data. Chain: EmailAgent syncs, then deploy viewer agent."
        agents = ["EmailAgent"]
        if food_signals:
            agents.append("FoodAgent")
        elif shop_signals:
            agents.append("ShoppingAgent")
        else:
            agents.append("ProfileAgent")
        plan["agents_to_deploy"] = agents
        plan["chain"] = True
        plan["chain_reason"] = "Sync first, then show results"

    # Simple: Single agent
    elif food_signals:
        plan["thinking"] = "Food-related request. Deploy FoodAgent."
        plan["agents_to_deploy"] = ["FoodAgent"]
    elif shop_signals:
        plan["thinking"] = "Shopping-related request. Deploy ShoppingAgent."
        plan["agents_to_deploy"] = ["ShoppingAgent"]
    elif email_signals:
        plan["thinking"] = "Email-related request. Deploy EmailAgent."
        plan["agents_to_deploy"] = ["EmailAgent"]
    elif profile_signals:
        plan["thinking"] = "Profile-related request. Deploy ProfileAgent."
        plan["agents_to_deploy"] = ["ProfileAgent"]
    else:
        plan["thinking"] = "General question. Deploy GeneralAgent."
        plan["agents_to_deploy"] = ["GeneralAgent"]

    return plan


# Agent registry for deployment
AGENT_REGISTRY = {
    "FoodAgent": food_agent,
    "ShoppingAgent": shopping_agent,
    "EmailAgent": email_agent,
    "ProfileAgent": profile_agent,
    "GeneralAgent": general_agent,
}

# Session services
_agent_sessions = {name: InMemorySessionService() for name in AGENT_REGISTRY}
_agent_runners = {
    name: Runner(agent=agent, app_name=name, session_service=_agent_sessions[name])
    for name, agent in AGENT_REGISTRY.items()
}

_verifier_session = InMemorySessionService()
_verifier_runner = Runner(agent=verifier_agent, app_name="Verifier", session_service=_verifier_session)


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

async def _deploy_agent(agent_name: str, message: str) -> str:
    """Deploy a single sub-agent and get its response."""
    if agent_name not in _agent_runners:
        return f"Agent {agent_name} not found."

    session_svc = _agent_sessions[agent_name]
    runner = _agent_runners[agent_name]

    sid = f"{agent_name}-{int(time.time() * 1000)}"
    await session_svc.create_session(app_name=agent_name, user_id="user", session_id=sid)

    content = types.Content(role="user", parts=[types.Part.from_text(text=message)])

    response = ""
    async for event in runner.run_async(user_id="user", session_id=sid, new_message=content):
        if event.is_final_response():
            if event.content and event.content.parts:
                response = event.content.parts[0].text or ""

    return response


async def _verify(user_message: str, agent_response: str) -> str:
    """Run Verifier Agent on the response."""
    try:
        sid = f"verify-{int(time.time() * 1000)}"
        await _verifier_session.create_session(app_name="Verifier", user_id="system", session_id=sid)

        prompt = f'User asked: "{user_message}"\n\nAgent responded: "{agent_response}"\n\nVerify and return the final response.'
        content = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])

        result = ""
        async for event in _verifier_runner.run_async(user_id="system", session_id=sid, new_message=content):
            if event.is_final_response():
                if event.content and event.content.parts:
                    result = event.content.parts[0].text or ""

        return result or agent_response
    except Exception:
        return agent_response


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER CHAT — Think → Plan → Deploy → Chain → Verify
# ═══════════════════════════════════════════════════════════════════════════════

async def chat(message: str, history: list[dict] | None = None) -> str:
    """Master Agent pipeline:
    1. THINK — analyze user intent
    2. PLAN — create execution plan (which agents, chain or not)
    3. DEPLOY — dispatch sub-agent(s)
    4. CHAIN — if plan requires, pass output of agent A as input to agent B
    5. VERIFY — validate final output
    """
    # Build context
    context = ""
    if history:
        context = "\n".join([f"{m['role']}: {m['content']}" for m in history[-8:]])

    # ── Step 1: THINK + PLAN ──
    plan = _plan_execution(message, context)

    # ── Step 2+3: DEPLOY + CHAIN ──
    if plan["chain"] and len(plan["agents_to_deploy"]) > 1:
        # Chain mode: output of agent A feeds into agent B
        chain_result = ""
        full_context = f"{context}\n\nUser: {message}" if context else message

        for i, agent_name in enumerate(plan["agents_to_deploy"]):
            if i == 0:
                # First agent gets the user's message
                chain_result = await _deploy_agent(agent_name, full_context)
            else:
                # Subsequent agents get previous result + original message
                chained_msg = f"Previous agent ({plan['agents_to_deploy'][i-1]}) found: {chain_result}\n\nOriginal user request: {message}\n\nContinue handling this request with the information above."
                next_result = await _deploy_agent(agent_name, chained_msg)
                # Combine results — later agent's response takes priority if substantive
                if next_result and len(next_result) > 20:
                    chain_result = next_result

        response = chain_result
    else:
        # Single agent deployment
        agent_name = plan["agents_to_deploy"][0] if plan["agents_to_deploy"] else "GeneralAgent"
        full_context = f"Conversation context:\n{context}\n\nUser: {message}" if context else message
        response = await _deploy_agent(agent_name, full_context)

    if not response:
        return "I couldn't process that request. Please try again."

    # ── Step 4: VERIFY ──
    verified = await _verify(message, response)

    return verified
