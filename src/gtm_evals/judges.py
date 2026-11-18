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
    raw = out.get("verdict", out.get("accuracy", ""))
    return "pass" if str(raw).lower() in PASS_WORDS else "fail"


def run(template: str, values: dict, model: str | None = None) -> dict:
    try:
        import anthropic  # optional dependency
    except ImportError as e:
        raise RuntimeError('running a judge needs the judges extra: pip install "gtm-evals[judges]"') from e

    system, user = render(template, values)
    msg = anthropic.Anthropic().messages.create(model=model or os.environ.get("JUDGE_MODEL", "claude-sonnet-5-5"),
                                                max_tokens=800, system=system, messages=[{"role": "user", "content": user}])
    text = msg.content[0].text
    try:
        out = json.loads(text[text.find("{"): text.rfind("}") + 1])
    except json.JSONDecodeError:
        out = {"verdict": "unparseable", "raw": text}
    out["_verdict"] = normalise(out)
    return out


def calibrate(template: str, rows: list[dict], model: str | None = None) -> dict:
    """rows: dicts with the template's variables + human_verdict. Returns agreement (KPI Q3)."""
    agree = total = 0
    results = []
    for r in rows:
        if r.get("human_verdict") is None:
            continue  # unlabelled (e.g. blank rows of a labelling sheet): don't spend a model call
        if not r.get("today") and r.get("date_sent"):
            r = dict(r, today=r["date_sent"])  # a label sheet's "today" is the day the message went out
        out = run(template, r, model)
        total += 1
        agree += int(out["_verdict"] == r["human_verdict"])
        results.append((r.get("id"), out["_verdict"], r.get("human_verdict")))
    return {"labelled_cases": total, "agreement": agree / total if total else 0.0, "results": results}


# ---------- labelling sheets ----------
LABEL_TAIL = ["human_verdict", "why"]


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
    hv = [str(r.get("human_verdict") or "").strip().lower() for r in rows]
    return {"labelled": sum(v in ("pass", "fail") for v in hv), "pass": hv.count("pass"), "fail": hv.count("fail")}


def update_manifest(path, template_name: str, labelled_cases: int, agreement: float) -> bool:
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
                    lines[k] = (f"{m.group(1)}calibration: {{labelled_cases: {labelled_cases}, "
                                f"agreement: {agreement:.2f}}}     # gtm-evals judge calibrate\n")
                    p.write_text("".join(lines), encoding="utf-8")
                    return True
    return False
