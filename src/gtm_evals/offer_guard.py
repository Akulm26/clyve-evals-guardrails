"""Claims about AI, and prices shown as discounts.

AI-washing: "98% accurate AI", "our AI guarantees leads", "earn ₹50,000 a month with AI" need a test
behind them. Write the evidence ID next to the claim ([EV-2026-014]) and keep it in the evidence register.

Reference prices: a "was ₹X" or struck-through MRP must trace to the lowest price charged in the 30 days
before the discount† (the rule in the EU's Omnibus directive; ASCI's code asks that savings claims not
mislead). MRP is different in India: it's the maximum retail price printed on the pack (Legal Metrology),
so "MRP ₹699" must match the product's printed MRP. A reading for engineers, not legal advice.

    check(text, policy, evidence_ids={"EV-2026-014"}, price_history=[{"date": "2026-11-01", "price": 549}],
          today="2026-11-18", mrp=699)
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from .core import Verdict

_RUPEES = r"(?:₹|rs\.?\s?|inr\s?)\s?(?P<amt>[\d,]+(?:\.\d+)?)"


def _amount(s: str) -> float:
    return float(s.replace(",", ""))


def check(text: str, policy: dict, evidence_ids=None, price_history: list[dict] | None = None,
          today: str | None = None, mrp: float | None = None) -> Verdict:
    cfg = policy["offers"]
    v: list[str] = []
    escalate = False
    ids = set(evidence_ids or [])
    cited = set(re.findall(cfg["evidence_ref"], text or ""))
    for pat in cfg["ai_claim_patterns"]:
        for m in re.finditer(pat, text or "", re.IGNORECASE):
            if not cited:
                v.append(f"AI claim with no test evidence: '{m.group(0)}' (cite it, e.g. [EV-2026-014])")
            elif not cited <= ids:
                v.append(f"AI claim cites evidence not in the register: {', '.join(sorted(cited - ids))}")
            break
    was = [m for p in cfg["reference_price_patterns"] for m in re.finditer(p + _RUPEES, text or "", re.IGNORECASE)]
    if was:
        if not price_history or not today:
            escalate = True
            v.append(f"'{was[0].group(0).strip()}' needs the last 30 days of prices to check the reference price")
        else:
            t = date.fromisoformat(today)
            window = [h for h in price_history
                      if t - timedelta(days=cfg["reference_window_days"]) <= date.fromisoformat(h["date"]) <= t]
            if not window:
                escalate = True
                v.append(f"no prices recorded in the last {cfg['reference_window_days']} days")
            else:
                low = min(float(h["price"]) for h in window)
                for m in was:
                    ref = _amount(m.group("amt"))
                    if ref > low:
                        v.append(f"reference price ₹{ref:,.0f} is above the lowest price in the last "
                                 f"{cfg['reference_window_days']} days (₹{low:,.0f})")
    for m in re.finditer(cfg["mrp_pattern"] + _RUPEES, text or "", re.IGNORECASE):
        if mrp is None:
            escalate = True
            v.append(f"'{m.group(0).strip()}': check it against the MRP printed on the pack")
        elif abs(_amount(m.group("amt")) - float(mrp)) > 0.5:
            v.append(f"'{m.group(0).strip()}' doesn't match the printed MRP (₹{float(mrp):,.0f})")
        break
    return Verdict.from_violations("offer_guard", v, escalate=escalate)
