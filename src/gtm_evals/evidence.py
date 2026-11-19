"""How much evidence a claim needs, and whether two labellers agree enough to use it.

    required_cases(rate, margin, confidence=0.95, population=None)   Cochran's formula (+ finite-population correction)
    strata_shortfall(rows, required, shares)                         real cases missing per stratum
    cohen_kappa(a, b)                                                agreement beyond chance between two labellers
    agreement(rows)                                                  κ, agreed rows and disagreements from a label sheet

Why: "30 real cases" can't show a 90% precision claim is right to within a few points. With n cases and an
observed rate p, the 95% margin is about 1.96·√(p(1−p)/n), so n follows from the claim, not from habit.
"""
from __future__ import annotations

import math
from statistics import NormalDist


def z_for(confidence: float) -> float:
    return NormalDist().inv_cdf(0.5 + confidence / 2)


def required_cases(rate: float = 0.5, margin: float = 0.10, confidence: float = 0.95,
                   population: int | None = None) -> int:
    """Cases needed to estimate a rate (precision, recall, agreement) to ±margin at the given confidence.
    rate=0.5 is the conservative choice when the true rate is unknown."""
    if not 0 < margin < 1 or not 0 <= rate <= 1 or not 0 < confidence < 1:
        raise ValueError("rate in [0, 1], margin and confidence in (0, 1)")
    z = round(z_for(confidence), 2)                     # 1.96 at 95%, as the formula is usually quoted
    p = min(max(rate, 1e-9), 1 - 1e-9)
    n0 = z * z * p * (1 - p) / (margin * margin)
    if population:
        n0 = n0 / (1 + (n0 - 1) / population)
    return math.ceil(n0 - 1e-9)


def strata_shortfall(rows: list[dict], required: int, shares: dict[str, float]) -> dict[str, int]:
    """How many more real cases each stratum needs. Rows without a stratum count as 'standard'."""
    have: dict[str, int] = {}
    for r in rows:
        s = r.get("stratum") or "standard"
        have[s] = have.get(s, 0) + 1
    return {s: math.ceil(required * share) - have.get(s, 0)
            for s, share in shares.items() if math.ceil(required * share) > have.get(s, 0)}


def cohen_kappa(a: list[str], b: list[str]) -> float:
    """Cohen's κ for two labellers' verdicts on the same items."""
    if len(a) != len(b):
        raise ValueError("both labellers must label the same items")
    n = len(a)
    if n == 0:
        return 0.0
    labels = set(a) | set(b)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(k) / n) * (b.count(k) / n) for k in labels)
    if pe == 1:
        return 1.0 if po == 1 else 0.0
    return (po - pe) / (1 - pe)


def _v(x) -> str | None:
    x = str(x or "").strip().lower()
    return x if x in ("pass", "fail") else None


def agreement(rows: list[dict]) -> dict:
    """From a label sheet with human_verdict and human_verdict_b: κ on rows both labelled, the rows
    they agree on (usable for calibration) and the ids they disagree on."""
    both = [(r.get("id"), _v(r.get("human_verdict")), _v(r.get("human_verdict_b"))) for r in rows]
    both = [(i, x, y) for i, x, y in both if x and y]
    k = cohen_kappa([x for _, x, _ in both], [y for _, _, y in both]) if both else 0.0
    return {"kappa": round(k, 3), "both_labelled": len(both),
            "agreed": [i for i, x, y in both if x == y],
            "disagree": [i for i, x, y in both if x != y],
            "second_labeller": any(_v(r.get("human_verdict_b")) for r in rows)}
