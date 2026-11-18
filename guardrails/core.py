from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_POLICY = Path(__file__).resolve().parent.parent / "policies" / "clyve_policy.yaml"


@dataclass
class Verdict:
    guard: str
    passed: bool
    violations: list[str] = field(default_factory=list)
    escalate: bool = False

    @classmethod
    def from_violations(cls, guard: str, violations: list[str], escalate: bool = False) -> "Verdict":
        return cls(guard=guard, passed=not violations and not escalate, violations=violations, escalate=escalate)

    def __bool__(self) -> bool:  # `if verdict:` reads as "did it pass"
        return self.passed


def load_policy(path: str | Path | None = None) -> dict:
    import yaml  # only dependency; guards themselves take plain dicts

    with open(path or DEFAULT_POLICY, encoding="utf-8") as f:
        return yaml.safe_load(f)


def combine(*verdicts: Verdict) -> Verdict:
    violations = [f"[{v.guard}] {x}" for v in verdicts for x in v.violations]
    return Verdict(
        guard="combined",
        passed=all(v.passed for v in verdicts),
        violations=violations,
        escalate=any(v.escalate for v in verdicts),
    )
