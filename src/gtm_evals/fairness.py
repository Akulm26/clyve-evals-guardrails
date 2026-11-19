"""Does a scoring feature track a protected group? The four-fifths (impact ratio) test.

Pincode, surname and community-linked lists can stand in for caste, religion or ethnicity in India.
A workflow that scores, ranks or targets on one of them must attach a fairness test: labelled rows
with the person's group (collected for the test only, with consent, never stored in the CRM) and
whether the workflow selected them.

rows = [{"group": "A", "selected": "1"}, {"group": "B", "selected": "0"}, ...]
    impact_ratio(rows)  →  {"ratio": 0.83, "rates": {"A": 0.30, "B": 0.25}, "small_groups": [], "rows": 412}
"""
from __future__ import annotations

TRUE = {"1", "true", "yes", "y", "selected", "pass"}


def _sel(v) -> bool:
    return v is True or str(v).strip().lower() in TRUE


def impact_ratio(rows: list[dict], group: str = "group", selected: str = "selected", min_group: int = 30) -> dict:
    """Lowest group selection rate ÷ highest. Groups smaller than min_group are listed, not scored."""
    counts: dict[str, list[int]] = {}
    for r in rows:
        g = str(r.get(group, "")).strip()
        if not g:
            continue
        c = counts.setdefault(g, [0, 0])
        c[0] += 1
        c[1] += int(_sel(r.get(selected)))
    small = sorted(g for g, (n, _) in counts.items() if n < min_group)
    rates = {g: s / n for g, (n, s) in counts.items() if n >= min_group}
    top = max(rates.values(), default=0.0)
    ratio = (min(rates.values()) / top) if len(rates) >= 2 and top > 0 else None
    return {"ratio": ratio, "rates": rates, "small_groups": small, "rows": sum(n for n, _ in counts.values())}
