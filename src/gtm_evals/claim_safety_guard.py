"""Claim safety for regulated categories: a rule-based first pass before the claim_safety judge.

Food, supplements, health, personal care and baby products can't make some claims at all
(a food that "cures" anything), and can make others only with proof the approver has seen
("clinically proven", "No. 1 in India"). Comparative claims about a named competitor need proof
in any category.

    check(text, category, policy)  →  blocks prohibited claims; escalates claims that need proof

Prohibited → violation (don't publish). Needs substantiation → escalate (a human checks the proof).
Patterns are a conservative starting point drawn from the ASCI code and FSSAI advertising rules;
they are not legal advice. Review them against current rules for each category and market.
"""
from __future__ import annotations

import re

from .core import Verdict


def _regulated(category: str | None, cfg: dict) -> bool:
    cat = re.sub(r"[-_/]+", " ", (category or "").lower())
    return any(c in cat for c in cfg["regulated_categories"])


def check(text: str, category: str | None, policy: dict, competitors: list[str] | None = None) -> Verdict:
    cfg = policy["claim_safety"]
    v: list[str] = []
    needs_proof: list[str] = []
    if _regulated(category, cfg):
        for pat in cfg["prohibited"]:
            for m in re.finditer(pat, text, flags=re.IGNORECASE):
                v.append(f"prohibited for '{category}': '{m.group(0)}' — remove it")
        for pat in cfg["needs_substantiation"]:
            for m in re.finditer(pat, text, flags=re.IGNORECASE):
                needs_proof.append(m.group(0))
    for pat in cfg["comparative"]:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            needs_proof.append(m.group(0))
    for name in competitors or []:
        if re.search(rf"\b{re.escape(name)}\b", text, flags=re.IGNORECASE):
            needs_proof.append(f"names competitor {name}")
    seen = []
    for x in needs_proof:
        if x.lower() not in (s.lower() for s in seen):
            seen.append(x)
    v += [f"needs proof the approver has seen: '{x}'" for x in seen]
    return Verdict.from_violations("claim_safety_guard", v, escalate=bool(seen))
