"""Score the simulated judge run and the two-layer (code + judge) coverage of held-out misses."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from evals.judge import normalise  # noqa: E402

cases = json.loads((ROOT / "sim/results/judge_cases.json").read_text())
outs = json.loads((ROOT / "sim/results/judge_sim_outputs.json").read_text())["outputs"]
agree = sum(normalise(outs[c["id"]]) == c["human_verdict"] for c in cases)
print(f"Judge simulation: {agree}/{len(cases)} verdicts match the expected label (templates render, schemas parse)")
by = {}
for c in cases:
    by.setdefault(c["template"], []).append(normalise(outs[c["id"]]) == c["human_verdict"])
for t, r in by.items():
    print(f"  {t:28} {sum(r)}/{len(r)}")
# held-out misses the code layer let through, and which judge case covers each
cover = {"Nearly half our buyers reorder.": "J07", "Our repeat rate doubled last year.": "J06",
         "Expect to see your brand in ChatGPT answers within a fortnight.": "J01",
         "This will definitely increase your sales.": "J02", "Congrats on the Shark Tank feature!": "J12"}
hold = json.loads((ROOT / "sim/results/holdout.json").read_text())
misses = [h for h in hold if h["expected"] != h["got"]]
caught = [m for m in misses if m["input"] in cover and normalise(outs[cover[m["input"]]]) == "fail"]
code_ok = len(hold) - len(misses)
print(f"\nHeld-out, code layer alone: {code_ok}/{len(hold)}")
print(f"Held-out, code + judge layer: {code_ok + len(caught)}/{len(hold)}")
for m in misses:
    print(f"  {'caught by ' + cover[m['input']] if m in caught else 'NOT CAUGHT':16} {m['input']}")
