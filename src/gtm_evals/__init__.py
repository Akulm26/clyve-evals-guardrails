"""gtm-evals — evals and guardrails for AI in marketing automation, GTM engineering, ContentOps and AI SEO.

    from gtm_evals import load_policy, claims_gate, outreach_guard, ActionGate

    policy = load_policy()                       # bundled defaults (+ ./gtm-evals.yaml if present)
    v = claims_gate.check(draft, register, policy)
    if not v:
        print(v.violations)

Every guard returns a Verdict: truthy when it passes, with .violations and .escalate.
"""
from . import (  # noqa: F401
    ai_seo_guard,
    automation_guard,
    claim_safety_guard,
    claims_gate,
    dark_pattern_guard,
    dpdp_guard,
    enrichment_guard,
    evidence,
    injection_guard,
    likeness_guard,
    manipulation_guard,
    outreach_guard,
    pii_guard,
    promise_guard,
    testimonial_guard,
    visibility_stats,
)
from .action_gate import ActionGate
from .core import Verdict, combine, list_profiles, load_policy

__version__ = "0.1.1"

GUARDS = {
    "claims": claims_gate, "promise": promise_guard, "pii": pii_guard, "injection": injection_guard,
    "outreach": outreach_guard, "automation": automation_guard, "manipulation": manipulation_guard,
    "claim_safety": claim_safety_guard, "dpdp": dpdp_guard, "testimonial": testimonial_guard, "likeness": likeness_guard, "dark_pattern": dark_pattern_guard, "enrichment": enrichment_guard, "ai_seo": ai_seo_guard,
}

__all__ = ["ActionGate", "Verdict", "combine", "load_policy", "list_profiles", "GUARDS", "__version__",
           "claims_gate", "promise_guard", "pii_guard", "injection_guard", "outreach_guard",
           "automation_guard", "manipulation_guard", "visibility_stats",
           "ai_seo_guard", "claim_safety_guard", "enrichment_guard", "dpdp_guard",
           "testimonial_guard", "likeness_guard", "dark_pattern_guard", "evidence"]
