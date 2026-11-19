import json

from tests.conftest import bind, clean_log, drilled, real_golden_rows
import copy
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
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
    gs.write_text("\n".join(json.dumps(r) for r in real_golden_rows()))
    m["golden_set"] = str(gs)
    labels = tmp_path / "labels.csv"
    labels.write_text("id,text,human_verdict,human_verdict_b\n"
                      + "\n".join(f"L{i},msg,{v},{v}" for i in range(30) for v in ['pass' if i % 2 else 'fail']))
    m["judges"][0]["labels"] = str(labels)
    m["judges"][0]["calibration"] = {"labelled_cases": 30, "agreement": 0.9, "kappa": 0.9, "runs": 3, "run_disagreement": 0.0, "net": 0.85}
    m["rollout"]["log"] = str(clean_log(tmp_path / "decisions.jsonl"))
    m["incident"] = drilled(tmp_path)
    assert check(bind(m), P)["verdict"] == "DEPLOYABLE"


def test_calibration_cannot_claim_more_labels_than_the_file_has(tmp_path):
    m = copy.deepcopy(GOOD)
    gs = tmp_path / "real.jsonl"
    gs.write_text("\n".join(json.dumps(r) for r in real_golden_rows()))
    m["golden_set"] = str(gs)
    m["judges"][0]["calibration"] = {"labelled_cases": 30, "agreement": 0.9, "kappa": 0.9, "runs": 3, "run_disagreement": 0.0, "net": 0.85}   # label file in repo is still empty
    r = check(m, P, base_dir=ROOT)
    assert r["verdict"] == "PILOT ONLY"
    assert any("matches its label file" in t and not ok for ok, t in r["deployable"])


def test_label_sheet_cli_and_manifest_update(tmp_path):
    from gtm_evals import judges
    t = judges.load_template("personalisation_factuality")
    assert judges.label_columns(t)[:2] == ["id", "text"] and judges.label_columns(t)[-3:] == ["human_verdict", "human_verdict_b", "why"]
    mf = tmp_path / "wf.yaml"
    mf.write_text("judges:\n  - template: personalisation_factuality\n    calibration: {labelled_cases: 0, agreement: 0}  # old\n")
    assert judges.update_manifest(mf, "personalisation_factuality", 34, 0.882)
    assert "calibration: {labelled_cases: 34, agreement: 0.88}" in mf.read_text()
    assert not judges.update_manifest(mf, "swap_test", 1, 1.0)


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
