"""gtm-evals — evals and guardrails for AI GTM engineering.

    from gtm_evals import load_policy, claims_gate, outreach_guard, ActionGate

    policy = load_policy()                       # bundled defaults (+ ./gtm-evals.yaml if present)
    v = claims_gate.check(draft, register, policy)
    if not v:
        print(v.violations)

Every guard returns a Verdict: truthy when it passes, with .violations and .escalate.
"""
from . import (  # noqa: F401
    automation_guard,
    claims_gate,
    injection_guard,
    manipulation_guard,
    outreach_guard,
    pii_guard,
    promise_guard,
    visibility_stats,
)
from .action_gate import ActionGate
from .core import Verdict, combine, list_profiles, load_policy

__version__ = "0.1.0"

GUARDS = {
    "claims": claims_gate, "promise": promise_guard, "pii": pii_guard, "injection": injection_guard,
    "outreach": outreach_guard, "automation": automation_guard, "manipulation": manipulation_guard,
}

__all__ = ["ActionGate", "Verdict", "combine", "load_policy", "list_profiles", "GUARDS", "__version__",
           "claims_gate", "promise_guard", "pii_guard", "injection_guard", "outreach_guard",
           "automation_guard", "manipulation_guard", "visibility_stats"]
