"""GTM engineering: what an enrichment or research agent may write into a CRM.

A record written by an agent becomes the "fact" that the next email quotes. So every field
needs a source and a date, has to be fresh, has to be a field you're allowed to keep, and
personal contact details need a lawful basis.

record = {
  "tenant_id": "brand-a", "workflow_tenant_id": "brand-a",
  "lead_id": "l1",
  "lawful_basis": "legitimate_interest" | "consent" | None,
  "fields": {
     "company": {"value": "Example Masala", "source": "https://…", "date": "2026-11-10", "confidence": 0.95},
     "work_email": {"value": "rhea@examplemasala.in", "source": "https://…", "date": "2026-11-10"},
     ...
  },
}
    check_write(record, policy, today="2026-11-18")  →  Verdict
"""
from __future__ import annotations

import re
from datetime import date

from . import pii_guard
from .core import Verdict

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_CONTACT_FIELDS = re.compile(r"(e-?mail|phone|mobile|whatsapp)", re.I)


def _names_forbidden(field: str, forbidden: set[str]) -> bool:
    """True if the field name contains a forbidden word as whole words: 'founder_religion', 'Religion',
    'bank-account-no' all match; 'page_views' does not match 'age'."""
    words = [w for w in re.split(r"[^a-z0-9]+", field.lower()) if w]
    for f in forbidden:
        fw = [w for w in re.split(r"[^a-z0-9]+", f) if w]
        if any(words[i:i + len(fw)] == fw for i in range(len(words) - len(fw) + 1)):
            return True
    return False


def check_write(record: dict, policy: dict, today: str) -> Verdict:
    cfg = policy["enrichment"]
    gate = policy["deployment_gate"]
    forbidden = {f.lower() for f in gate["forbidden_data_fields"]} | {f.lower() for f in gate["protected_attributes"]}
    allowed = {f.lower() for f in cfg.get("allowed_fields") or []}
    t = date.fromisoformat(today)
    v: list[str] = []

    tenants = {record.get("tenant_id"), record.get("workflow_tenant_id")}
    if len(tenants) != 1 or None in tenants:
        v.append(f"tenant mismatch: {sorted(map(str, tenants))}")

    for name, f in (record.get("fields") or {}).items():
        key = name.lower()
        f = f if isinstance(f, dict) else {"value": f}
        val = "" if f.get("value") is None else str(f.get("value"))
        if _names_forbidden(key, forbidden):
            v.append(f"'{name}' may never be stored (minimisation / protected attribute)")
            continue
        if allowed and key not in allowed:
            v.append(f"'{name}' is not in enrichment.allowed_fields")
            continue
        if not f.get("source"):
            v.append(f"'{name}' has no source — the next email can't cite it")
        if not f.get("date"):
            v.append(f"'{name}' has no date")
        else:
            try:
                age = (t - date.fromisoformat(str(f["date"])[:10])).days
            except ValueError:
                v.append(f"'{name}' has an unreadable date: '{f['date']}'")
            else:
                if age > cfg["max_age_days"]:
                    v.append(f"'{name}' is {age} days old (max {cfg['max_age_days']}) — re-check before writing")
                elif age < 0:
                    v.append(f"'{name}' is dated in the future: '{f['date']}'")
        conf = f.get("confidence")
        if isinstance(conf, (int, float)) and conf < cfg["min_confidence"]:
            v.append(f"'{name}' confidence {conf:.2f} below {cfg['min_confidence']:.2f}")

        if cfg.get("work_contact_only") and _CONTACT_FIELDS.search(key) and not record.get("lawful_basis") == "consent":
            m = _EMAIL.search(val)
            if m and m.group(1).lower() in {d.lower() for d in cfg["personal_email_domains"]}:
                v.append(f"'{name}' is a personal email ({m.group(1)}) — needs consent, not legitimate interest")
            if re.search(r"(phone|mobile|whatsapp)", key) and not key.startswith(("work_", "office_", "company_")):
                v.append(f"'{name}' is a personal phone number — needs consent")
        elif not _CONTACT_FIELDS.search(key):
            pii = pii_guard.check(val)
            if not pii:
                v.append(f"'{name}' contains personal data in a free-text field ({', '.join(x.split()[-1] for x in pii.violations)})")

    if not record.get("lawful_basis") and any(_CONTACT_FIELDS.search(k) for k in record.get("fields") or {}):
        v.append("contact details written with no lawful basis on the record")
    return Verdict.from_violations("enrichment_guard", v)
