"""Block lines that are only true when results go well.

A match is ignored when a negation sits just before it ("we can't guarantee rankings"),
because saying what you won't promise is exactly the honest phrasing we want.
"""
from __future__ import annotations

import re

from .core import Verdict

NEGATION = re.compile(r"\b(can't|cannot|can not|won't|will not|don't|do not|never|no one|nobody|not|no)\b[^.!?]{0,40}$", re.IGNORECASE)


def check(text: str, policy: dict) -> Verdict:
    violations, spans = [], []
    for pat in policy["promise"]["banned"]:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            if NEGATION.search(text[max(0, m.start() - 60):m.start()]):
                continue
            if any(m.start() < e and s < m.end() for s, e in spans):
                continue  # overlaps a phrase already reported
            spans.append((m.start(), m.end()))
            violations.append(f"promise language: '{m.group(0)}'")
            break
    return Verdict.from_violations("promise_guard", violations)
