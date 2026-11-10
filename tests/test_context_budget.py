"""The token budget is a hard limit even when the slice is dense: a hub called
from many places used to overflow on call-graph lines alone, since only
source snippets were ever trimmed."""
from __future__ import annotations

from rudhmap.context import build_context_pack, estimate_tokens


def test_dense_slice_stays_within_budget(tmp_path):
    callers = "\n".join(f"def caller_{i}():\n    return hub_target()\n" for i in range(60))
    (tmp_path / "app.py").write_text(f"def hub_target():\n    return 1\n\n{callers}", encoding="utf-8")

    pack = build_context_pack(tmp_path, "hub target", token_budget=400)

    assert pack.status == "ok"
    assert estimate_tokens(pack.text) <= 400
    assert pack.pack_tokens <= 400
    assert pack.omitted_edges > 0 or pack.omitted_references > 0
    assert "more" in pack.text  # the cut is stated, not silent
