import copy
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from gtm_evals.gate import check  # noqa: E402
from gtm_evals import load_policy, manipulation_guard  # noqa: E402

P = load_policy(profile="clyve")
GOOD = yaml.safe_load((ROOT / "workflows/teardown-outreach.yaml").read_text())
BAD = yaml.safe_load((ROOT / "workflows/examples/bad-lifecycle-flow.yaml").read_text())


def test_bad_flow_blocked():
    assert check(BAD, P)["verdict"] == "BLOCKED"


def test_teardown_is_pilot_until_evidence_is_real():
    assert check(GOOD, P)["verdict"] == "PILOT ONLY"


def test_deployable_when_evidence_real(tmp_path, monkeypatch):
    m = copy.deepcopy(GOOD)
    gs = tmp_path / "real.jsonl"
    gs.write_text("\n".join('{"source": "real"}' for _ in range(30)))
    m["golden_set"] = str(gs)
    m["judges"][0]["calibration"] = {"labelled_cases": 30, "agreement": 0.9}
    assert check(m, P)["verdict"] == "DEPLOYABLE"


def test_protected_attribute_blocks():
    m = copy.deepcopy(GOOD); m["scoring_features"].append("religion")
    assert check(m, P)["verdict"] == "BLOCKED"


def test_missing_guard_blocks():
    m = copy.deepcopy(GOOD); m["guards"].remove("promise_guard")
    assert check(m, P)["verdict"] == "BLOCKED"


def test_manipulation_escalates():
    v = manipulation_guard.check("Only 3 slots left — last chance!", P)
    assert not v and v.escalate
    assert manipulation_guard.check("We take 4 audits a month so each gets proper time.", P)


def test_csv_label_sheet_loads(tmp_path):
    from gtm_evals.runner import load_rows
    p = tmp_path / "labels.csv"
    p.write_text("id,text,signals,human_verdict\nL1,hi,S1: x,PASS\nL2,hi,S1: x,\n,,,\n", encoding="utf-8")
    rows = load_rows(p)
    assert [r["id"] for r in rows] == ["L1", "L2"]
    assert rows[0]["human_verdict"] == "pass" and rows[1]["human_verdict"] is None
