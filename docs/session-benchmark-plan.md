# Option 2: multi-question session benchmark (pre-registered plan)

**Status:** planned, not run. **Written:** 2026-11-17, before any harness code for it exists.
Background: step C (`eval/reports/stepC-benchmark.md`) failed on cost with one question per session.

## 1. Hypothesis

Step C tested **one question per fresh session**, the worst case for RudhMap: fixed overhead is paid in
full and nothing is reused. In real use a developer asks several questions in one session. Everything
Claude reads stays in the conversation and is **re-sent on every later model call**, so a file read for
question 1 is paid for again on every call of questions 2-5. If RudhMap adds **less content per
question** than Grep/Read, that difference should compound over a session even if the round count per
question doesn't change.

**Claim under test:** *"Over a multi-question session, Claude with RudhMap uses at least 30% fewer
tokens than without it, with answers at least as correct."*

## 2. Prediction, written before running

Step C's data weakens the hypothesis. Median new content added per question (round 3):

| Setup | New content per question |
|---|---|
| Plain | 5.5k |
| RudhMap natural | 5.8k |
| RudhMap-only | 5.2k |

In natural mode Claude used RudhMap *and* still read files, so it added about as much as plain. Add
RudhMap's ~743 tokens on every call, and **the expectation is that natural does not pass**. RudhMap-only
and nudged have a better chance. The test is still worth running because it is cheap, needs no new
tools, and is decisive. The prediction is written down so the result can't be rationalised afterwards.

## 3. Session design

- **Sessions:** one per repo, made of that repo's 5 tuning questions (answer keys exist in
  `eval/bench/questions.yaml`), asked one after another in the same Claude Code session.
  - Knowledge-News-App: kna-1 → kna-5
  - fastapi template: tpl-1 → tpl-5
  - httpx: httpx-1 → httpx-5
- **Order effects:** half the sessions ask in **forward** order and half in **reverse**.
- **Runs:** 4 sessions per repo per setup (2 forward, 2 reverse).
- **Same conditions as step C:**
  - clean git exports with no CLAUDE.md;
  - Haiku;
  - the same per-question prompt wording;
  - the same grader (Sonnet, 3 votes, `must` lines).
- **Auto-compaction:** if Claude Code compacts the conversation, it is recorded and the session is
  flagged. Five questions are not expected to trigger it.

## 4. Setups

| Setup | Role |
|---|---|
| Plain Haiku | Baseline |
| RudhMap (natural) | The real-use claim |
| RudhMap (nudged) | Natural + the one-line CLAUDE.md instruction; reported separately |
| RudhMap-only | Diagnostic: best case for content size |
| Plain Sonnet | Optional reference (~10x cost) |

Size: 3 repos × 4 sessions × 4 Haiku setups = 48 sessions × 5 questions = **240 graded answers**, about
one step C round.

## 5. Measurements

- **Per session:**
  - **cumulative tokens** over all 5 questions (main metric);
  - **context size at the end** (what the last call re-sent, i.e. how full the context window got);
  - total model calls;
  - output size by tool type (RudhMap vs Read/Grep).
- **Per question within a session:** incremental tokens (that question's cost, including re-sending
  everything before it) and correctness.
- **Key chart:** incremental cost of question 1 → 5 per setup. The hypothesis predicts plain's cost per
  question rises faster than RudhMap's as the session goes on.
- **Dollars,** reported next to tokens: re-sent context is mostly cache reads, billed at ~10%.

## 6. Pass criteria (natural vs plain Haiku)

| # | Criterion | Target |
|---|---|---|
| 1 | **Quality:** questions answered correctly (correct in >= 2 of 4 sessions), over all 15 | >= plain Haiku's count |
| 2 | **Cost:** median cumulative session tokens | <= **0.7 x** plain Haiku's |
| 3 | **Consistency:** criterion 2 holds in at least 2 of 3 repos | 2 of 3 |
| 4 | **No reliable regressions:** no question plain gets right in most sessions and RudhMap gets wrong in all | none |
| 5 | **Held-out**, run once only if 1-4 pass: a 4-question session on `rich` (rich-1..4, `eval/bench/questions_heldout.yaml`) | criteria 1 and 2 also hold |

Nudged and RudhMap-only are scored against the same criteria. A claim is made only for a setup that
passes, with its conditions stated (e.g. "requires the CLAUDE.md line").

## 7. Decision rules (fixed now)

- **Natural passes:** claim session-level token reduction and go to step D (release) with the real
  numbers.
- **Only nudged passes:** same, with the CLAUDE.md line as part of the documented setup.
- **Nothing passes:** session reuse isn't the answer. Move to option 1 (a hook that injects context
  before the first model call), informed by where this test shows content comes from.
- **One measurement, no tuning rounds:** the current tools, measured once. A failure leads to a
  different design, not tweaks until it passes.

## 8. Risks and limits

- **Five questions is a short session.** Results are stated for 5 only, with no extrapolation to longer
  sessions.
- **The questions in a session share a repo,** so later ones may get easier for every setup. Order
  alternation limits this bias but doesn't remove it.
- **The dollar difference will be smaller than the token difference** (cache reads are cheap).
- **Claude Code only;** other agents have different fixed context sizes.
