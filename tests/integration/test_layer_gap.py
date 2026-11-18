"""Known gaps between the code layer and the judge layer.

These tests pin down what the deterministic guards get WRONG on purpose, so the gap stays
visible. If you improve a guard and one of these starts failing, you closed a gap: update
`deterministic_verdict` in evals/datasets/layer_gap.jsonl and say so in the PR.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from gtm_evals import load_policy, promise_guard  # noqa: E402
from gtm_evals.outreach_guard import _overlap  # noqa: E402

P = load_policy(profile="clyve")
ROWS = [json.loads(x) for x in (ROOT / "evals/datasets/layer_gap.jsonl").read_text(encoding="utf-8").splitlines() if x]


@pytest.mark.parametrize("row", ROWS, ids=[r["id"] for r in ROWS])
def test_deterministic_layer_behaves_as_documented(row):
    if row["guard"] == "promise":
        got = "pass" if promise_guard.check(row["text"], P) else "fail"
    else:
        got = "pass" if any(_overlap(row["claim"], s["fact"]) for s in row["signals"]) else "fail"
    assert got == row["deterministic_verdict"], row["lesson"]
