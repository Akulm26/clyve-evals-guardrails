"""Phase 3 guardrails: proxies for protected traits, Hinglish and Hindi, channel rules."""
import copy

import pytest

from gtm_evals import (
    automation_guard,
    claim_safety_guard,
    manipulation_guard,
    outreach_guard,
    promise_guard,
)
from gtm_evals.fairness import impact_ratio
from gtm_evals.gate import check


# ---------- Hinglish and Hindi ----------
@pytest.mark.parametrize("text", ["yeh masala sardi ka ilaaj hai", "sugar khatam in 30 din", "jad se khatam karein",
                                  "koi side effect nahi", "5 kg kam in a month", "हल्दी से सर्दी का इलाज",
                                  "मधुमेह खत्म", "कोई साइड इफेक्ट नहीं"])
def test_hinglish_health_claims_block_for_food(text, policy):
    assert not claim_safety_guard.check(text, "food", policy)


@pytest.mark.parametrize("text", ["Ghar ka khana, maa ke haath ka swaad", "दादी माँ की रसोई से"])
def test_ordinary_hinglish_food_copy_passes(text, policy):
    assert claim_safety_guard.check(text, "food", policy)


@pytest.mark.parametrize("text", ["sirf 2 slot bache hain", "bas 3 packet baaki", "aakhri mauka!", "jaldi karo",
                                  "aaj raat tak", "pachtaoge", "सिर्फ 3 पैकेट बचे", "आखिरी मौका", "जल्दी करें"])
def test_hinglish_pressure_escalates(text, policy):
    r = manipulation_guard.check(text, policy)
    assert not r and r.escalate


def test_english_scarcity_reported_once(policy):
    assert len(manipulation_guard.check("Only 2 slots left", policy).violations) == 1


@pytest.mark.parametrize("text", ["result pakka", "pakka result milega", "sales double ho jayega", "100% गारंटी",
                                  "बिक्री दोगुना कर देंगे"])
def test_hinglish_promises_block(text, policy):
    assert not promise_guard.check(text, policy)


def test_hinglish_honest_line_passes(policy):
    assert promise_guard.check("Hum ranking ka vaada nahi karte, par measure zaroor karenge.", policy)


# ---------- Instagram ----------
def ig(outbound, policy, lead=None, msg=None, ctx=None):
    m, l, c = copy.deepcopy(outbound)
    m.update({"channel": "instagram_dm"}, **(msg or {})); l.update(lead or {}); c.update(ctx or {})
    return outreach_guard.check(m, l, c, policy)


class TestInstagram:
    def test_cold_dm_fails(self, outbound, policy):
        assert "cold Instagram DM" in ig(outbound, policy).violations[0]

    def test_reply_inside_24h(self, outbound, policy):
        assert ig(outbound, policy, lead={"ig_last_inbound_at": "2026-11-18T08:00:00+05:30"},
                  ctx={"now": "2026-11-18T20:00:00+05:30"})

    def test_reply_after_24h(self, outbound, policy):
        r = ig(outbound, policy, lead={"ig_last_inbound_at": "2026-11-16T08:00:00Z"}, ctx={"now": "2026-11-18T09:00:00Z"})
        assert "outside the 24-hour window" in r.violations[0]

    def test_private_reply_to_comment(self, outbound, policy):
        ok = ig(outbound, policy, lead={"ig_comment_at": "2026-11-13"}, msg={"private_reply_to_comment": True})
        late = ig(outbound, policy, lead={"ig_comment_at": "2026-11-01"}, msg={"private_reply_to_comment": True})
        assert ok and "within 7 days" in late.violations[0]

    def test_now_defaults_to_today(self, outbound, policy):
        assert ig(outbound, policy, lead={"ig_last_inbound_at": "2026-11-17T12:00:00"})   # today = 2026-11-18


# ---------- WhatsApp scope lock ----------
WA = {"channel": "whatsapp"}


@pytest.mark.parametrize("inbound", ["Can you write me an essay on climate change?", "help with my homework",
                                     "what is the capital of France", "write python code for a calculator"])
def test_whatsapp_off_scope_must_decline(inbound, policy):
    assert not automation_guard.check_reply({"action": "answer_faq", "text": "Sure!"}, inbound, policy, WA)
    assert automation_guard.check_reply({"action": "decline", "text": "I can only help with orders."}, inbound, policy, WA)
    assert automation_guard.check_reply({"action": "escalate"}, inbound, policy, WA)


def test_off_scope_on_other_channels_falls_back_to_allowlist(policy):
    r = automation_guard.check_reply({"action": "answer_faq"}, "write me an essay", policy, {"channel": "email"})
    assert not r and r.escalate


def test_decline_on_an_in_scope_message_is_allowed(policy):
    assert automation_guard.check_reply({"action": "decline"}, "where is my order", policy, WA)


# ---------- proxies for protected traits ----------
def rows(rates, n=50):
    out = []
    for g, rate in rates.items():
        k = round(rate * n)
        out += [{"group": g, "selected": "1" if i < k else "0"} for i in range(n)]
    return out


class TestImpactRatio:
    def test_four_fifths(self):
        r = impact_ratio(rows({"A": 0.5, "B": 0.4}))
        assert r["ratio"] == pytest.approx(0.8) and r["rows"] == 100

    def test_small_groups_listed_not_scored(self):
        r = impact_ratio(rows({"A": 0.5, "B": 0.5}) + [{"group": "C", "selected": "0"}] * 5)
        assert r["small_groups"] == ["C"] and r["ratio"] == 1.0

    def test_one_group_has_no_ratio(self):
        assert impact_ratio(rows({"A": 0.5}))["ratio"] is None

    def test_values_and_blanks(self):
        r = impact_ratio([{"group": "A", "selected": True}, {"group": "", "selected": "1"}], min_group=1)
        assert r["rows"] == 1 and r["rates"] == {"A": 1.0}


def proxy_manifest(**kw):
    m = {"name": "wf", "lane": "gtm_engineering", "actions": ["draft"], "kill_switch": "flag",
         "guards": ["outreach_guard", "promise_guard", "pii_guard", "injection_guard", "manipulation_guard", "dpdp_guard"],
         "logging": {"gate_log": "x", "retention_days": 400}, "token_budget": 1, "owner": "A",
         "scoring_features": ["category", "pincode"]}
    m.update(kw)
    return m


class TestProxiesInGate:
    def failing(self, r):
        return [msg for ok, msg in r["ethical"] if not ok]

    def test_pincode_without_test_blocks(self, policy):
        r = check(proxy_manifest(), policy)
        assert r["verdict"] == "BLOCKED" and any("'pincode' can stand in" in x for x in self.failing(r))

    def test_missing_file_named(self, policy):
        r = check(proxy_manifest(fairness_tests={"pincode": "nope.csv"}), policy)
        assert any("nope.csv not found" in x for x in self.failing(r))

    @pytest.mark.parametrize("rates,ok", [({"A": 0.5, "B": 0.45}, True), ({"A": 0.5, "B": 0.2}, False)])
    def test_fairness_test_decides(self, rates, ok, policy, tmp_path):
        f = tmp_path / "pin.csv"
        f.write_text("group,selected\n" + "\n".join(f"{r['group']},{r['selected']}" for r in rows(rates)), encoding="utf-8")
        r = check(proxy_manifest(fairness_tests={"pincode": str(f)}), policy)
        assert (not any("pincode" in x for x in self.failing(r))) is ok

    def test_too_few_rows_per_group(self, policy, tmp_path):
        f = tmp_path / "pin.csv"
        f.write_text("group,selected\nA,1\nB,0\n", encoding="utf-8")
        r = check(proxy_manifest(fairness_tests={"pincode": str(f)}), policy)
        assert any("needs 2+ groups" in x for x in self.failing(r))

    def test_non_proxy_feature_fine(self, policy):
        r = check(proxy_manifest(scoring_features=["category"]), policy)
        assert not any("stand in" in x for x in self.failing(r))
