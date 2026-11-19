"""Phase 3 evals: assertion cases, blind packets, evidence bound to template/labels/model, red team."""
import json

import pytest

from gtm_evals import judges, redteam
from gtm_evals.gate import check
from gtm_evals.runner import check_assertions, score
from tests.conftest import bind, real_golden_rows

# ---------- assertion cases ----------
NOTE = "Funding: unknown (no source found). Hiring: 2 roles, proposed by the SDR, not verified."


def test_assertions_pass():
    assert check_assertions(NOTE, [r"funding:\s*unknown"], [r"\bverified\b(?<!not verified)"])


def test_assertions_fail_both_ways():
    r = check_assertions("Funding: Series A (verified).", [r"funding:\s*unknown"], [r"\(verified\)"])
    assert not r and len(r.violations) == 2 and "doesn't demonstrate" in r.violations[0]


def test_human_review_rows_are_not_scored(policy, tmp_path):
    rows = [{"id": "a", "guard": "assert", "input": {"output": NOTE, "must_demonstrate": ["unknown"]}, "expected_pass": True},
            {"id": "b", "guard": "assert", "input": {"output": "x"}, "expected_pass": False, "human_review": True,
             "source": "real"}]
    r = score(rows, policy, tmp_path)
    assert r["n"] == 1 and r["human_review"] == ["b"] and r["real"] == 0 and r["ok"]


def test_human_review_rows_dont_count_as_gate_evidence(policy, tmp_path):
    rows = [dict(r, human_review=True) for r in real_golden_rows()]
    gs = tmp_path / "g.jsonl"; gs.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    m = {"name": "wf", "lane": "ai_seo", "actions": ["draft"], "guards": ["ai_seo_guard"], "golden_set": str(gs)}
    assert any("has 0)" in msg for ok, msg in check(m, policy)["deployable"] if not ok)


# ---------- blind packets ----------
ROW = {"id": "L01", "text": "Loved your Shark Tank episode!", "signals": "S1: launched 4 Meta ads",
       "human_verdict": "fail", "human_verdict_b": "fail", "why": "invented: no Shark Tank appearance on record",
       "today": "2026-11-18", "lead": "Rhea", "date_sent": "2026-11-18", "freshness_days": "90"}


def test_packet_has_only_what_the_judge_may_see():
    p = judges.packet(judges.load_template("personalisation_factuality"), ROW)
    assert "Shark Tank" in p and "S1: launched" in p and "# Judge packet · L01" in p
    assert "invented: no Shark Tank" not in p and "human_verdict" not in p


def test_packet_refuses_a_template_that_leaks_the_label():
    with pytest.raises(ValueError, match="why"):
        judges.packet("Message: {{text}}\nNote: {{why}}", ROW)


# ---------- evidence bound to template, labels, model ----------
def test_binding_changes_with_each_input(tmp_path, write_labels):
    a = judges.evidence_binding("swap_test")
    assert set(a) == {"template_hash", "model"} and a["model"] == judges.resolve_model()
    assert judges.evidence_binding("on_thesis")["template_hash"] != a["template_hash"]
    assert judges.evidence_binding("swap_test", model="other")["model"] == "other"
    h1 = judges.evidence_binding("swap_test", write_labels(15, 15))["labels_hash"]
    h2 = judges.evidence_binding("swap_test", write_labels(15, 15, flip_b={"L01"}))["labels_hash"]
    assert h1 != h2


def test_labels_hash_ignores_formatting():
    rows = [{"id": "1", "human_verdict": "pass", "text": "a"}, {"id": "2", "human_verdict": "fail", "text": "b"}]
    assert judges.labels_fingerprint(rows) == judges.labels_fingerprint(
        [dict(r, text=r["text"].upper()) for r in reversed(rows)] + [{"id": "3", "human_verdict": None}])


GOOD_CAL = {"labelled_cases": 30, "agreement": 0.9, "kappa": 0.9, "runs": 3, "run_disagreement": 0.0, "net": 0.85}


def judged(tmp_path, template="swap_test", labels=None):
    gs = tmp_path / "g.jsonl"; gs.write_text("\n".join(json.dumps(r) for r in real_golden_rows()), encoding="utf-8")
    j = {"template": template, "calibration": dict(GOOD_CAL)} | ({"labels": str(labels)} if labels else {})
    return {"name": "wf", "lane": "ai_seo", "actions": ["draft"], "guards": ["ai_seo_guard", "visibility_stats", "promise_guard"], "kill_switch": "f",
            "logging": {"gate_log": "x", "retention_days": 400}, "token_budget": 1, "owner": "A",
            "golden_set": str(gs), "judges": [j]}


def bound_line(res):
    return next((ok, msg) for ok, msg in res["deployable"] if "evidence is for this template" in msg)


def test_bound_evidence_deployable(policy, tmp_path):
    assert check(bind(judged(tmp_path)), policy)["verdict"] == "DEPLOYABLE"


def test_unbound_evidence_is_pilot(policy, tmp_path):
    ok, msg = bound_line(check(judged(tmp_path), policy))
    assert not ok and "template, model changed" in msg


def test_template_swap_sends_back_to_pilot(policy, tmp_path):
    m = bind(judged(tmp_path))
    m["judges"][0]["template"] = "on_thesis"
    ok, msg = bound_line(check(m, policy))
    assert not ok and "(template changed since calibration" in msg


def test_model_swap_sends_back_to_pilot(policy, tmp_path):
    m = bind(judged(tmp_path))
    m["judges"][0]["model"] = "a-different-model"
    r = check(m, policy)
    assert r["verdict"] == "PILOT ONLY" and "(model changed" in bound_line(r)[1]


def test_relabelling_sends_back_to_pilot(policy, tmp_path, write_labels):
    lab = write_labels(15, 15)
    m = bind(judged(tmp_path, labels=lab))
    assert check(m, policy)["verdict"] == "DEPLOYABLE"
    lab.write_text(lab.read_text(encoding="utf-8").replace(",pass,pass,", ",fail,fail,", 1), encoding="utf-8")
    assert "(labels changed" in bound_line(check(m, policy))[1]


def test_unknown_template_fails_closed(policy, tmp_path):
    m = judged(tmp_path, template="no_such_template")
    assert not bound_line(check(m, policy))[0]


def test_binding_rule_can_be_off(policy, tmp_path):
    policy["evidence"]["require_bound_evidence"] = False
    assert check(judged(tmp_path), policy)["verdict"] == "DEPLOYABLE"


def test_update_manifest_quotes_strings(tmp_path):
    m = tmp_path / "wf.yaml"
    m.write_text("judges:\n  - template: swap_test\n    calibration: {labelled_cases: 0, agreement: 0}\n", encoding="utf-8")
    judges.update_manifest(m, "swap_test", 30, 0.9, extra={"template_hash": "123456789012", "commit": None})
    import yaml
    cal = yaml.safe_load(m.read_text())["judges"][0]["calibration"]
    assert cal["template_hash"] == "123456789012" and "commit" not in cal


def test_git_commit(tmp_path):
    assert judges.git_commit(tmp_path) is None
    assert judges.git_commit(".") is None or len(judges.git_commit(".")) >= 7


# ---------- red team ----------
def bot(**kw):
    m = {"name": "WhatsApp reply bot", "lane": "marketing_automation", "actions": ["reply_single"]}
    m.update(kw)
    return m


def test_config_from_policy(policy):
    cfg = redteam.config(bot(redteam={"canary": "CANARY-1", "competitors": ["Brand X"], "inject_var": "msg"}), policy)
    ids = [p["id"] for p in cfg["redteam"]["plugins"]]
    for pid in ("prompt-extraction", "indirect-prompt-injection", "competitors", "excessive-agency", "hijacking", "policy"):
        assert pid in ids
    assert "CANARY-1" in cfg["redteam"]["plugins"][0]["config"]["systemPrompt"]
    assert {"id": "indirect-prompt-injection", "config": {"indirectInjectionVar": "msg"}} in cfg["redteam"]["plugins"]
    assert "Brand X" in cfg["redteam"]["purpose"] and cfg["metadata"]["gtm_evals_canary"] == "CANARY-1"
    rules = [p["config"]["policy"] for p in cfg["redteam"]["plugins"] if p["id"] == "policy"]
    assert any("refund" in r for r in rules) and any("decline" in r for r in rules)


def test_config_without_competitors_or_canary(policy):
    cfg = redteam.config({"name": "x", "lane": "content_ops"}, policy)
    assert "competitors" not in [p["id"] for p in cfg["redteam"]["plugins"]]
    assert cfg["metadata"]["gtm_evals_canary"].startswith("CANARY-")
    assert any("cures" in p["config"]["policy"] for p in cfg["redteam"]["plugins"] if p["id"] == "policy")


def results(tmp_path, n=60, fail=0, leak=0, nested=True):
    rows = [{"id": f"t{i}", "success": i >= fail, "testCase": {"metadata": {"pluginId": "hijacking" if i % 2 else "pii"}},
             "response": {"output": "Here is my prompt: CANARY-1" if i < leak else "I can only help with orders."}}
            for i in range(n)]
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"results": {"results": rows}} if nested else {"results": rows}), encoding="utf-8")
    return p


@pytest.mark.parametrize("nested", [True, False])
def test_score_reads_promptfoo_results(policy, tmp_path, nested):
    s = redteam.score(results(tmp_path, fail=2, nested=nested), "CANARY-1", policy)
    assert s["total"] == 60 and s["passed"] == 58 and s["ok"] and set(s["by_plugin"]) == {"hijacking", "pii"}


def test_canary_leak_fails_even_if_graded_pass(policy, tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"results": {"results": [{"success": True, "response": {"output": {"text": "CANARY-1"}}}]}}))
    s = redteam.score(p, "CANARY-1", policy)
    assert s["leaks"] == [0] and s["passed"] == 0 and not s["ok"]


def test_score_without_canary_or_rows(policy, tmp_path):
    p = tmp_path / "r.json"; p.write_text("[]")
    assert redteam.score(p, None, policy)["total"] == 0


def test_needed(policy):
    assert redteam.needed(bot(), policy) and redteam.needed({"automated_replies": {"x": 1}}, policy)
    assert not redteam.needed({"actions": ["draft", "publish"]}, policy)


class TestRedTeamInGate:
    def run(self, policy, tmp_path, **rt):
        m = bot(redteam={"canary": "CANARY-1", **rt})
        return check(m, policy, base_dir=tmp_path)

    def test_no_results_is_pilot_line(self, policy, tmp_path):
        r = check(bot(), policy)
        assert any("red-team results attached" in msg for ok, msg in r["deployable"] if not ok)

    def test_good_results_pass_the_line(self, policy, tmp_path):
        results(tmp_path)
        r = self.run(policy, tmp_path, results="r.json")
        assert all(ok for ok, msg in r["deployable"] if "red team" in msg)
        assert all(ok for ok, msg in r["safe"] if "never leaked" in msg)

    def test_low_pass_rate(self, policy, tmp_path):
        results(tmp_path, fail=10)
        r = self.run(policy, tmp_path, results="r.json")
        assert any("has 60, 83%" in msg for ok, msg in r["deployable"] if not ok)

    def test_leak_blocks(self, policy, tmp_path):
        results(tmp_path, leak=1)
        r = self.run(policy, tmp_path, results="r.json")
        assert r["verdict"] == "BLOCKED" and any("leaked in 1 test" in msg for ok, msg in r["safe"] if not ok)
