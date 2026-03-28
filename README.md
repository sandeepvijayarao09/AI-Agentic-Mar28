# Agentic-Second-Brain

> An AI-powered second brain — unified knowledge management, task orchestration, and persistent agent memory.

## Vision

A living, intelligent knowledge system where AI agents actively help you:

- **Capture** — ingest notes, documents, URLs, meeting transcripts, ideas
- **Connect** — surface non-obvious relationships between stored knowledge
- **Act** — break goals into tasks, execute them autonomously, track progress
- **Remember** — agents retain memory across sessions and learn your context over time

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                  User Interfaces                 │
│          (Web App / CLI / API / Webhooks)        │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│              Agent Orchestration Layer           │
│                  (Railtrack / Agents)            │
└──────┬──────────────────────────┬───────────────┘
       │                          │
┌──────▼──────┐          ┌────────▼────────┐
│  Knowledge  │          │   Task Engine   │
│    Base     │          │  & Scheduler    │
│ (Vector DB) │          └────────┬────────┘
└──────┬──────┘                   │
       │                  ┌───────▼───────┐
┌──────▼──────────────────▼───────────────┐
│              Google APIs                │
│  (Gemini · Drive · Calendar · Search)   │
└─────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│           Infrastructure (DigitalOcean)          │
│       App Platform · Managed Postgres · Spaces   │
└─────────────────────────────────────────────────┘
```

## Tech Stack (Evolving)

| Layer | Technology |
|---|---|
| AI / LLM | Google Gemini API |
| Agent Infra | Railtrack |
| Storage | Vector DB + Postgres |
| Deployment | DigitalOcean App Platform |
| Version Control | GitHub |

## Project Structure

```
Agentic-Second-Brain/
├── agents/          # Agent definitions and workflows
├── api/             # Backend API layer
├── memory/          # Persistent memory stores and schemas
├── knowledge/       # Knowledge ingestion and retrieval pipelines
├── tasks/           # Task engine and scheduler
├── infra/           # Infrastructure-as-code (DigitalOcean)
├── docs/            # Architecture decisions and notes
└── scripts/         # Utility and dev scripts
```

## Roadmap

- [ ] **Phase 1** — Core knowledge ingestion (text, URLs, files)
- [ ] **Phase 2** — Vector search + semantic retrieval
- [ ] **Phase 3** — Agent orchestration with Railtrack
- [ ] **Phase 4** — Task management and autonomous execution
- [ ] **Phase 5** — DigitalOcean deployment pipeline
- [ ] **Phase 6** — Google APIs integration (Drive, Calendar, Search)

## Getting Started

> Setup instructions will be added as the stack solidifies.

## Contributing

This is a personal project in active development. Architecture decisions are documented in [`docs/`](./docs/).

## License

MIT
