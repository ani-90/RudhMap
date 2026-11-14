# Step C: Benchmark and iterate

**Branch:** `stepC-benchmark` · **Dates:** 2026-11-12 to 2026-11-14 · **Verdict: FAIL on cost after 3 rounds → stop rule applies to the token-saving claim**

This report records what we set out to show, what happened in each round, and, as asked, **what we
intended Claude to do with the tools versus what it actually did.** Every number comes from the raw
runs in `eval/results/bench/stepC-r1/`, `stepC-r2/` and `stepC-r3/` (one JSON file per run, plus a
`runs.md` table with one row per run).

---

## 1. Goal and pass criteria

Show that a small model (Claude Haiku) with RudhMap answers repo questions **at least as correctly**
as plain Haiku, using **at least 30% fewer tokens**. The criteria were committed before any RudhMap run
(`eval/THRESHOLDS.md`, commit `c7e3acd`):

| # | Criterion (Haiku + RudhMap, natural setup, vs plain Haiku) |
|---|---|
| 1 | Correct questions >= plain Haiku's (a question counts as correct if >= 2 of its 3 runs are) |
| 2 | Median tokens per question <= 0.7 x plain Haiku's |
| 3 | No question plain Haiku gets right that RudhMap gets wrong in all 3 runs |
| — | At most 3 rounds of fixes. **Stop rule:** if they don't pass, don't ship a token saver that doesn't save |
| — | Passing also requires the 8 held-out questions to pass, run once at the end (they were never run) |

## 2. Setups

The same 15 tuning questions over 3 repos (Knowledge-News-App, fastapi template, httpx). Every run is a
fresh headless Claude Code session on a clean export of the repo, with 3 runs per question.

| Setup | Tools available | Question it answers |
|---|---|---|
| **Plain** | Read, Grep, Glob | The baseline |
| **RudhMap (natural)** | Read, Grep, Glob + RudhMap's 4 tools; the model chooses | Does RudhMap help in real use? (**judged by the pass criteria**) |
| **RudhMap (nudged)** (round 3) | Natural + one system-prompt line, the line a README would ask users to put in CLAUDE.md: *"get code with the rudhmap tools… don't re-read the same code with Read or Grep"* | Does an explicit instruction fix trust? |
| **RudhMap-only** | Only RudhMap's 4 tools | Are the tools *sufficient*? (diagnostic) |
| Plain Sonnet | Read, Grep, Glob | Reference point |

Plain Haiku and Sonnet were run in round 1. Rounds 2 and 3 re-ran only the RudhMap setups, since nothing
about the baseline changed. Total: **405 benchmark runs**, each graded 3 times by a blind Sonnet grader.

## 3. Results

### 3.1 Headline per round (Haiku)

| Round | Setup | Correct questions | Correct runs | Median tokens / question | vs Plain | Median model calls | Read/Grep after RudhMap answered (mean per run) |
|---|---|---|---|---|---|---|---|
| — | **Plain** | 12/15 | 37/45 | 31,430 | — | 3 | — |
| 1 | Natural | 11/15 | 32/45 | 33,685 | 107% | 3 | 2.7 |
| 1 | Only | 8/15 | 24/45 | 30,756 | 98% | 4 | 0 |
| 2 | Natural | 12/15 | 34/45 | 35,428 | 113% | 4 | 2.5 |
| 2 | Only | 12/15 | 33/45 | 30,106 | 96% | 4 | 0 |
| 3 | Natural | **13/15** | 36/45 | 35,375 | 113% | 4 | 2.0 |
| 3 | **Nudged** | **13/15** | **40/45** | 41,667 | 133% | 4 | **0.4** |
| 3 | Only | 10/15 | 32/45 | 29,871 | 95% | 4 | 0 |
| — | Plain **Sonnet** | 12/15 | 36/45 | 23,507 | — | 3 | — |

Round 2's figures are after re-grading; see issue 7.1.

### 3.2 Pass criteria, final round (natural)

| Criterion | Target | Result | Pass |
|---|---|---|---|
| 1. Quality | >= 12/15 | 13/15 | ✅ |
| 2. Cost | <= 22,001 tokens | 35,375 (113%) | ❌ |
| 3. No reliable regressions | none | none | ✅ |

**Step C fails on criterion 2 in every round.** No setup with Read/Grep available reached even
"equal tokens". The stop rule applies to the token-saving claim.

### 3.3 Per question, round 3 (median tokens of 3 runs; correct runs in brackets)

| Q | Plain Haiku | Natural | Nudged | Only | Plain Sonnet |
|---|---|---|---|---|---|
| kna-1 | 17,585 (0/3) | 26,675 (1/3) | 26,797 (2/3) | 12,600 (1/3) | 21,200 (0/3) |
| kna-2 | 55,689 (1/3) | 57,170 (2/3) | 51,186 (3/3) | 44,051 (2/3) | 40,731 (1/3) |
| kna-3 | 46,192 (3/3) | 59,858 (3/3) | 41,667 (3/3) | 34,057 (3/3) | 29,725 (3/3) |
| kna-4 | 28,362 (3/3) | 38,652 (3/3) | 38,820 (3/3) | 26,341 (3/3) | 30,057 (3/3) |
| kna-5 | 36,588 (3/3) | 38,448 (3/3) | 40,004 (3/3) | 29,871 (3/3) | 31,503 (3/3) |
| tpl-1 | 31,430 (3/3) | 32,325 (3/3) | 27,520 (3/3) | 20,241 (3/3) | 21,242 (2/3) |
| tpl-2 | 26,916 (3/3) | 29,207 (3/3) | 48,192 (3/3) | 38,141 (3/3) | 23,173 (3/3) |
| tpl-3 | 92,925 (3/3) | 80,138 (3/3) | 73,685 (3/3) | 78,726 (1/3) | 38,592 (3/3) |
| tpl-4 | 28,690 (0/3) | 34,996 (0/3) | 50,334 (1/3) | 27,160 (0/3) | 21,058 (0/3) |
| tpl-5 | 32,254 (3/3) | 35,375 (3/3) | 37,080 (3/3) | 25,612 (3/3) | 20,133 (3/3) |
| httpx-1 | 26,270 (3/3) | 32,834 (2/3) | 22,007 (3/3) | 16,969 (3/3) | 22,562 (3/3) |
| httpx-2 | 24,411 (3/3) | 25,555 (3/3) | 25,577 (3/3) | 18,740 (3/3) | 14,828 (3/3) |
| httpx-3 | 58,573 (3/3) | 43,765 (3/3) | 44,889 (1/3) | 31,613 (1/3) | 38,241 (3/3) |
| httpx-4 | 28,767 (3/3) | 33,489 (2/3) | 44,699 (3/3) | 30,507 (0/3) | 24,143 (3/3) |
| httpx-5 | 67,261 (3/3) | 40,799 (2/3) | 41,861 (3/3) | 32,015 (3/3) | 23,507 (3/3) |

---

## 4. What we intended vs what Claude actually did

### The intended workflow

Step A showed that cost is driven by **model calls**: every call re-sends ~6.4k tokens of fixed context
(Claude Code's instructions, tool definitions, the conversation so far). So RudhMap was designed for
this flow:

> **Call 1:** `show <function>` → the function's source plus what it calls (one line each, tiny bodies
> inline) plus who calls it plus constants it uses, everything needed. **Call 2:** answer. Two calls,
> no file reading, no grep.

The model was expected to (a) pick RudhMap first, (b) trust its output as the real source, (c) not
re-read the same code, and (d) stop once it had what it needed.

### What actually happened

| # | Intended | What Claude did | Evidence | Effect |
|---|---|---|---|---|
| **B1** | Pick RudhMap first | ✅ **Did this.** RudhMap was the first tool in most natural runs | Natural: 40/45 runs (r1), 38/45 (r2), 35/45 (r3) used RudhMap first; nudged 45/45 | Adoption was never the problem |
| **B2** | Use RudhMap *instead of* Grep | ❌ **Hedged: Grep in parallel** with RudhMap in the very first call, "just in case" | First call contained both Grep/Glob and a RudhMap tool in 30/45 (r1), 23/45 (r2), 20/45 (r3) natural runs | Paid for both kinds of output from the start |
| **B3** | Trust `show` output as the real code | ❌ **Didn't trust it: fell back to Read/Grep after RudhMap had answered** | Mean Read/Grep calls after the first RudhMap answer: 2.7 (r1), 2.5 (r2), 2.0 (r3). Round 1 alone: 82 Reads + 29 Greps; round 2: 73 Reads | The single biggest cost driver in natural: RudhMap's cost stacked on top of the normal cost instead of replacing it |
| **B4** | Not re-open what it was shown | ❌ **Re-read files RudhMap had just shown.** In r2 the most re-read files were exactly the ones whose functions `show` had returned (`crud.py` 7, `login.py` 6, `_client.py` 5, `_models.py` 4, `aggregator.py` 4) | Per-run tool sequences in `runs.md`; e.g. kna-5 r1: `show app/api/quiz.py` → `Read quiz.py` | Same content paid for twice |
| **B5** | Look up and open in one step | ❌ **Two steps:** `find_symbol` (names only) → `show` in the next call, often → `find_symbol` again | RudhMap-only r2 sequences: "find_symbol > show" (6 runs), "find_symbol > show > find_symbol" (6), "find_symbol+repo_map > show" (3)… | +1 model call vs Plain, whose first call often does Grep+Read in parallel, guessing the path from the question |
| **B6** | Answer from the caller list | ❌ **Got the right list and still read the files.** It used the right tool (`trace … direction=up` returned all callers), plus a parallel Grep, then read 3 files anyway | tpl-2 r1 (natural): `Grep` + `trace get_user_by_email up` → Read `login.py`, `users.py`, `crud.py` | An answer it already had cost 3 extra file reads. (An earlier version of this analysis called this a wrong-direction mistake; checking the run showed `direction=up` was used, so it is the same distrust as B3/B4) |
| **B7** | Follow the chain RudhMap shows | ❌ **Stopped early** once it had one function, even when the answer needed the next hop | kna-1 (RudhMap-only, r1): one `show refresh_feed`, then answer, missing what the background pipeline does (0/3 in r1) | Wrong answers (fixed in r2 by printing the chain inside `show`) |
| **B8** | Use facts that are explicitly shown | ❌ **Ignored a shown fact.** `embed()` → `return []` was printed inline, yet the answer said semantic dedup works | kna-2 (r1/r2, several runs): major false claim | Wrong answer despite correct context (fixed by flagging `[stub: always returns []]`) |
| **B9** | An explicit instruction fixes trust | ✅/❌ **Partly.** The nudge cut fallback from 2.0 to 0.4 Read/Grep per run and gave the best accuracy of any setup (40/45 runs) | r3 nudged row | But tokens went **up** (133%): calls stayed at 4, and Claude now opened *more* through RudhMap, with bigger outputs (median 3.1k tokens of RudhMap output per run vs 1.1k natural) |
| **B10** | Fewer calls → fewer tokens | ❌ **Call count didn't move.** Mean model calls per run: Plain 3.69; natural 3.78 / 3.76 / 3.64; nudged 3.69; only 4.18 / 3.87 / 3.69 | Cross-round stats (§3.1 and the per-round analysis) | RudhMap changed *what* Claude read, not *how many rounds* it took. Every RudhMap call also carries +650-743 tokens of tool definitions, so equal calls means more tokens |

### The core finding

**Claude Haiku's number of rounds is a habit of the model, not a function of how much it learns per
round.** It explores in about 3-4 rounds whatever the tools return. Better results changed its
*answers*, raising accuracy to 13/15 and 40/45 runs, but not its *round count*. Because cost is rounds ×
~7k tokens, a tool that adds ~700 tokens to every round and doesn't remove rounds cannot save tokens in
this harness. The original plan assumed "complete results → fewer follow-up calls". That assumption
is what failed.

---

## 5. Tool gaps found and fixed between rounds

All were found by the RudhMap-only setup (which fails when the tools lack something) and fixed as
general rules, not per-question patches.

| Round found | Gap | Example | Fix (round) |
|---|---|---|---|
| 1 | Module-level constants invisible | `ALGORITHM = "HS256"`, `password_hash = PasswordHash((Argon2Hasher(), BcryptHasher()))`; tpl-1 0/3 | `show` lists module values the code uses, from its file or imported (r2) |
| 1 | `show <file>` returned a 33-token outline even with `detail=full` | tpl-4: route guard in module-level code; kna-5: model Read the file instead | File source with line numbers on request, and by default for files up to 120 lines (r2) |
| 1 | No text search for phrases | "access_token localStorage" matched no function | `find_symbol` adds lines containing all the words (r2) |
| 1 | Indirection followed one hop only | `refresh_feed` → `_run_pipeline_bg` → `run_pipeline`, stopping before the agents (kna-1 0/3) | "which calls" follows callbacks/module values up to 3 levels (r2) |
| 1 | Stubs not flagged | `embed()` → `return []` misread | `[stub: always returns []]` (r2) |
| 1 | (Believed) who-calls not obvious from `trace`; the premise turned out wrong, see B6 | — | `trace` (down) also states the callers; descriptions clarified (r2). Harmless, but made on a misread run |
| 2 | Lookup and open took separate calls | B5 above | `find_symbol` opens a clear best match in the same call; `show "a, b"` opens several at once (r3) |

Effect on sufficiency (RudhMap-only correct): **8/15 → 12/15 → 10/15**. Round 3's dip came from bigger
combined outputs: httpx-3/httpx-4/tpl-3 lost runs where the model answered from a cut or crowded output
(see `runs.md`).

## 6. Where RudhMap did help (real, but not the claim we set out to prove)

1. **Accuracy.** Natural and nudged reached **13/15 questions** vs plain Haiku's 12. Nudged had **40/45
   correct runs, more than plain Haiku (37) and plain Sonnet (36).** On Knowledge-News-App, RudhMap-only
   beat both plain Haiku and Sonnet in round 2. Haiku with RudhMap matched or beat Sonnet's correctness
   at about 7% of Sonnet's dollar cost.
2. **The most expensive questions got cheaper.** These are the long explorations where plain Haiku
   wanders:

   | Q | Plain Haiku | Natural (r3) |
   |---|---|---|
   | tpl-3 | 92.9k | 80.1k |
   | httpx-3 | 58.6k | 43.8k |
   | httpx-5 | 67.3k | 40.8k |

   The median is dominated by cheap questions, where plain Haiku already needs only 2-3 calls and
   RudhMap's per-call overhead makes it more expensive.
3. **RudhMap-only spends fewer tokens:**
   - **Mean:** 31.9k per run vs plain's 41.8k (−24%) in r3.
   - **Median:** 95% of plain.
   - **But** at lower accuracy (10/15). With no fallback the model can't hedge, which is cheaper but
     sometimes misses.
4. **Dollar cost** was slightly lower for every RudhMap setup ($0.09-0.11 per 45 runs vs $0.12), because
   more of its tokens are cheap cache reads.

## 7. Issues found in the evaluation itself

**7.1 Grader outage created a false regression (round 2).**
- **Symptom:** 12 answers ungraded, all on tpl-4/tpl-5. Criterion 3 flagged tpl-5 as "plain right,
  RudhMap wrong in all runs".
- **Root cause:** the account hit its usage limit mid-grading, and the grader replied with a limit
  message instead of JSON. Ungraded runs counted as incorrect.
- **Fix:** the grader retries with backoff on non-JSON replies.
- **Result:** after re-grading, tpl-5 is 3/3 correct in both RudhMap setups, and round 2 natural is 12/15,
  not 11/15.
- **Lesson:** a missing grade must never silently count as a wrong answer.

**7.2 Clock glitch (round 3).** Three runs failed with "timed out after −201 seconds", which points to a
system clock jump, not RudhMap. They were re-run; all 135 r3 runs are complete.

**7.3 Machine slowdown.** During rounds 2-3 the PC ran 5-7× slower. I confirmed this was the machine by
re-measuring step B's unchanged code: 8.2 s cold build vs 2.1 s earlier. It affected wall time only,
not tokens or correctness. Latency should be re-measured on an idle machine before any release claim.

**7.4 `num_turns` ≠ model calls** (found in step A). The harness records real model calls.

**7.5 RudhMap's cache had polluted a benchmark repo** (found in step B). It was fixed before step C by
moving the cache out of the repo.

**7.6 Tool-definition overhead grew with each round of fixes:** 649 → 685 → 743 tokens per call, all
measured. Each fix added description text, which is a direct cost on every call.

## 8. Limits of this evaluation

- **Sample size:** 15 tuning questions, 3 runs each. One question flipping moves a count by 1.
- **Harness specificity:** Claude Code's ~6.4k-token system prompt makes per-call cost high. Agents
  with a smaller fixed context (custom harnesses, other clients) could see different economics; that
  is untested.
- **Model specificity:** Haiku only for the RudhMap setups. Sonnet makes fewer, more decisive calls and
  might use the tools differently; that is untested.
- **The held-out set was not run,** so nothing here is confirmed out of sample. In particular, the
  accuracy gain (§6.1) is measured only on the tuning questions the tools were iterated on.

## 9. Decision

- **Step C fails** the pre-committed cost criterion in all three rounds. Per the stop rule, **RudhMap is
  not released as a token saver**, and no token-saving claim is made.
- **The held-out set was not run.** It is the one-shot confirmation set, so it is kept for whichever
  claim is pursued next.

What the data does support, as decision options for the project owner:
1. **Re-aim the claim at accuracy:** "Haiku + RudhMap answers as well as Sonnet at a fraction of the
   cost." This needs its own pre-registered criteria, then a single held-out run to confirm, since the
   accuracy gain was seen only on tuning questions.
2. **Attack the round count directly,** the actual cost driver. For example, a single
   "context for this question" call that returns everything in round 1, or measuring a harness with a
   smaller fixed prompt. That would be a new design, not a 4th round of the current one.
3. **Stop here** and keep the engine, tools and evaluation as a documented negative result.
