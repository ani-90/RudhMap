# RudhMap: the story so far

One page covering what was attempted at each step, what happened, and what was learned. Details,
numbers and the root-cause analysis of every miss are in the linked reports. Every step's pass criteria
were written and committed before its work began.

## The idea

**RudhMap** maps a code repository: every function and class, and what calls what. It builds the map
directly from the code with tree-sitter, with no LLM, and gives AI coding assistants (Claude Code,
Cursor) exactly the code they need. The aim is fewer tokens and fewer round trips than their usual
grep-and-read-whole-files approach, so that even small models answer well.

It started (Oct 2026) as an **evidence-cited architecture diagram generator**: every box and arrow cites
the `file:line` that proves it. On 2026-11-10 the direction changed to **context for LLMs**, because
diagrams added little value. The diagram code is frozen, not removed.

## Timeline

| Step | Goal | Result | Key lesson | Report |
|---|---|---|---|---|
| Phases 0-7 (Oct) | Extractors, graph, slicer, verifier, MCP server, draw.io diagrams | Working diagram pipeline; 12x faster scans; 232 tests | A diagram of a real repo is a "hub tangle"; the graph is the asset, not the picture | `CLAUDE.md` history |
| Context packs (Oct 25) | One `get_context` tool returning a token-budgeted pack | **No token saving** in a real Claude Code test | Comparing a pack to "read every file" flattered it; real agents read only 2-3 files | `eval/cases.md` (Case 6-7) |
| **1. Engine correctness** (Nov 10) | A complete, clean graph | Recall **55.9% → 99.3%**, precision 100% on 145 hand-labelled call sites | A stale `.claude/worktrees` copy had silently doubled the graph and zeroed cross-file links; the answer key had 9 omissions | `eval/reports/step1-engine.md` |
| **A. Baseline** (Nov 11) | Measure plain Claude before building anything | Haiku and Sonnet both 12/15 correct; Haiku 35k tokens per question | **Cost = model calls × ~6.4k fixed tokens.** 79% of tokens are cache reads; file content only ~16%. 16 of 17 wrong answers stopped one file short | `eval/reports/stepA-baseline.md` |
| **B. Tools** (Nov 12) | `find_symbol`, `show`, `trace`, `repo_map`: compact, complete, cited | All criteria passed: 0/1,161 outputs over budget, 97% find accuracy, 12/15 coverage, 42 ms warm | Most of the React frontend had been invisible (arrow components, `@/` aliases, default exports); libraries used relative imports the resolver skipped | `eval/reports/stepB-tools.md` |
| **C. Benchmark** (Nov 12-14) | Haiku + RudhMap: >= as correct, <= 70% of tokens | **Failed on cost in all 3 rounds** (107-133% of plain). Accuracy improved: 13/15, nudged 40/45 runs (Sonnet 36/45) | **Haiku's round count (~3.7) doesn't change with better tool results.** It adopted the tools but hedged with Grep and re-read files it had been shown, and every round carries ~700 tokens of tool definitions | `eval/reports/stepC-benchmark.md` |
| Option 2 (planned) | Test multi-question sessions, where compact results should compound | Not run; plan and pass criteria pre-registered | Prediction recorded in advance: natural probably won't pass | `docs/session-benchmark-plan.md` |

## What exists now

- **Engine:** Python and TypeScript/React extraction, call/inheritance/reference resolution, type
  tracking from stated types and return annotations, a cache outside the repo.
- **Tools:** 4 MCP tools plus the CLI (`rudhmap find|show|trace|map`), an in-memory index that rebuilds
  on file changes, 280+ tests.
- **Evaluation:**
  - hand-keyed question sets (15 tuning questions, 8 held-out, unused);
  - a headless Claude Code benchmark harness with 4 setups and per-run reports;
  - a 3-vote grader validated against hand grading;
  - an engine ground-truth eval;
  - a tool eval.

## Lessons that apply beyond this project

1. **Measure the real agent, not a proxy.** Two proxies (pack vs whole files, coverage) looked good; real
   runs didn't.
2. **In agent harnesses, rounds are the cost.** A tool that makes each round richer but doesn't remove
   rounds costs more, because its own definitions ride along on every round.
3. **Pre-register criteria and keep a held-out set.** It stopped three rounds of "almost passing" from
   turning into a claim.
4. **Check the checker.** The grader was too strict at first (fixed with one-line `must` facts), the
   answer key was wrong once, and a usage-limit outage produced a fake regression. Each was caught only
   by reading the raw runs.

## Branches

`step1-engine-fixes` → `stepA-baseline` → `stepB-tools` → `stepC-benchmark`, each building on the
previous one. All are pushed; none is merged into `main` yet.
