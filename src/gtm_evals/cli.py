"""gtm-evals command line.

    gtm-evals init                       scaffold config, a workflow manifest, a golden set
    gtm-evals gate workflows/*.yaml      DEPLOYABLE / PILOT ONLY / BLOCKED per workflow
    gtm-evals eval evals/*.jsonl         score the guards on your golden sets
    gtm-evals check draft.txt            run text guards on a draft (claims, promises, pressure, PII, injection)
                                         --category food adds the regulated-claims check
    gtm-evals seo page.html              AI SEO: crawler access, readable without JS, schema, entity consistency
    gtm-evals visibility runs.jsonl      did AI visibility really move? (noise + chance bands)
    gtm-evals judge list|render|labels|status|agreement|calibrate
    gtm-evals policy --show              print the effective policy
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from importlib import resources
from pathlib import Path

from . import (__version__, ai_seo_guard, claim_safety_guard, claims_gate, injection_guard, judges, manipulation_guard,
               pii_guard, promise_guard, visibility_stats)
from .core import combine, list_profiles, load_policy
from .gate import check as gate_check
from .gate import report as gate_report
from .runner import load_rows, score

OK, NO = "✅", "❌"


def _policy(a):
    return load_policy(getattr(a, "policy", None), getattr(a, "profile", None))


def cmd_init(a):
    dest = Path(a.dir)
    src = resources.files("gtm_evals").joinpath("data", "templates")
    made = []

    def walk(node, rel=Path()):
        for item in node.iterdir():
            r = rel / item.name
            if item.is_dir():
                walk(item, r)
                continue
            target = dest / r
            if target.exists() and not a.force:
                print(f"  skip  {r} (exists)")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(item.read_bytes())
            made.append(str(r))
    walk(src)
    for m in made:
        print(f"  made  {m}")
    print("\nNext:\n  1. gtm-evals eval evals/golden.jsonl      score the guards on the sample cases"
          "\n  2. edit workflows/outreach.yaml           set owner and human_approver (blocked until you do)"
          "\n  3. gtm-evals gate workflows/*.yaml        DEPLOYABLE / PILOT ONLY / BLOCKED"
          "\n  4. add your own real cases to evals/golden.jsonl with \"source\": \"real\""
          "\n  5. gtm-evals judge labels <judge>           a labelling sheet to calibrate an LLM judge")


def cmd_redteam(a):
    import yaml

    from . import redteam
    p = _policy(a)
    if a.action == "init":
        m = yaml.safe_load(Path(a.path).read_text(encoding="utf-8")) or {}
        cfg = redteam.config(m, p)
        canary = cfg["metadata"]["gtm_evals_canary"]
        text = yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)
        if a.out:
            Path(a.out).write_text(text, encoding="utf-8")
            print(f"wrote {a.out} ({len(cfg['redteam']['plugins'])} plugins)")
        else:
            print(text)
        if not (m.get("redteam") or {}).get("canary"):
            print(f"ℹ️ put this canary in the bot's system prompt and in the manifest (redteam.canary): {canary}",
                  file=sys.stderr)
        return 0
    canary = a.canary
    if a.manifest:
        canary = canary or ((yaml.safe_load(Path(a.manifest).read_text(encoding="utf-8")) or {}).get("redteam") or {}).get("canary")
    s = redteam.score(a.path, canary, p)
    rc = p["redteam"]
    print(f"{OK if s['ok'] else NO} {s['passed']}/{s['total']} red-team tests passed ({s['pass_rate']:.0%}; "
          f"gate: ≥ {rc['min_pass_rate']:.0%} on ≥ {rc['min_tests']})")
    for k, b in s["by_plugin"].items():
        print(f"  {k:28} {b['passed']}/{b['tests']}")
    if not canary:
        print("ℹ️ no canary given: system-prompt leaks weren't checked")
    elif s["leaks"]:
        print(f"{NO} the canary leaked in {len(s['leaks'])} reply(ies): the bot reveals its instructions")
    return 0 if s["ok"] else 1


def cmd_gate(a):
    import yaml
    p = _policy(a)
    blocked = False
    out = []
    for path in a.manifests:
        res = gate_check(yaml.safe_load(Path(path).read_text(encoding="utf-8")), p, base_dir=a.base or Path.cwd())
        blocked |= res["verdict"] == "BLOCKED"
        out.append(res)
        if not a.json:
            print(gate_report(res))
    if a.json:
        print(json.dumps([{**r, **{k: [{"ok": o, "check": m} for o, m in r[k]] for k in ("safe", "ethical", "deployable")}} for r in out], indent=1, ensure_ascii=False))
    return 1 if blocked else 0


def cmd_eval(a):
    p = _policy(a)
    all_ok = True
    for path in a.golden:
        try:
            res = score(load_rows(path), p, Path(path).parent.parent if Path(path).parent.name == "evals" else Path(path).parent)
        except (ValueError, KeyError, FileNotFoundError) as e:
            print(f"{NO} {path}: {e}", file=sys.stderr)
            return 2
        print(f"\n{path}  ·  {res['n']} cases ({res['real']} real)")
        if res.get("human_review"):
            print(f"  ℹ️ {len(res['human_review'])} case(s) marked human_review: a person decides, not scored: {res['human_review']}")
        for g, s in res["guards"].items():
            print(f"  {OK if s['ok'] else NO} {g:17} recall {s['recall']:.2f}  precision {s['precision']:.2f}"
                  + (f"  misses: {s['misses']}" if s["misses"] else "") + (f"  false alarms: {[x for x, _ in s['false_alarms']]}" if s["false_alarms"] else ""))
        all_ok &= res["ok"]
    return 0 if all_ok else 1


def cmd_check(a):
    p = _policy(a)
    text = Path(a.file).read_text(encoding="utf-8") if a.file != "-" else sys.stdin.read()
    reg = json.loads(Path(a.register).read_text(encoding="utf-8")) if a.register else None
    vs = [promise_guard.check(text, p), manipulation_guard.check(text, p), pii_guard.check(text), injection_guard.check(text)]
    if reg is not None:
        vs.insert(0, claims_gate.check(text, reg, p))
    if a.category or a.competitor:
        vs.append(claim_safety_guard.check(text, a.category, p, a.competitor))
    v = combine(*vs)
    if a.json:
        print(json.dumps(v.to_dict(), indent=1, ensure_ascii=False))
    else:
        print(f"{OK} passes all text guards" if v else f"{NO} {len(v.violations)} issue(s)" + (" · escalate to a human" if v.escalate else ""))
        for x in v.violations:
            print(f"   {x}")
        for x in v.notes:
            print(f"   ℹ️  {x}")
        if reg is None:
            print("   (no --register given, so numbers were not checked against a claims register)")
    return 0 if v else 1


def cmd_seo(a):
    p = _policy(a)
    read = lambda f: Path(f).read_text(encoding="utf-8")
    sections, ok = [], True
    if a.robots:
        r = read(a.robots)
        v = ai_seo_guard.crawler_access(r, p, a.path)
        sections.append(("AI search crawlers", v))
        train = ai_seo_guard.training_access(r, p, a.path)
        blocked = [b for b, allowed in train.items() if not allowed]
        sections.append(("training crawlers (client's choice, not a failure)",
                         f"blocked: {', '.join(blocked)}" if blocked else "all allowed"))
    if a.page:
        html = read(a.page)
        sections.append(("readable without JavaScript", ai_seo_guard.raw_html(html, p, a.must)))
        types = [t.strip() for t in a.schema.split(",")] if a.schema else None
        sections.append(("schema (JSON-LD)", ai_seo_guard.schema(html, p, types)))
    if a.entity:
        d = json.loads(read(a.entity))
        sections.append(("entity consistency", ai_seo_guard.entity_consistency(d["profiles"], d["canonical"], p)))
    if not sections:
        print(f"{NO} give a page, --robots or --entity (see: gtm-evals seo --help)", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps({t: (v.to_dict() if hasattr(v, "to_dict") else v) for t, v in sections}, indent=1, ensure_ascii=False))
    for title, v in sections:
        if isinstance(v, str):
            if not a.json:
                print(f"  ℹ️  {title}: {v}")
            continue
        ok &= bool(v)
        if not a.json:
            print(f"  {OK if v else NO} {title}")
            for x in v.violations:
                print(f"     - {x}")
            for x in v.notes:
                print(f"     ℹ️  {x}")
    return 0 if ok else 1


def cmd_visibility(a):
    p = _policy(a)
    rows = load_rows(a.runs)
    for prob in visibility_stats.validate_rows(rows, p):
        print(f"  {NO} {prob}")
    code = 0
    for qt in p["visibility"]["query_types"]:
        if not any(r.get("query_type") == qt for r in rows):
            continue
        try:
            r = visibility_stats.real_change(rows, a.before, a.after, qt, p, engine=a.engine)
        except ValueError as e:
            print(f"  {qt:8} {e}")
            continue
        n = sum(1 for x in rows if x["checkpoint"] == a.before and x["query_type"] == qt and (a.engine is None or x["engine"] == a.engine))
        print(f"  {qt:8} {r['before']:.0%} → {r['after']:.0%}  ({r['delta'] * 100:+.1f} pts; noise {r['noise'] * 100:.1f}, chance ±{r['z_band'] * 100:.1f}, "
              f"smallest provable {visibility_stats.smallest_provable_move(n) * 100:.0f})  {r['verdict']}")
    return code


def cmd_judge(a):
    if a.action == "list":
        for t in judges.templates():
            print(t)
        return 0
    t = judges.load_template(a.template)
    vals = dict(kv.split("=", 1) for kv in (a.vars or []))
    for kv in a.var_file or []:
        k, f = kv.split("=", 1)
        vals[k] = Path(f).read_text(encoding="utf-8")
    if a.action == "render":
        miss = judges.missing_vars(t, vals)
        s, u = judges.render(t, vals)
        print(f"### SYSTEM\n{s}\n\n### USER\n{u}")
        if miss:
            print(f"\n(unfilled: {', '.join(miss)})", file=sys.stderr)
        return 0
    if a.action == "labels":
        import csv
        out = Path(a.dataset or f"evals/labels/{Path(a.template).stem}.csv")
        if out.exists() and not a.force:
            print(f"{out} exists — add --force to overwrite")
            return 1
        out.parent.mkdir(parents=True, exist_ok=True)
        defaults = dict(kv.split("=", 1) for kv in (a.vars or []))
        defaults.setdefault("freshness_days", str(load_policy()["outreach"]["signal_freshness_days"]))
        rows = judges.blank_label_rows(t, a.rows, defaults=defaults)
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=judges.label_columns(t))
            w.writeheader(); w.writerows(rows)
        print(f"made {out}: {a.rows} blank rows, columns {', '.join(judges.label_columns(t))}")
        print("Open it in any spreadsheet, fill one real case per row, set human_verdict to pass or fail, "
              f"then: gtm-evals judge calibrate {a.template} {out}")
        return 0
    if a.action == "agreement":
        from .evidence import agreement as two_labellers
        if not a.dataset:
            print(f"{NO} agreement needs a label file: gtm-evals judge agreement {a.template} labels.csv", file=sys.stderr)
            return 2
        r = two_labellers(load_rows(a.dataset))
        if not r["second_labeller"]:
            print(f"{NO} no second labeller yet: fill the human_verdict_b column without looking at human_verdict")
            return 1
        need = load_policy()["evidence"]["min_kappa"]
        print(f"{OK if r['kappa'] >= need else NO} κ {r['kappa']:.2f} on {r['both_labelled']} rows both labelled "
              f"(need ≥ {need:.2f}); they agree on {len(r['agreed'])}")
        for i in r["disagree"]:
            print(f"  disagree  {i}: settle it with a third person, or drop the row")
        return 0 if r["kappa"] >= need else 1
    if a.action == "status":
        if not a.dataset:
            print(f"{NO} status needs a label file: gtm-evals judge status {a.template} labels.csv", file=sys.stderr)
            return 2
        c = judges.count_labelled(load_rows(a.dataset))
        ready = c["labelled"] >= 30 and c["pass"] >= 10 and c["fail"] >= 10
        print(f"{c['labelled']}/30 labelled · {c['pass']} pass · {c['fail']} fail · "
              + ("ready to calibrate" if ready else "not ready (need 30, with ≥10 pass and ≥10 fail)"))
        return 0 if ready else 1
    if a.action == "packet":
        if not a.dataset:
            print(f"{NO} packet needs a label file: gtm-evals judge packet {a.template} labels.csv --id L01", file=sys.stderr)
            return 2
        rows = [r for r in load_rows(a.dataset) if not a.id or str(r.get("id")) == a.id]
        if not rows:
            print(f"{NO} no row with id {a.id}", file=sys.stderr)
            return 2
        try:
            text = "\n---\n\n".join(judges.packet(t, r) for r in rows)
        except ValueError as e:
            print(f"{NO} {e}", file=sys.stderr)
            return 1
        if a.out:
            Path(a.out).write_text(text, encoding="utf-8")
            print(f"wrote {len(rows)} blind packet(s) to {a.out}: no labels, notes or expected answers")
        else:
            print(text)
        return 0
    if a.action == "calibrate":
        import os
        if not a.dataset:
            print(f"{NO} calibrate needs a label file: gtm-evals judge calibrate {a.template} labels.csv", file=sys.stderr)
            return 2
        rows = load_rows(a.dataset)
        if judges.count_labelled(rows)["labelled"] and not os.environ.get("ANTHROPIC_API_KEY"):
            print(f"{NO} set ANTHROPIC_API_KEY to run the judge (labels are counted with: gtm-evals judge status)", file=sys.stderr)
            return 2
        ev = load_policy()["evidence"]
        runs = a.runs or ev["judge_runs"]
        try:
            res = judges.calibrate(t, rows, a.model, runs=runs, cache_dir=None if a.no_cache else a.cache,
                                   max_calls=a.max_calls)
        except RuntimeError as e:
            print(f"{NO} {e}", file=sys.stderr)
            return 2
        print(f"agreement {res['agreement']:.0%} on {res['labelled_cases']} labelled cases (gate: ≥85% on ≥30)")
        print(f"net score {res['net']:+.2f} (right +1, can't-tell 0, wrong −1; gate ≥ {ev['min_judge_net']:+.2f}); "
              f"{res['abstained']} abstained")
        print(f"{res['runs']} run(s) per row; runs disagreed on {res['run_disagreement']:.0%} of rows "
              f"(gate ≤ {ev['max_run_disagreement']:.0%}); {res['calls']} model calls")
        if not res["complete"]:
            print(f"{NO} stopped at --max-calls {a.max_calls}: not every labelled row was judged")
        if "kappa" in res:
            print(f"two labellers: κ {res['kappa']:.2f}; {len(res['disagree'])} rows they disagree on were left out")
        for rid, got, want in res["results"]:
            if got != want:
                print(f"  disagree  {rid}: judge {got}, human {want}")
        if a.update:
            ok = judges.update_manifest(a.update, Path(a.template).stem, res["labelled_cases"], res["agreement"],
                                        res.get("kappa"), extra={"net": round(res["net"], 2), "runs": res["runs"],
                                                                 "run_disagreement": round(res["run_disagreement"], 2),
                                                                 **judges.evidence_binding(a.template, a.dataset, a.model),
                                                                 "commit": judges.git_commit()})
            print(f"{'updated' if ok else 'no judge entry for this template in'} {a.update}")
        good = (res["complete"] and res["labelled_cases"] >= 30 and res["agreement"] >= 0.85
                and res["net"] >= ev["min_judge_net"] and res["run_disagreement"] <= ev["max_run_disagreement"])
        return 0 if good else 1


def cmd_policy(a):
    import yaml
    if a.profiles:
        print("\n".join(list_profiles()))
        return 0
    print(yaml.safe_dump(_policy(a), sort_keys=False, allow_unicode=True))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gtm-evals", description="Evals and guardrails for AI GTM engineering.")
    ap.add_argument("--version", action="version", version=f"gtm-evals {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--policy", help="config file (default: ./gtm-evals.yaml if present)")
        p.add_argument("--profile", help=f"preset layered under your config: {', '.join(list_profiles())}")

    p = sub.add_parser("init", help="scaffold config, a workflow manifest and a golden set"); p.add_argument("dir", nargs="?", default="."); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_init)
    p = sub.add_parser("redteam", help="promptfoo red-team config from the policy, and scoring its results")
    p.add_argument("action", choices=["init", "score"]); p.add_argument("path", help="init: a workflow manifest · score: promptfoo results.json")
    p.add_argument("-o", "--out"); p.add_argument("--canary"); p.add_argument("--manifest", help="score: read the canary from here")
    common(p); p.set_defaults(fn=cmd_redteam)
    p = sub.add_parser("gate", help="rule workflows DEPLOYABLE / PILOT ONLY / BLOCKED"); p.add_argument("manifests", nargs="+"); p.add_argument("--base", help="resolve golden-set paths from here"); p.add_argument("--json", action="store_true"); common(p); p.set_defaults(fn=cmd_gate)
    p = sub.add_parser("eval", help="score guards on golden sets"); p.add_argument("golden", nargs="+"); common(p); p.set_defaults(fn=cmd_eval)
    p = sub.add_parser("check", help="run text guards on a draft ('-' for stdin)"); p.add_argument("file"); p.add_argument("--register", help="claims register JSON"); p.add_argument("--json", action="store_true")
    p.add_argument("--category", help="product category, e.g. food or skincare: adds the regulated-claims check")
    p.add_argument("--competitor", action="append", help="a competitor's name; naming one needs proof"); common(p); p.set_defaults(fn=cmd_check)
    p = sub.add_parser("seo", help="AI SEO: crawler access, readable without JS, schema, entity consistency")
    p.add_argument("page", nargs="?", help="a saved HTML page (as served, before JavaScript)"); p.add_argument("--robots", help="the site's robots.txt")
    p.add_argument("--path", default="/", help="URL path checked against robots.txt (default /)")
    p.add_argument("--must", action="append", help="a phrase that must be in the raw HTML (repeatable)")
    p.add_argument("--schema", help="required schema types, comma-separated (default from policy: Organization)")
    p.add_argument("--entity", help='JSON: {"canonical": {...}, "profiles": {channel: {name, description}}}')
    p.add_argument("--json", action="store_true"); common(p); p.set_defaults(fn=cmd_seo)
    p = sub.add_parser("visibility", help="did AI visibility really move?"); p.add_argument("runs"); p.add_argument("--before", default="day0"); p.add_argument("--after", default="day30"); p.add_argument("--engine"); common(p); p.set_defaults(fn=cmd_visibility)
    p = sub.add_parser("judge", help="LLM judge templates"); p.add_argument("action", choices=["list", "render", "labels", "status", "agreement", "calibrate", "packet"]); p.add_argument("template", nargs="?"); p.add_argument("dataset", nargs="?")
    p.add_argument("--rows", type=int, default=30, help="labels: number of blank rows"); p.add_argument("--force", action="store_true")
    p.add_argument("--update", metavar="MANIFEST", help="calibrate: write the result into this workflow manifest")
    p.add_argument("--runs", type=int, help="calibrate: judge each row this many times (default: policy evidence.judge_runs)")
    p.add_argument("--cache", default=".gtm-evals-cache/judges", help="calibrate: where judge results are cached")
    p.add_argument("--no-cache", action="store_true", help="calibrate: always call the model")
    p.add_argument("--max-calls", type=int, help="calibrate: stop before making more model calls than this")
    p.add_argument("--id", help="packet: only this row")
    p.add_argument("-o", "--out", help="packet: write to this file")
    p.add_argument("--var", dest="vars", action="append", help="key=value"); p.add_argument("--var-file", action="append", help="key=path (file contents become the value)"); p.add_argument("--model"); p.set_defaults(fn=cmd_judge)
    p = sub.add_parser("policy", help="print the effective policy"); p.add_argument("--show", action="store_true"); p.add_argument("--profiles", action="store_true"); common(p); p.set_defaults(fn=cmd_policy)

    a = ap.parse_args(argv)
    if a.cmd == "judge" and a.action != "list" and not a.template:
        ap.error("judge render/labels/status/agreement/calibrate needs a template name (see: gtm-evals judge list)")
    sys.exit(a.fn(a) or 0)


if __name__ == "__main__":
    main()
