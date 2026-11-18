"""Deployment gate: is this AI automation deployable, safe and ethical?

Every Clyve workflow ships with a manifest (workflows/*.yaml). This checker reads it, runs the
three tests, and returns one of:

    DEPLOYABLE   every test passes, evidence is real
    PILOT ONLY   safe and ethical, but evidence is still synthetic or judges uncalibrated
    BLOCKED      a safety or ethics test fails — do not run it

    python gate/check_workflow.py workflows/teardown-outreach.yaml
    python gate/check_workflow.py workflows/*.yaml          # exit 1 if any is BLOCKED
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from guardrails import load_policy  # noqa: E402
from guardrails.action_gate import ActionGate  # noqa: E402

GUARD_FILES = {p.stem for p in (ROOT / "guardrails").glob("*.py")} - {"__init__", "core"}


def _rows(path):
    p = ROOT / path
    if not p.exists():
        return None
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def check(manifest: dict, policy: dict) -> dict:
    g = policy["deployment_gate"]
    gate = ActionGate(policy)
    deploy, safe, ethical = [], [], []   # (ok: bool, message)

    lane = manifest.get("lane")
    actions = manifest.get("actions", [])
    tiers = {a: gate.tier(a) for a in actions}
    has_r3 = "R3" in tiers.values()
    guards = set(manifest.get("guards", []))

    # ---------- SAFE ----------
    safe.append((lane in g["lanes"], f"lane '{lane}' is a known lane"))
    unknown = [a for a in actions if a not in policy["action_gate"]["action_tiers"]]
    safe.append((not unknown, "every action has a declared risk tier" + (f" (unknown → treated as R3: {unknown})" if unknown else "")))
    missing = [x for x in g["lanes"].get(lane, []) if x not in guards]
    safe.append((not missing, "all required guards for the lane are wired in" + (f" (missing: {missing})" if missing else "")))
    ghost = [x for x in guards if x not in GUARD_FILES]
    safe.append((not ghost, "every guard named exists in guardrails/" + (f" (no such guard: {ghost})" if ghost else "")))
    ks = manifest.get("kill_switch")
    safe.append((bool(ks), f"kill switch declared ({ks or 'none'})"))
    if has_r3:
        safe.append((bool(manifest.get("human_approver")), "R3 actions have a named human approver"))
        safe.append((manifest.get("canary_percent", 0) > 0, "R3 actions run a canary first"))
    log = manifest.get("logging", {})
    safe.append((bool(log.get("gate_log")), "every gate decision is logged"))
    safe.append((log.get("retention_days", 0) >= g["min_log_retention_days"], f"logs kept ≥ {g['min_log_retention_days']} days"))
    safe.append((bool(manifest.get("token_budget")), "per-run token budget set"))

    # ---------- ETHICAL ----------
    data = manifest.get("data", {})
    if data.get("personal_data"):
        ethical.append((bool(data.get("lawful_basis_field")), "contacts store a lawful basis (DPDP)"))
        ethical.append((bool(data.get("consent_checked_at_send")), "consent checked at send time, not from a cached list"))
        bad = [f for f in data.get("fields", []) if f.lower() in g["forbidden_data_fields"]]
        ethical.append((not bad, "collects only permitted personal data (minimisation)" + (f" (forbidden: {bad})" if bad else "")))
        ethical.append((data.get("opt_out_hours", 999) <= 48, "opt-outs honoured within 48 hours"))
    feats = [f.lower() for f in manifest.get("scoring_features", [])]
    prot = [f for f in feats if f in g["protected_attributes"]]
    ethical.append((not prot, "no protected attribute is used to score, rank or target people" + (f" (found: {prot})" if prot else "")))
    rep = manifest.get("automated_replies")
    if rep:
        ethical.append((bool(rep.get("discloses_automation")), "automated replies say they are automated"))
        ethical.append((bool(rep.get("human_escalation_path")), "a human is always reachable from an automated reply"))
    if any(x in guards for x in ("claims_gate", "outreach_guard")) or lane in ("content_ops", "gtm_engineering"):
        ethical.append(("promise_guard" in guards, "no outcome promises reach a reader (honesty)"))
    ethical.append(("manipulation_guard" in guards or lane == "ai_visibility", "pressure tactics are flagged for a human (no manipulation)"))

    # ---------- DEPLOYABLE (evidence) ----------
    gs = manifest.get("golden_set")
    rows = _rows(gs) if gs else None
    deploy.append((rows is not None, f"golden set exists ({gs or 'none'})"))
    real = sum(1 for r in (rows or []) if r.get("source") == "real")
    deploy.append((real >= g["min_real_golden_cases"], f"≥ {g['min_real_golden_cases']} real cases in the golden set (has {real})"))
    for j in manifest.get("judges", []):
        cal = j.get("calibration") or {}
        ok = cal.get("labelled_cases", 0) >= g["judge_min_labels"] and cal.get("agreement", 0) >= g["judge_min_agreement"]
        deploy.append((ok, f"judge '{j.get('template')}' calibrated (≥{g['judge_min_labels']} labels, ≥{g['judge_min_agreement']:.0%} agreement)"))
    deploy.append((bool(manifest.get("owner")), "a named owner"))

    if not all(o for o, _ in safe + ethical):
        verdict = "BLOCKED"
    elif not all(o for o, _ in deploy):
        verdict = "PILOT ONLY"
    else:
        verdict = "DEPLOYABLE"
    return {"name": manifest.get("name"), "verdict": verdict, "tiers": tiers,
            "safe": safe, "ethical": ethical, "deployable": deploy}


def report(res: dict) -> str:
    out = [f"\n{res['name']}  →  {res['verdict']}", f"  risk tiers: {res['tiers']}"]
    for k in ("safe", "ethical", "deployable"):
        out.append(f"  {k.upper()}")
        out += [f"    {'✅' if ok else '❌'} {msg}" for ok, msg in res[k]]
    return "\n".join(out)


def main(paths):
    import yaml
    policy = load_policy()
    blocked = False
    for p in paths:
        res = check(yaml.safe_load(Path(p).read_text(encoding="utf-8")), policy)
        print(report(res))
        blocked |= res["verdict"] == "BLOCKED"
    sys.exit(1 if blocked and "--allow-blocked" not in sys.argv else 0)


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if not a.startswith("--")])
