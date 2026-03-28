# Architecture Decision Log

## ADR-001: Monorepo Structure

**Date:** 2026-03-28
**Status:** Accepted

**Decision:** Keep all components (agents, API, memory, knowledge, tasks, infra) in a single monorepo.

**Why:** Early-stage project — tight coupling between layers is expected. Splitting into multiple repos adds overhead before patterns emerge. Revisit after Phase 3.

---

## ADR-002: Google Gemini as Primary LLM

**Date:** 2026-03-28
**Status:** Proposed

**Decision:** Use Google Gemini API for LLM inference.

**Why:** Integration with Google ecosystem (Drive, Calendar, Search) is core to the product. Gemini's long context window is valuable for knowledge retrieval tasks.

**Trade-offs:** Vendor lock-in to Google. Mitigated by abstracting LLM calls behind an interface.

---

## ADR-003: Railtrack for Agent Orchestration

**Date:** 2026-03-28
**Status:** Under investigation

**Decision:** Use Railtrack as the agent building and orchestration infrastructure.

**Why:** Purpose-built for agentic workflows. Evaluate against alternatives (LangGraph, CrewAI) during Phase 3.

---

## ADR-004: DigitalOcean for Deployment

**Date:** 2026-03-28
**Status:** Accepted

**Decision:** Deploy on DigitalOcean App Platform with Managed Postgres and Spaces (object storage).

**Why:** Simple pricing, good CLI tooling (`doctl`), App Platform handles containers without K8s complexity.
