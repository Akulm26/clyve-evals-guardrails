"""Run guards against a golden set and score them.

Golden-set format (JSONL, one case per line):

    {"id": "c1", "guard": "claims", "input": {"text": "...", "register": "claims_register.json"},
     "expected_pass": false, "source": "real", "why": "invented stat"}

guard ∈ claims | promise | manipulation | injection | pii | outreach | automation_send | automation_reply
source ∈ real | synthetic  (only "real" rows count toward deployment evidence)
"""
from __future__ import annotations

import json
from pathlib import Path

from . import automation_guard, claims_gate, injection_guard, manipulation_guard, outreach_guard, pii_guard, promise_guard
from .core import Verdict


def _register(reg, base: Path):
    if isinstance(reg, str):
        return json.loads((base / reg).read_text(encoding="utf-8"))
    return reg or []


def run_case(row: dict, policy: dict, base: Path) -> Verdict:
    g, x = row["guard"], row["input"]
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
        return automation_guard.check_reply(x["proposed"], x["inbound"], policy)
    raise ValueError(f"unknown guard '{g}' in case {row.get('id')}")


def load_rows(path: str | Path) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def score(rows: list[dict], policy: dict, base: Path) -> dict:
    """Positive class = 'should be blocked'. Returns per-guard recall/precision and the misses."""
    per: dict[str, dict] = {}
    for r in rows:
        v = run_case(r, policy, base)
        s = per.setdefault(r["guard"], {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "misses": [], "false_alarms": []})
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
    real = sum(1 for r in rows if r.get("source") == "real")
    return {"guards": per, "n": len(rows), "real": real, "ok": all(s["ok"] for s in per.values())}
