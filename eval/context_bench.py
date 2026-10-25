"""Token-spend benchmark for context packs.

    python eval/context_bench.py <repo_path> <questions.txt> [--budget N]

`questions.txt` holds one question per line (blank lines and `#` comments are
skipped). For each question this prints the pack's estimated size next to
what reading every file the slice touches, whole, would cost -- the cheap
proxy for "an agent that greps and then reads files". It doesn't judge
whether the pack actually answers the question; that still needs a human (or
a real agent run with and without `get_context`) to grade. See
eval/context_questions_knowledge_news_app.txt for an example question set.
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

from rudhmap.context import DEFAULT_TOKEN_BUDGET, build_context_pack


def _questions(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [q.strip() for q in lines if q.strip() and not q.lstrip().startswith("#")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_path")
    parser.add_argument("questions")
    parser.add_argument("--budget", type=int, default=DEFAULT_TOKEN_BUDGET)
    parser.add_argument(
        "--show-files", action="store_true", help="list each whole file counted in the baseline, with its size"
    )
    args = parser.parse_args()

    root = Path(args.repo_path).resolve()
    ratios = []
    print(f"{'pack':>6} {'whole':>6} {'ratio':>6} {'snip':>4} {'refs':>4}  question / seeds")
    for question in _questions(Path(args.questions)):
        pack = build_context_pack(root, question, args.budget)
        if pack.status != "ok":
            print(f"{'-':>6} {'-':>6} {'-':>6} {'-':>4} {'-':>4}  {question}  [no match]")
            continue
        ratio = pack.baseline_tokens / pack.pack_tokens if pack.pack_tokens else 0.0
        ratios.append(ratio)
        print(
            f"{pack.pack_tokens:>6} {pack.baseline_tokens:>6} {ratio:>5.1f}x "
            f"{len(pack.snippets):>4} {len(pack.references):>4}  {question}"
        )
        print(f"{'':>31}seeds: {', '.join(pack.seed_ids)}")
        if args.show_files:
            for file, tokens in pack.baseline_breakdown:
                print(f"{'':>31}  {tokens:>5}  {file}")
    if ratios:
        print(f"\nmedian whole-file/pack ratio: {statistics.median(ratios):.1f}x over {len(ratios)} answered questions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
