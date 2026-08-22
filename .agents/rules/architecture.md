---
activation: always_on
description: Core architecture and stack for Manak Sahayak
---

# Architecture

Manak Sahayak is a bounded AI reasoning/orchestration layer over BIS's
existing information ecosystem (SIH26107). It is not generic RAG — the
technical centerpiece is entity resolution + cross-source structured
reasoning. Read @/docs/PRD_v6.md before any architectural change.

## Stack
- Backend: Python, FastAPI, Pydantic v2, Uvicorn
- ORM/migrations: SQLAlchemy + Alembic
- Structured data: PostgreSQL
- Semantic retrieval: RAGFlow, linked to Postgres only via stable BIS
  entity/document IDs — never duplicate structured facts into the
  document index or vice versa.
- Frontend: undecided, API-first. Framework must not contain domain logic.

## Module map
- `app/core/` — entities.py (DecisionObject, Evidence, Confidence),
  states.py (five-state enum), errors.py
- `app/normalization/` — vocabulary.py, resolver.py, rules.py (Gate A1 critical path)
- `app/retrieval/` — ragflow_client.py, structured.py, candidate_ranking.py
- `app/workflows/` — base.py (Workflow ABC + WorkflowResult), workflow1/2/3
- `app/reasoning/` — applicability.py, qco.py, confidence.py, evidence.py
- `app/orchestration/` — router.py (intent -> workflow dispatch, checks gate readiness)
- `app/generation/` — llm.py, prompts.py, response_builder.py
- `app/actions/` — router.py, destinations.py (handoff URLs)
- `app/gates/` — criteria.py, status.py, registry.py
- `app/db/` — models.py, session.py, migrations/

## Pipeline
query -> intent -> entities -> workflow (if gate ready) -> DecisionObject
-> evidence -> LLM explanation -> action router -> API response
