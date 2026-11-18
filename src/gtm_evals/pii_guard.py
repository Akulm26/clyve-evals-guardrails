"""Redact personal data before it reaches a model or a log.

Covers emails, Indian mobile numbers, PAN, Aadhaar-shaped numbers. Returns redacted text
plus a local map so values can be restored *after* the model call, outside the model.
"""
from __future__ import annotations

import re

from .core import Verdict

PATTERNS = {
    "EMAIL": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "EMAIL_OBFUSCATED": re.compile(r"[\w.+-]+\s*(\[at\]|\(at\)|\{at\})\s*[\w-]+\s*(\[dot\]|\(dot\)|\{dot\})\s*\w+", re.IGNORECASE),
    # 4-4-4 with spaces or hyphens always; 12 straight digits only when labelled, so order IDs pass.
    "AADHAAR": re.compile(r"(?<!\d)\d{4}[\s-]\d{4}[\s-]\d{4}(?!\d)|(?i:aadhaar|aadhar|uid)\D{0,15}(?<!\d)\d{12}(?!\d)"),
    "PHONE_IN": re.compile(r"(?<!\d)(?:\+91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"),
    "PAN": re.compile(r"\b[A-Za-z]{5}\d{4}[A-Za-z]\b"),
}


def redact(text: str) -> tuple[str, dict[str, str]]:
    mapping: dict[str, str] = {}
    counter = 0
    for label, rx in PATTERNS.items():
        def _sub(m: re.Match) -> str:
            nonlocal counter
            counter += 1
            token = f"<{label}_{counter}>"
            mapping[token] = m.group(0)
            return token
        text = rx.sub(_sub, text)
    return text, mapping


def restore(text: str, mapping: dict[str, str]) -> str:
    for token, value in mapping.items():
        text = text.replace(token, value)
    return text


def check(text: str) -> Verdict:
    """Fails if any PII is present (use on logs, prompts, exports)."""
    found = [label for label, rx in PATTERNS.items() if rx.search(text)]
    return Verdict.from_violations("pii_guard", [f"contains {f}" for f in found])
