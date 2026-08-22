---
activation: always_on
description: Definition of done and testing requirements
---

# Definition of Done

Never report a task complete until:
1. Relevant unit/integration/contract tests pass.
2. Type/static checks pass where configured (mypy/ruff or equivalent).
3. The affected workflow's gate status is still valid (re-check, don't assume).
4. No existing contract/integration tests regress.
5. The final diff has actually been inspected, not just generated.
6. If behavior changed, the relevant test or benchmark doc is updated.

## New workflow requirement
Every new/changed workflow ships with a contract test asserting the
state invariants in @/.agents/rules/workflow-contract.md — at minimum:
- a workflow cannot return ANSWERED without decision+evidence,
- a workflow cannot return CLARIFICATION with a decision present.

## Test layout
`backend/tests/` — keep flat unless it grows past ~15 files, then split
into unit/ and contracts/. Do not pre-create empty ceremony folders.
