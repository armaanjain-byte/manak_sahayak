---
name: run-evaluation
description: Use when running or reporting results from the 120-query stratified benchmark. Ensures the frozen benchmark isn't mutated and results are reported per the PRD's in-coverage/out-of-coverage split.
---

# Run Evaluation

1. Verify `data/benchmark/` taxonomy_version matches the currently
   frozen vocabulary version — do not run eval against a vocabulary
   that has changed since the benchmark was frozen without bumping
   the benchmark version too.
2. Confirm the benchmark composition matches the PRD split: ~50%
   direct in-coverage, ~17% ambiguous/adversarial in-coverage, ~33%
   out-of-coverage (unseen/unsupported/abstention cases).
3. Run all 120 queries through the live orchestration path (not a
   shortcut/mock), per `backend/tests/benchmark/run_eval.py`.
4. Report metrics SEPARATELY for in-coverage vs out-of-coverage —
   never merge them into a single blended accuracy number.
5. Do not modify queries, remove failing cases, or add vocabulary
   entries to fix a failure after this run has started. If a real bug
   is found, fix the bug, rerun the full frozen set, and record it as
   a new evaluation run against the same frozen benchmark version.
