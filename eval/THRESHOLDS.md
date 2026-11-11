# Benchmark thresholds (committed 2026-11-11, before any RudhMap arm was run)

These decide step C. They are written before the step B tools exist so they
can't be tuned to the result. Changing them later requires a dated entry below
explaining why, and the original numbers stay in the report.

Question set: `eval/bench/questions.yaml` (15 questions, 3 repos). Harness:
`eval/bench/run_bench.py`. Each (question, arm) is run 3 times.

## Definitions

- **Correct**: the grader finds every critical fact and no major false claim.
  A question counts as correct for an arm if at least 2 of its 3 runs are correct.
- **Tokens**: `total` = input + cache writes + cache reads + output, as reported
  by Claude Code, summed over the whole run. Also reported: `context` = input +
  cache writes (new content the model had to read, excluding cached system prompt
  re-reads).
- Per arm we report the **median per question** (median of the 3 runs, then the
  median across questions) and the **sum over all runs**.

## Step C pass (all must hold)

1. **Quality:** Haiku + RudhMap correct count >= plain Haiku correct count.
2. **Cost:** Haiku + RudhMap median `total` tokens per question <= 0.7 x plain
   Haiku's (at least 30% fewer).
3. **No big regressions:** no question where plain Haiku is correct and
   Haiku + RudhMap is wrong in all 3 runs, unless its RCA shows the cause is
   outside RudhMap (grader error, ambiguous key).

## Headline (reported, not required)

- Haiku + RudhMap correct count >= plain Sonnet's.
- Sonnet + RudhMap: same criteria as above against plain Sonnet.

## Stop rule

If 3 rounds of step C changes don't meet the pass criteria, stop and rethink
the product instead of shipping a token saver that doesn't save.

## Changes

(none)
