"""gate.check, one rule at a time, on manifests built in memory."""
import copy

import pytest

from gtm_evals.gate import check, report

GOOD = {
    "name": "wf", "owner": "Akul", "lane": "gtm_engineering",
    "actions": ["score_lead", "send_single", "send_bulk"],
    "guards": ["outreach_guard", "promise_guard", "pii_guard", "injection_guard", "manipulation_guard"],
    "human_approver": "Akul", "canary_percent": 5, "kill_switch": "KS", "token_budget": 1000,
    "logging": {"gate_log": True, "retention_days": 365},
    "data": {"personal_data": True, "fields": ["name", "work_email"], "lawful_basis_field": True,
             "consent_checked_at_send": True, "opt_out_hours": 24},
    "scoring_features": ["category"],
}


def make(**changes):
    m = copy.deepcopy(GOOD)
    for k, v in changes.items():
        if v is None:
            m.pop(k, None)
        else:
            m[k] = v
    return m


def failing(res):
    return [msg for k in ("safe", "ethical", "deployable") for ok, msg in res[k] if not ok]


@pytest.fixture
def evidence(tmp_path):
    gs = tmp_path / "g.jsonl"
    gs.write_text("\n".join('{"source": "real"}' for _ in range(30)), encoding="utf-8")
    return {"golden_set": str(gs)}


def test_good_manifest_is_deployable(policy, evidence):
    res = check(make(**evidence), policy)
    assert res["verdict"] == "DEPLOYABLE", failing(res)
    assert res["tiers"] == {"score_lead": "R1", "send_single": "R2", "send_bulk": "R3"}


def test_no_golden_set_is_pilot(policy):
    assert check(make(), policy)["verdict"] == "PILOT ONLY"


def test_synthetic_evidence_is_pilot(policy, tmp_path):
    gs = tmp_path / "g.jsonl"
    gs.write_text("\n".join('{"source": "synthetic"}' for _ in range(50)), encoding="utf-8")
    res = check(make(golden_set=str(gs)), policy)
    assert res["verdict"] == "PILOT ONLY" and any("has 0" in m for m in failing(res))


SAFE_BREAKS = [
    ("unknown lane", {"lane": "crypto"}, "is a known lane"),
    ("unknown action", {"actions": ["send_bulk", "export_list"]}, "unknown → treated as R3"),
    ("missing guard", {"guards": ["outreach_guard"]}, "missing:"),
    ("ghost guard", {"guards": GOOD["guards"] + ["vibes_guard"]}, "no such guard"),
    ("no kill switch", {"kill_switch": None}, "kill switch declared (none)"),
    ("no approver for R3", {"human_approver": ""}, "named human approver"),
    ("no canary for R3", {"canary_percent": 0}, "canary first"),
    ("no gate log", {"logging": {"gate_log": False, "retention_days": 365}}, "logged"),
    ("short retention", {"logging": {"gate_log": True, "retention_days": 30}}, "≥ 90 days"),
    ("no token budget", {"token_budget": 0}, "token budget"),
]

ETHICAL_BREAKS = [
    ("no lawful basis", {"data": {**GOOD["data"], "lawful_basis_field": False}}, "lawful basis"),
    ("cached consent", {"data": {**GOOD["data"], "consent_checked_at_send": False}}, "consent checked at send"),
    ("forbidden field", {"data": {**GOOD["data"], "fields": ["name", "Aadhaar"]}}, "forbidden: ['Aadhaar']"),
    ("slow opt-out", {"data": {**GOOD["data"], "opt_out_hours": 72}}, "48 hours"),
    ("protected attribute", {"scoring_features": ["category", "Gender"]}, "found: ['gender']"),
    ("undisclosed bot", {"automated_replies": {"discloses_automation": False, "human_escalation_path": "x"}}, "say they are automated"),
    ("no human path", {"automated_replies": {"discloses_automation": True, "human_escalation_path": ""}}, "human is always reachable"),
    ("no promise guard", {"guards": [g for g in GOOD["guards"] if g != "promise_guard"]}, "no outcome promises"),
]


@pytest.mark.parametrize("why,change,msg", SAFE_BREAKS + ETHICAL_BREAKS, ids=[x[0] for x in SAFE_BREAKS + ETHICAL_BREAKS])
def test_each_rule_blocks(why, change, msg, policy, evidence):
    res = check(make(**evidence, **change), policy)
    assert res["verdict"] == "BLOCKED"
    assert any(msg in m for m in failing(res)), failing(res)


def test_no_r3_means_no_approver_needed(policy, evidence):
    res = check(make(**evidence, actions=["score_lead", "send_single"], human_approver="", canary_percent=0), policy)
    assert res["verdict"] == "DEPLOYABLE", failing(res)


def test_no_personal_data_skips_data_rules(policy, evidence):
    res = check(make(**evidence, data={"personal_data": False}), policy)
    assert res["verdict"] == "DEPLOYABLE" and not any("lawful basis" in m for _, m in res["ethical"])


AI_SEO = dict(lane="ai_seo", guards=["ai_seo_guard", "visibility_stats", "promise_guard"], actions=["report_draft"],
              data={"personal_data": False})


def test_ai_seo_lane_needs_no_manipulation_guard(policy, evidence):
    res = check(make(**evidence, **AI_SEO), policy)
    assert res["verdict"] == "DEPLOYABLE", failing(res)


def test_old_ai_visibility_name_still_accepted(policy, evidence):
    assert check(make(**evidence, **dict(AI_SEO, lane="ai_visibility")), policy)["verdict"] == "DEPLOYABLE"


@pytest.mark.parametrize("missing", ["ai_seo_guard", "promise_guard"])
def test_ai_seo_lane_requires_technical_and_promise_guards(missing, policy, evidence):
    res = check(make(**evidence, **dict(AI_SEO, guards=[g for g in AI_SEO["guards"] if g != missing])), policy)
    assert res["verdict"] == "BLOCKED" and any(missing in m for m in failing(res))


CONTENT = dict(lane="content_ops", actions=["draft", "publish"], approval_log="approvals.jsonl", data={"personal_data": False},
               guards=["claims_gate", "promise_guard", "manipulation_guard", "claim_safety_guard", "pii_guard", "injection_guard"])


def test_content_lane_deployable(policy, evidence):
    res = check(make(**evidence, **CONTENT), policy)
    assert res["verdict"] == "DEPLOYABLE", failing(res)


@pytest.mark.parametrize("missing", ["claim_safety_guard", "pii_guard", "injection_guard"])
def test_content_lane_requires_new_guards(missing, policy, evidence):
    res = check(make(**evidence, **dict(CONTENT, guards=[g for g in CONTENT["guards"] if g != missing])), policy)
    assert res["verdict"] == "BLOCKED"


def test_publish_needs_an_approval_log(policy, evidence):
    res = check(make(**evidence, **dict(CONTENT, approval_log="")), policy)
    assert res["verdict"] == "BLOCKED" and any("recorded approval" in m for m in failing(res))


def test_gtm_crm_writes_need_enrichment_guard(policy, evidence):
    res = check(make(**evidence, actions=["crm_update", "send_single"]), policy)
    assert res["verdict"] == "BLOCKED" and any("enrichment_guard" in m for m in failing(res))
    ok = check(make(**evidence, actions=["crm_update", "send_single"], guards=GOOD["guards"] + ["enrichment_guard"]), policy)
    assert ok["verdict"] == "DEPLOYABLE", failing(ok)


def test_no_owner_is_pilot(policy, evidence):
    assert check(make(**evidence, owner=""), policy)["verdict"] == "PILOT ONLY"


class TestJudges:
    def test_uncalibrated_judge_is_pilot(self, policy, evidence):
        m = make(**evidence, judges=[{"template": "swap_test", "calibration": {"labelled_cases": 30, "agreement": 0.8}}])
        assert check(m, policy)["verdict"] == "PILOT ONLY"

    def test_calibrated_judge_without_label_file(self, policy, evidence):
        m = make(**evidence, judges=[{"template": "swap_test", "calibration": {"labelled_cases": 30, "agreement": 0.9}}])
        assert check(m, policy)["verdict"] == "DEPLOYABLE"

    def test_label_file_must_back_the_claim(self, policy, evidence, write_labels):
        few = write_labels(5, 5)
        m = make(**evidence, judges=[{"template": "swap_test", "labels": str(few),
                                      "calibration": {"labelled_cases": 30, "agreement": 0.9}}])
        res = check(m, policy)
        assert res["verdict"] == "PILOT ONLY" and any("file has 10 labelled" in x for x in failing(res))

    def test_label_file_backs_the_claim(self, policy, evidence, write_labels):
        m = make(**evidence, judges=[{"template": "swap_test", "labels": str(write_labels(15, 15, blank=5)),
                                      "calibration": {"labelled_cases": 30, "agreement": 0.9}}])
        assert check(m, policy)["verdict"] == "DEPLOYABLE"

    def test_missing_label_file(self, policy, evidence):
        m = make(**evidence, judges=[{"template": "swap_test", "labels": "nope.csv",
                                      "calibration": {"labelled_cases": 30, "agreement": 0.9}}])
        assert any("label file" in x and "exists" in x for x in failing(check(m, policy)))

    def test_paths_resolve_from_base_dir(self, policy, tmp_path, write_labels):
        sub = tmp_path / "repo"; sub.mkdir()
        (sub / "g.jsonl").write_text("\n".join('{"source": "real"}' for _ in range(30)), encoding="utf-8")
        write_labels(15, 15).rename(sub / "l.csv")
        m = make(golden_set="g.jsonl", judges=[{"template": "swap_test", "labels": "l.csv",
                                                "calibration": {"labelled_cases": 30, "agreement": 0.9}}])
        assert check(m, policy, base_dir=sub)["verdict"] == "DEPLOYABLE"


def test_report_lists_every_check(policy, evidence):
    res = check(make(**evidence), policy)
    text = report(res)
    assert "wf  →  DEPLOYABLE" in text and text.count("✅") == len(res["safe"]) + len(res["ethical"]) + len(res["deployable"])


def test_publish_preview_counts_as_its_canary(policy, evidence):
    m = make(**evidence, **dict(CONTENT, actions=["draft", "publish"]), human_approver="Akul", canary_percent=0)
    assert check(m, policy)["verdict"] == "BLOCKED"
    m["preview_before_publish"] = True
    assert check(m, policy)["verdict"] == "DEPLOYABLE", failing(check(m, policy))


def test_preview_does_not_excuse_bulk_sends(policy, evidence):
    m = make(**evidence, canary_percent=0, preview_before_publish=True)   # GOOD has send_bulk
    assert check(m, policy)["verdict"] == "BLOCKED"
