"""Checker for the three break-and-fix exercises.   python learn/check.py 1|2|3"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from gtm_evals import claims_gate, load_policy, outreach_guard, visibility_stats  # noqa: E402

LEARN = ROOT / "learn"
DATA = ROOT / "evals" / "datasets"
OK, NO = "✅", "❌"


def jl(name):
    return [json.loads(x) for x in (DATA / name).read_text(encoding="utf-8").splitlines() if x.strip()]


def ex1():
    p = load_policy(LEARN / "policy_exercise.yaml")
    reg = json.loads((DATA / "claims_register_demo.json").read_text(encoding="utf-8"))
    attack = (LEARN / "ex1_attack.txt").read_text(encoding="utf-8").strip()
    if not attack or attack.startswith("#"):
        return print("Write your attack sentence in learn/ex1_attack.txt first.")
    v = claims_gate.check(attack, reg, p)
    words = [w for w in load_policy(profile="clyve")["claims"]["number_words"] if w in attack.lower()]
    if not p["claims"]["block_number_words"]:
        print("PART A: break it")
        if v.passed and words:
            print(f"{OK} You broke it. The gate passed an invented quantity ('{words[0]}').")
            print("   Now PART B: set block_number_words: true in learn/policy_exercise.yaml, then rerun.")
        elif v.passed:
            print(f"{NO} The gate passed it, but there's no invented quantity in it. Make the sentence claim a number.")
        else:
            print(f"{NO} Blocked: {v.violations}. Try writing the number another way.")
        return
    print("PART B: fix it")
    print(f"{OK if not v.passed else NO} your attack is {'now blocked' if not v.passed else 'STILL passing'}")
    alarms = [r["id"] for r in jl("content_drafts.jsonl") if r["expected_pass"] and not claims_gate.check(r["text"], reg, p)]
    print(f"{OK if not alarms else NO} golden-set false alarms: {alarms or 'none'}")
    if not v.passed and not alarms:
        print("\nLesson: every guard has a blind spot. The eval set is how you find it before a founder does.")


def ex2():
    p = load_policy(profile="clyve")
    rows = []
    for cp, hits in (("day0", [8, 10, 6]), ("day30", [11, 10, 12])):
        for run, h in enumerate(hits, 1):
            for i in range(20):
                rows.append({"prompt_id": f"b{i}", "query_type": "brand", "engine": "chatgpt", "checkpoint": cp,
                             "run": run, "mentioned": i < h})
    res = visibility_stats.real_change(rows, "day0", "day30", "brand", p)
    ans = [x.strip().lower() for x in (LEARN / "ex2_answer.txt").read_text(encoding="utf-8").splitlines()
           if x.strip() and not x.startswith("#")]
    if not ans:
        return print("Write your answers in learn/ex2_answer.txt first.")
    print(f"Brand mentions moved {res['before']:.0%} → {res['after']:.0%} (+{res['delta']*100:.0f} pts) across 20 prompts × 3 runs.")
    guess = ans[0]
    truth = "real" if res["real"] else "noise"
    print(f"{OK if guess == truth else NO} Part A: you said '{guess}', the math says '{truth}' "
          f"(run spread {res['noise']*100:.0f} pts, chance band ±{res['z_band']*100:.0f} pts)")
    if len(ans) < 2:
        return print("Add Part B on line 2: how many prompts per query type would you need?")
    try:
        n_guess = int(ans[1])
    except ValueError:
        return print("Line 2 should be a whole number.")
    pbar, delta, z = 0.475, 0.15, p["visibility"]["z"]
    n_min = next(n for n in range(1, 500) if z * math.sqrt(pbar * (1 - pbar) * 2 / (3 * n)) < delta)
    good = n_min <= n_guess <= n_min + 3
    print(f"{OK if good else NO} Part B: you said {n_guess}, the minimum is {n_min} prompts per query type "
          f"(with 3 runs and zero run-to-run spread)")
    print(f"\nLesson: with {n_min} brand prompts you can see a 15-pt move. With 10 you can't, however good the "
          "content is. The prompt set's size decides how small a win you can prove.")


def ex3():
    p = load_policy(LEARN / "policy_exercise.yaml")
    rows = jl("outreach_messages.jsonl")
    base = rows[0]

    def run(claim):
        m = dict(base["message"], claims_about_lead=[claim])
        c = dict(base["context"], suppression=set())
        return outreach_guard.check(m, base["lead"], c, p)

    target = "launched 4 new Meta ads for the winter chai masala range that are already doubling sales"
    v = run(target)
    print(f"{OK if not v.passed else NO} the stretched claim is {'blocked' if not v.passed else 'STILL passing'}")
    alarms = []
    for r in rows:
        if r["expected_pass"]:
            c = dict(r["context"], suppression=set(r["context"]["suppression"]))
            if not outreach_guard.check(r["message"], r["lead"], c, p):
                alarms.append(r["id"])
    print(f"{OK if not alarms else NO} golden-set false alarms: {alarms or 'none'}")
    hidden = ["launched 4 new Meta ads for the winter chai masala range, now selling out weekly",
              "launched 4 new Meta ads for the winter chai masala range and growing 40% a month"]
    caught = sum(not run(h) for h in hidden)
    print(f"{'⭐' if caught == 2 else '·'} bonus: {caught}/2 hidden stretched claims caught")
    print("\nLesson: the cheap rule catches the common stretch. The personalisation judge is there for the rest. "
          "See evals/datasets/layer_gap.jsonl.")


if __name__ == "__main__":
    {"1": ex1, "2": ex2, "3": ex3}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
