"""Checks for one outbound message (teardown email, DM, InMail, follow-up).

message = {
  "channel": "email" | "whatsapp" | "sms" | "instagram_dm" | "inmail",
  "body": str,
  "claims_about_lead": [str, ...],   # every specific fact the message states about the lead
  "inbox": "akul@clyve.io",
}
lead = {
  "email": str, "phone": str, "category": str, "stage": "prospect" | "audit" | ...,
  "lawful_basis": "legitimate_interest" | "consent" | None,
  "optin_channels": [..],
  "signals": [{"fact": str, "source_url": str, "date": "YYYY-MM-DD"}],
}
context = {"today": "YYYY-MM-DD", "suppression": set(), "sent_today_by_inbox": {inbox: n},
           "sender_auth": {"spf": True, "dkim": True, "dmarc": True}}
"""
from __future__ import annotations

import re
from datetime import date

from .core import Verdict


def _d(s: str) -> date:
    return date.fromisoformat(s)


def check(message: dict, lead: dict, context: dict, policy: dict) -> Verdict:
    cfg = policy["outreach"]
    v: list[str] = []
    body = message.get("body", "")
    channel = message.get("channel", "email")
    today = _d(context["today"])

    # Who may we contact at all?
    ids = {lead.get("email"), lead.get("phone")} - {None}
    if ids & set(context.get("suppression", set())):
        v.append("contact is on the suppression list")
    if not lead.get("lawful_basis"):
        v.append("no lawful basis recorded for this contact")
    if channel in cfg["optin_required_for"] and channel not in lead.get("optin_channels", []):
        v.append(f"no {channel} opt-in on record")
    cat = re.sub(r"[-_/]+", " ", (lead.get("category") or "").lower())
    if any(x in cat for x in cfg["excluded_categories"]):
        v.append(f"category '{cat}' is outside ICP")

    # Message hygiene
    if channel in cfg["require_unsubscribe_for"]:
        if not any(p in body.lower() for p in cfg["unsubscribe_patterns"]):
            v.append("no unsubscribe / opt-out line")
        auth = context.get("sender_auth", {})
        missing = [k for k in cfg["sender_auth_required"] if not auth.get(k)]
        if missing:
            v.append(f"sender auth missing: {', '.join(missing)}")
    words = len(body.split())
    if words > cfg["max_words"]:
        v.append(f"too long: {words} words > {cfg['max_words']}")

    # Personalisation must be traceable and fresh
    fresh_days = cfg["signal_freshness_days"]
    for claim in message.get("claims_about_lead", []):
        match = next((s for s in lead.get("signals", []) if _overlap(claim, s["fact"])), None)
        if match is None:
            v.append(f"personalisation not backed by any signal: '{claim}'")
        elif stretched := [w for w in cfg.get("outcome_words", [])
                           if re.search(rf"\b{re.escape(w)}", claim, re.I) and not re.search(rf"\b{re.escape(w)}", match["fact"], re.I)]:
            v.append(f"stretched personalisation — '{', '.join(stretched)}' not in the signal: '{claim}'")
        elif not match.get("source_url"):
            v.append(f"signal has no source URL: '{claim}'")
        elif (today - _d(match["date"])).days > fresh_days:
            v.append(f"stale signal ({(today - _d(match['date'])).days}d old): '{claim}'")

    # Statements about the lead in the body that were never declared as claims (and so never checked)
    for s in _undeclared_lead_statements(body, message.get("claims_about_lead", []), lead.get("name")):
        v.append(f"statement about the lead not declared in claims_about_lead: '{s[:80]}'")

    # No private metrics before intake
    if lead.get("stage") not in cfg["stages_with_private_data"]:
        for pat in cfg["private_metric_patterns"]:
            m = re.search(pat, body, flags=re.IGNORECASE)
            if m:
                v.append(f"implies private data before intake: '{m.group(0)}'")

    # Volume
    inbox = message.get("inbox")
    if inbox and context.get("sent_today_by_inbox", {}).get(inbox, 0) >= cfg["daily_cap_per_inbox"]:
        v.append(f"daily cap reached for {inbox}")

    return Verdict.from_violations("outreach_guard", v)


def _tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9₹]+", s.lower()) if len(w) > 2}


def _overlap(claim: str, fact: str, threshold: float = 0.6) -> bool:
    """A claim is backed if most of its meaningful words appear in the stored signal."""
    c = _tokens(claim)
    return bool(c) and len(c & _tokens(fact)) / len(c) >= threshold


_ABOUT_THEM = re.compile(r"\byour\b|\byou\s+(just\s+)?(launched|ran|posted|shipped|hired|raised|dropped|started|opened|released|announced|won|did)\b", re.I)
_SPECIFIC = re.compile(r"(?<!\d)\d+(?!\d)(?![-\s]?(?:min|mins|minute|minutes|hour|hours|hr|hrs)\b)|\b(drop|launch|campaign|ads?|range|collection|sale|video|reel|post|hire|funding|store|outlet|award|feature|collab|podcast)\b", re.I)


def _undeclared_lead_statements(body: str, claims: list, lead_name: str | None = None) -> list:
    """Heuristic: a sentence that talks about the lead ('your …', 'you launched …') AND names something
    specific must be covered by a declared claim. Generic lines ('worth a call for your team?') pass."""
    out = []
    for sent in re.split(r"(?<=[.!?;])\s+", body):
        if not _ABOUT_THEM.search(sent):
            continue
        rest = re.sub(r"^\W*\w+", "", sent)  # ignore the sentence's first word (capitalised anyway)
        specific = _SPECIFIC.search(sent) or re.search(r"\b[A-Z][a-z]{2,}", rest)
        if not specific:
            continue
        if not any(_overlap(c, sent) for c in claims):
            out.append(sent.strip())
    return out


def deliverability(stats: dict, policy: dict) -> Verdict:
    """stats = {"sent": int, "bounced": int, "spam_complaints": int} for one inbox."""
    cfg = policy["outreach"]
    sent = max(stats.get("sent", 0), 1)
    v = []
    if stats.get("bounced", 0) / sent >= cfg["stop_bounce_rate"]:
        v.append("bounce rate at or above stop threshold — pause inbox")
    if stats.get("spam_complaints", 0) / sent >= cfg["stop_spam_complaint_rate"]:
        v.append("spam complaint rate at or above stop threshold — pause inbox")
    return Verdict.from_violations("deliverability", v)
