---
name: agentic-second-brain
description: AI personal assistant that learns your orders from Gmail and acts on them with Google ADK + Gemini agents
author: sandeepvijayarao09
version: 1.0.0
tags: [ai-agent, gmail, shopping, food-ordering, google-adk, gemini]
---

# Agentic Second Brain

An AI-powered personal assistant with a master agent, five sub-agents plus a verifier, two scheduled agents, 15 tools, and 2-pass vision that:

- Connects to Gmail and extracts food/shopping order history into a structured database
- Suggests food based on most-ordered restaurants (weighted random — highest ordered = highest priority)
- Optionally (ENABLE_BROWSER_AUTOMATION=1) opens a real browser to add products to your Amazon cart or find a restaurant on DoorDash
- Identifies products from photos using 2-pass Gemini Vision and finds them on Amazon
- Finds past purchases in Gmail and helps you reorder
- Sends emails on your behalf
- Supports voice input and voice output
- Runs scheduled agents daily to sync new orders and validate data accuracy

## Setup

1. Clone: `git clone https://github.com/sandeepvijayarao09/AI-Agentic-Mar28`
2. Install (Python 3.12): `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add your GEMINI_API_KEY and Google OAuth credentials
4. Run: `uvicorn api.main:app --port 8080`
5. Connect Gmail: visit `http://localhost:8080/auth/gmail/authorize`
6. Sync orders: click "Sync Orders Now" in Settings or `POST /sync/gmail`
7. Chat: open `http://localhost:8080` and start talking

## Agents

| Agent | Type | Tools | Description |
|---|---|---|---|
| MasterAgent | Chat | 15 (across sub-agents) | Routes to Food, Shopping, Email, Profile and General sub-agents; Verifier checks the answer |
| EmailSyncAgent | Scheduled | 1 | Checks Gmail daily for new order confirmations |
| FavouritesValidator | Scheduled | 0 | Recomputes favourites accuracy from order data |

## Tech Stack

Google ADK, Google Gemini 2.5 Flash Lite, FastAPI, SQLAlchemy, Playwright, Gmail API, DigitalOcean App Platform spec

## Demo mode

No live deployment right now. Run `DEMO_MODE=1 uvicorn api.main:app --port 8080` to try the UI with synthetic orders and no Gmail account.

## GitHub

https://github.com/sandeepvijayarao09/AI-Agentic-Mar28
