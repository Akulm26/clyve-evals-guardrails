"""Live proof: shadow → canary → segment, read from the decision log the workflow already writes.

Offline cases show a workflow can work. Only live traffic shows it does. Each stage has a share of
traffic and a number of clean days; a breach on any day drops the workflow back to shadow.

manifest["rollout"] = {
  "log": "logs/decisions.jsonl",
  "stages": [{"name": "shadow", "share": 0.0, "days": 7}, {"name": "canary", "share": 0.05, "days": 7},
             {"name": "segment", "share": 0.25, "days": 14}],
  "guard_metrics": {"reply_rate_min": 0.02, "unsubscribe_rate_max": 0.01, "complaint_rate_max": 0.001,
                    "guard_fail_rate_max": 0.05},
}
manifest["budgets"] = {"usd_per_item": 0.25, "p95_seconds": 90, "whatsapp_rates": {"marketing": 0.0107, "utility": 0.0014}}

A log row (one per item the workflow handled):
  {"ts": "2026-11-18T10:02:00+05:30", "sent": true, "guard_passed": true, "replied": false,
   "unsubscribed": false, "complained": false, "cost_usd": 0.03, "latency_s": 41.2,
   "channel": "whatsapp", "category": "marketing", "kill_switch": false}
A row with no outcome at all ("sent", "guard_passed" both missing) counts as a failed guard: silence isn't a pass.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path


def read_log(path) -> list[dict]:
    p = Path(path)
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def _day(row: dict) -> date:
    return datetime.fromisoformat(str(row["ts"]).replace("Z", "+00:00")).date()


def day_metrics(rows: list[dict]) -> dict:
    n = len(rows)
    sent = [r for r in rows if r.get("sent")]
    s = len(sent) or 1
    fail = sum(1 for r in rows if r.get("guard_passed") is False or ("sent" not in r and "guard_passed" not in r))
    return {"items": n, "sent": len(sent),
            "reply_rate": sum(bool(r.get("replied")) for r in sent) / s,
            "unsubscribe_rate": sum(bool(r.get("unsubscribed")) for r in sent) / s,
            "complaint_rate": sum(bool(r.get("complained")) for r in sent) / s,
            "guard_fail_rate": fail / n if n else 0.0,
            "kill_switch": any(r.get("kill_switch") for r in rows)}


def breaches(m: dict, gm: dict) -> list[str]:
    out = []
    if m["kill_switch"]:
        out.append("kill switch flipped")
    for key, label in (("unsubscribe_rate", "unsubscribes"), ("complaint_rate", "complaints"), ("guard_fail_rate", "guard failures")):
        cap = gm.get(f"{key}_max")
        if cap is not None and m[key] > cap:
            out.append(f"{label} {m[key]:.2%} > {cap:.2%}")
    floor = gm.get("reply_rate_min")
    if floor is not None and m["sent"] and m["reply_rate"] < floor:
        out.append(f"replies {m['reply_rate']:.2%} < {floor:.2%}")
    return out


def p95(values: list[float]) -> float | None:
    v = sorted(values)
    return v[max(0, math.ceil(0.95 * len(v)) - 1)] if v else None


def budget_status(rows: list[dict], budgets: dict) -> dict:
    """Cost per item and p95 latency from the log. WhatsApp rows without a logged cost are priced by category."""
    rates = budgets.get("whatsapp_rates") or {}
    costs, missing = [], 0
    for r in rows:
        c = r.get("cost_usd")
        if c is None and r.get("channel") == "whatsapp" and r.get("category") in rates:
            c = rates[r["category"]]
        if c is None:
            missing += 1
        else:
            costs.append(float(c))
    lat = [float(r["latency_s"]) for r in rows if r.get("latency_s") is not None]
    per_item = sum(costs) / len(costs) if costs else None
    out = {"usd_per_item": per_item, "p95_seconds": p95(lat), "unpriced_rows": missing, "problems": []}
    if budgets.get("usd_per_item") is not None and per_item is not None and per_item > budgets["usd_per_item"]:
        out["problems"].append(f"cost ${per_item:.3f}/item > budget ${budgets['usd_per_item']:.3f}")
    if budgets.get("p95_seconds") is not None and out["p95_seconds"] is not None and out["p95_seconds"] > budgets["p95_seconds"]:
        out["problems"].append(f"p95 latency {out['p95_seconds']:.0f}s > budget {budgets['p95_seconds']:.0f}s")
    return out


def status(rollout: dict, rows: list[dict], policy: dict, budgets: dict | None = None) -> dict:
    """Walk the log day by day: clean days advance a stage, a breach drops back to shadow."""
    cfg = policy["rollout"]
    stages = rollout.get("stages") or cfg["default_stages"]
    gm = {**cfg["default_guard_metrics"], **(rollout.get("guard_metrics") or {})}
    by_day: dict[date, list[dict]] = defaultdict(list)
    for r in rows:
        by_day[_day(r)].append(r)
    i, clean, history = 0, 0, []
    for d in sorted(by_day):
        m = day_metrics(by_day[d])
        why = breaches(m, gm)
        if budgets:
            why += budget_status(by_day[d], budgets)["problems"]
        if why:
            history.append({"day": d.isoformat(), "stage": stages[i]["name"], "event": "breach", "why": why})
            i, clean = 0, 0
            continue
        if m["items"] < cfg["min_items_per_day"]:
            history.append({"day": d.isoformat(), "stage": stages[i]["name"], "event": "thin",
                            "why": [f"{m['items']} items < {cfg['min_items_per_day']}"]})
            continue
        clean += 1
        if clean >= stages[i]["days"] and i < len(stages) - 1:
            history.append({"day": d.isoformat(), "stage": stages[i]["name"], "event": "advance",
                            "why": [f"{clean} clean days"]})
            i, clean = i + 1, 0
    done = i == len(stages) - 1 and clean >= stages[i]["days"]
    return {"stage": stages[i]["name"], "stage_index": i, "clean_days": clean, "days_needed": stages[i]["days"],
            "complete": done, "history": history, "stages": [s["name"] for s in stages]}


def approver_fatigue(rows: list[dict], policy: dict) -> list[dict]:
    """Approvers who pass nearly everything in seconds: a sign-off that isn't a review.
    rows: approval-log lines [{"approver": "Akul", "approved": true, "seconds": 3.2}]."""
    cfg = policy["incident"]["approver_fatigue"]
    by: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r.get("approver"):
            by[r["approver"]].append(r)
    out = []
    for who, rs in sorted(by.items()):
        if len(rs) < cfg["min_items"]:
            continue
        rate = sum(bool(r.get("approved")) for r in rs) / len(rs)
        secs = sorted(float(r["seconds"]) for r in rs if r.get("seconds") is not None)
        med = secs[len(secs) // 2] if secs else None
        if rate >= cfg["max_approval_rate"] and med is not None and med < cfg["min_median_seconds"]:
            out.append({"approver": who, "items": len(rs), "approval_rate": rate, "median_seconds": med})
    return out
