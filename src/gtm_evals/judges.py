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
    import anthropic  # optional dependency

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
        out = run(template, r, model)
        total += 1
        agree += int(out["_verdict"] == r["human_verdict"])
        results.append((r.get("id"), out["_verdict"], r.get("human_verdict")))
    return {"labelled_cases": total, "agreement": agree / total if total else 0.0, "results": results}
