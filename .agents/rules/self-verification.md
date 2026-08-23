---
activation: always_on
description: Mandatory self-verification before any PR is declared ready
---

# Self-Verification (Pre-PR Checklist)

Before declaring ANY branch/PR ready for merge, you MUST actually run
the following and paste real output — not describe what you expect
to happen:

```
ruff check .
mypy app/
pytest -v
```

## Report format
End every "done" report with this exact block, filled with real values:

```
## Self-Verification
- ruff:   PASS/FAIL (N issues)
- mypy:   PASS/FAIL (N errors)
- pytest: PASS/FAIL (N passed, N failed)
- Files touched outside this phase's scope: <list, or "none">
- Gate/contract invariants affected: <list, or "none">
- Ambiguities flagged: <list, or "none">
```

If any check fails, do not report done — fix it or stop and explain
the blocker. Never mark a task complete on the basis of "this should
work" or "the logic looks correct" without having actually executed it.

## Diff discipline
Before finishing, run `git diff --stat` against the branch's base and
confirm the changed-files list matches only what this phase's prompt
asked for. If it doesn't, either justify the extra change against
.agents/rules/scope-control.md or revert it.

This rule exists so the human reviewer can trust a "done" report
without re-running everything themselves for every PR.
