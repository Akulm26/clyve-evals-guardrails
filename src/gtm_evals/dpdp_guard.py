"""India's Digital Personal Data Protection Act 2023 and DPDP Rules 2025: the parts a marketing or
GTM automation touches.

    check_campaign(campaign, policy)   children's data: verifiable parental consent, no tracking or
                                       behavioural targeting directed at children (DPDP s.9)
    check_notice(text, policy)         a consent notice says what's collected, why, how to withdraw,
                                       who to contact, and that a complaint can go to the Data Protection Board
    check_contact(contact, policy)     each contact carries the consent record that proves it (an ID,
                                       and the consent manager's ID when one was used)

campaign = {"category": "kids nutrition", "audience": {"may_include_minors": True, "min_age": 13},
            "targeting": {"behavioural": True, "segments": ["recent browsers"]},
            "parental_consent_records": False}

This encodes a reading of the Act and Rules for engineers; it isn't legal advice. Several duties apply
from dates set in the Rules: check the current schedule before relying on any of them.
"""
from __future__ import annotations

import re

from .core import Verdict


def _cat(s: str | None) -> str:
    return re.sub(r"[-_/]+", " ", (s or "").lower())


def may_include_minors(campaign: dict, policy: dict) -> bool:
    cfg = policy["dpdp"]
    aud = campaign.get("audience") or {}
    if aud.get("may_include_minors"):
        return True
    if isinstance(aud.get("min_age"), (int, float)) and aud["min_age"] < cfg["adult_age"]:
        return True
    return any(k in _cat(campaign.get("category")) for k in cfg["child_categories"])


def check_campaign(campaign: dict, policy: dict) -> Verdict:
    cfg = policy["dpdp"]
    if not may_include_minors(campaign, policy):
        return Verdict.from_violations("dpdp_guard", [])
    v: list[str] = []
    t = campaign.get("targeting") or {}
    if t.get("behavioural") or any(re.search(p, s, re.I) for s in t.get("segments", []) for p in cfg["behavioural_segment_patterns"]):
        v.append("behavioural targeting where the audience may include children (DPDP s.9: no tracking, "
                 "behavioural monitoring or targeted ads directed at children)")
    if campaign.get("processes_child_data", True) and not campaign.get("parental_consent_records"):
        v.append("children's data processed without verifiable parental consent records (DPDP s.9)")
    return Verdict.from_violations("dpdp_guard", v,
                                   notes=["audience may include under-18s: keep targeting contextual, not behavioural"])


def check_notice(text: str, policy: dict) -> Verdict:
    """A consent notice must be readable on its own (DPDP s.5 and the Rules' notice requirements)."""
    low = (text or "").lower()
    v = [f"notice doesn't say {what}" for what, pats in policy["dpdp"]["notice_must_cover"].items()
         if not any(re.search(p, low) for p in pats)]
    return Verdict.from_violations("dpdp_guard", v)


def check_contact(contact: dict, policy: dict) -> Verdict:
    cfg = policy["dpdp"]
    v: list[str] = []
    if cfg.get("require_consent_record"):
        rec = contact.get("consent_record") or {}
        if not rec.get("id"):
            v.append("no consent record ID for this contact (DPDP: consent must be provable)")
        if rec.get("via_consent_manager") and not rec.get("consent_manager_id"):
            v.append("consent came through a consent manager but its ID isn't stored")
    return Verdict.from_violations("dpdp_guard", v)
