# Agentic Second Brain 🧠

> **Multimodal Frontier Hackathon 2026** — An AI-powered personal assistant that autonomously learns from your email to manage food orders, shopping, favourites, and more.

## What It Does

Your **Agentic Second Brain** connects to your Gmail, autonomously extracts order confirmations (DoorDash, Uber Eats, Amazon, Walmart, etc.), builds a structured knowledge base, and uses AI agents to:

- **Answer questions** about your order history ("What did I order last week?")
- **Recommend food** based on your most-ordered restaurants and items
- **Help you shop** by providing direct links to buy products you've purchased before
- **Auto-manage favourites** by analyzing order frequency
- **Update your profile** through natural conversation

## Demo

Chat with your Second Brain:

```
You: "I'm hungry, what should I order?"
Brain: Based on your order history, you've ordered from Chipotle 12 times
       and Panda Express 8 times. Here are direct links to order:
       - [Chipotle on DoorDash](https://doordash.com/...)
       - [Panda Express on Uber Eats](https://ubereats.com/...)
```

## Architecture

```
┌──────────────────────────────────────────────────┐
│           Next.js Chat UI (assistant-ui)         │
└────────────────────┬─────────────────────────────┘
                     │ POST /chat
┌────────────────────▼─────────────────────────────┐
│              FastAPI Backend                       │
│   ┌──────────────────────────────────────────┐   │
│   │     Railtracks Agent Orchestration        │   │
│   │  ┌──────┐ ┌──────┐ ┌────────┐ ┌──────┐ │   │
│   │  │ Food │ │ Shop │ │Favourit│ │General│ │   │
│   │  │Agent │ │Agent │ │ Agent  │ │ Agent │ │   │
│   │  └──┬───┘ └──┬───┘ └───┬────┘ └──┬───┘ │   │
│   └─────┼────────┼─────────┼──────────┼──────┘   │
│         │        │         │          │           │
│   ┌─────▼────────▼─────────▼──────────▼──────┐   │
│   │           Google Gemini API               │   │
│   └──────────────────────────────────────────┘   │
│   ┌──────────────┐  ┌───────────────────────┐    │
│   │   SQLite DB   │  │    Gmail API (OAuth)  │    │
│   │ food_orders   │  │  Auto-sync orders     │    │
│   │ shopping      │  │  from confirmations   │    │
│   │ favourites    │  └───────────────────────┘    │
│   │ user_bio      │                               │
│   └──────────────┘                                │
└──────────────────────────────────────────────────┘
                     │
        DigitalOcean App Platform
```

## Sponsor Tools Used

| Sponsor | Usage |
|---------|-------|
| **Railtracks** | Agent orchestration framework — routes user intent to specialized agents (food, shopping, general) with tool-calling capabilities |
| **DigitalOcean** | Deployment platform — App Platform hosts both backend and frontend |
| **assistant-ui** | React chat UI component library — powers the frontend conversation interface |
| **Augment Code** | AI-powered development — used throughout the build process |

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, SQLite
- **AI/LLM**: Google Gemini API (via Railtracks + litellm)
- **Agent Framework**: Railtracks 1.3.6
- **Frontend**: Next.js 16, React 19, Tailwind CSS, assistant-ui
- **Email**: Gmail API with OAuth 2.0
- **Deployment**: DigitalOcean App Platform

## Project Structure

```
Agentic-Second-Brain/
├── api/
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # Environment configuration
│   ├── agents/
│   │   ├── brain.py          # Railtracks agent (main orchestrator)
│   │   └── tools.py          # Tool functions (DB queries, search, sync)
│   ├── auth/
│   │   └── gmail.py          # Gmail OAuth 2.0 flow
│   ├── db/
│   │   └── base.py           # SQLAlchemy engine + models
│   ├── models/               # Database models
│   │   ├── food_order.py
│   │   ├── shopping.py
│   │   ├── user_favourite.py
│   │   └── user_bio.py
│   ├── routes/               # API endpoints
│   │   ├── chat.py           # POST /chat
│   │   ├── gmail.py          # Gmail auth + email operations
│   │   ├── sync.py           # POST /sync/gmail
│   │   └── bio.py            # GET/PUT /bio
│   └── services/
│       ├── gmail.py           # Gmail read/send/search
│       ├── order_parser.py    # Email → structured order data
│       └── sync.py            # Gmail-to-DB sync pipeline
├── frontend/
│   ├── app/                   # Next.js app router
│   └── components/
│       └── SecondBrainChat.tsx # Chat UI
├── requirements.txt
└── .env.example
```

## Quick Start

### 1. Backend

```bash
cd Agentic-Second-Brain
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your GEMINI_API_KEY and Google OAuth credentials to .env
uvicorn api.main:app --port 8080 --reload
```

### 2. Gmail Auth

Visit `http://localhost:8080/auth/gmail/authorize` to connect your Gmail.

### 3. Sync Orders

```bash
curl -X POST http://localhost:8080/sync/gmail
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000` and start chatting!

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Send message to AI agent |
| GET | `/auth/gmail/authorize` | Start Gmail OAuth |
| GET | `/auth/gmail/status` | Check Gmail auth status |
| POST | `/sync/gmail` | Sync orders from Gmail |
| GET | `/sync/stats` | DB record counts |
| GET | `/bio` | Get user profile |
| PUT | `/bio` | Update user profile |
| GET | `/api/health` | Health check |

## Autonomy Features

- **Auto-sync**: Extracts food and shopping orders from Gmail automatically
- **Auto-favourites**: Analyzes order frequency to build favourites list
- **Smart routing**: Agent autonomously decides which tool to use based on user intent
- **Real-time data**: Queries live database for personalized recommendations

## License

MIT
