from __future__ import annotations

import copy
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path


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

    def to_dict(self) -> dict:
        return {"guard": self.guard, "passed": self.passed, "violations": self.violations, "escalate": self.escalate}


def _data(*parts: str) -> str:
    return resources.files("gtm_evals").joinpath("data", *parts).read_text(encoding="utf-8")


def _merge(base: dict, over: dict) -> dict:
    """Deep-merge dicts; lists and scalars in `over` replace those in `base`."""
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def load_policy(path: str | Path | None = None, profile: str | None = None) -> dict:
    """Bundled defaults ← optional profile (e.g. "clyve") ← optional user file (e.g. gtm-evals.yaml).

    If `path` is None and ./gtm-evals.yaml exists, it is used automatically.
    """
    import yaml

    policy = yaml.safe_load(_data("default.yaml"))
    user = None
    if path is None and Path("gtm-evals.yaml").exists():
        path = "gtm-evals.yaml"
    if path:
        user = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        profile = profile or user.pop("profile", None)
    if profile:
        policy = _merge(policy, yaml.safe_load(_data("profiles", f"{profile}.yaml")) or {})
    if user:
        policy = _merge(policy, user)
    return policy


def list_profiles() -> list[str]:
    return sorted(p.name[:-5] for p in resources.files("gtm_evals").joinpath("data", "profiles").iterdir() if p.name.endswith(".yaml"))


def combine(*verdicts: Verdict) -> Verdict:
    violations = [f"[{v.guard}] {x}" for v in verdicts for x in v.violations]
    return Verdict(
        guard="combined",
        passed=all(v.passed for v in verdicts),
        violations=violations,
        escalate=any(v.escalate for v in verdicts),
    )
