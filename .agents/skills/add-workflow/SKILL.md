---
name: add-workflow
description: Use when implementing or modifying one of the three deep BIS workflows (standard/QCO, laboratory, hallmarking) or adding a new bounded workflow. Ensures gate checks, the WorkflowResult contract, and contract tests are all wired consistently.
---

# Add / Modify a Workflow

1. Read @/.agents/rules/gates.md and confirm which gate (A1/A2/A3) this
   workflow depends on, and its exact pass criteria.
2. Read @/.agents/rules/workflow-contract.md for the required interface
   and state invariants.
3. Implement the workflow in `app/workflows/<name>.py`, subclassing
   `Workflow` from `app/workflows/base.py`. Return only `WorkflowResult`.
4. Wire evidence sourcing through `app/retrieval/` (RAGFlow) and/or
   `app/db/` (Postgres) — never hardcode regulatory facts (see
   @/.agents/rules/data-and-security.md).
5. Register the workflow with `app/orchestration/router.py`, gated on
   `gate_registry.is_ready(<workflow>)`.
6. Write a contract test in `backend/tests/` asserting:
   - ANSWERED requires decision + evidence,
   - CLARIFICATION never carries a decision,
   - unready gate -> workflow does not claim BUILD-level behavior.
7. Run tests + type checks. Do not report done until they pass (see
   @/.agents/rules/testing.md).
8. If this workflow's existence or scope wasn't already in
   @/docs/PRD_v6.md, stop and flag the scope conflict per
   @/.agents/rules/scope-control.md instead of proceeding.
