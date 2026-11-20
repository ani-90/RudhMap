# I built a code-graph MCP server to cut Claude Code's token use. 525 benchmark runs later, it doesn't. Here's why.

**TL;DR**
- **The build:** a tool that gives Claude Code a precise map of a codebase: every function, what it calls, what calls it, each fact cited to `file:line`. The goal was for a small model (Claude Haiku) to answer repo questions with at least 30% fewer tokens and no loss in accuracy.
- **The result:** across 405 benchmark sessions on three repos, plus a 120-session held-out run, it never reduced tokens in a realistic setup.
- **The early win that wasn't:** an accuracy gain on my tuning questions disappeared on questions I hadn't tuned on.
- **Why:**
  - In an agent loop, the cost is set by the number of rounds, not by how much code the model reads.
  - Better tool answers didn't reduce the number of rounds.
  - Every tool you add is paid for again on every round.

Everything below is measured, and the harness and data are in this repo.

---

## What I built

RudhMap parses a repository with tree-sitter (Python and TypeScript/React) into a graph of functions, classes and calls. It resolves calls across files, including:
- relative imports;
- methods called on variables whose type the code states;
- inherited methods;
- callbacks passed as values;
- React components used in JSX, along with `@/` path aliases and barrel re-exports.

There is no LLM anywhere in the engine. On a hand-labelled set of 145 call sites, it finds 99.3% of the real connections and draws no false ones.

It exposes four MCP tools (and the same commands on a CLI):

| Tool | Returns |
|---|---|
| `find_symbol` | Matches for a name or keywords, with `file:line`; lines where an identifier is used; the best match's full source when one clearly wins |
| `show` | A function/class/file: its source with line numbers, what it calls (signature + doc, tiny bodies inline), who calls it, constants it uses, overrides, stubs flagged |
| `trace` | The call path between two functions, or the tree below or above one |
| `repo_map` | Files with their main functions and HTTP routes |

The index lives in memory, refreshes when files change, and answers in about 40 ms on a 38k-line repo.

The bet was simple. Instead of grepping, opening a file, and then opening the next file, the model calls `show` once and has everything it needs.

## How I measured it

I wanted a result I could trust in either direction, so:
- **Real questions with hand-written answers.**
  - **Tuning set:** 15 questions over three repos: my own FastAPI app, `fastapi/full-stack-fastapi-template` (Python + React/TS) and `encode/httpx`.
  - **What they ask:** "explain `refresh_feed()`", "what's affected if I change `get_user_by_email`", "how does httpx follow redirects"…
  - **What a key looks like:** each question has 3–5 required facts, each with a one-line "must state" sentence.
- **A held-out set:** 8 more questions, 4 of them on `Textualize/rich` (~38k lines), never used while tuning.
- **Fresh headless Claude Code sessions** (`claude -p`) for every run, on a clean git export of the repo with any CLAUDE.md removed. 3 runs per question per setup.
- **Grading:**
  - **The grader:** a separate Sonnet instance grades each answer against its key, without knowing which setup produced it, and the majority of 3 votes wins.
  - **The check on it:** I hand-graded a sample and got 17/18 agreement, but only after fixing how the facts were written (more on that below).
- **Pass criteria committed to git before the first RudhMap run:**
  - **Accuracy:** at least as many correct answers as plain Haiku.
  - **Cost:** a median of at most 70% of plain Haiku's tokens.
  - **Stop rule:** at most 3 rounds of fixes, then stop.

The four setups:
- **Plain:** Read, Grep and Glob only.
- **Natural:** plain plus RudhMap, with Claude choosing what to use.
- **Nudged:** natural plus one line in the system prompt: *"get code with the rudhmap tools… don't re-read the same code with Read or Grep"*.
- **RudhMap-only:** RudhMap's tools alone, as a diagnostic.

## Result 1: tokens didn't go down

Final round, 15 questions × 3 runs per setup:

| Setup | Correct questions | Median tokens / question | vs plain Haiku | Model calls / run |
|---|---|---|---|---|
| Plain Haiku | 12/15 | 31.4k | — | 3.69 |
| Haiku + RudhMap (natural) | 13/15 | 35.4k | 113% | 3.64 |
| Haiku + RudhMap (nudged) | 13/15 | 41.7k | 133% | 3.69 |
| Haiku + RudhMap only | 10/15 | 29.9k | 95% | 3.69 |
| Plain Sonnet | 12/15 | 23.5k | — | 3.44 |

The target was 22k. Three rounds of fixes moved the natural setup from 107% to 113% of plain, the wrong way.

## Why: the arithmetic of agent loops

This is the part I wish I'd understood before I started.

An LLM keeps no memory between calls. Every time Claude Code calls the model, it sends everything again: its system prompt, every tool's description, your question, and every tool result so far. I measured the fixed part directly with a session that does nothing but reply "ok": **6,431 tokens per call** in Claude Code. So, roughly:

```
total tokens ≈ rounds × fixed context  +  content read × rounds remaining after it was read
```

In my baseline runs, **79% of all tokens were cached re-sends of that context; the code the model actually read was about 16%.** Plain Haiku needs about 3–4 rounds per question, so roughly 20–25k of its ~31k tokens are fixed cost before it reads a line of code.

Two consequences:

1. **A tool saves tokens only if it removes rounds.** Making each tool answer smaller barely matters when content is 16% of the bill.
2. **Tool descriptions are a tax on every round.** RudhMap's four tool definitions added 649 tokens to every single call, measured the same way, even calls that didn't use them. After three rounds of improving the descriptions, that grew to 743. At equal rounds, adding the tools can only cost more.

The question became whether RudhMap removed rounds. It didn't: **every setup sat at about 3.7 model calls per run.** RudhMap changed *what* Haiku read, not *how many rounds* it took.

## What Claude actually did with the tools

I logged every tool call. The model **did** adopt RudhMap: it was the first tool called in 35–40 of 45 natural runs, and in all 45 nudged runs. What it didn't do was trust it.

- **It hedged.** In 20–30 of 45 natural runs, Haiku grepped *in parallel* with its first RudhMap call, just in case.
- **It re-read what it had been shown.** After RudhMap returned a function's full source, Haiku still made 2.0–2.7 Read/Grep calls per run, often opening the exact file `show` had just printed.
- **It split "look up" and "open" into two rounds.** `find_symbol`, then `show` in the next round, then sometimes `find_symbol` again. I changed `find_symbol` to open a clear best match inline and let `show` take several functions at once. Calls didn't drop.
- **It ignored facts it had been shown.** RudhMap printed `def embed(text): return []` inline. The answer still described the embedding-based dedup as working. Flagging it explicitly as `[stub: always returns []]` helped.

The nudge was the most interesting experiment:
- **What one sentence changed:** "don't re-read with Read or Grep" cut fallback reads from 2.0 to 0.4 per run, and gave the best accuracy of any setup on the tuning questions (40/45 correct runs, ahead of plain Sonnet's 36/45).
- **What it did to tokens:** they went *up*, to 133%. Haiku trusted RudhMap and used it more heavily, pulling more code through it in the same ~3.7 rounds.

So trust wasn't the bottleneck. Round count was, and better answers didn't move it.

## Result 2: an accuracy gain that wasn't real

After step C failed on cost, I still had what looked like a consolation prize: "Haiku + RudhMap answers more questions correctly than plain Haiku, and more than Sonnet."

Then I ran the held-out set: 8 questions, never seen during tuning, all setups, 3 runs each.

| Setup | Correct questions | Correct runs | Median tokens | vs plain Haiku |
|---|---|---|---|---|
| Plain Haiku | 6/8 | 20/24 | 50.5k | — |
| Natural | 5/8 | 15/24 | 53.8k | 107% |
| Nudged | 4/8 | 12/24 | 51.3k | 102% |
| RudhMap-only | 3/8 | 8/24 | 37.8k | 75% |
| Plain Sonnet | 7/8 | 18/24 | 29.3k | — |

Every RudhMap setup was *less* accurate than plain Haiku. The tuning-set gain was overfitting: three rounds of fixing the tools against the same 15 questions had made them good at those 15. Without the held-out set I would have believed it, and probably put it on my resume.

The worst failure is the most instructive one. The question was *"what's affected if I change `Console.render_lines`?"*
- **What RudhMap returned:** 7 of its 13 callers. `rich` writes type hints as strings (`console: "Console"`, a common pattern to avoid circular imports), and my type tracking skips string annotations, so six callers were never connected.
- **What Haiku did with it:** it treated the list as complete. One answer stated flatly that Panel and Table "are not in the call graph".
- **What plain Haiku did:** it grepped `render_lines` and found all 13.

Plain Haiku got that question right 3/3; every RudhMap setup got it 0/3.

**A tool that is confident but incomplete is worse than no tool, because the model stops looking.** If I build anything like this again, every list it returns will say what it could *not* resolve, as prominently as what it found.

## Things that went wrong in my own evaluation

I'm including these because each one would have changed the conclusion if I hadn't caught it.

- **My answer key was wrong.** I wrote that a feature worked; the models said `embed()` was a stub returning `[]`. They were right. I had never opened the file. Since then I don't accept a "wrong answer" without reading the source myself.
- **The grader was too strict.** At first it agreed with my hand grades only 14/18 of the time, because facts bundled several details. One precise "must state" line per fact plus a 3-vote majority got it to 17/18.
- **A usage-limit outage faked a regression.** Mid-grading, my account hit its usage limit and the grader returned a limit message instead of a verdict. Twelve answers were silently counted as wrong, and one question looked like a reliable RudhMap regression. Re-grading made it disappear. The grader now retries, and a missing grade can never count as a wrong answer.
- **Claude Code's `num_turns` is not the number of model calls.** One run reported 3 turns but made 2 calls, because two tool calls went out in parallel. I count distinct model replies instead.
- **My tool's cache was polluting the benchmark.** RudhMap wrote its cache into the repo it scanned, where the agents' Grep could see it. I moved it out of the repo before the benchmark.

## What I'd tell anyone building MCP tools for coding agents

1. **Measure the real agent.** My first proxy ("our context pack is 4× smaller than reading every touched file") looked great. Real agents read only 2–3 files, and the saving vanished.
2. **Count rounds, not tokens per answer.** Total cost ≈ rounds × fixed context. If your tool doesn't remove rounds, it adds cost.
3. **Your tool descriptions are paid for on every round.** Measure them in the real client. My estimate from the JSON schema was 827 tokens; the measured cost was 1,134 before trimming.
4. **Models adopt tools quickly and trust them slowly.** Expect hedging and re-reading. An instruction fixes trust, but not cost.
5. **Say what you don't know.** Partial results presented as complete stop the model from searching further.
6. **Keep a held-out set and pre-register your criteria.** Mine caught an overfit accuracy gain and stopped three rounds of "almost passing" from turning into a claim.

## Limits

- **Small question sets:** 15 tuning questions and 8 held-out ones. One question flipping moves a count by one.
- **One client, one model in focus:** Claude Code only, and mostly Haiku. Other agents have different fixed context sizes, so the economics could differ.
- **The question mix:** mostly "understand existing code". Tasks that write code weren't tested.
- **One machine,** which ran slowly for part of the work. That affected wall-clock times, not tokens.

## What's next

The only lever with real headroom is **removing rounds before the model starts**: a Claude Code hook that finds the code a question refers to and attaches it to the prompt before the first round, with no MCP tools at all. That removes both the "finding" rounds and the per-round tool tax.
- **The arithmetic:** 1–2 rounds instead of 3–4 would be a 40–65% saving.
- **The catch:** it depends on picking the right code from the question alone, which is exactly where keyword-based retrieval failed before.

It will be tested the same way: criteria first, then a fresh held-out set.

## Reproduce it

Everything is in this repo (branch `stepC-benchmark`):

```bash
pip install -e ".[dev]"
# benchmark: setups none | rudhmap | rudhmap-nudge | rudhmap-only
python eval/bench/run_bench.py run   --label mine --arms none,rudhmap --models haiku --reps 3
python eval/bench/run_bench.py grade --label mine
python eval/bench/run_bench.py runs  --label mine        # one row per run + summary
# engine accuracy against the hand-labelled call sites
python eval/engine_eval.py --label mine
```

- **Questions and answer keys:** `eval/bench/questions.yaml` and `questions_heldout.yaml`.
- **Pass criteria, as committed before the runs:** `eval/THRESHOLDS.md`.
- **The full write-up with every root-cause analysis:** `eval/reports/`.
- **Every run's raw log and grade:** `eval/results/bench/`.

The benchmark uses your own Claude Code login. A full round (180 sessions plus grading) costs a few dollars at API prices.
