# RudhMap

RudhMap is an experiment in giving AI coding assistants a better way to understand a codebase.

When you ask a tool like Claude Code or Cursor a question about your code, such as "what does `refresh_feed()` do?" or "what breaks if I change this function?", it works the way a newcomer would. It searches for a name, opens a file, reads it, notices a call to something else, opens another file, and keeps going until it thinks it has enough. That works, but it's slow and expensive. Every step re-sends the whole conversation to the model, and the assistant often stops one file too early and answers with a gap.

RudhMap's idea is to do the reading up front. It parses the repository once and builds a map of it: every function and class, which ones call which, what gets passed where, which class inherits from which. The assistant can then ask the map directly instead of exploring file by file. "Show me `refresh_feed`" returns the function's source together with the functions it calls, the places that call it, and the constants it depends on, each with the file and line it came from.

The map is built from the code itself, with no AI involved, so it doesn't guess. Either the code proves a connection or RudhMap doesn't draw it.

## What it does

RudhMap reads Python and TypeScript/React projects. It follows calls across files and imports, and works out which method a call refers to when the code states the type. It tracks inheritance, functions passed around as callbacks, and React components used in JSX. On a hand-checked sample it finds 99.3% of the real call connections and doesn't invent any.

It offers four ways to look at the map, both as tools an assistant can call (over MCP) and as commands you can run yourself:

- **find:** search by name, keywords or a phrase. It also finds where a setting like `SECRET_KEY` is used, even though it isn't a function.
- **show:** one function, class or file, with its source, what it calls and what calls it. Small helper functions are shown inline, so a stub like `return []` is impossible to miss.
- **trace:** how one function reaches another, or everything that depends on a function before you change it.
- **map:** a short overview of a repository's files, main functions and HTTP routes.

The map stays in memory while you work and updates itself when files change, so answers come back in a few dozen milliseconds.

## What we learned

The original goal was to make assistants cheaper: answer the same questions with fewer tokens. A small model like Claude Haiku would answer well, without exploring.

To test that properly, I built a benchmark. It asks Claude Code real questions about real repositories, in fresh sessions, with and without RudhMap. Every answer is checked against correct answers I wrote by hand, and a separate set of questions is held back to catch results that only work on the questions I tuned against. Over 500 sessions later, the honest result is that **RudhMap did not make the assistant cheaper**, and an early accuracy improvement did not hold up on the held-back questions.

The reasons turned out to be more interesting than the tool:

- **An assistant's cost comes from how many rounds it takes, not how much it reads.** Each round re-sends thousands of tokens of instructions and history. The code itself is a small part of the bill.
- **Better answers didn't mean fewer rounds.** Claude used RudhMap readily, but kept its habit of double-checking with its own searches. It took the same number of steps whatever the tool returned.
- **Every tool an assistant has costs something on every round,** even when it isn't used, because its description is sent each time.
- **A confident but incomplete answer is worse than none.** When RudhMap missed some callers of a function, the assistant trusted the list and stopped looking, while plain search found them all.

The full write-up is in [`blog/README.md`](blog/README.md). The step-by-step story, with every measurement and what went wrong along the way, is in [`docs/journey.md`](docs/journey.md) and [`eval/reports/`](eval/reports/).

## Where it's going

The findings point to one approach that could work: give the assistant the relevant code *before* it starts, attached to the question, so it doesn't spend rounds finding it at all. That is the next experiment.

## Try it

You need Python 3.10 or newer.

```bash
git clone https://github.com/ani-90/RudhMap && cd RudhMap
pip install -e ".[dev]"
```

From inside any Python or TypeScript repository:

```bash
rudhmap map                      # overview of the repo
rudhmap find "refresh feed"      # search
rudhmap show refresh_feed        # a function with its context
rudhmap trace refresh_feed --up  # who depends on it
```

To let Claude Code use it, run this in the repository you're working on:

```bash
claude mcp add rudhmap -- rudhmap-mcp
```

RudhMap keeps its cache in your user cache folder, never inside your repository.

## Limits

RudhMap only understands what the code states. Calls decided at runtime, such as a function picked from a dictionary, a callback received as a parameter, or a type written as a string, can be missing. So treat "called by" as a starting point, not a complete list. It reads Python and TypeScript files only, not shell scripts, configuration or documentation.

## Background

RudhMap began as a generator of architecture diagrams in which every box and arrow is backed by a line of code. Those commands (`rudhmap scan`, `slice`, `diagram`) still work but are no longer developed. The project changed direction in November 2026, when it became clear the map itself was more useful than the pictures.

To re-run the benchmark or the accuracy checks, see [`eval/`](eval/). The commands are listed at the end of [`blog/README.md`](blog/README.md).
