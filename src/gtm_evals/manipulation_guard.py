"""Ethics: flag pressure tactics (false urgency, false scarcity, guilt, fear) for a human to verify.

These lines are only acceptable if true and sourced, which code can't verify, so the guard
escalates rather than blocks. Policy: src/gtm_evals/data/default.yaml → manipulation.patterns
"""
from __future__ import annotations

import re

from .core import Verdict


def check(text: str, policy: dict) -> Verdict:
    hits = []
    for pat in policy.get("manipulation", {}).get("patterns", []):
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            hits.append(f"pressure tactic — verify it is true and sourced: '{m.group(0)}'")
    return Verdict.from_violations("manipulation_guard", hits, escalate=bool(hits))
