"""claim_safety_guard: prohibited claims block, claims needing proof escalate, only in regulated categories."""
import pytest

from gtm_evals import claim_safety_guard as cs


@pytest.mark.parametrize("text", ["Cures colds", "heals your gut", "treats diabetes naturally", "helps prevent high blood pressure",
                                  "anti-cancer spices", "no side effects", "lose 5 kg in a month"])
def test_prohibited_in_food(text, policy):
    v = cs.check(text, "food", policy)
    assert not v and "prohibited for 'food'" in v.violations[0] and not v.escalate


@pytest.mark.parametrize("text", ["Clinically proven", "dermatologist-tested", "immunity booster", "100% natural",
                                  "chemical-free", "sugar free", "detox blend", "lab tested"])
def test_needs_proof_escalates(text, policy):
    v = cs.check(text, "skincare", policy)
    assert not v and v.escalate and "needs proof" in v.violations[0]


@pytest.mark.parametrize("category", ["Food", "spice blends", "ayurvedic skincare", "Personal-Care", "baby_food", "D2C beverage"])
def test_regulated_category_detection(category, policy):
    assert not cs.check("clinically proven", category, policy)


@pytest.mark.parametrize("category", ["saas", "apparel", None, ""])
def test_unregulated_categories_skip_health_rules(category, policy):
    assert cs.check("Clinically proven, cures boredom", category, policy)


@pytest.mark.parametrize("text", ["India's best masala", "No. 1 brand in India", "best-selling chai", "healthier than other brands"])
def test_comparatives_need_proof_in_any_category(text, policy):
    v = cs.check(text, "apparel", policy)
    assert not v and v.escalate


def test_named_competitor(policy):
    v = cs.check("Tastier than MDH", "saas", policy, competitors=["MDH", "Everest"])
    assert not v and "names competitor MDH" in v.violations[0]
    assert cs.check("Tastier every week", "saas", policy, competitors=["MDH"])


def test_duplicates_reported_once(policy):
    assert len(cs.check("Clinically proven. CLINICALLY PROVEN.", "food", policy).violations) == 1


def test_plain_facts_pass(policy):
    assert cs.check("Stone-ground every week in Ludhiana. Rated 4.6 by 2,140 buyers.", "spice", policy)
