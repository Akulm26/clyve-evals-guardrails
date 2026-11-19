"""Phase 2 evals: abstain scored below right and above wrong; repeat runs; cache; call budget."""
import pytest

from gtm_evals import judges


def rows(n_pass, n_fail):
    return ([{"id": f"R{i:02d}", "text": "m", "human_verdict": "pass"} for i in range(n_pass)]
            + [{"id": f"F{i:02d}", "text": "m", "human_verdict": "fail"} for i in range(n_fail)])


@pytest.fixture
def fake(monkeypatch):
    """judges.run replaced by a script: script[(row id, run index)] → verdict, else the human verdict."""
    state = {"script": {}, "calls": []}

    def run(template, values, model=None):
        i = sum(1 for c in state["calls"] if c == values["id"])
        state["calls"].append(values["id"])
        v = state["script"].get((values["id"], i), state["script"].get(values["id"], values["human_verdict"]))
        return {"verdict": v, "_verdict": judges.normalise({"verdict": v})}
    monkeypatch.setattr(judges, "run", run)
    return state


@pytest.mark.parametrize("raw,want", [("PASS", "pass"), ("fail", "fail"), ("abstain", "abstain"),
                                      ("insufficient_evidence", "abstain"), ("Unsure", "abstain"), ("junk", "fail")])
def test_normalise_abstain(raw, want):
    assert judges.normalise({"verdict": raw}) == want


def test_wrong_scores_below_abstain(fake):
    fake["script"] = {"R00": "fail", "R01": "fail"}
    wrong = judges.calibrate("t", rows(10, 10))
    fake["calls"].clear()
    fake["script"] = {"R00": "abstain", "R01": "abstain"}
    unsure = judges.calibrate("t", rows(10, 10))
    assert wrong["net"] == pytest.approx(0.8) and unsure["net"] == pytest.approx(0.9)
    assert unsure["agreement"] == 1.0 and unsure["abstained"] == 2 and wrong["abstained"] == 0


def test_repeat_runs_majority_and_disagreement(fake):
    fake["script"] = {("R00", 1): "fail", ("R01", 0): "fail", ("R01", 1): "fail"}
    r = judges.calibrate("t", rows(10, 10), runs=3)
    assert r["calls"] == 60 and r["runs"] == 3
    assert r["run_disagreement"] == pytest.approx(0.10)       # R00 and R01 split
    got = {i: v for i, v, _ in r["results"]}
    assert got["R00"] == "pass" and got["R01"] == "fail"      # majority


def test_tie_counts_as_abstain(fake):
    fake["script"] = {("R00", 1): "fail"}
    r = judges.calibrate("t", rows(1, 0), runs=2)
    assert r["results"][0][1] == "abstain" and r["net"] == 0.0


def test_cache_makes_reruns_free(fake, tmp_path):
    judges.calibrate("t", rows(5, 5), runs=2, cache_dir=tmp_path)
    assert len(fake["calls"]) == 20 and len(list(tmp_path.glob("*.json"))) == 20
    judges.calibrate("t", rows(5, 5), runs=2, cache_dir=tmp_path)
    assert len(fake["calls"]) == 20
    judges.calibrate("t", rows(5, 5), model="other", runs=2, cache_dir=tmp_path)   # new model: new keys
    assert len(fake["calls"]) == 40


def test_cache_key_changes_with_template_row_model_run():
    k = judges._cache_key("t", {"a": 1}, "m", 0)
    assert len({k, judges._cache_key("u", {"a": 1}, "m", 0), judges._cache_key("t", {"a": 2}, "m", 0),
                judges._cache_key("t", {"a": 1}, "n", 0), judges._cache_key("t", {"a": 1}, "m", 1)}) == 5
    assert judges._cache_key("t", {"a": 1, "b": 2}, "m", 0) == judges._cache_key("t", {"b": 2, "a": 1}, "m", 0)


def test_max_calls_stops_cleanly(fake):
    r = judges.calibrate("t", rows(10, 10), runs=3, max_calls=10)
    assert r["calls"] == 9 and r["labelled_cases"] == 3 and r["complete"] is False


def test_update_manifest_writes_extra(tmp_path):
    m = tmp_path / "wf.yaml"
    m.write_text("judges:\n  - template: swap_test\n    calibration: {labelled_cases: 0, agreement: 0}\n", encoding="utf-8")
    assert judges.update_manifest(m, "swap_test", 30, 0.9, 0.85, extra={"net": 0.8, "runs": 3, "run_disagreement": 0.03})
    assert "calibration: {labelled_cases: 30, agreement: 0.90, kappa: 0.85, net: 0.80, runs: 3, run_disagreement: 0.03}" in m.read_text()
