"""evidence: sample size from the claim, strata, Cohen's kappa, label-sheet agreement."""
import pytest

from gtm_evals.evidence import agreement, cohen_kappa, required_cases, strata_shortfall


@pytest.mark.parametrize("rate,margin,pop,n", [(0.9, 0.05, None, 139), (0.5, 0.05, None, 385), (0.5, 0.05, 2000, 323),
                                               (0.9, 0.10, None, 35), (0.5, 0.10, None, 97), (0.85, 0.10, None, 49)])
def test_required_cases(rate, margin, pop, n):
    assert required_cases(rate, margin, population=pop) == n


def test_higher_confidence_needs_more():
    assert required_cases(0.5, 0.1, confidence=0.99) > required_cases(0.5, 0.1)


@pytest.mark.parametrize("bad", [dict(margin=0), dict(margin=1.2), dict(rate=-0.1), dict(confidence=1)])
def test_bad_inputs(bad):
    with pytest.raises(ValueError):
        required_cases(**{"rate": 0.5, "margin": 0.1, **bad})


def test_extreme_rates_dont_divide_by_zero():
    assert required_cases(1.0, 0.1) >= 1 and required_cases(0.0, 0.1) >= 1


class TestStrata:
    SHARES = {"standard": 0.40, "ambiguous": 0.35, "adversarial": 0.25}

    def test_shortfall_per_stratum(self):
        rows = [{"stratum": "standard"}] * 40 + [{"stratum": "ambiguous"}] * 10
        assert strata_shortfall(rows, 97, self.SHARES) == {"ambiguous": 24, "adversarial": 25}

    def test_missing_stratum_counts_as_standard(self):
        assert "standard" not in strata_shortfall([{}] * 39, 97, self.SHARES)

    def test_enough_everywhere(self):
        rows = [{"stratum": s} for s, n in (("standard", 39), ("ambiguous", 34), ("adversarial", 25)) for _ in range(n)]
        assert strata_shortfall(rows, 97, self.SHARES) == {}


class TestKappa:
    def test_perfect(self):
        assert cohen_kappa(["pass", "fail"] * 5, ["pass", "fail"] * 5) == 1.0

    def test_chance_level_is_zero(self):
        assert cohen_kappa(["pass", "pass", "fail", "fail"], ["pass", "fail", "pass", "fail"]) == 0.0

    def test_worked_example(self):
        # 30 items: A = 20 pass / 10 fail; B = 19 pass / 11 fail, agreeing on 27 → po = 0.9,
        # pe = (20·19 + 10·11) / 900 = 0.544, κ = (0.9 − 0.544) / (1 − 0.544) = 0.780
        a = ["pass"] * 20 + ["fail"] * 10
        b = ["pass"] * 18 + ["fail"] * 2 + ["fail"] * 9 + ["pass"]
        assert round(cohen_kappa(a, b), 3) == 0.780

    def test_same_single_label_everywhere(self):
        assert cohen_kappa(["pass"] * 5, ["pass"] * 5) == 1.0

    def test_lengths_must_match(self):
        with pytest.raises(ValueError):
            cohen_kappa(["pass"], [])

    def test_empty(self):
        assert cohen_kappa([], []) == 0.0


class TestAgreement:
    def test_from_rows(self):
        rows = [{"id": "a", "human_verdict": "pass", "human_verdict_b": "pass"},
                {"id": "b", "human_verdict": "fail", "human_verdict_b": "pass"},
                {"id": "c", "human_verdict": "fail", "human_verdict_b": "fail"},
                {"id": "d", "human_verdict": "pass", "human_verdict_b": None}]
        r = agreement(rows)
        assert r["both_labelled"] == 3 and r["agreed"] == ["a", "c"] and r["disagree"] == ["b"] and r["second_labeller"]

    def test_no_second_labeller(self):
        r = agreement([{"id": "a", "human_verdict": "pass"}])
        assert not r["second_labeller"] and r["kappa"] == 0.0

    def test_case_and_whitespace(self):
        assert agreement([{"id": "a", "human_verdict": " PASS", "human_verdict_b": "pass "}])["agreed"] == ["a"]
