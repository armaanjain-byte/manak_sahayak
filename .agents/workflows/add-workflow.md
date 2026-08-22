---
title: Add Workflow
description: End-to-end sequence for adding a new gated workflow.
---

# /add-workflow

1. Ask the user which workflow (1/2/3, or new) and confirm the target
   gate (A1/A2/A3) per @/.agents/rules/gates.md.
2. Apply the `add-workflow` skill.
3. Implement the workflow file and register it in the orchestration router.
4. Write and run contract tests.
5. Run full test suite + type checks.
6. Report: gate status, test results, and diff summary for review.
   Do not mark [BUILD] in any doc/comment unless the gate registry
   actually reports ready.
