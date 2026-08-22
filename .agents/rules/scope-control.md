---
activation: always_on
description: Prevent silent scope/coverage expansion
---

# Scope Control

This project's core risk is not bad code — it is silent scope creep
that undermines the bounded-coverage claims the PRD depends on.

Do NOT, without an explicit user request:
- Add new BIS service domains opportunistically.
- Increase taxonomy coverage beyond the currently active gate target.
- Add a new workflow without also adding/updating its gate in
  `app/gates/registry.py` and @/.agents/rules/gates.md.
- Convert [SPEC] or [PARTIAL] functionality into [BUILD] by assumption
  rather than by the relevant gate actually passing.
- Modify the frozen benchmark (`data/benchmark/`) to improve scores,
  remove failing cases, or add taxonomy entries solely to fix a failure.
  Any benchmark change creates a new benchmark version — never edit v1
  in place once frozen.

## Ambiguity rule
When a request conflicts with PRD-defined scope: do not silently pick
an implementation. Stop and state:
1. the conflict,
2. the applicable PRD/gate rule,
3. the smallest PRD-compliant implementation, for the user to confirm.

## Versioning
Taxonomy and benchmark changes must be versioned
(`taxonomy_version`, `benchmark_version`), not silently mutated in place.
