"""Phase 4 evals: as-of replay, shadow → canary → segment, budgets, and the gate rules that read them."""
import json

import pytest

from gtm_evals import rollout
from gtm_evals.gate import check
from gtm_evals.runner import as_of, run_case
from tests.conftest import clean_log


# ---------- as-of replay ----------
def test_as_of_hides_later_signals():
    x = {"lead": {"signals": [{"fact": "launched 4 ads", "date": "2026-10-01"},
                              {"fact": "raised Series A", "date": "2026-11-15"}]},
         "context": {"today": "2026-11-18"}}
    y = as_of(x, "2026-11-01")
    assert [s["fact"] for s in y["lead"]["signals"]] == ["launched 4 ads"] and y["context"]["today"] == "2026-11-01"


def test_as_of_drops_dated_fields_in_dicts():
    rec = {"fields": {"stage": {"value": "Series A", "date": "2026-11-15"}, "company": {"value": "X", "date": "2026-09-01"}}}
    assert list(as_of(rec, "2026-10-01")["fields"]) == ["company"]


def test_as_of_case_cant_pass_on_a_later_signal(outbound, policy, tmp_path):
    m, lead, ctx = outbound
    m = dict(m, body=m["body"].replace("saw you launched 4 new Meta ads for the winter chai masala range",
                                       "saw you raised a Series A"), claims_about_lead=["raised a Series A"])
    lead = dict(lead, signals=[{"fact": "raised a Series A", "source_url": "https://x", "date": "2026-11-15"}])
    ctx = dict(ctx, suppression=[], today="2026-11-18")
    row = {"id": "a", "guard": "outreach", "input": {"message": m, "lead": lead, "context": ctx}, "expected_pass": False}
    assert run_case(row, policy, tmp_path)                       # today's view: the signal exists
    assert not run_case(dict(row, as_of="2026-11-10"), policy, tmp_path)   # as it stood then: no signal


# ---------- rollout ----------
STAGES = [{"name": "shadow", "share": 0, "days": 2}, {"name": "canary", "share": 0.05, "days": 2},
          {"name": "segment", "share": 0.25, "days": 3}]


def rows_for(days, per_day=25, bad_day=None, **bad):
    out = []
    for d in range(days):
        for i in range(per_day):
            r = {"ts": f"2026-10-{d + 1:02d}T10:{i:02d}:00", "sent": True, "guard_passed": True, "replied": i < 2}
            if d == bad_day:
                r.update(bad)
            out.append(r)
    return out


def test_clean_days_advance(policy):
    st = rollout.status({"stages": STAGES}, rows_for(7), policy)
    assert st["stage"] == "segment" and st["complete"] and [h["event"] for h in st["history"]] == ["advance", "advance"]


@pytest.mark.parametrize("bad,why", [({"unsubscribed": True}, "unsubscribes"), ({"complained": True}, "complaints"),
                                     ({"guard_passed": False}, "guard failures"), ({"kill_switch": True}, "kill switch")])
def test_breach_drops_to_shadow(bad, why, policy):
    st = rollout.status({"stages": STAGES}, rows_for(5, bad_day=3, **bad), policy)
    br = [h for h in st["history"] if h["event"] == "breach"]
    assert st["stage"] == "shadow" and st["clean_days"] == 1 and br[0]["stage"] == "canary" and why in br[0]["why"][0]


def test_reply_floor(policy):
    st = rollout.status({"stages": STAGES, "guard_metrics": {"reply_rate_min": 0.2}}, rows_for(2), policy)
    assert st["history"][0]["event"] == "breach" and "replies" in st["history"][0]["why"][0]


def test_thin_days_dont_count(policy):
    st = rollout.status({"stages": STAGES}, rows_for(3, per_day=5), policy)
    assert st["stage"] == "shadow" and st["clean_days"] == 0 and all(h["event"] == "thin" for h in st["history"])


def test_silent_rows_count_as_failures(policy):
    rows = rows_for(1) + [{"ts": "2026-10-01T11:00:00"}] * 5
    assert rollout.day_metrics(rows)["guard_fail_rate"] == pytest.approx(5 / 30)


def test_default_stages_from_policy(policy):
    st = rollout.status({}, rows_for(1), policy)
    assert st["stages"] == ["shadow", "canary", "segment"] and st["days_needed"] == 7


def test_read_log_missing(tmp_path):
    assert rollout.read_log(tmp_path / "nope.jsonl") == []


# ---------- budgets ----------
def test_budget_status():
    rows = [{"cost_usd": 0.1, "latency_s": s} for s in range(1, 101)]
    b = rollout.budget_status(rows, {"usd_per_item": 0.05, "p95_seconds": 90})
    assert b["p95_seconds"] == 95 and len(b["problems"]) == 2 and "p95 latency 95s > budget 90s" in b["problems"][1]


def test_whatsapp_priced_by_category():
    rows = [{"channel": "whatsapp", "category": "marketing"}, {"channel": "whatsapp", "category": "utility"},
            {"channel": "email"}]
    b = rollout.budget_status(rows, {"whatsapp_rates": {"marketing": 0.01, "utility": 0.002}})
    assert b["usd_per_item"] == pytest.approx(0.006) and b["unpriced_rows"] == 1 and not b["problems"]


def test_budget_breach_is_a_rollout_stop(policy):
    rows = rows_for(3)
    for r in rows[25:50]:
        r["latency_s"] = 140
    st = rollout.status({"stages": STAGES}, rows, policy, {"p95_seconds": 90})
    assert any("p95 latency 140s" in w for h in st["history"] if h["event"] == "breach" for w in h["why"])


def test_p95_empty():
    assert rollout.p95([]) is None


# ---------- the gate ----------
GOOD = {"name": "wf", "owner": "A", "lane": "gtm_engineering", "actions": ["send_single", "send_bulk"],
        "guards": ["outreach_guard", "promise_guard", "pii_guard", "injection_guard", "manipulation_guard", "dpdp_guard",
                   "output_guard"],
        "human_approver": "A", "canary_percent": 5, "kill_switch": "KS", "token_budget": 1,
        "logging": {"gate_log": True, "retention_days": 365}}


def lines(res, part):
    return {msg: ok for ok, msg in res[part]}


def test_bulk_send_needs_a_live_log(policy):
    r = check(dict(GOOD), policy)
    assert any("live rollout log attached" in m and not ok for m, ok in lines(r, "deployable").items())


def test_log_earns_the_stage(policy, tmp_path):
    early = clean_log(tmp_path / "a.jsonl", days=9)
    r = check(dict(GOOD, rollout={"log": str(early)}), policy)
    assert any("(now: canary, 2/7 clean days)" in m and not ok for m, ok in lines(r, "deployable").items())
    full = clean_log(tmp_path / "b.jsonl", days=14)
    r = check(dict(GOOD, rollout={"log": str(full)}), policy)
    assert all(ok for m, ok in lines(r, "deployable").items() if "live rollout" in m)


def test_draft_only_workflows_dont_need_rollout(policy):
    r = check(dict(GOOD, actions=["draft", "send_single"]), policy)
    assert not any("rollout" in m for m in lines(r, "deployable"))


def test_budget_breach_blocks(policy, tmp_path):
    log = clean_log(tmp_path / "d.jsonl", latency_s=140)
    r = check(dict(GOOD, rollout={"log": str(log)}, budgets={"p95_seconds": 90}), policy)
    assert r["verdict"] == "BLOCKED" and any("p95 latency 140s" in m for m, ok in lines(r, "safe").items() if not ok)


def test_crm_writes_need_provenance(policy):
    r = check(dict(GOOD, actions=["crm_update"], guards=GOOD["guards"] + ["enrichment_guard"]), policy)
    assert any("provenance" in m and not ok for m, ok in lines(r, "safe").items())


def test_trace_required_needs_provenance(policy):
    r = check(dict(GOOD, actions=["draft"], trace_required_for=["research_note"]), policy)
    assert any("tool trace" in m and not ok for m, ok in lines(r, "safe").items())


def test_tools_retrieval_memory(policy):
    r = check(dict(GOOD, actions=["crm_update"], guards=GOOD["guards"] + ["enrichment_guard", "provenance"],
                   tools=[{"name": "mail", "scopes": ["send"]}], retrieval={}, memory={"agent_writes": True}), policy)
    bad = [m for m, ok in lines(r, "safe").items() if not ok]
    assert r["verdict"] == "BLOCKED" and len(bad) == 3
    assert any("least privilege" in m for m in bad) and any("client" in m for m in bad) and any("untrusted" in m for m in bad)
    r = check(dict(GOOD, retrieval={"client_filter": "tenant_id"}, memory={"agent_writes": True, "treated_as_untrusted": True},
                   tools=[{"name": "mail", "scopes": ["send", "bulk_send"]}]), policy)
    assert all(ok for m, ok in lines(r, "safe").items() if "client" in m or "untrusted" in m or "least" in m)


def test_teardown_manifest_has_rollout_and_budgets(root):
    import yaml
    m = yaml.safe_load((root / "workflows/teardown-outreach.yaml").read_text())
    assert m["rollout"]["log"] and m["budgets"]["p95_seconds"] == 90
    assert json.dumps(m)   # plain data
