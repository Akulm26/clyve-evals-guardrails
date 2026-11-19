"""Real people's faces and voices need consent; synthetic media needs a label.

Rules this encodes (a reading for engineers, not legal advice): MeitY's IT Amendment Rules 2026 on
synthetically generated information (a visible label on synthetic visuals, a spoken disclosure at the
start of synthetic audio); ASCI's guidelines on AI-generated ads (labels for virtual influencers,
consented likeness or voice clones and realistic synthetic product demos; deepfakes or likenesses used
without consent are not allowed, labelled or not). Text written with AI needs no label.

asset = {"id": "A1", "type": "image" | "video" | "audio" | "text", "is_synthetic": True,
         "label": "AI-generated", "label_position": "start",          # audio: the disclosure comes first
         "people": [{"name": "Rhea", "likeness_id": "L1"}],           # real faces or voices shown or heard
         "virtual_influencer": False, "endorses_product": True}
register = [{"id": "L1", "name": "Rhea", "consent": True, "scope": ["ads", "social"], "expires": "2027-06-30"}]

    check_asset(asset, register, policy, today="YYYY-MM-DD", usage="ads")
"""
from __future__ import annotations

import re
from datetime import date

from .core import Verdict


def check_asset(asset: dict, register: list[dict], policy: dict, today: str | None = None, usage: str = "ads") -> Verdict:
    cfg = policy["likeness"]
    v: list[str] = []
    notes: list[str] = []
    reg = {r.get("id"): r for r in register or []}
    t = date.fromisoformat(today) if today else None
    for p in asset.get("people") or []:
        rec = reg.get(p.get("likeness_id"))
        name = p.get("name") or p.get("likeness_id") or "a real person"
        if not rec:
            v.append(f"{name}'s face or voice is used with no consent record (deepfakes and unconsented likenesses aren't allowed, labelled or not)")
            continue
        if not rec.get("consent"):
            v.append(f"{name}'s likeness record has no consent")
        if rec.get("scope") and usage not in rec["scope"]:
            v.append(f"{name}'s consent doesn't cover '{usage}' (covers: {', '.join(rec['scope'])})")
        if t and rec.get("expires") and date.fromisoformat(rec["expires"]) < t:
            v.append(f"{name}'s consent expired on {rec['expires']}")
    kind = (asset.get("type") or "").lower()
    synthetic = asset.get("is_synthetic") or asset.get("virtual_influencer")
    if synthetic and kind in cfg["label_required_types"]:
        label = asset.get("label") or ""
        if not any(re.search(p, label, re.IGNORECASE) for p in cfg["label_patterns"]):
            v.append(f"synthetic {kind} needs a visible AI label (e.g. 'AI-generated')")
        elif kind == "audio" and asset.get("label_position") != "start":
            v.append("synthetic audio must disclose it's AI-generated at the start")
    elif synthetic and kind == "text":
        notes.append("AI-written text needs no label; the claims in it still go through the other guards")
    if asset.get("is_synthetic") and asset.get("endorses_product") and not asset.get("people") and not asset.get("virtual_influencer"):
        v.append("a synthetic person endorsing the product reads as a real customer: label it as a virtual character or drop it")
    return Verdict.from_violations("likeness_guard", v, notes=notes)
