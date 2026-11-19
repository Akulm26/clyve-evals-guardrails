"""Checks for one outbound message (teardown email, DM, InMail, follow-up).

message = {
  "channel": "email" | "whatsapp" | "sms" | "instagram_dm" | "inmail",
  "body": str,
  "claims_about_lead": [str, ...],   # every specific fact the message states about the lead
  "inbox": "outreach@clyve.example",
}
lead = {
  "email": str, "phone": str, "category": str, "stage": "prospect" | "audit" | ...,
  "lawful_basis": "legitimate_interest" | "consent" | None,
  "optin_channels": [..],
  "signals": [{"fact": str, "source_url": str, "date": "YYYY-MM-DD"}],
}
Instagram DMs also read lead["ig_last_inbound_at"], lead["ig_comment_at"], message["private_reply_to_comment"]
and context["now"] (ISO datetime; defaults to the start of "today").
context = {"today": "YYYY-MM-DD", "suppression": set(), "sent_today_by_inbox": {inbox: n}, "bulk_sender": bool,
           "sent_today_by_channel": {"inmail": n, "instagram_dm": n, ...},   # this sender account, today
           "sender_auth": {"spf": True, "dkim": True, "dmarc": True}}
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from .core import Verdict


def _d(s: str) -> date:
    return date.fromisoformat(s)


def _dt(x) -> datetime | None:
    if not x:
        return None
    d = datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _instagram_problems(message: dict, lead: dict, context: dict, cfg: dict) -> list[str]:
    """No cold DMs: a reply inside 24 hours of their message, or one private reply to their comment within 7 days."""
    ig = cfg["instagram"]
    now = _dt(context.get("now")) or datetime.combine(_d(context["today"]), datetime.min.time(), timezone.utc)
    last = _dt(lead.get("ig_last_inbound_at"))
    if last and now - last <= timedelta(hours=ig["reply_window_hours"]):
        return []
    comment = _dt(lead.get("ig_comment_at"))
    if message.get("private_reply_to_comment"):
        if comment and now - comment <= timedelta(days=ig["comment_reply_days"]):
            return []
        return [f"private reply to a comment must go within {ig['comment_reply_days']} days of the comment"]
    if last:
        return [f"Instagram DM outside the {ig['reply_window_hours']}-hour window since their last message"]
    return ["cold Instagram DM: a business may only message someone who messaged it first "
            f"(within {ig['reply_window_hours']} hours) or reply privately to their comment"]


def check(message: dict, lead: dict, context: dict, policy: dict) -> Verdict:
    cfg = policy["outreach"]
    v: list[str] = []
    notes: list[str] = []
    body = message.get("body", "")
    channel = message.get("channel", "email")
    today = _d(context["today"])

    # Who may we contact at all?
    ids = {lead.get("email"), lead.get("phone")} - {None}
    if ids & set(context.get("suppression", set())):
        v.append("contact is on the suppression list")
    if not lead.get("lawful_basis"):
        v.append("no lawful basis recorded for this contact")
    if channel == "instagram_dm" and "instagram" in cfg:
        v.extend(_instagram_problems(message, lead, context, cfg))
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
        elif "dmarc" in cfg["sender_auth_required"]:
            v += _dmarc_problems(auth, cfg, notes)
        need_one_click = cfg.get("one_click_unsubscribe", "bulk")
        if need_one_click == "always" or (need_one_click == "bulk" and context.get("bulk_sender")):
            v += _one_click_problems(message.get("headers"))
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
    cap = cfg.get("daily_cap_per_channel", {}).get(channel)
    sent = context.get("sent_today_by_channel", {}).get(channel, 0)
    if cap is not None and sent >= cap:
        v.append(f"daily {channel} cap reached ({sent}/{cap}) — protects the sender account")

    return Verdict.from_violations("outreach_guard", v, notes=notes)


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


def _dmarc_problems(auth: dict, cfg: dict, notes: list[str]) -> list[str]:
    """Gmail and Outlook bulk rules: DMARC published (p=none is enough) and aligned with SPF or DKIM.
    auth = {"spf": True, "dkim": True, "dmarc": True, "dmarc_policy": "none", "spf_aligned": True, "dkim_aligned": False}"""
    out = []
    pol = auth.get("dmarc_policy")
    if pol is not None and str(pol).lower() not in cfg.get("dmarc_allowed_policies", ["none", "quarantine", "reject"]):
        out.append(f"DMARC policy '{pol}' is not a valid p= value")
    if "spf_aligned" in auth or "dkim_aligned" in auth:
        if not (auth.get("spf_aligned") or auth.get("dkim_aligned")):
            out.append("DMARC not aligned: the From domain must match the SPF or DKIM domain")
    else:
        notes.append("DMARC alignment not checked: pass sender_auth.spf_aligned / dkim_aligned")
    return out


def _one_click_problems(headers: dict | None) -> list[str]:
    """RFC 8058: List-Unsubscribe with an https URL, plus List-Unsubscribe-Post: List-Unsubscribe=One-Click."""
    h = {k.lower(): str(v) for k, v in (headers or {}).items()}
    out = []
    lu = h.get("list-unsubscribe", "")
    if "https://" not in lu.lower():
        out.append("no one-click unsubscribe: List-Unsubscribe needs an https URL (RFC 8058)")
    if h.get("list-unsubscribe-post", "").replace(" ", "").lower() != "list-unsubscribe=one-click":
        out.append("no one-click unsubscribe: missing 'List-Unsubscribe-Post: List-Unsubscribe=One-Click'")
    return out


def deliverability(stats: dict, policy: dict) -> Verdict:
    """stats = {"sent": int, "bounced": int, "spam_complaints": int} for one inbox."""
    cfg = policy["outreach"]
    sent = max(stats.get("sent", 0), 1)
    v = []
    if stats.get("bounced", 0) / sent >= cfg["stop_bounce_rate"]:
        v.append("bounce rate at or above stop threshold — pause inbox")
    rate = stats.get("spam_complaints", 0) / sent
    notes = []
    if rate >= cfg["stop_spam_complaint_rate"]:
        v.append(f"spam complaint rate {rate:.2%} at or above {cfg['stop_spam_complaint_rate']:.1%} — pause inbox")
    elif rate >= cfg.get("warn_spam_complaint_rate", 1):
        notes.append(f"spam complaint rate {rate:.2%} above {cfg['warn_spam_complaint_rate']:.1%} — fix before it reaches "
                     f"{cfg['stop_spam_complaint_rate']:.1%}")
    return Verdict.from_violations("deliverability", v, notes=notes)
