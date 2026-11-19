"""LLM judges: render a template with ground truth, run it, normalise the verdict.

Templates ship in gtm_evals/data/judges/: swap_test, on_thesis, personalisation_factuality,
claim_safety, description_accuracy, promise_check. Rendering needs no API key; running needs
ANTHROPIC_API_KEY and `pip install gtm-evals[judges]`.
"""
from __future__ import annotations

import json
import os
import re
from importlib import resources

PASS_WORDS = {"pass", "on", "accurate"}
ABSTAIN_WORDS = {"abstain", "unsure", "uncertain", "cannot_judge", "insufficient", "insufficient_evidence", "unknown"}


def templates() -> list[str]:
    return sorted(p.name[:-3] for p in resources.files("gtm_evals").joinpath("data", "judges").iterdir() if p.name.endswith(".md"))


def load_template(name_or_path: str) -> str:
    if os.path.exists(name_or_path):
        return open(name_or_path, encoding="utf-8").read()
    return resources.files("gtm_evals").joinpath("data", "judges", f"{name_or_path}.md").read_text(encoding="utf-8")


def render(template: str, values: dict) -> tuple[str, str]:
    body = template.split("---", 1)[-1]
    sys_part, _, user_part = body.partition("USER")
    sys_part = sys_part.replace("SYSTEM", "", 1)
    fill = lambda s: re.sub(r"\{\{(\w+)\}\}", lambda m: str(values.get(m.group(1), m.group(0))), s)
    return fill(sys_part).strip(), fill(user_part).strip()


def missing_vars(template: str, values: dict) -> list[str]:
    return sorted(set(re.findall(r"\{\{(\w+)\}\}", template)) - set(values))


def normalise(out: dict) -> str:
    """Map each template's own vocabulary to pass/fail so agreement can be computed."""
    raw = str(out.get("verdict", out.get("accuracy", ""))).lower()
    if raw in ABSTAIN_WORDS:
        return "abstain"      # an honest "can't tell": scored 0, below right (+1) and above wrong (−1)
    return "pass" if raw in PASS_WORDS else "fail"


def resolve_model(model: str | None = None) -> str:
    return model or os.environ.get("JUDGE_MODEL", "claude-sonnet-5-5")


def _h(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()[:12]


def labels_fingerprint(rows: list[dict]) -> str:
    """Hash of what the labels say (id + both verdicts), so reformatting the sheet doesn't count as a change."""
    keep = sorted((str(r.get("id")), str(r.get("human_verdict")), str(r.get("human_verdict_b")))
                  for r in rows if r.get("human_verdict") is not None)
    return _h(repr(keep).encode("utf-8"))


def evidence_binding(template: str, labels_path=None, model: str | None = None) -> dict:
    """What a calibration was measured on: the template's text, the labels and the judge model.
    Change any of them and the calibration no longer describes the judge you're running."""
    out = {"template_hash": _h(load_template(template).encode("utf-8")), "model": resolve_model(model)}
    if labels_path:
        from .runner import load_rows
        out["labels_hash"] = labels_fingerprint(load_rows(labels_path))
    return out


def git_commit(cwd=None) -> str | None:
    import subprocess
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=cwd, timeout=5)
        return r.stdout.strip() or None if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def packet(template: str, row: dict) -> str:
    """The blind packet: exactly what the judge sees for one row, and nothing else.
    No human labels, no notes, no assertions, no expected answer, no model or tool names."""
    hidden = {"human_verdict", "human_verdict_b", "why", "expected", "expected_pass", "must_demonstrate",
              "must_avoid", "human_review", "model", "generator", "tool", "labeller", "labeller_b"}
    leaked = sorted(set(template_vars(template)) & hidden)
    if leaked:
        raise ValueError(f"row {row.get('id')}: the template would show the judge {', '.join(leaked)}")
    system, user = render(template, {k: v for k, v in row.items() if k not in hidden})
    return f"# Judge packet · {row.get('id', '?')}\n\n## System\n\n{system}\n\n## User\n\n{user}\n"


def run(template: str, values: dict, model: str | None = None) -> dict:
    try:
        import anthropic  # optional dependency
    except ImportError as e:
        raise RuntimeError('running a judge needs the judges extra: pip install "gtm-evals[judges]"') from e

    system, user = render(template, values)
    msg = anthropic.Anthropic().messages.create(model=resolve_model(model),
                                                max_tokens=800, system=system, messages=[{"role": "user", "content": user}])
    text = msg.content[0].text
    try:
        out = json.loads(text[text.find("{"): text.rfind("}") + 1])
    except json.JSONDecodeError:
        out = {"verdict": "unparseable", "raw": text}
    out["_verdict"] = normalise(out)
    return out


def _cache_key(template: str, values: dict, model: str | None, run_i: int) -> str:
    import hashlib
    import json
    blob = json.dumps({"t": template, "v": {k: values[k] for k in sorted(values)}, "m": model or "", "r": run_i},
                      sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def _cached_run(template: str, values: dict, model: str | None, run_i: int, cache_dir) -> dict:
    """judges.run, remembered on disk by (template, row, model, run number): a rerun costs nothing."""
    import json
    from pathlib import Path
    if cache_dir is None:
        return run(template, values, model)
    p = Path(cache_dir) / f"{_cache_key(template, values, model, run_i)}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    out = run(template, values, model)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, default=str), encoding="utf-8")
    return out


def calibrate(template: str, rows: list[dict], model: str | None = None, runs: int = 1,
              cache_dir=None, max_calls: int | None = None) -> dict:
    """rows: dicts with the template's variables + human_verdict (+ human_verdict_b from a second labeller).

    - Two labellers: only rows both agree on are used, and κ is reported.
    - runs > 1: each row is judged `runs` times; the row's verdict is the majority, and
      `run_disagreement` is the share of rows whose runs didn't all agree.
    - Scoring: right +1, abstain 0, wrong −1. `agreement` = right / rows answered (KPI Q3),
      `net` = (right − wrong) / rows, so a judge that guesses scores below one that says "can't tell".
    - max_calls: stop cleanly when the next row would exceed it; `complete` says whether every row ran.
    """
    from collections import Counter

    from .evidence import agreement as two_labellers
    agr = two_labellers(rows)
    if agr["second_labeller"]:
        keep = set(agr["agreed"])
        rows = [r for r in rows if r.get("id") in keep]
    right = wrong = abstained = split = calls = 0
    results = []
    complete = True
    for r in rows:
        if r.get("human_verdict") is None:
            continue  # unlabelled (e.g. blank rows of a labelling sheet): don't spend a model call
        if max_calls is not None and calls + runs > max_calls:
            complete = False
            break
        if not r.get("today") and r.get("date_sent"):
            r = dict(r, today=r["date_sent"])  # a label sheet's "today" is the day the message went out
        verdicts = [_cached_run(template, r, model, i, cache_dir)["_verdict"] for i in range(runs)]
        calls += runs
        top = Counter(verdicts).most_common()
        verdict = top[0][0] if len(top) == 1 or top[0][1] > top[1][1] else "abstain"   # a tie can't be trusted
        split += int(len(set(verdicts)) > 1)
        if verdict == "abstain":
            abstained += 1
        elif verdict == r["human_verdict"]:
            right += 1
        else:
            wrong += 1
        results.append((r.get("id"), verdict, r.get("human_verdict")))
    total = right + wrong + abstained
    answered = right + wrong
    out = {"labelled_cases": total, "agreement": right / answered if answered else 0.0,
           "net": (right - wrong) / total if total else 0.0, "abstained": abstained,
           "runs": runs, "run_disagreement": split / total if total else 0.0,
           "calls": calls, "complete": complete, "results": results}
    if agr["second_labeller"]:
        out.update(kappa=agr["kappa"], disagree=agr["disagree"])
    return out


# ---------- labelling sheets ----------
LABEL_TAIL = ["human_verdict", "human_verdict_b", "why"]   # _b: a second labeller, without seeing the first


def template_vars(template: str) -> list[str]:
    """Variables a template needs, in first-use order, with the message text first."""
    import re
    seen = []
    for v in re.findall(r"{{\s*(\w+)\s*}}", template):
        if v not in seen:
            seen.append(v)
    return sorted(seen, key=lambda v: v != "text")


def label_columns(template: str) -> list[str]:
    return ["id", *template_vars(template), *LABEL_TAIL]


def blank_label_rows(template: str, n: int = 30, prefix: str = "L", defaults: dict | None = None) -> list[dict]:
    cols = label_columns(template)
    return [{c: (f"{prefix}{i:02d}" if c == "id" else (defaults or {}).get(c, "")) for c in cols} for i in range(1, n + 1)]


def count_labelled(rows: list[dict]) -> dict:
    """Rows with a pass/fail label. With a second labeller (human_verdict_b), only rows both agree on count."""
    if any(str(r.get("human_verdict_b") or "").strip().lower() in ("pass", "fail") for r in rows):
        from .evidence import agreement as two_labellers
        agr = two_labellers(rows)
        keep = set(agr["agreed"])
        rows = [r for r in rows if r.get("id") in keep]
    hv = [str(r.get("human_verdict") or "").strip().lower() for r in rows]
    return {"labelled": sum(v in ("pass", "fail") for v in hv), "pass": hv.count("pass"), "fail": hv.count("fail")}


def update_manifest(path, template_name: str, labelled_cases: int, agreement: float, kappa: float | None = None,
                    extra: dict | None = None) -> bool:
    """Write a calibration result into a workflow manifest in place, keeping its comments.
    Returns False if the manifest has no judge entry for this template."""
    import re
    from pathlib import Path
    p = Path(path)
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    for i, line in enumerate(lines):
        if re.search(rf"template:\s*{re.escape(template_name)}\b", line):
            for k in range(i + 1, min(i + 6, len(lines))):
                m = re.match(r"(\s*)calibration:\s*{[^}]*}(.*)", lines[k].rstrip("\n"))
                if m:
                    kap = f", kappa: {kappa:.2f}" if kappa is not None else ""
                    for key, val in (extra or {}).items():
                        if val is None:
                            continue
                        kap += (f", {key}: {val:.2f}" if isinstance(val, float)
                                else f', {key}: "{val}"' if isinstance(val, str) else f", {key}: {val}")
                    lines[k] = (f"{m.group(1)}calibration: {{labelled_cases: {labelled_cases}, "
                                f"agreement: {agreement:.2f}{kap}}}     # gtm-evals judge calibrate\n")
                    p.write_text("".join(lines), encoding="utf-8")
                    return True
    return False
