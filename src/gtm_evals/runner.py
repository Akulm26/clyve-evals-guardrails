"""Run guards against a golden set and score them.

Golden-set format (JSONL, one case per line):

    {"id": "c1", "guard": "claims", "input": {"text": "...", "register": "claims_register.json"},
     "expected_pass": false, "source": "real", "why": "invented stat"}

guard ∈ claims | promise | manipulation | injection | pii | outreach | automation_send | automation_reply
        | claim_safety | enrichment | ai_seo_crawlers | ai_seo_page | ai_seo_entity
source ∈ real | synthetic  (only "real" rows count toward deployment evidence)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import (ai_seo_guard, automation_guard, claim_safety_guard, claims_gate, dark_pattern_guard, dpdp_guard,
               enrichment_guard, injection_guard, isolation, likeness_guard, manipulation_guard, outreach_guard,
               output_guard, pii_guard, promise_guard, provenance, testimonial_guard, visibility_stats)
from .core import Verdict


def _register(reg, base: Path):
    if isinstance(reg, str):
        return json.loads((base / reg).read_text(encoding="utf-8"))
    return reg or []


def run_case(row: dict, policy: dict, base: Path) -> Verdict:
    if not isinstance(row, dict) or "guard" not in row or "input" not in row:
        rid = row.get("id", "?") if isinstance(row, dict) else "?"
        raise ValueError(f"case {rid}: not a golden-set row (needs 'guard', 'input' and 'expected_pass'; see the README)")
    g, x = row["guard"], row["input"]
    if row.get("as_of"):
        x = as_of(x, row["as_of"])
    if g == "claims":
        return claims_gate.check(x["text"], _register(x.get("register"), base), policy)
    if g == "promise":
        return promise_guard.check(x["text"], policy)
    if g == "manipulation":
        return manipulation_guard.check(x["text"], policy)
    if g == "injection":
        return injection_guard.check(x["text"])
    if g == "pii":
        return pii_guard.check(x["text"])
    if g == "outreach":
        ctx = dict(x["context"], suppression=set(x["context"].get("suppression", [])))
        return outreach_guard.check(x["message"], x["lead"], ctx, policy)
    if g == "automation_send":
        return automation_guard.check_send(x["event"], x.get("history", []), policy)
    if g == "automation_reply":
        return automation_guard.check_reply(x["proposed"], x["inbound"], policy, x.get("context"))
    if g == "deliverability":
        return outreach_guard.deliverability(x["stats"], policy)
    if g == "visibility_rows":
        problems = visibility_stats.validate_rows(x["rows"], policy)
        return Verdict.from_violations("visibility_stats", problems)
    if g == "dpdp_campaign":
        return dpdp_guard.check_campaign(x["campaign"], policy)
    if g == "dpdp_notice":
        return dpdp_guard.check_notice(x["text"], policy)
    if g == "testimonial":
        return testimonial_guard.check(x["text"], x.get("register", []), policy)
    if g == "likeness":
        return likeness_guard.check_asset(x["asset"], x.get("register", []), policy, x.get("today"), x.get("usage", "ads"))
    if g == "dark_pattern":
        return dark_pattern_guard.check_flow(x["spec"], policy)
    if g == "claim_safety":
        return claim_safety_guard.check(x["text"], x.get("category"), policy, x.get("competitors"))
    if g == "enrichment":
        return enrichment_guard.check_write(x["record"], policy, x["today"])
    if g == "output":
        return output_guard.check(x["text"], policy, x.get("context"))
    if g == "provenance":
        return provenance.check_record(x["record"], x.get("pages", {}), policy)
    if g == "tool_use":
        return provenance.check_trace(x["claims"], x.get("trace", []), policy)
    if g == "isolation_retrieval":
        return isolation.check_retrieval(x["request"], x["tenant"])
    if g == "assert":
        return check_assertions(x["output"], x.get("must_demonstrate", []), x.get("must_avoid", []))
    if g == "ai_seo_crawlers":
        return ai_seo_guard.crawler_access(x.get("robots"), policy, x.get("path", "/"))
    if g == "ai_seo_page":
        return ai_seo_guard.check_page(x["html"], policy, x.get("robots"), x.get("path", "/"),
                                       x.get("must_contain"), x.get("schema"))
    if g == "ai_seo_entity":
        return ai_seo_guard.entity_consistency(x["profiles"], x["canonical"], policy)
    raise ValueError(f"unknown guard '{g}' in case {row.get('id')}")


_DATE_KEYS = ("date", "ts", "at", "recorded_at", "observed_at", "created_at")


def _stamp(d: dict) -> str | None:
    return next((str(d[k])[:10] for k in _DATE_KEYS if d.get(k)), None)


def as_of(x, day: str):
    """Replay an input as it stood on `day`: anything dated later is hidden, and "today" becomes `day`.
    A CRM-history case can't pass on a signal that was only recorded after the decision."""
    if isinstance(x, list):
        return [as_of(i, day) for i in x if not (isinstance(i, dict) and (_stamp(i) or "") > day)]
    if isinstance(x, dict):
        out = {}
        for k, val in x.items():
            if isinstance(val, dict) and (_stamp(val) or "") > day:
                continue
            out[k] = day if k in ("today", "now") else as_of(val, day)
        return out
    return x


def check_assertions(output: str, must_demonstrate: list[str], must_avoid: list[str]) -> Verdict:
    """An assertion case: the output must show each `must_demonstrate` pattern and none of `must_avoid`.
    e.g. a research note must say "unknown" where it has no source, and must never upgrade "proposed" to "verified"."""
    v = [f"doesn't demonstrate: {p}" for p in must_demonstrate if not re.search(p, output or "", re.I | re.S)]
    v += [f"does what it must avoid: '{m.group(0)}'" for p in must_avoid
          for m in [re.search(p, output or "", re.I | re.S)] if m]
    return Verdict.from_violations("assertions", v)


def load_rows(path: str | Path) -> list[dict]:
    """JSONL, or CSV (e.g. a labelling sheet exported from a spreadsheet). In CSV, a blank
    human_verdict means "not labelled yet" and the row is skipped by calibration."""
    path = Path(path)
    if path.suffix.lower() == ".csv":
        import csv
        with path.open(encoding="utf-8-sig", newline="") as f:
            rows = [{k.strip(): (v or "").strip() for k, v in r.items() if k} for r in csv.DictReader(f)]
        for r in rows:
            for col in ("human_verdict", "human_verdict_b"):
                if col in r or col == "human_verdict":
                    hv = (r.get(col) or "").lower()
                    r[col] = hv if hv in ("pass", "fail") else None
        return [r for r in rows if any(v for k, v in r.items() if k not in ("human_verdict", "human_verdict_b"))]
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def score(rows: list[dict], policy: dict, base: Path) -> dict:
    """Positive class = 'should be blocked'. Returns per-guard recall/precision and the misses."""
    per: dict[str, dict] = {}
    review = []
    for r in rows:
        if r.get("human_review"):
            review.append(r.get("id"))   # a person decides this one; it isn't scored or counted as evidence
            continue
        v = run_case(r, policy, base)
        s = per.setdefault(r["guard"], {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "misses": [], "false_alarms": []})
        if "expected_pass" not in r:
            raise ValueError(f"case {r.get('id', '?')}: missing 'expected_pass'")
        should_block, blocked = not r["expected_pass"], not v.passed
        if should_block and blocked:
            s["tp"] += 1
        elif should_block:
            s["fn"] += 1; s["misses"].append(r.get("id"))
        elif blocked:
            s["fp"] += 1; s["false_alarms"].append((r.get("id"), v.violations))
        else:
            s["tn"] += 1
    ev = policy["evals"]
    for s in per.values():
        s["recall"] = s["tp"] / (s["tp"] + s["fn"]) if s["tp"] + s["fn"] else 1.0
        s["precision"] = s["tp"] / (s["tp"] + s["fp"]) if s["tp"] + s["fp"] else 1.0
        s["ok"] = s["recall"] >= ev["min_recall_must_block"] and s["precision"] >= ev["min_precision"]
    real = sum(1 for r in rows if r.get("source") == "real" and not r.get("human_review"))
    return {"guards": per, "n": len(rows) - len(review), "real": real, "human_review": review,
            "ok": all(s["ok"] for s in per.values())}
