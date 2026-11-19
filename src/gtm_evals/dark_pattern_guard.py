"""Dark patterns in landing pages, checkouts and lifecycle flows.

Based on India's Guidelines for Prevention and Regulation of Dark Patterns, 2023 (CCPA), which name
13 patterns; this checks the ones a marketing or GTM flow can contain. A reading for engineers, not
legal advice. Text-level pressure (false urgency and scarcity in copy) is manipulation_guard's job;
this guard reads the *flow*.

spec = {"name": "checkout", "elements": [
          {"kind": "addon", "label": "Gift wrap ₹49", "preselected": True},
          {"kind": "countdown", "real_deadline": False},
          {"kind": "decline", "text": "No thanks, I don't like saving money"},
          {"kind": "fee", "label": "Convenience fee", "shown_at": "final_step"},
          {"kind": "content", "sponsored": True, "labelled": False},
          {"kind": "prompt", "repeats_per_session": 4},
          {"kind": "consent", "text": "Uncheck this box if you don't want to not receive offers"},
          {"kind": "gate", "requires": "app download", "needed_for_purchase": False}],
        "advertised_price": 499, "final_price": 548,
        "signup_steps": 1, "cancel_steps": 5, "cancel_online": False, "auto_renew_notice": False}
"""
from __future__ import annotations

import re

from .core import Verdict


def check_flow(spec: dict, policy: dict) -> Verdict:
    cfg = policy["dark_patterns"]
    v: list[str] = []
    for e in spec.get("elements") or []:
        k = e.get("kind")
        if k == "addon" and e.get("preselected"):
            v.append(f"basket sneaking: add-on '{e.get('label', '')}' is pre-selected")
        elif k == "countdown" and not e.get("real_deadline"):
            v.append("false urgency: countdown not tied to a real deadline")
        elif k == "stock" and not e.get("live"):
            v.append("false urgency: stock or viewer count isn't live")
        elif k == "decline" and any(re.search(p, e.get("text", ""), re.IGNORECASE) for p in cfg["confirm_shaming"]):
            v.append(f"confirm shaming: '{e.get('text')}'")
        elif k == "fee" and e.get("shown_at") in cfg["late_fee_steps"]:
            v.append(f"drip pricing: '{e.get('label', 'a fee')}' first shown at {e['shown_at']}")
        elif k == "content" and e.get("sponsored") and not e.get("labelled"):
            v.append("disguised ad: sponsored content isn't labelled as an ad")
        elif k == "prompt" and e.get("repeats_per_session", 0) > cfg["max_prompt_repeats"]:
            v.append(f"nagging: the same prompt shows {e['repeats_per_session']} times a session "
                     f"(max {cfg['max_prompt_repeats']})")
        elif k == "consent" and len(re.findall(cfg["negation_words"], e.get("text", ""), re.IGNORECASE)) >= 2:
            v.append(f"trick question: double negative in '{e.get('text')}'")
        elif k == "gate" and e.get("needed_for_purchase") is False:
            v.append(f"forced action: '{e.get('requires')}' required but not needed to buy")
        elif k == "choice" and e.get("decline_visible") is False:
            v.append("interface interference: the decline option is hidden or harder to see than accept")
    adv, fin = spec.get("advertised_price"), spec.get("final_price")
    if adv is not None and fin is not None and fin > adv and not spec.get("fees_disclosed_upfront"):
        v.append(f"bait and switch / drip pricing: advertised ₹{adv}, charged ₹{fin}")
    s, c = spec.get("signup_steps"), spec.get("cancel_steps")
    if s and c and c > s + cfg["max_extra_cancel_steps"]:
        v.append(f"subscription trap: cancelling takes {c} steps, signing up {s}")
    if spec.get("cancel_online") is False and spec.get("signup_online", True):
        v.append("subscription trap: signup is online but cancelling isn't")
    if spec.get("auto_renew") and not spec.get("auto_renew_notice"):
        v.append("SaaS billing: auto-renewal without notice before the charge")
    return Verdict.from_violations("dark_pattern_guard", v)
