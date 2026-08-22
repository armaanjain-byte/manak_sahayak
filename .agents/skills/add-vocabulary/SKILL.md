---
name: add-vocabulary
description: Use when adding or editing canonical product concepts, aliases, or product-to-standard/QCO mappings in the controlled BIS vocabulary. Enforces the curation flow and gate targets from the PRD.
---

# Add / Edit Vocabulary

1. Read @/.agents/rules/gates.md for the active gate's numeric targets
   (canonical_concepts, aliases, validated mappings). Check current
   counts in `data/curated/vocabulary/` before adding more —
   never expand past the active gate's target (see scope-control.md).
2. Extract candidate terms into `data/raw/` first — do not write
   directly into `data/curated/`.
3. Collapse raw terms into a canonical concept + alias list. LLM
   assistance is fine for generating alias candidates; the
   canonical-concept decision and the product->standard/QCO mapping
   must be human-validated, not LLM-asserted (see workflow-contract.md
   LLM boundary).
4. Write the validated result into `data/curated/vocabulary/` with a
   `taxonomy_version` bump.
5. Run normalization tests (`app/normalization/`) to confirm the new
   entries resolve correctly and don't collide with existing aliases.
6. Never touch `data/benchmark/` to make a query pass — see
   evaluation-freeze behavior in @/.agents/rules/scope-control.md.
