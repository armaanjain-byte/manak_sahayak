---
activation: always_on
description: Open PRs and enable auto-merge automatically after self-verification passes
---

# PR Automation

After completing a phase and passing the checklist in
@/.agents/rules/self-verification.md (ruff/mypy/pytest all green,
diff scoped correctly), do the following automatically — do not wait
to be asked:

1. Push the current feature branch:
   `git push -u origin <branch-name>`

2. Open a PR against `develop` using the GitHub CLI:
   ```
   gh pr create --base develop --head <branch-name> \
     --title "<phase summary>" \
     --body "<self-verification checklist output + scope summary>"
   ```
   The PR body MUST include the full self-verification block
   (ruff/mypy/pytest results) so the human can review without
   re-running anything.

3. Enable auto-merge on that PR:
   `gh pr merge <branch-name> --auto --merge`
   (Use `--merge`, not `--squash` or `--rebase`, to preserve the
   `--no-ff`-style history the branching model expects.)

4. Do NOT delete the branch after merge — repo policy is to keep
   feature branches (see architecture.md). If `gh pr merge` prompts
   about branch deletion, decline it or pass `--delete-branch=false`.

## When NOT to auto-open/auto-merge
- If any self-verification check fails, do not open a PR. Fix and
  re-verify first, or stop and report the blocker.
- If the diff touches files outside this phase's declared scope
  (per scope-control.md), do not auto-merge — flag the scope conflict
  and wait for explicit human confirmation instead.
- If this is a high-stakes/foundational file explicitly flagged in a
  prompt as needing manual review (e.g. core contracts, gate criteria
  changes), open the PR but do NOT enable auto-merge — say so
  explicitly and wait for the human to merge manually.
