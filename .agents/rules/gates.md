---
activation: always_on
description: A1/A2/A3 workflow readiness gates
---

# Gates

Gate criteria are authoritative in @/docs/PRD_v6.md §20. This file
operationalizes them as engineering constraints — do not treat it as
a replacement source of truth; if it drifts from the PRD, the PRD wins
and this file must be updated to match.

## Rule
A workflow may only be marked/behave as [BUILD] if `app/gates/registry.py`
reports its gate as passed at runtime. Never hardcode readiness assumptions
in workflow or orchestration code.

## A1 — Vocabulary Readiness (Workflow 1: Standard/QCO)
- canonical_concepts >= 25
- aliases >= 75
- validated_standard_mappings >= 20
- validated_qco_mappings >= 10
Miss: freeze achieved subset, Workflow 1 serves only that subset,
clarify/abstain outside it. Never expand silently past target.

## A2 — Laboratory Readiness (Workflow 2)
- standards_with_validated_scope_mappings >= 20
- eligible_standard_lab_relationships >= 25 across >= 8 labs
- 100% of demo-recommended labs checked for current recognition/status + validity
- successful_e2e_lab_queries >= 10
Miss: keep validated subset only. Must never block Workflow 1 or 3.

## A3 — Hallmarking/HUID Readiness (Workflow 3)
- validated_huid_flows >= 6
- authoritative_evidence_records_mapped >= 15
- successful_e2e_consumer_queries >= 10
- verified_official_handoffs >= 2 (including HUID verification)
Miss: retain validated subset only. Must never block Workflow 1 or 2.

## Checkpoint B — Final Coverage Freeze (80% of build window)
Pure cutoff, not a dependency gate. Freeze all workflow coverage
permanently. No further expansion after B regardless of gate status.
Remaining time -> reliability, evaluation, adversarial testing, polish.

## Orchestration behavior
Orchestration checks `gate_registry.is_ready(workflow)` before dispatch.
If not ready: do not silently fall back to generic RAG. Use the bounded
fallback — clarification, abstention, or official BIS handoff.
