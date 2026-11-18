"""claims_gate: every number traceable, every ₹ figure stamped, ASSUMED figures are ranges."""
import pytest

from gtm_evals import claims_gate


def ok(text, register, policy):
    return claims_gate.check(text, register, policy)


class TestNumbers:
    @pytest.mark.parametrize("text", ["4.6★ from 2,140 reviews", "Rated 4.6 by 2140 buyers", "4.6/5 stars"])
    def test_proven_numbers_pass(self, text, register, policy):
        assert ok(text, register, policy)

    def test_unknown_number_fails(self, register, policy):
        v = ok("Trusted by 50,000 kitchens", register, policy)
        assert not v and "unsourced number '50,000'" in v.violations[0]

    @pytest.mark.parametrize("text,status", [("40% come back", "gettable"), ("in 12 cities", "none")])
    def test_unproven_status_named(self, text, status, register, policy):
        v = ok(text, register, policy)
        assert not v and f"status is '{status}'" in v.violations[0]

    @pytest.mark.parametrize("text", ["Founded in 2019.", "Day 30 re-score", "Step 1, step 2, step 3"])
    def test_years_and_step_counts_ignored(self, text, register, policy):
        assert ok(text, register, policy)

    def test_year_outside_range_is_a_number(self, register, policy):
        assert not ok("since 1850", register, policy)

    def test_empty_register_blocks_any_number(self, policy):
        assert not ok("we did 7 launches", [], policy)

    def test_text_without_numbers_passes_empty_register(self, policy):
        assert ok("Spices ground fresh every week.", [], policy)

    @pytest.mark.parametrize("text", ["fifty thousand kitchens", "two lakh orders", "double the reviews"])
    def test_number_words_blocked(self, text, register, policy):
        v = ok(text, register, policy)
        assert not v and "written as words" in v.violations[0]

    def test_number_words_can_be_disabled(self, register, policy):
        policy["claims"]["block_number_words"] = False
        assert ok("fifty thousand kitchens", register, policy)

    def test_each_bad_number_reported(self, register, policy):
        assert len(ok("50,000 kitchens in 9 states", register, policy).violations) == 2


class TestRupees:
    def test_unstamped_rupee_fails(self, register, policy):
        v = ok("Gap of ₹2–4 lakh a month", register, policy)
        assert not v and "no confidence stamp" in v.violations[0]

    def test_assumed_point_fails(self, register, policy):
        v = ok("Gap of ₹3 lakh a month (ASSUMED · ±1)", register, policy)
        assert not v and "use a range" in v.violations[0]

    @pytest.mark.parametrize("text", ["Gap of ₹2–4 lakh a month (ASSUMED · ±1)", "₹2-4 lakh (ASSUMED · ±1)",
                                      "₹2 to 4 lakh (ASSUMED · ±1)", "Moved ₹1.2 lakh (CAPTURED)",
                                      "₹40,000 spent (OBSERVED)"])
    def test_stamped_rupees_pass(self, text, register, policy):
        assert ok(text, register, policy)

    @pytest.mark.parametrize("text", ["Rs 3 lakh (ASSUMED · ±1)", "INR 3 lakh (ASSUMED · ±1)"])
    def test_rs_and_inr_spellings_treated_as_rupees(self, text, register, policy):
        assert not ok(text, register, policy)   # point estimate under ASSUMED

    def test_stamp_too_far_away_doesnt_count(self, register, policy):
        assert not ok("₹2–4 lakh" + " filler" * 40 + " (ASSUMED · ±1)", register, policy)

    def test_point_allowed_when_range_rule_off(self, register, policy):
        policy["claims"]["assumed_requires_range"] = False
        assert ok("₹3 lakh (ASSUMED · ±1)", register, policy)
