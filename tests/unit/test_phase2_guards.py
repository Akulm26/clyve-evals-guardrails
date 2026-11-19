"""Phase 2 guardrails: testimonials and social proof, likeness and AI labels, dark patterns."""
import pytest

from gtm_evals import dark_pattern_guard as dp
from gtm_evals import likeness_guard as lk
from gtm_evals import testimonial_guard as tg

REG = [{"id": "T1", "quote": "Best haldi I've bought in years.", "author": "Rhea", "source": "https://x", "consent": True}]


class TestTestimonials:
    def test_quotes_ignore_apostrophes_and_short_quotes(self):
        assert tg.quotes("We call it 'the good stuff' and I've said so") == []
        assert tg.quotes('"Too short" — A') == []
        assert tg.quotes('“Best haldi I’ve bought in years.” — Rhea, Ludhiana')[0][1].startswith("Rhea")

    @pytest.mark.parametrize("text", ['"Best haldi I\'ve bought in years." — Rhea', "“Best haldi I’ve bought in years.”"])
    def test_exact_match_passes(self, text, policy):
        assert tg.check(text, REG, policy)

    def test_curly_and_straight_quotes_normalise(self, policy):
        assert tg.check('"BEST haldi I’ve bought in years!!"', REG, policy)

    @pytest.mark.parametrize("field,value,msg", [("consent", False, "no consent"), ("ai_generated", True, "AI-generated"),
                                                ("source", None, "no source")])
    def test_registered_but_unusable(self, field, value, msg, policy):
        r = tg.check('"Best haldi I\'ve bought in years."', [dict(REG[0], **{field: value})], policy)
        assert not r and msg in r.violations[0]

    def test_consent_check_can_be_off(self, policy):
        policy["testimonial"]["require_consent"] = False
        assert tg.check('"Best haldi I\'ve bought in years."', [dict(REG[0], consent=False)], policy)

    def test_reworded_escalates(self, policy):
        r = tg.check('"Best haldi I have bought in many years"', REG, policy)
        assert not r and r.escalate and "closest: T1" in r.violations[0]

    def test_unregistered_with_attribution_blocks(self, policy):
        r = tg.check('"This masala changed my cooking forever." — Priya', REG, policy)
        assert not r and not r.escalate and "— Priya" in r.violations[0]

    def test_quoted_phrase_without_testimonial_cues_is_fine(self, policy):
        assert tg.check('Our tagline is "spice that remembers home" and always has been.', REG, policy)

    def test_unregistered_quote_with_cue_blocks(self, policy):
        assert not tg.check('A customer review: "spice that remembers home, truly"', REG, policy)

    def test_empty_register(self, policy):
        assert not tg.check('"Changed my life completely." — Priya', [], policy)
        assert tg.check("No quotes here.", None, policy)

    @pytest.mark.parametrize("text", ["1,200+ shoppers are viewing this", "57 sold in the last 2 hours",
                                      "Someone in Mohali just bought this"])
    def test_social_proof_counters(self, text, policy):
        r = tg.check(text, REG, policy)
        assert not r and "social-proof" in r.violations[0]

    def test_stars_need_a_rating_source(self, policy):
        assert not tg.check("Rated ★★★★★ by customers", REG, policy)
        assert tg.check("Rated ★★★★★ by customers", REG + [{"id": "R", "kind": "rating", "source": "https://g"}], policy)


LREG = [{"id": "L1", "name": "Rhea", "consent": True, "scope": ["ads"], "expires": "2027-01-01"}]


class TestLikeness:
    def test_consented_real_person_unlabelled_real_footage(self, policy):
        assert lk.check_asset({"type": "video", "people": [{"name": "Rhea", "likeness_id": "L1"}]}, LREG, policy,
                              today="2026-11-19")

    @pytest.mark.parametrize("rec,msg", [({"consent": False}, "no consent"), ({"scope": ["social"]}, "doesn't cover"),
                                         ({"expires": "2026-01-01"}, "expired")])
    def test_bad_consent_records(self, rec, msg, policy):
        r = lk.check_asset({"type": "image", "people": [{"name": "Rhea", "likeness_id": "L1"}]}, [dict(LREG[0], **rec)],
                           policy, today="2026-11-19")
        assert not r and msg in r.violations[0]

    def test_unknown_person(self, policy):
        r = lk.check_asset({"type": "image", "people": [{"likeness_id": "Z"}]}, LREG, policy)
        assert not r and "Z's face or voice" in r.violations[0]

    @pytest.mark.parametrize("kind", ["image", "video", "audio"])
    def test_synthetic_media_needs_label(self, kind, policy):
        assert not lk.check_asset({"type": kind, "is_synthetic": True}, [], policy)

    @pytest.mark.parametrize("label", ["AI-generated", "Created with AI", "Digitally created", "Virtual influencer"])
    def test_labels_accepted(self, label, policy):
        assert lk.check_asset({"type": "image", "is_synthetic": True, "label": label}, [], policy)

    def test_audio_label_must_lead(self, policy):
        a = {"type": "audio", "is_synthetic": True, "label": "AI-generated voice"}
        assert not lk.check_asset(a, [], policy)
        assert lk.check_asset(dict(a, label_position="start"), [], policy)

    def test_text_needs_no_label_but_gets_a_note(self, policy):
        r = lk.check_asset({"type": "text", "is_synthetic": True}, [], policy)
        assert r and r.notes

    def test_virtual_influencer_needs_label(self, policy):
        assert not lk.check_asset({"type": "video", "virtual_influencer": True}, [], policy)

    def test_synthetic_endorser_reads_as_customer(self, policy):
        r = lk.check_asset({"type": "image", "is_synthetic": True, "label": "AI-generated", "endorses_product": True},
                           [], policy)
        assert not r and "virtual character" in r.violations[0]


class TestDarkPatterns:
    def test_clean_flow(self, policy):
        assert dp.check_flow({"elements": [{"kind": "addon", "preselected": False}, {"kind": "stock", "live": True},
                                           {"kind": "fee", "shown_at": "cart"}, {"kind": "prompt", "repeats_per_session": 2},
                                           {"kind": "content", "sponsored": True, "labelled": True},
                                           {"kind": "gate", "needed_for_purchase": True},
                                           {"kind": "choice", "decline_visible": True}],
                              "advertised_price": 499, "final_price": 548, "fees_disclosed_upfront": True,
                              "signup_steps": 2, "cancel_steps": 3, "auto_renew": True, "auto_renew_notice": True}, policy)

    @pytest.mark.parametrize("el,msg", [
        ({"kind": "addon", "label": "Insurance", "preselected": True}, "basket sneaking"),
        ({"kind": "countdown"}, "false urgency"),
        ({"kind": "stock", "live": False}, "isn't live"),
        ({"kind": "decline", "text": "I'd rather pay full price"}, "confirm shaming"),
        ({"kind": "fee", "label": "Handling", "shown_at": "payment"}, "drip pricing"),
        ({"kind": "content", "sponsored": True}, "disguised ad"),
        ({"kind": "prompt", "repeats_per_session": 5}, "nagging"),
        ({"kind": "consent", "text": "Untick if you don't want to not get offers"}, "trick question"),
        ({"kind": "gate", "requires": "app download", "needed_for_purchase": False}, "forced action"),
        ({"kind": "choice", "decline_visible": False}, "interface interference"),
    ])
    def test_each_pattern(self, el, msg, policy):
        r = dp.check_flow({"elements": [el]}, policy)
        assert not r and msg in r.violations[0]

    def test_price_and_subscription_traps(self, policy):
        r = dp.check_flow({"advertised_price": 499, "final_price": 548, "signup_steps": 1, "cancel_steps": 5,
                           "cancel_online": False, "auto_renew": True}, policy)
        joined = " | ".join(r.violations)
        for msg in ("advertised ₹499", "cancelling takes 5 steps", "cancelling isn't", "auto-renewal"):
            assert msg in joined

    def test_empty_spec(self, policy):
        assert dp.check_flow({}, policy)
