"""Checks for one automated send or reply (lifecycle flows, n8n, CRM-triggered).

event = {"tenant_id", "workflow_tenant_id", "contact": {"id", "tenant_id", "consent": {channel: bool}},
         "channel", "template_id", "template_approved": bool, "type": "promo"|"transactional"|...,
         "ts_ist": "YYYY-MM-DDTHH:MM", "audience_size": int, "last_audience_size": int}
history = [{"contact_id", "template_id", "channel", "ts_ist"}]   # recent sends
"""
from __future__ import annotations

import re
from datetime import datetime, time, timedelta

from .core import Verdict


def _t(s: str) -> time:
    return datetime.strptime(s, "%H:%M").time()


def _in_quiet_hours(ts: datetime, start: time, end: time) -> bool:
    t = ts.time()
    return t >= start or t < end if start > end else start <= t < end


def check_send(event: dict, history: list[dict], policy: dict) -> Verdict:
    cfg = policy["automation"]
    v: list[str] = []
    ts = datetime.fromisoformat(event["ts_ist"])
    contact = event["contact"]
    channel = event["channel"]

    # Tenant isolation: event, workflow and contact must all belong to the same client
    tenants = {event.get("tenant_id"), event.get("workflow_tenant_id"), contact.get("tenant_id")}
    if len(tenants) != 1 or None in tenants:
        v.append(f"tenant mismatch: {sorted(map(str, tenants))}")

    # Consent at send time, from source of truth
    c = contact.get("consent", {}).get(channel)
    if not (c.get("granted") if isinstance(c, dict) else c):
        v.append(f"no current {channel} consent")
    if channel == "whatsapp" and not event.get("template_approved"):
        v.append("WhatsApp template not approved")

    # Idempotency: same contact + template inside the dedupe window
    win = timedelta(hours=cfg["dedupe_window_hours"])
    for h in history:
        if (h["contact_id"] == contact["id"] and h["template_id"] == event["template_id"]
                and abs(ts - datetime.fromisoformat(h["ts_ist"])) < win):
            v.append("duplicate: same template sent to this contact inside dedupe window")
            break

    # Frequency cap per channel, rolling 7 days
    cap = cfg["max_per_contact_per_7d"].get(channel)
    if cap is not None:
        recent = [h for h in history if h["contact_id"] == contact["id"] and h["channel"] == channel
                  and timedelta(0) <= ts - datetime.fromisoformat(h["ts_ist"]) < timedelta(days=7)]
        if len(recent) >= cap:
            v.append(f"frequency cap: {len(recent)} {channel} sends in 7d (cap {cap})")

    # Quiet hours for promotional sends. Any offer inside a service message makes it promotional (TRAI mixed-content rule).
    q = cfg["quiet_hours_ist"]
    body = (event.get("body") or "").lower()
    is_promo = ((event.get("type") or "").lower() in cfg["promotional_types"] or event.get("has_offer")
                or any(w in body for w in cfg.get("offer_words", [])))
    if is_promo and _in_quiet_hours(ts, _t(q["start"]), _t(q["end"])):
        v.append(f"promotional send in quiet hours ({q['start']}–{q['end']} IST)")

    v += _trai(event, contact, channel, ts, is_promo, policy)

    # Audience sanity (null filter / broken segment)
    last = event.get("last_audience_size")
    if last and event.get("audience_size", 0) > cfg["max_audience_growth_factor"] * last:
        v.append(f"audience jumped {event['audience_size']} vs last {last} — likely broken filter")

    return Verdict.from_violations("automation_guard", v)


def _when(x) -> datetime | None:
    if isinstance(x, dict):
        x = x.get("at")
    return datetime.fromisoformat(str(x)[:16]) if x else None


def _trai(event: dict, contact: dict, channel: str, ts: datetime, is_promo: bool, policy: dict) -> list[str]:
    """TRAI commercial-communication rules (TCCCPR as amended Feb 2025) for SMS and voice.

    contact["consent"][channel] may be True or {"granted": True, "at": ts, "source": "explicit" | "transaction"}
    contact["opt_outs"] = {channel: ts}            last opt-out
    event["is_consent_request"] = True             this send asks the contact to opt in again
    event["header"] = "AX-BRANDX-P"                 sender header; its suffix must match the message category
    event["dlt_template_id"], event["dlt_template_category"]   registered DLT template for this send
    """
    cfg = policy.get("trai", {})
    if channel not in cfg.get("channels", []):
        return []
    v = []
    category = "promotional" if is_promo else ((event.get("type") or "").lower() or "service")
    category = cfg.get("category_aliases", {}).get(category, category)

    out = _when((contact.get("opt_outs") or {}).get(channel))
    if out and event.get("is_consent_request") and ts - out < timedelta(days=cfg["reconsent_lock_days"]):
        v.append(f"asks for consent again {(ts - out).days} days after an opt-out "
                 f"(TRAI: not within {cfg['reconsent_lock_days']} days)")
    c = (contact.get("consent") or {}).get(channel)
    if isinstance(c, dict) and c.get("source") == "transaction" and is_promo:
        at = _when(c)
        if at and ts - at > timedelta(days=cfg["transaction_consent_days"]):
            v.append(f"consent taken during a transaction is {(ts - at).days} days old "
                     f"(TRAI: valid {cfg['transaction_consent_days']} days)")

    if channel in cfg.get("dlt_channels", []):
        if not event.get("dlt_template_id"):
            v.append("no DLT template ID: SMS content must use a registered template")
        elif event.get("dlt_template_category") and event["dlt_template_category"].lower() != category:
            v.append(f"DLT template is registered as '{event['dlt_template_category']}' but this message is {category}")
        header = event.get("header") or ""
        want = cfg.get("header_suffix", {}).get(category)
        if header and want and not header.upper().endswith(f"-{want}"):
            v.append(f"header '{header}' doesn't carry the -{want} suffix for {category} messages")
    return v


def check_reply(proposed: dict, inbound_text: str, policy: dict) -> Verdict:
    """proposed = {"action": str, "text": str}. AI reply agent output for an inbound message."""
    cfg = policy["automation"]
    v: list[str] = []
    if proposed.get("action") not in cfg["reply_agent_allowed_actions"]:
        v.append(f"action '{proposed.get('action')}' not in allowed list")
    blob = f"{inbound_text}\n{proposed.get('text', '')}".lower()
    hits = [k for k in cfg["escalate_keywords"] if k in blob]
    auto_ok = any(re.search(p, inbound_text, re.I) for p in cfg.get("reply_auto_ok_patterns", []))
    needs_human = bool(hits) or not auto_ok
    escalate = needs_human and proposed.get("action") != "escalate"
    if escalate:
        why = f"sensitive topic ({', '.join(hits)})" if hits else "not a known-safe question"
        v.append(f"{why} — must escalate to a human")
    return Verdict.from_violations("reply_guard", v, escalate=escalate)
