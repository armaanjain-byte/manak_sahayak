---
activation: always_on
description: Workflow interface and state invariants
---

# Workflow Contract

Every workflow in `app/workflows/` MUST subclass `Workflow` (see
`app/workflows/base.py`) and its `run()` method MUST return only a
`WorkflowResult` — never a raw dict, never a bare string.

```python
class WorkflowResult(BaseModel):
    state: ResponseState  # ANSWERED | CLARIFICATION | CONFLICT | NOT_FOUND | HANDOFF
    decision: DecisionObject | None = None
    evidence: list[Evidence] = []
    clarification: ClarificationRequest | None = None
    action: Action | None = None
```

## State invariants (enforced, not advisory)
- `ANSWERED` -> `decision` AND `evidence` (>=1 authoritative item) are required.
- `CLARIFICATION` -> `clarification` required; `decision` MUST be absent.
- `CONFLICT` -> conflicting evidence items required.
- `NOT_FOUND` -> no `decision` present.
- `HANDOFF` -> `action` with an official BIS destination is required.

A workflow returning `ANSWERED` without decision+evidence is a bug, not
a style choice. Every new workflow ships with a contract test asserting
this invariant (see `.agents/skills/add-workflow`).

## Evidence contract
- `ANSWERED` requires >= 1 authoritative evidence item.
- mandatory_status=true requires authoritative QCO evidence.
- effective_from date requires a source supporting that date.
- Lab recommendation requires current status + scope evidence.
- `HANDOFF` requires a real official BIS destination URL.

## Regulatory data rule
Never hardcode IS numbers, QCO identifiers, mandatory status, effective
dates, lab eligibility, or certification requirements inside workflow
logic. These come only from structured data (Postgres) or evidence
(RAGFlow), linked by stable BIS entity IDs. Workflow code implements
reasoning, not regulatory facts.

## LLM boundary
LLM output MAY: classify intent, extract candidate entities, generate
clarification questions, explain an existing DecisionObject, localize
the final response (English/Hindi).

LLM output MAY NOT: establish mandatory status, establish an effective
date, establish a QCO relationship, establish laboratory eligibility,
invent an authoritative IS/QCO identifier. Treat any LLM-produced
identifier as a candidate needing structured validation, never as fact.
