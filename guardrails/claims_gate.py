"""Every number must trace to a proven claim. Every ₹ figure must carry a stamp.

Claims register rows look like:
    {"id": "C1", "claim": "4.6★ average across 2,140 reviews", "values": ["4.6", "2140"],
     "status": "have", "source": "https://..."}
status ∈ {have, gettable, none}. Only `have` may appear in output.
"""
from __future__ import annotations

import re

from .core import Verdict

_UNIT = r"(?:\s?(?:k|K|L|lakh|lakhs|cr|crore|Cr))?"
_AMOUNT = r"[\d][\d,]*(?:\.\d+)?" + _UNIT
RUPEE_RE = re.compile(r"₹\s?" + _AMOUNT + r"(?:\s?(?:–|-|to)\s?₹?\s?" + _AMOUNT + r")?")
NUMBER_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w])")


def _norm(n: str) -> str:
    n = n.replace(",", "")
    if "." in n:
        n = n.rstrip("0").rstrip(".")
    return n


def _register_index(register: list[dict]) -> dict[str, str]:
    idx: dict[str, str] = {}
    rank = {"have": 3, "gettable": 2, "none": 1}
    for row in register:
        for v in row.get("values", []):
            key = _norm(str(v))
            if rank.get(row.get("status", "none"), 0) > rank.get(idx.get(key, ""), 0):
                idx[key] = row.get("status", "none")
    return idx


def check(text: str, register: list[dict], policy: dict) -> Verdict:
    cfg = policy["claims"]
    violations: list[str] = []
    idx = _register_index(register)
    lo, hi = cfg["ignore_years"]
    ignore = {_norm(x) for x in cfg["ignore_numbers"]}

    # 1. Every number traceable to a `have` claim.
    for m in NUMBER_RE.finditer(text):
        raw = m.group(0)
        n = _norm(raw)
        if n in ignore:
            continue
        if re.fullmatch(r"\d{4}", n) and lo <= int(n) <= hi:
            continue
        # numbers inside a stamped ₹ estimate are checked by rule 2, not the register
        if _inside_rupee(text, m.start()):
            continue
        status = idx.get(n)
        if status is None:
            violations.append(f"unsourced number '{raw}' — not in claims register")
        elif status != "have":
            violations.append(f"unproven claim '{raw}' — register status is '{status}'")

    # 1b. Quantities written as words ("fifty thousand kitchens") can't be traced either.
    if cfg.get("block_number_words"):
        for w in cfg.get("number_words", []):
            for m in re.finditer(rf"\b{re.escape(w)}\b", text, flags=re.IGNORECASE):
                if _inside_rupee(text, m.start()):
                    continue  # "₹2–4 lakh" — a unit inside a stamped figure, checked by rule 2
                violations.append(f"quantity written as words '{m.group(0)}' — use a register figure")

    # 2. Every ₹ figure stamped; ASSUMED figures must be ranges.
    stamps = cfg["stamps"]
    win = cfg["stamp_window_chars"]
    for m in RUPEE_RE.finditer(text):
        fig = m.group(0).strip()
        window = text[max(0, m.start() - win): m.end() + win]
        found = [s for s in stamps if s in window]
        if not found:
            violations.append(f"₹ figure '{fig}' has no confidence stamp")
            continue
        is_range = bool(re.search(r"(–|-|to)", fig))
        if cfg.get("assumed_requires_range") and any(s.startswith("ASSUMED") for s in found) and not is_range:
            violations.append(f"₹ figure '{fig}' is ASSUMED but shown as a point — use a range")

    return Verdict.from_violations("claims_gate", violations)


def _inside_rupee(text: str, pos: int) -> bool:
    return any(m.start() <= pos < m.end() for m in RUPEE_RE.finditer(text))
