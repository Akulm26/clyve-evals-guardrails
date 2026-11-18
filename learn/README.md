# Learn by breaking things

Three exercises, about 10 minutes each. In each one you **break a guard, then fix it**. Nothing to read first.

Everything runs against `learn/policy_exercise.yaml`, a copy of the real policy with two rules switched off.

---

## 1 · Sneak a fake number past the claims gate

**Break:** write one sentence in `learn/ex1_attack.txt` that claims a number this brand can't prove, and still passes the gate.
```bash
python learn/check.py 1
```
*Hint: the gate looks for digits.*

**Fix:** set `block_number_words: true` in `learn/policy_exercise.yaml`. Rerun. Your attack should now be blocked, with **zero** false alarms on the golden set.

---

## 2 · Is it a win or is it noise?

Brand-query mentions went from 40% to 55% between Day 0 and Day 30 (20 prompts, 3 runs each).

In `learn/ex2_answer.txt`:
- **Line 1:** `real` or `noise`? Decide before you run anything.
- **Line 2:** how many brand prompts would you need to prove a 15-point move? (3 runs, assume runs agree perfectly)

```bash
python learn/check.py 2
```

---

## 3 · Catch the stretched personalisation

The lead's real signal: *"launched 4 new Meta ads for the winter chai masala range"*.
The opener says: *"…launched 4 new Meta ads for the winter chai masala range that are already doubling sales."*

The word-overlap check passes it (most of the words match). Run it and see:
```bash
python learn/check.py 3
```

**Fix:** fill `outreach.outcome_words` in `learn/policy_exercise.yaml` with results words that a claim may only use if the signal itself contains them. Match is by word start, so `doubl` catches *doubling*. Block the stretch, keep zero false alarms, and try for the bonus.

---

When you're done, compare your fixes with `policies/clyve_policy.yaml`. The real policy ships with both rules on.
