"""Run every deterministic guard against its golden set and report catch rates.

Positive class = "should be blocked". Recall = share of bad cases caught (misses ship).
Precision = share of blocks that were right (false alarms make people bypass guards).
Exit code 1 if any lane falls under the policy thresholds, so this can gate CI.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from gtm_evals import load_policy  # noqa: E402
from gtm_evals import automation_guard, claims_gate, injection_guard, outreach_guard, pii_guard, promise_guard, visibility_stats  # noqa: E402
from gtm_evals.core import combine  # noqa: E402

DATA = ROOT / "evals" / "datasets"


def jl(name):
    return [json.loads(x) for x in (DATA / name).read_text(encoding="utf-8").splitlines() if x.strip()]


def lane_content(policy):
    reg = json.loads((DATA / "claims_register_demo.json").read_text(encoding="utf-8"))
    for r in jl("content_drafts.jsonl"):
        v = combine(claims_gate.check(r["text"], reg, policy), promise_guard.check(r["text"], policy))
        yield r, v


def lane_outreach(policy):
    for r in jl("outreach_messages.jsonl"):
        c = dict(r["context"], suppression=set(r["context"]["suppression"]))
        body = r["message"]["body"]
        v = combine(outreach_guard.check(r["message"], r["lead"], c, policy), promise_guard.check(body, policy))
        yield r, v


def lane_automation(policy):
    for r in jl("automation_events.jsonl"):
        if r["kind"] == "send":
            v = automation_guard.check_send(r["event"], r["history"], policy)
        else:
            v = combine(automation_guard.check_reply(r["proposed"], r["inbound"], policy),
                        injection_guard.check(r["inbound"]))
        yield r, v


def lane_security(policy):
    for r in jl("security_inputs.jsonl"):
        g = injection_guard if r["guard"] == "injection" else pii_guard
        yield r, g.check(r["text"])


LANES = {"content": lane_content, "outreach": lane_outreach, "automation": lane_automation, "security": lane_security}


def score(lane, results, policy, verbose):
    tp = fp = fn = tn = 0
    misses = []
    for r, v in results:
        should_block, blocked = not r["expected_pass"], not v.passed
        if should_block and blocked:
            tp += 1
        elif should_block and not blocked:
            fn += 1
            misses.append(f"  MISS  {r['id']}: {r.get('why', '')}")
        elif blocked:
            fp += 1
            misses.append(f"  FALSE ALARM  {r['id']}: {'; '.join(v.violations)}")
        else:
            tn += 1
        if verbose:
            print(f"    {r['id']:5} {'BLOCK' if blocked else 'pass ':5}  {'; '.join(v.violations)[:110]}")
    recall = tp / (tp + fn) if tp + fn else 1.0
    precision = tp / (tp + fp) if tp + fp else 1.0
    ok = recall >= policy["evals"]["min_recall_must_block"] and precision >= policy["evals"]["min_precision"]
    print(f"{lane:11} n={tp+fp+fn+tn:3}  recall={recall:.2f}  precision={precision:.2f}  {'OK' if ok else 'FAIL'}")
    for m in misses:
        print(m)
    return ok


def visibility(policy):
    rows = jl("visibility_runs.jsonl")
    probs = visibility_stats.validate_rows(rows, policy)
    ok = not probs
    for qt, expect in (("brand", True), ("best_x", False)):
        res = visibility_stats.real_change(rows, "day0", "day30", qt, policy)
        good = res["real"] == expect
        ok &= good
        print(f"visibility  {qt:7} {res['before']:.2f} → {res['after']:.2f}  noise={res['noise']:.2f}  "
              f"{res['verdict']}  {'OK' if good else 'FAIL (expected real=' + str(expect) + ')'}")
    for p in probs:
        print("  ", p)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", choices=[*LANES, "visibility"])
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    policy = load_policy(profile="clyve")
    all_ok = True
    for name, fn in LANES.items():
        if a.lane in (None, name):
            all_ok &= score(name, fn(policy), policy, a.verbose)
    if a.lane in (None, "visibility"):
        all_ok &= visibility(policy)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
