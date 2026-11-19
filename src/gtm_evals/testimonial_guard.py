"""Testimonials, reviews and social proof must be real, consented and quoted as given.

Rules this encodes (as a reading for engineers, not legal advice): ASCI's guidelines bar fabricated
endorsements even when labelled; the US FTC rule on fake reviews (16 CFR 465, in force 21 Oct 2024)
bars AI-written or insider reviews presented as independent and fake social-proof indicators.

register = [{"id": "T1", "quote": "Best haldi I've bought in years.", "author": "Rhea, Ludhiana",
             "source": "https://…/reviews/123", "date": "2026-09-02", "consent": True,
             "ai_generated": False, "insider": False}]

    check(text, register, policy)   →  every quote with an attribution must match a registered entry;
                                       reworded quotes escalate; social-proof counters need a live source
"""
from __future__ import annotations

import re

from .core import Verdict

# Double or curly quotes only: single quotes clash with apostrophes ("I've").
_QUOTE = re.compile(r"[\"“”]([^\"“”]{12,400})[\"“”]\s*(?:[—–-]{1,2}|,\s*says|said)?\s*([A-Z][\w.]+(?:[ ,][A-Z]?[\w.]+){0,4})?")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", re.sub(r"\s+", " ", (s or "").lower())).strip()


def _tok(s: str) -> set[str]:
    return {w for w in _norm(s).split() if len(w) > 2}


def quotes(text: str) -> list[tuple[str, str | None]]:
    """(quote, attribution or None) pairs that look like testimonials: at least 3 words in quotation marks."""
    out = []
    for m in _QUOTE.finditer(text or ""):
        q = m.group(1).strip()
        if len(q.split()) >= 3:
            out.append((q, (m.group(2) or "").strip() or None))
    return out


def check(text: str, register: list[dict], policy: dict) -> Verdict:
    cfg = policy["testimonial"]
    v: list[str] = []
    escalate = False
    reg = [r for r in register or []]
    for q, who in quotes(text):
        nq = _norm(q)
        exact = next((r for r in reg if _norm(r.get("quote", "")) == nq), None)
        if exact:
            if cfg.get("require_consent", True) and not exact.get("consent"):
                v.append(f"testimonial {exact.get('id')} has no consent to publish: '{q[:60]}'")
            if exact.get("ai_generated"):
                v.append(f"testimonial {exact.get('id')} was AI-generated: it can't be shown as a customer's words")
            if exact.get("insider") and not re.search(cfg["insider_disclosure"], text, re.IGNORECASE):
                v.append(f"testimonial {exact.get('id')} is from an insider (staff, family, paid) and isn't disclosed")
            if not exact.get("source"):
                v.append(f"testimonial {exact.get('id')} has no source on record")
            continue
        near = max(reg, key=lambda r: len(_tok(q) & _tok(r.get("quote", ""))) / max(len(_tok(q)), 1), default=None)
        overlap = len(_tok(q) & _tok(near.get("quote", ""))) / max(len(_tok(q)), 1) if near else 0
        if overlap >= cfg["reworded_overlap"]:
            escalate = True
            v.append(f"reworded testimonial (closest: {near.get('id')}): use the registered wording exactly: '{q[:60]}'")
        elif who or re.search(cfg["testimonial_cues"], text, re.IGNORECASE):
            v.append(f"testimonial not in the register (no source, no consent): '{q[:60]}'"
                     + (f" — {who}" if who else ""))
    for pat in cfg["social_proof_patterns"]:
        for m in re.finditer(pat, text or "", re.IGNORECASE):
            v.append(f"social-proof counter needs a live, sourced number: '{m.group(0)}'")
    for pat in cfg["star_patterns"]:
        if re.search(pat, text or "") and not any(r.get("kind") == "rating" for r in reg):
            escalate = True
            v.append("star rating shown with no registered rating source")
            break
    return Verdict.from_violations("testimonial_guard", v, escalate=escalate)
