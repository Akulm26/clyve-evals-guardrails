"""Checks for one automated send or reply (lifecycle flows, n8n, CRM-triggered).

event = {"tenant_id", "workflow_tenant_id", "contact": {"id", "tenant_id", "consent": {channel: bool}},
         "channel", "template_id", "template_approved": bool, "type": "promo"|"transactional"|...,
         "ts_ist": "YYYY-MM-DDTHH:MM", "audience_size": int, "last_audience_size": int}
history = [{"contact_id", "template_id", "channel", "ts_ist"}]   # recent sends
"""
from __future__ import annotations

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
    if not contact.get("consent", {}).get(channel):
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

    # Quiet hours for promotional types
    q = cfg["quiet_hours_ist"]
    if event.get("type") in cfg["promotional_types"] and _in_quiet_hours(ts, _t(q["start"]), _t(q["end"])):
        v.append(f"promotional send in quiet hours ({q['start']}–{q['end']} IST)")

    # Audience sanity (null filter / broken segment)
    last = event.get("last_audience_size")
    if last and event.get("audience_size", 0) > cfg["max_audience_growth_factor"] * last:
        v.append(f"audience jumped {event['audience_size']} vs last {last} — likely broken filter")

    return Verdict.from_violations("automation_guard", v)


def check_reply(proposed: dict, inbound_text: str, policy: dict) -> Verdict:
    """proposed = {"action": str, "text": str}. AI reply agent output for an inbound message."""
    cfg = policy["automation"]
    v: list[str] = []
    if proposed.get("action") not in cfg["reply_agent_allowed_actions"]:
        v.append(f"action '{proposed.get('action')}' not in allowed list")
    blob = f"{inbound_text}\n{proposed.get('text', '')}".lower()
    hits = [k for k in cfg["escalate_keywords"] if k in blob]
    escalate = bool(hits) and proposed.get("action") != "escalate"
    if escalate:
        v.append(f"sensitive topic ({', '.join(hits)}) — must escalate to a human")
    return Verdict.from_violations("reply_guard", v, escalate=escalate)
