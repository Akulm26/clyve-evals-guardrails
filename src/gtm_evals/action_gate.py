"""The last gate before anything touches the outside world.

It checks the *action payload*, not what the agent said it would do.

    gate = ActionGate(policy)
    verdict = gate.authorize("send_bulk", checks=[v1, v2], evaluator_passed=True,
                             approval_id="AK-2026-11-18-03", canary_done=False)
"""
from __future__ import annotations

import os

from .core import Verdict


class ActionGate:
    def __init__(self, policy: dict):
        self.cfg = policy["action_gate"]
        self.tokens_used = 0
        self.recent: list[bool] = []   # guard outcomes, newest last (circuit breaker)

    def record(self, verdict: Verdict) -> None:
        """Feed every guard verdict here; the breaker trips when too many recent ones failed."""
        self.recent.append(bool(verdict.passed))
        self.recent = self.recent[-self.cfg.get("circuit_breaker", {}).get("window", 50):]

    def breaker_open(self) -> bool:
        cb = self.cfg.get("circuit_breaker") or {}
        if len(self.recent) < cb.get("min_items", 10):
            return False
        return self.recent.count(False) / len(self.recent) > cb.get("max_fail_rate", 0.2)

    def tier(self, action: str) -> str:
        # Unknown actions get the strictest tier. Demote only with evidence.
        return self.cfg["action_tiers"].get(action, "R3")

    def spend(self, tokens: int) -> None:
        self.tokens_used += tokens

    def authorize(self, action: str, checks: list[Verdict] | None = None, evaluator_passed: bool | None = None,
                  approval_id: str | None = None, canary_done: bool | None = None) -> Verdict:
        tier = self.tier(action)
        req = self.cfg["tiers"][tier]
        v: list[str] = []

        if os.environ.get(self.cfg["kill_switch_env"]) and tier != "R0":
            v.append("kill switch is on")
        if tier != "R0" and self.breaker_open():
            v.append(f"circuit breaker open: guards failed on {self.recent.count(False)} of the last {len(self.recent)} items")
        if self.tokens_used > self.cfg["max_tokens_per_run"]:
            v.append(f"token budget exceeded ({self.tokens_used})")
        if req["checks"]:
            if not checks:  # None or [] — either way, nothing actually ran
                v.append(f"{tier} needs deterministic checks; none ran")
            v += [f"check failed: {c.guard}: {'; '.join(c.violations) or 'escalate'}" for c in (checks or []) if not c.passed]
        if req["evaluator"] and evaluator_passed is not True:
            v.append(f"{tier} needs an evaluator pass")
        if req["human"] and not (approval_id or "").strip():
            v.append(f"{tier} needs a human approval ID")
        if req["canary"] and canary_done is not True:
            v.append(f"{tier} needs a canary run first (send to 5%, check, then continue)")

        return Verdict.from_violations(f"action_gate:{tier}", v)
