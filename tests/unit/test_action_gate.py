"""ActionGate: R0–R3 evidence, kill switch, token budget."""
import pytest

from gtm_evals import ActionGate
from gtm_evals.core import Verdict

OK, BAD = Verdict("x", True), Verdict("y", False, ["nope"])


@pytest.fixture
def gate(policy):
    return ActionGate(policy)


@pytest.mark.parametrize("action,tier", [("draft", "R0"), ("crm_update", "R1"), ("send_single", "R2"),
                                         ("send_bulk", "R3"), ("brand_new_action", "R3")])
def test_tiers(gate, action, tier):
    assert gate.tier(action) == tier


def test_r0_needs_nothing(gate):
    assert gate.authorize("draft")


class TestEvidence:
    @pytest.mark.parametrize("checks", [None, []])
    def test_r1_needs_checks_that_ran(self, gate, checks):
        v = gate.authorize("crm_update", checks=checks)
        assert not v and "none ran" in v.violations[0]

    def test_failed_check_reported(self, gate):
        v = gate.authorize("crm_update", checks=[OK, BAD])
        assert not v and "check failed: y: nope" in v.violations

    @pytest.mark.parametrize("ev", [None, False, "yes", 1])
    def test_r2_evaluator_must_be_exactly_true(self, gate, ev):
        assert not gate.authorize("send_single", checks=[OK], evaluator_passed=ev)

    @pytest.mark.parametrize("approval", [None, "", "   "])
    def test_r3_needs_real_approval_id(self, gate, approval):
        assert not gate.authorize("send_bulk", checks=[OK], evaluator_passed=True, approval_id=approval, canary_done=True)

    @pytest.mark.parametrize("canary", [None, False, "done"])
    def test_r3_canary_must_be_true(self, gate, canary):
        assert not gate.authorize("send_bulk", checks=[OK], evaluator_passed=True, approval_id="A1", canary_done=canary)

    def test_r3_full_evidence(self, gate):
        assert gate.authorize("send_bulk", checks=[OK], evaluator_passed=True, approval_id="A1", canary_done=True)

    def test_unknown_action_treated_as_r3(self, gate):
        assert not gate.authorize("brand_new_action", checks=[OK], evaluator_passed=True)


class TestStops:
    def test_kill_switch_stops_r1_to_r3(self, gate, policy, monkeypatch):
        monkeypatch.setenv(policy["action_gate"]["kill_switch_env"], "1")
        assert "kill switch is on" in gate.authorize("crm_update", checks=[OK]).violations
        assert gate.authorize("draft")   # R0 still allowed

    def test_kill_switch_env_from_profile(self, clyve, monkeypatch):
        monkeypatch.setenv("CLYVE_KILL_SWITCH", "1")
        assert not ActionGate(clyve).authorize("crm_update", checks=[OK])

    def test_token_budget(self, gate, policy):
        gate.spend(policy["action_gate"]["max_tokens_per_run"] + 1)
        assert any("token budget" in x for x in gate.authorize("crm_update", checks=[OK]).violations)

    def test_budget_accumulates(self, gate, policy):
        half = policy["action_gate"]["max_tokens_per_run"] // 2
        gate.spend(half); gate.spend(half)
        assert gate.authorize("crm_update", checks=[OK])
        gate.spend(1)
        assert not gate.authorize("crm_update", checks=[OK])
