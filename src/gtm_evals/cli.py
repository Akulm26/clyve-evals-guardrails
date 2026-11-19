"""gtm-evals command line.

    gtm-evals init                       scaffold config, a workflow manifest, a golden set
    gtm-evals gate workflows/*.yaml      DEPLOYABLE / PILOT ONLY / BLOCKED per workflow
    gtm-evals eval evals/*.jsonl         score the guards on your golden sets
    gtm-evals check draft.txt            run text guards on a draft (claims, promises, pressure, PII, injection)
                                         --category food adds the regulated-claims check
    gtm-evals seo page.html              AI SEO: crawler access, readable without JS, schema, entity consistency
    gtm-evals visibility runs.jsonl      did AI visibility really move? (noise + chance bands)
    gtm-evals judge list|render|labels|status|calibrate
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
    if a.action == "status":
        if not a.dataset:
            print(f"{NO} status needs a label file: gtm-evals judge status {a.template} labels.csv", file=sys.stderr)
            return 2
        c = judges.count_labelled(load_rows(a.dataset))
        ready = c["labelled"] >= 30 and c["pass"] >= 10 and c["fail"] >= 10
        print(f"{c['labelled']}/30 labelled · {c['pass']} pass · {c['fail']} fail · "
              + ("ready to calibrate" if ready else "not ready (need 30, with ≥10 pass and ≥10 fail)"))
        return 0 if ready else 1
    if a.action == "calibrate":
        import os
        if not a.dataset:
            print(f"{NO} calibrate needs a label file: gtm-evals judge calibrate {a.template} labels.csv", file=sys.stderr)
            return 2
        rows = load_rows(a.dataset)
        if judges.count_labelled(rows)["labelled"] and not os.environ.get("ANTHROPIC_API_KEY"):
            print(f"{NO} set ANTHROPIC_API_KEY to run the judge (labels are counted with: gtm-evals judge status)", file=sys.stderr)
            return 2
        try:
            res = judges.calibrate(t, rows, a.model)
        except RuntimeError as e:
            print(f"{NO} {e}", file=sys.stderr)
            return 2
        print(f"agreement {res['agreement']:.0%} on {res['labelled_cases']} labelled cases (gate: ≥85% on ≥30)")
        for rid, got, want in res["results"]:
            if got != want:
                print(f"  disagree  {rid}: judge {got}, human {want}")
        if a.update:
            ok = judges.update_manifest(a.update, Path(a.template).stem, res["labelled_cases"], res["agreement"])
            print(f"{'updated' if ok else 'no judge entry for this template in'} {a.update}")
        return 0 if res["labelled_cases"] >= 30 and res["agreement"] >= 0.85 else 1


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
    p = sub.add_parser("judge", help="LLM judge templates"); p.add_argument("action", choices=["list", "render", "labels", "status", "calibrate"]); p.add_argument("template", nargs="?"); p.add_argument("dataset", nargs="?")
    p.add_argument("--rows", type=int, default=30, help="labels: number of blank rows"); p.add_argument("--force", action="store_true")
    p.add_argument("--update", metavar="MANIFEST", help="calibrate: write the result into this workflow manifest")
    p.add_argument("--var", dest="vars", action="append", help="key=value"); p.add_argument("--var-file", action="append", help="key=path (file contents become the value)"); p.add_argument("--model"); p.set_defaults(fn=cmd_judge)
    p = sub.add_parser("policy", help="print the effective policy"); p.add_argument("--show", action="store_true"); p.add_argument("--profiles", action="store_true"); common(p); p.set_defaults(fn=cmd_policy)

    a = ap.parse_args(argv)
    if a.cmd == "judge" and a.action != "list" and not a.template:
        ap.error("judge render/labels/status/calibrate needs a template name (see: gtm-evals judge list)")
    sys.exit(a.fn(a) or 0)


if __name__ == "__main__":
    main()
