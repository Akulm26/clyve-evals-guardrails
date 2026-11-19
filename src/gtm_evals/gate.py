"""Deployment gate: is this AI automation deployable, safe and ethical?

Every workflow ships with a manifest (workflows/*.yaml). This checker reads it, runs the
three tests, and returns one of:

    DEPLOYABLE   every test passes, evidence is real
    PILOT ONLY   safe and ethical, but evidence is still synthetic or judges uncalibrated
    BLOCKED      a safety or ethics test fails — do not run it

    gtm-evals gate workflows/*.yaml          # exit 1 if any is BLOCKED
"""
from __future__ import annotations

import json
from pathlib import Path

from .action_gate import ActionGate
from .evidence import agreement, required_cases, strata_shortfall

GUARD_FILES = {"claims_gate", "promise_guard", "pii_guard", "injection_guard", "outreach_guard",
               "automation_guard", "manipulation_guard", "visibility_stats", "action_gate",
               "ai_seo_guard", "claim_safety_guard", "enrichment_guard", "dpdp_guard",
               "testimonial_guard", "likeness_guard", "dark_pattern_guard"}
_BASE = [Path.cwd()]


def _rows(path):
    p = next((b / path for b in _BASE if (b / path).exists()), Path(path))
    if not p.exists():
        return None
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def check(manifest: dict, policy: dict, base_dir: str | Path | None = None) -> dict:
    """Run the safe / ethical / deployable tests on one workflow manifest."""
    _BASE[:] = [Path(base_dir)] if base_dir else [Path.cwd()]
    g = policy["deployment_gate"]
    gate = ActionGate(policy)
    deploy, safe, ethical = [], [], []   # (ok: bool, message)

    lane = g.get("lane_aliases", {}).get(manifest.get("lane"), manifest.get("lane"))
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
        r3 = [a for a, t in tiers.items() if t == "R3"]
        preview_ok = set(r3) <= {"publish"} and bool(manifest.get("preview_before_publish"))
        safe.append((manifest.get("canary_percent", 0) > 0 or preview_ok,
                     "R3 actions run a canary first" + (" (publish: a preview is reviewed before going live)" if preview_ok else "")))
    log = manifest.get("logging", {})
    safe.append((bool(log.get("gate_log")), "every gate decision is logged"))
    safe.append((log.get("retention_days", 0) >= g["min_log_retention_days"], f"logs kept ≥ {g['min_log_retention_days']} days"))
    safe.append((bool(manifest.get("token_budget")), "per-run token budget set"))
    if "publish" in actions:
        safe.append((bool(manifest.get("approval_log")), "every publish has a recorded approval (approval_log)"))
    if any(a in actions for a in ("crm_update", "client_crm_bulk_write")) and lane == "gtm_engineering":
        safe.append(("enrichment_guard" in guards, "CRM writes go through enrichment_guard (sourced, dated, allowed fields)"))

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
    if any(x in guards for x in ("claims_gate", "outreach_guard")) or lane in ("content_ops", "gtm_engineering", "ai_seo"):
        ethical.append(("promise_guard" in guards, "no outcome promises reach a reader (honesty)"))
    ethical.append(("manipulation_guard" in guards or lane == "ai_seo", "pressure tactics are flagged for a human (no manipulation)"))

    # ---------- DEPLOYABLE (evidence) ----------
    gs = manifest.get("golden_set")
    rows = _rows(gs) if gs else None
    deploy.append((rows is not None, f"golden set exists ({gs or 'none'})"))
    ev = policy["evidence"]
    claim = manifest.get("claims") or {}
    rate, margin = claim.get("precision", ev["default_rate"]), claim.get("margin", ev["default_margin"])
    need = max(g["min_real_golden_cases"], required_cases(rate, margin, ev["confidence"]))
    real_rows = [r for r in (rows or []) if r.get("source") == "real"]
    deploy.append((len(real_rows) >= need, f"≥ {need} real cases to show {rate:.0%} ±{margin:.0%} at "
                                            f"{ev['confidence']:.0%} confidence (has {len(real_rows)})"))
    short = strata_shortfall(real_rows, need, claim.get("strata", ev["strata"]))
    deploy.append((not short, "real cases cover each stratum" + (
        f" (short: {', '.join(f'{k} {n}' for k, n in short.items())})" if short else "")))
    for j in manifest.get("judges", []):
        cal = j.get("calibration") or {}
        ok = cal.get("labelled_cases", 0) >= g["judge_min_labels"] and cal.get("agreement", 0) >= g["judge_min_agreement"]
        deploy.append((ok, f"judge '{j.get('template')}' calibrated (≥{g['judge_min_labels']} labels, ≥{g['judge_min_agreement']:.0%} agreement)"))
        kappa = cal.get("kappa")
        if j.get("labels"):
            lp = next((b / j["labels"] for b in _BASE if (b / j["labels"]).exists()), None)
            if lp is None:
                deploy.append((False, f"label file for '{j.get('template')}' exists ({j['labels']})"))
            else:
                from .judges import count_labelled
                from .runner import load_rows
                lab = load_rows(lp)
                agr = agreement(lab)
                have = len(agr["agreed"]) if agr["second_labeller"] else count_labelled(lab)["labelled"]
                claimed = cal.get("labelled_cases", 0)
                deploy.append((claimed <= have, f"calibration for '{j.get('template')}' matches its label file "
                                                f"(claims {claimed}, file has {have} labelled)"))
                kappa = agr["kappa"] if agr["second_labeller"] else None
        if ev.get("require_repeat_runs"):
            runs, split, net = cal.get("runs", 1), cal.get("run_disagreement"), cal.get("net")
            deploy.append((runs >= ev["judge_runs"] and split is not None and split <= ev["max_run_disagreement"],
                           f"judge '{j.get('template')}' stable across {ev['judge_runs']} runs "
                           f"(≤ {ev['max_run_disagreement']:.0%} of rows disagreeing; has {runs} run(s)"
                           + (f", {split:.0%}" if split is not None else "") + ")"))
            deploy.append((net is not None and net >= ev["min_judge_net"],
                           f"judge '{j.get('template')}' net score ≥ {ev['min_judge_net']:+.2f} (wrong answers count against it"
                           + (f"; has {net:+.2f})" if net is not None else "; not measured)")))
        if ev.get("require_two_labellers"):
            deploy.append((kappa is not None and kappa >= ev["min_kappa"],
                           f"judge '{j.get('template')}' labels agreed by two labellers (κ ≥ {ev['min_kappa']:.2f}"
                           + (f", has {kappa:.2f})" if kappa is not None else ", no second labeller)")))
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
