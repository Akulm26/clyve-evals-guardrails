"""Run an LLM judge template over a JSONL dataset and compare with human labels.

    python evals/judge.py evals/judges/swap_test.md data.jsonl --vars brand="Ghar Ka Masala" competitors="A, B"

Each dataset row needs "text" (or the fields the template uses) and optionally "human_verdict".
Prints agreement with human labels. Below ~85%, fix the rubric before trusting the judge.
Needs ANTHROPIC_API_KEY and `pip install anthropic`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys


def render(template: str, values: dict) -> tuple[str, str]:
    body = template.split("---", 1)[-1]
    sys_part, _, user_part = body.partition("USER")
    sys_part = sys_part.replace("SYSTEM", "", 1)
    fill = lambda s: re.sub(r"\{\{(\w+)\}\}", lambda m: str(values.get(m.group(1), f"{{{{{m.group(1)}}}}}")), s)
    return fill(sys_part).strip(), fill(user_part).strip()


PASS_WORDS = {"pass", "on", "accurate"}  # everything else (fail, adjacent, off, partly, inaccurate, needs_review) is not a pass


def normalise(out: dict) -> str:
    """Map each template's own vocabulary to pass/fail so agreement can be computed."""
    raw = out.get("verdict", out.get("accuracy", ""))
    return "pass" if str(raw).lower() in PASS_WORDS else "fail"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template")
    ap.add_argument("dataset")
    ap.add_argument("--model", default=os.environ.get("JUDGE_MODEL", "claude-sonnet-5-5"))
    ap.add_argument("--vars", nargs="*", default=[])
    a = ap.parse_args()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY to run model judges. Deterministic evals: python evals/run_evals.py")
    import anthropic

    client = anthropic.Anthropic()
    tmpl = open(a.template, encoding="utf-8").read()
    extra = dict(kv.split("=", 1) for kv in a.vars)
    agree = total = 0
    for line in open(a.dataset, encoding="utf-8"):
        if not line.strip():
            continue
        row = json.loads(line)
        system, user = render(tmpl, {**extra, **row})
        msg = client.messages.create(model=a.model, max_tokens=800, system=system,
                                     messages=[{"role": "user", "content": user}])
        out = msg.content[0].text
        try:
            verdict = normalise(json.loads(out[out.find("{"): out.rfind("}") + 1]))
        except json.JSONDecodeError:
            verdict = "unparseable"
        human = row.get("human_verdict")
        if human is not None:
            total += 1
            agree += int(human == verdict)
        print(f"{row.get('id', '?'):6} judge={verdict:12} human={human}")
    if total:
        print(f"\nagreement with human labels: {agree}/{total} = {agree / total:.0%}")


if __name__ == "__main__":
    main()
