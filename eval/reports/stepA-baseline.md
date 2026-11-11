# Step A: Questions and baseline

**Branch:** `stepA-baseline` · **Date:** 2026-11-11 · **Verdict: PASS**

## 1. Goal

Measure how well, and at what cost, Claude Code answers real repo questions with
its built-in tools only. That is the bar RudhMap has to beat in step C. Pass
criteria, written before the runs (`docs/plan.md`):

| Criterion | Target | Result |
|---|---|---|
| Question set + answer keys written before any RudhMap run on these repos | yes | yes (`c7e3acd`) |
| Step C thresholds committed before any RudhMap run | yes | yes, `eval/THRESHOLDS.md` (`c7e3acd`) |
| All runs complete, no harness failures | 90/90 | 90/90 |
| Grader agrees with a 20% hand check | >= 90% | 17/18 (94%), after RCA 2 |
| Run-to-run variance reported | yes | yes (§4) |
| RCA of every wrong answer and of where tokens go | yes | §5, §4.2 |

## 2. Changes

| What | Files |
|---|---|
| Plan re-ordered for the fastest route to v1: A baseline, B tools, C iterate, D release; diagrams, `get_context`, step 1b, local model and cross-layer links cut from v1 | `docs/plan.md` |
| 15 questions over 3 repos with hand-written answer keys: 51 facts, 50 critical, each critical fact with a one-line `must` | `eval/bench/questions.yaml` |
| Benchmark harness: clean git export per repo, fresh headless Claude Code per run, per-call logging, blind 3-vote grader, report | `eval/bench/run_bench.py` |
| Step C pass/headline/stop thresholds | `eval/THRESHOLDS.md` |

Repos (pinned): Knowledge-News-App `20d352e` (FastAPI, 1.7k lines), fastapi/full-stack-fastapi-template
`aabb901` (FastAPI + React/TS, ~8.6k lines plus a generated client), encode/httpx `b5addb6`
(library, 8.8k lines). Question types: explain (3), trace (6), impact (3), behaviour (2), usage (1).
Two template questions are frontend; tpl-3 and tpl-4 cross frontend and backend.

## 3. Evaluation suite

```
python eval/bench/run_bench.py run    --label stepA --models haiku,sonnet --arms none --reps 3
python eval/bench/run_bench.py grade  --label stepA          # Sonnet grader, majority of 3 votes
python eval/bench/run_bench.py report --label stepA
```

- **Isolation per run:**
  - the repo is exported with `git archive` at the pinned commit into `%LOCALAPPDATA%\Temp\rudhmap_bench\`, with CLAUDE.md/AGENTS.md removed;
  - `claude -p` runs with `--tools Read,Grep,Glob`, `--strict-mcp-config` (no MCP), `--setting-sources ""` (no user/project settings) and `--no-session-persistence`.
  Models: `haiku` = claude-haiku-5-5, `sonnet` = claude-sonnet-5-5.
- **Prompt:** "Answer this question about the codebase in the current directory: {q}. Cite file:line for the
  key claims. Keep the answer under 300 words."
- **Logged per run:**
  - the answer;
  - Claude Code's own usage (input, cache writes, cache reads, output);
  - turns, cost and wall time;
  - every tool call with its input and the size of its result.
- **Grading:**
  - **Grader:** Sonnet, given only the question, the key and the answer, not the arm or model. Each answer is graded 3 times and the majority wins, per fact and for "major false claim".
  - **Correct:** every critical `must` stated and no major false claim. A question is correct for a model when ≥2 of its 3 runs are.
- **Hand check:** 18 answers (20%), chosen to over-sample wrong and borderline ones. They are recorded with reasons in
  `eval/results/bench/stepA-handcheck.json`.

## 4. Results

Raw runs: `eval/results/bench/stepA/<question>/<arm>-<model>-r<n>.json`; summary: `.../stepA/summary.json`;
first-pass grades before RCA 1-2: `eval/results/bench/stepA-grades-v1/`.

### 4.1 Headline

| Arm / model | Correct (of 15) | Fact score | Median tokens / question | Median new context | Median turns | Total tokens, 45 runs | Cost, 45 runs |
|---|---|---|---|---|---|---|---|
| none / Haiku | **12** | 0.82 | **35,452** | 5,532 | 6 | 1.92M | $0.12 |
| none / Sonnet | **12** | 0.82 | **23,080** | 4,331 | 4 | 1.22M | $1.50 |

Tokens per correct run: Haiku 52.0k, Sonnet 34.8k.

Per question (median of 3 runs; spread = min-max total tokens):

| Q | Haiku correct | Haiku tokens (spread) | Haiku turns | Sonnet correct | Sonnet tokens (spread) | Sonnet turns |
|---|---|---|---|---|---|---|
| kna-1 explain refresh_feed | 0/3 | 17.7k (17.7-17.7) | 3 | 0/3 | 21.2k (21.2-21.8) | 3 |
| kna-2 article lifecycle | 1/3 | 53.9k (53.1-72.7) | 12 | 0/3 | 40.5k (40.2-41.3) | 5 |
| kna-3 scheduler running? | 3/3 | 35.5k | 7 | 3/3 | 27.6k | 4 |
| kna-4 similarity_threshold | 3/3 | 39.5k | 6 | 3/3 | 30.9k | 5 |
| kna-5 quiz | 3/3 | 38.9k | 6 | 3/3 | 31.5k | 6 |
| tpl-1 login | 3/3 | 31.6k | 6 | 2/3 | 22.1k | 5 |
| tpl-2 get_user_by_email callers | 3/3 | 27.1k | 5 | 3/3 | 22.2k | 3 |
| tpl-3 delete item, front to back | 3/3 | **115.9k (84.7-143.8)** | 15 | 3/3 | 33.9k | 9 |
| tpl-4 frontend auth / expiry | 0/3 | 25.5k | 5 | 0/3 | 20.9k | 4 |
| tpl-5 SECRET_KEY | 3/3 | 32.4k | 4 | 3/3 | 20.1k | 3 |
| httpx-1 redirects | 3/3 | 46.9k | 6 | 3/3 | 22.0k | 4 |
| httpx-2 handle_request impact | 3/3 | 25.9k | 5 | 3/3 | 14.1k | 2 |
| httpx-3 timeouts | 3/3 | 54.3k (44.3-72.1) | 7 | 3/3 | 50.5k (43.0-54.8) | 8 |
| httpx-4 DigestAuth | 3/3 | 29.6k | 4 | 3/3 | 25.1k | 4 |
| httpx-5 Response.text | 3/3 | 59.3k (54.1-68.8) | 8 | 3/3 | 23.1k | 5 |

Run-to-run variance is moderate.
- **Haiku:** 18 of 30 (question, model) cells have a max/min token ratio under 1.25, and the worst is 1.7×
  (tpl-3 1.70, tpl-4 1.69, httpx-3 1.63). One run in a cell taking an extra exploration turn or two
  accounts for most of the spread. The Haiku medians are therefore the noisier baseline, which is why
  step C compares medians of 3 runs.
- **Sonnet:** steadier, with 3 cells over 1.25 and a worst of 1.40.
- **Correctness:** stable. Every (question, model) cell is 0/3 or 3/3 except kna-2/Haiku (1/3) and
  tpl-1/Sonnet (2/3).

### 4.2 Where the tokens go

| | Haiku | Sonnet |
|---|---|---|
| Cache reads (system prompt + conversation re-sent every turn) | **78.9%** | **78.8%** |
| Cache writes (new content: tool results, new turns) | 16.4% | 16.1% |
| Output | 4.7% | 5.1% |
| Median tokens per turn | 6,127 | 6,123 |
| Correlation of turns with total tokens | 0.90 | 0.82 |
| Tool calls (Read / Grep / Glob) | 154 / 91 / 11 | 70 / 96 / 2 |
| Reads of a whole file (no offset/limit) | 73 of 154 (47%) | 12 of 70 (17%) |

**Cost is driven by the number of model calls.** Every call to the model re-sends Claude Code's
system prompt and tool definitions plus the conversation so far, about **6,430 fixed tokens per call**.
That figure was measured afterwards with a trivial 1-call run (2 + 3,206 + 3,223 tokens, then
6,429 all from cache). The file contents the model actually reads are only about 16% of the total.
Haiku costs more than Sonnet because it makes more calls and reads whole files three times as often,
not because it reads bigger files.

**Correction (added after the report):** "turns" in the tables above is Claude Code's `num_turns`.
It is **not** the number of model calls. A re-run of kna-1/Haiku had `num_turns: 3` but only
**2 model calls**: one that requested Grep and Read in parallel, and one that answered. Its tokens
split as ~12.9k fixed (2 × 6.43k), ~3.4k tool results and requests, and ~1.3k output.
The "~6.1k tokens per turn" figure is total ÷ num_turns, so it mixes the fixed overhead with
content. The harness now records `model_calls` (distinct model replies) per run. Step A's runs
predate that change, so step C re-runs the plain-Haiku baseline alongside the RudhMap arm with
the same harness. The conclusion is unchanged: a tool saves tokens by removing model calls, and
2 calls (gather, answer) is the floor, about 13k tokens.

## 5. RCA

### 5.1 Wrong answers (17 of 90 runs)

Every wrong run except one has the same cause: **the model stopped one hop short.** It didn't
open the function or file that held the missing fact.

| Q | Runs wrong | What was missed | Why | Files it never opened |
|---|---|---|---|---|
| kna-1 | 6/6 | What the background pipeline does (agents, then aggregator) | All 6 runs read only `feed.py`, then answered; several say "I did not read graph.py" | `app/pipeline/graph.py` |
| kna-2 | 5/6 | Where queries come from (Groq-generated or fallback); semantic dedup never runs | Sonnet read only `base_agent.py` and `aggregator.py`, saw `embedder.embed(...)` called, and assumed it works. The two Haiku runs that opened `embedder.py` got that fact right. The query source sits in `_fetch_all`, which was read, but `generate_queries` was not followed | `app/services/embedder.py`, `app/services/groq_client.py` |
| tpl-4 | 6/6 | The backend is what rejects an expired token (`get_current_user`, 403) | All 6 runs stayed in the frontend, which is a frontend→backend hop. Haiku also missed the route guards in 2 runs | `backend/app/api/deps.py` |
| tpl-1 | 1/3 Sonnet | Token details (JWT, HS256, SECRET_KEY) | Read `login.py` and `crud.py`, not `security.py` | `backend/app/core/security.py` |

Because 16 of 17 wrong runs are "didn't open the next thing", the fix has to come from
what a tool returns, not from smarter search:
- **kna-1, kna-2:** a `show` result that lists each callee with its signature and first doc line
  would have put `run_pipeline → run_all_agents_node, aggregator_node` in front of the model.
  Printing callee bodies of 1-3 lines in full would have shown `def embed(text): return []`.
  Both fixes are inside the step B design.
- **tpl-4:** this needs a frontend → backend link: the generated client's
  `/api/v1/...` URL pointing to the FastAPI route and its dependencies. That is cross-layer
  linking, which is cut from v1. **Expect RudhMap not to fix tpl-4 in step C.** If it turns out
  to matter, it is the first post-v1 feature.

### 5.2 Answer key and grading issues found during the step

**RCA 1: the answer key was wrong on kna-2/kna-4 (my error).** The first grading pass marked 4
kna-2 answers as making a "major false claim": that `embedder.embed()` returns `[]`, so semantic
dedup never runs. Those answers were right. `app/services/embedder.py` is a 2-line stub that I never
opened while writing the key, so I had assumed embeddings work. The key was corrected and logged in
the amendment log in `questions.yaml`. This is the same failure the benchmark measures: stopping one
file short. A grader that trusts the key blindly would have punished the models that read more
carefully. **Rule kept:** every "major false claim" is checked against the source before
it is accepted.

**RCA 2: grader agreement was 14/18 (78%), below the 90% bar.**
- **Symptom:** the grader and I disagreed on 4 of 18 hand-checked answers. After loosening the
  rubric to "main point only", it was still 14/18, but now the errors went both ways.
- **Root cause:** facts bundled several details ("JWT, HS256, SECRET_KEY, default 8 days"), so
  "is this fact stated?" was a judgment call, and a single grader run landed on either side of
  borderline cases.
- **Fix:** each critical fact got a one-line `must` saying exactly what has to be said, and every
  answer is graded 3 times by majority vote.
- **Result:** 17/18 agreement, and the 3 votes agree on 84 of 90 answers.
- **Caveat:** these changes were made after seeing step A's answers but before any RudhMap run, and
  they apply to every arm the same way. The hand grades were made once and not changed (re-checked
  against the `must` lines).

The one remaining disagreement is httpx-1/Sonnet r1. The grader credits "redirects are off by
default" because the answer describes what happens when `follow_redirects` is false. I don't,
because the answer never says false is the default. It is borderline, and it doesn't change the
question's result (3/3).

**Grade history (Haiku / Sonnet correct of 15):**

| Pass | Haiku | Sonnet |
|---|---|---|
| First pass, original key | 8 | 10 |
| After the key fix | 8 | 10 |
| "Main point" rubric | 11 | 12 |
| `must` lines, 3 votes (final) | 12 | 12 |

The jump between the first and final pass came from grading strictness, not from the answers
changing. That is why grading was fixed before any RudhMap run.

### 5.3 Other observations
- **Baseline quality is already high.** Plain Haiku matches plain Sonnet (12/15), so the "Haiku +
  RudhMap matches Sonnet" headline is nearly free and means little. Quality headroom is 3 questions:
  kna-1, kna-2 and tpl-4, one of which (tpl-4) is out of v1's reach. **RudhMap's case in step C rests
  mostly on cost.**
- **The earlier `get_context` result is now explained.** That test found that adding a tool didn't
  cut tokens. With cost ≈ turns × 6k, a tool only saves tokens if it **removes turns**. Smaller reads
  hardly matter.

## 5.4 Held-out set (added after the review of this baseline)

**Gap found:** step C tunes against the same 15 questions for up to 3 rounds, so its result could
be overfit. And every repo was small or medium, the largest ~9k lines.

**Fix:** `eval/bench/questions_heldout.yaml`, 8 questions written and keyed before any RudhMap
run on them:
- 4 on `Textualize/rich` @ `3a109ccd` (~38k lines);
- 4 new questions on the tuning repos.

They were baselined with the same harness, which now also records model calls. The rule in
`eval/THRESHOLDS.md`: the set is never used for tuning, only these totals are looked at until
step C's final run, and step C passes only if the held-out set passes too.

| Held-out, 3 runs each | Correct (of 8) | Median tokens / question | Median model calls | Median Claude Code turns | Cost |
|---|---|---|---|---|---|
| none / Haiku | 6 | 59,442 | 5 | 8 | $0.08 |
| none / Sonnet | 6 | 24,759 | 3 | 6 | $0.86 |

**Held-out targets for step C:** Haiku + RudhMap ≥ 6/8 correct and median ≤ 41,609 tokens.

On the larger repo, plain Haiku costs 2.4× Sonnet (vs 1.5× on the tuning set): it makes more
calls and takes in more new content (median 9.1k vs 4.6k). Per-question results were
deliberately not inspected.

**Harness bug fixed during this run:** the grader crashed on facts that had a `must` but no
`text`; 24 answers were graded after the fix.

## 6. Limits of this evaluation

- 15 questions across 3 repos. Mostly Python backends, with 2 frontend questions. Small samples:
  one question flipping changes the count by 1.
- **The grader is an LLM.** It was checked against my hand grades, and I am also an LLM. I also wrote
  the key and the tools. The `must` lines and the logged amendments are the guard against that.
- **"Tokens" counts cache reads at full weight,** but they are billed at about 10%. That is why Sonnet
  costs 12× Haiku with fewer tokens. The step C threshold uses total tokens, as committed, and cost
  is reported alongside.
- **Claude Code's system prompt dominates per-turn cost.** Other agents (Cursor, smaller harnesses)
  have different overheads, so the savings may not carry over one-to-one.

## 7. Decision

All step A criteria are met. **Step A passes.**

Step C targets (from `eval/THRESHOLDS.md`, with the numbers filled in):
- **Quality:** Haiku + RudhMap correct ≥ **12/15**.
- **Cost:** Haiku + RudhMap median tokens per question ≤ **24,816** (0.7 × 35,452), which means
  about **4 turns or fewer** per question instead of 6.
- **No regressions:** no question where plain Haiku is correct and RudhMap is wrong in all 3 runs.

Design constraints for step B, derived from the RCA:
1. **Cut model calls.** One tool call should answer what currently takes 2-3 Grep/Read rounds. Each
   removed model call saves about 6.4k fixed tokens; a 1-2k-token tool result is cheap in comparison.
2. **`show` must go one hop further than the model would.** Callees and callers with signature +
   first doc line, and full bodies when they are tiny (≤3 lines), so stubs like `embed() -> []`
   are visible.
3. **Replace whole-file reads** with `skeleton`/`full` symbol views. Haiku reads whole files in 47%
   of its Reads.
4. **Keep the tool surface small.** Tool schemas are re-sent on every turn, so 4 tools with short
   descriptions. Step C measures the fixed per-turn overhead of adding the MCP server.
5. **tpl-4 needs cross-layer links** and stays out of v1; it is recorded as a known loss.
