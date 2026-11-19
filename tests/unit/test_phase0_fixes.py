"""Phase 0: checks the research showed were wrong (Gmail/Outlook sender rules, FSSAI "100%",
crawler groups, rank metrics). Each test names the rule it encodes."""
import copy

import pytest

from gtm_evals import ai_seo_guard as seo
from gtm_evals import claim_safety_guard as cs
from gtm_evals import outreach_guard, visibility_stats
from gtm_evals.core import Verdict, combine
from gtm_evals.outreach_guard import deliverability

ONE_CLICK = {"List-Unsubscribe": "<https://x.example/u/123>, <mailto:u@x.example>",
             "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"}


def run(outbound, policy, msg=None, ctx=None):
    m, l, c = copy.deepcopy(outbound)
    m.update(msg or {}); c.update(ctx or {})
    return outreach_guard.check(m, l, c, policy)


class TestOneClickUnsubscribe:
    """Gmail bulk-sender rules: RFC 8058 headers on marketing email."""

    def test_bulk_sender_without_headers_fails(self, outbound, policy):
        v = run(outbound, policy, ctx={"bulk_sender": True})
        assert sum("one-click unsubscribe" in x for x in v.violations) == 2

    def test_bulk_sender_with_headers_passes(self, outbound, policy):
        assert run(outbound, policy, msg={"headers": ONE_CLICK}, ctx={"bulk_sender": True})

    def test_header_names_are_case_insensitive(self, outbound, policy):
        h = {k.lower(): v for k, v in ONE_CLICK.items()}
        assert run(outbound, policy, msg={"headers": h}, ctx={"bulk_sender": True})

    def test_mailto_only_is_not_one_click(self, outbound, policy):
        h = dict(ONE_CLICK, **{"List-Unsubscribe": "<mailto:u@x.example>"})
        v = run(outbound, policy, msg={"headers": h}, ctx={"bulk_sender": True})
        assert any("https URL" in x for x in v.violations)

    def test_low_volume_sender_not_required_by_default(self, outbound, policy):
        assert run(outbound, policy)

    @pytest.mark.parametrize("mode,bulk,ok", [("always", False, False), ("never", True, True)])
    def test_policy_modes(self, mode, bulk, ok, outbound, policy):
        policy["outreach"]["one_click_unsubscribe"] = mode
        assert bool(run(outbound, policy, ctx={"bulk_sender": bulk})) is ok

    def test_dms_never_need_headers(self, outbound, policy):
        assert run(outbound, policy, msg={"channel": "instagram_dm"}, ctx={"bulk_sender": True})


class TestDmarcAlignment:
    AUTH = {"spf": True, "dkim": True, "dmarc": True}

    def test_unaligned_fails(self, outbound, policy):
        v = run(outbound, policy, ctx={"sender_auth": dict(self.AUTH, spf_aligned=False, dkim_aligned=False)})
        assert "DMARC not aligned" in v.violations[0]

    @pytest.mark.parametrize("aligned", [{"spf_aligned": True}, {"dkim_aligned": True}])
    def test_either_alignment_is_enough(self, aligned, outbound, policy):
        assert run(outbound, policy, ctx={"sender_auth": dict(self.AUTH, **aligned)})

    def test_p_none_is_enough_but_junk_policy_fails(self, outbound, policy):
        assert run(outbound, policy, ctx={"sender_auth": dict(self.AUTH, dmarc_policy="none", spf_aligned=True)})
        assert not run(outbound, policy, ctx={"sender_auth": dict(self.AUTH, dmarc_policy="maybe", spf_aligned=True)})

    def test_unknown_alignment_is_a_note_not_a_failure(self, outbound, policy):
        v = run(outbound, policy)
        assert v and any("alignment not checked" in n for n in v.notes)


class TestSpamRate:
    @pytest.mark.parametrize("complaints,ok,noted", [(0, True, False), (1, True, True), (2, True, True), (3, False, False)])
    def test_warn_at_point_1_stop_at_point_3(self, complaints, ok, noted, policy):
        v = deliverability({"sent": 1000, "spam_complaints": complaints}, policy)
        assert bool(v) is ok and bool(v.notes) is noted


class TestFood100Percent:
    """FSSAI advisory (30 May 2025): no "100%" on food labels or promotional content."""

    @pytest.mark.parametrize("text", ["100% pure haldi", "100 % natural", "made with 100 per cent ghee", "100%"])
    @pytest.mark.parametrize("category", ["spice", "food", "honey", "masala blends"])
    def test_blocked_for_food(self, text, category, policy):
        v = cs.check(text, category, policy)
        assert not v and "prohibited for food (FSSAI)" in v.violations[0] and not v.escalate

    def test_reported_once_not_also_as_needs_proof(self, policy):
        v = cs.check("100% natural", "spice", policy)
        assert len(v.violations) == 1

    def test_still_needs_proof_outside_food(self, policy):
        v = cs.check("100% natural", "skincare", policy)
        assert not v and v.escalate and "needs proof" in v.violations[0]

    def test_numbers_like_1000_are_not_100_percent(self, policy):
        assert cs.check("1000 happy kitchens", "spice", policy)


class TestCrawlerGroups:
    def test_user_triggered_block_is_a_note(self, policy):
        v = seo.crawler_access("User-agent: ChatGPT-User\nUser-agent: Claude-User\nDisallow: /\n", policy)
        assert v and len(v.notes) == 2 and "firewall" in v.notes[0]

    def test_google_extended_block_is_noted_as_visibility(self, policy):
        v = seo.crawler_access("User-agent: Google-Extended\nDisallow: /\n", policy)
        assert v and any("Gemini" in n for n in v.notes)

    def test_gptbot_block_stays_silent(self, policy):
        v = seo.crawler_access("User-agent: GPTBot\nDisallow: /\n", policy)
        assert v and v.notes == []

    def test_answer_crawler_block_still_fails(self, policy):
        assert not seo.crawler_access("User-agent: Claude-SearchBot\nDisallow: /\n", policy)


class TestPresenceNotRank:
    ROW = {"checkpoint": "d0", "query_type": "brand", "engine": "chatgpt", "prompt_id": "b1", "run": 0,
           "mentioned": True, "surface": "api"}

    @pytest.mark.parametrize("field", ["rank", "position", "Rank"])
    def test_rank_fields_rejected(self, field, policy):
        rows = [dict(self.ROW, run=0, **{field: 1}), dict(self.ROW, run=1)]
        assert any("presence rate only" in p for p in visibility_stats.validate_rows(rows, policy))


class TestNotes:
    def test_notes_never_change_passed(self):
        assert Verdict.from_violations("g", [], notes=["fyi"]).passed

    def test_combine_keeps_notes_prefixed(self):
        c = combine(Verdict("a", True, notes=["x"]), Verdict("b", True))
        assert c.notes == ["[a] x"] and c.to_dict()["notes"] == ["[a] x"]

    def test_to_dict_omits_empty_notes(self):
        assert "notes" not in Verdict("a", True).to_dict()
