"""Block lines that are only true when results go well."""
from __future__ import annotations

import re

from .core import Verdict


def check(text: str, policy: dict) -> Verdict:
    violations = []
    for pat in policy["promise"]["banned"]:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            violations.append(f"promise language: '{m.group(0)}'")
    return Verdict.from_violations("promise_guard", violations)
