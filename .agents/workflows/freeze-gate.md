---
title: Freeze Gate
description: Evaluate and freeze a gate (A1/A2/A3) at a checkpoint.
---

# /freeze-gate

1. Ask which gate (A1/A2/A3) is being evaluated.
2. Pull current counts from `data/curated/` / `app/gates/registry.py`.
3. Compare against the numeric targets in @/.agents/rules/gates.md.
4. Report PASS or MISS explicitly, with the actual numbers.
5. Either way: freeze current vocabulary/coverage for that workflow,
   bump the relevant version, and confirm downstream workflow code
   only claims [BUILD] for the frozen subset.
6. Do not resume expansion for that gate after this freeze without an
   explicit new user request.
