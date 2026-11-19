"""outreach_guard: who may be contacted, message hygiene, sourced + fresh personalisation, caps."""
import copy

import pytest

from gtm_evals import outreach_guard
from gtm_evals.outreach_guard import _overlap, _undeclared_lead_statements, deliverability


def run(outbound, policy, msg=None, lead=None, ctx=None):
    m, l, c = copy.deepcopy(outbound)
    m.update(msg or {}); l.update(lead or {}); c.update(ctx or {})
    return outreach_guard.check(m, l, c, policy)


def test_clean_message_passes(outbound, policy):
    v = run(outbound, policy)
    assert v, v.violations


class TestWhoMayBeContacted:
    def test_suppressed_email(self, outbound, policy):
        assert "suppression" in run(outbound, policy, ctx={"suppression": {"f@brand.example"}}).violations[0]

    def test_suppressed_phone(self, outbound, policy):
        assert not run(outbound, policy, ctx={"suppression": ["+91 90000 00001"]})

    @pytest.mark.parametrize("basis", [None, ""])
    def test_no_lawful_basis(self, basis, outbound, policy):
        assert "lawful basis" in run(outbound, policy, lead={"lawful_basis": basis}).violations[0]

    @pytest.mark.parametrize("channel", ["whatsapp", "sms"])
    def test_optin_channels(self, channel, outbound, policy):
        assert f"no {channel} opt-in" in run(outbound, policy, msg={"channel": channel}).violations[0]
        assert run(outbound, policy, msg={"channel": channel}, lead={"optin_channels": [channel]})

    @pytest.mark.parametrize("cat", ["Real Estate", "real-estate", "real_estate", "stock trading"])
    def test_icp_exclusions_normalised(self, cat, outbound, clyve):
        v = run(outbound, clyve, lead={"category": cat})
        assert not v and "outside ICP" in v.violations[0]

    def test_no_exclusions_by_default(self, outbound, policy):
        assert run(outbound, policy, lead={"category": "real estate"})


class TestHygiene:
    def test_missing_unsubscribe(self, outbound, policy):
        body = outbound[0]["body"].replace(" If not relevant, reply stop and I won't write again.", "")
        assert "unsubscribe" in run(outbound, policy, msg={"body": body}).violations[0]

    def test_unsubscribe_not_required_on_dm(self, outbound, policy):
        body = outbound[0]["body"].replace(" If not relevant, reply stop and I won't write again.", "")
        assert run(outbound, policy, msg={"body": body, "channel": "inmail"})

    def test_sender_auth(self, outbound, policy):
        v = run(outbound, policy, ctx={"sender_auth": {"spf": True}})
        assert "sender auth missing: dkim, dmarc" in v.violations

    def test_too_long(self, outbound, policy):
        policy["outreach"]["max_words"] = 20
        assert any("too long" in x for x in run(outbound, policy).violations)

    def test_daily_cap(self, outbound, policy):
        assert "daily cap" in run(outbound, policy, ctx={"sent_today_by_inbox": {"o@x.example": 30}}).violations[0]


class TestPersonalisation:
    def test_unbacked_claim(self, outbound, policy):
        v = run(outbound, policy, msg={"claims_about_lead": ["your founder spoke at a Delhi D2C summit"]})
        assert any("not backed by any signal" in x for x in v.violations)

    def test_stale_signal(self, outbound, policy):
        lead = copy.deepcopy(outbound[1]); lead["signals"][0]["date"] = "2026-06-01"
        v = run(outbound, policy, lead={"signals": lead["signals"]})
        assert any("stale signal (170d old)" in x for x in v.violations)

    def test_signal_without_source(self, outbound, policy):
        lead = copy.deepcopy(outbound[1]); lead["signals"][0]["source_url"] = ""
        assert any("no source URL" in x for x in run(outbound, policy, lead={"signals": lead["signals"]}).violations)

    def test_stretched_outcome_word(self, outbound, policy):
        claims = ["launched 4 new Meta ads for the winter chai masala range and sales doubled"]
        assert any("stretched" in x for x in run(outbound, policy, msg={"claims_about_lead": claims}).violations)

    def test_undeclared_statement_in_body(self, outbound, policy):
        body = outbound[0]["body"].replace("Worth a", "Loved your Shark Tank episode! Worth a")
        v = run(outbound, policy, msg={"body": body})
        assert any("not declared in claims_about_lead" in x and "Shark Tank" in x for x in v.violations)

    @pytest.mark.parametrize("line", ["Your team might find this useful.", "Worth a 30-minute call for your team?"])
    def test_generic_lines_about_them_pass(self, line):
        assert _undeclared_lead_statements(line, []) == []

    def test_overlap_threshold(self):
        assert _overlap("launched 4 new Meta ads", "launched 4 new Meta ads for winter")
        assert not _overlap("raised a Series A", "launched 4 new Meta ads")
        assert not _overlap("", "anything")


class TestPrivateMetrics:
    @pytest.mark.parametrize("line", ["Your conversion rate is probably under 1%.", "your CAC looks high",
                                      "Your revenue is flat", "you're losing ₹40,000 on ads"])
    def test_blocked_before_intake(self, line, outbound, policy):
        body = outbound[0]["body"] + " " + line
        assert any("private data before intake" in x for x in run(outbound, policy, msg={"body": body}).violations)

    def test_allowed_after_intake(self, outbound, policy):
        body = outbound[0]["body"] + " Your conversion rate moved."
        v = run(outbound, policy, msg={"body": body}, lead={"stage": "audit"})
        assert not any("private data" in x for x in v.violations)


class TestDeliverability:
    @pytest.mark.parametrize("stats,ok", [({"sent": 1000, "bounced": 25}, False), ({"sent": 1000, "spam_complaints": 3}, False),
                                          ({"sent": 1000, "spam_complaints": 2}, True),
                                          ({"sent": 1000, "bounced": 5}, True), ({}, True)])
    def test_stop_rules(self, stats, ok, policy):
        assert bool(deliverability(stats, policy)) is ok


class TestChannelCaps:
    @pytest.mark.parametrize("channel,cap", [("inmail", 20), ("instagram_dm", 20), ("linkedin_dm", 30)])
    def test_daily_cap_per_channel(self, channel, cap, outbound, policy):
        v = run(outbound, policy, msg={"channel": channel}, ctx={"sent_today_by_channel": {channel: cap}})
        assert any(f"daily {channel} cap reached ({cap}/{cap})" in x for x in v.violations)

    def test_under_cap_passes(self, outbound, policy):
        assert run(outbound, policy, msg={"channel": "inmail"}, ctx={"sent_today_by_channel": {"inmail": 19}})

    def test_channel_without_cap(self, outbound, policy):
        assert run(outbound, policy, ctx={"sent_today_by_channel": {"email": 10_000}})
