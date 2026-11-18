# 04 · The eval system

## Build order

```
1. Write down what "good" means       → rubric with pass/fail anchors, not 1–10 vibes
2. Build a golden set                 → 30–50 real cases, hand-labelled, incl. the nasty ones
3. Deterministic evals first          → L1, in CI, every change
4. Judge evals second                 → L2, calibrated against your labels before you trust them
5. Online evals                       → sample production, cheap signals (approver edits, replies)
6. Outcome evals                      → L3, per checkpoint, against a frozen baseline
```

## Golden sets

Every lane has one in `evals/datasets/`. Each row is an input, the expected verdict, and *why*.

**What goes in:**
- ~60% normal cases (they should pass)
- ~30% known failure patterns (invented stat, missing stamp, stale signal, duplicate send)
- ~10% adversarial (injection in a review, a "guaranteed" hidden mid-sentence, a lookalike competitor name)

**Where cases come from:** every time a human approver rejects or edits something, the before/after becomes a candidate row. That's the cheapest data-collection loop you'll ever get.

## LLM judges, done properly

A judge is only as good as its reference. Rules:

1. **Binary or 3-level anchors.** "Pass / fail with the failing line quoted" beats "rate 1–10". Scales drift; quotes can be checked.
2. **Give it ground truth.** The on-thesis judge gets the thesis sentence and claims register. The swap-test judge gets the named competitors. The personalisation judge gets the lead's actual signals.
3. **Ask for evidence first, verdict last.** The output schema forces `evidence` before `verdict`.
4. **Calibrate before you trust it.** Run the judge on 30+ human-labelled cases. Agreement under ~85%? Fix the rubric, not the threshold.
5. **Re-calibrate when the model changes.** A model upgrade is a new judge.
6. **Never the only gate on R3.** A judge can lower the human's load. It can't replace their sign-off.

## Online evals (cheap, always on)

| Signal | Lane | What it tells you |
|---|---|---|
| **Approver edit distance** | Content | Rising = the engine is drifting off voice or thesis. The single best quality signal you already have. |
| **Approver rejection reasons** (tagged) | Content | Which guard or judge to strengthen next |
| **Escalation rate** | All | Too high = gates too strict or generator weak; zero = suspicious |
| **Bounce / spam complaint rate** | GTM | Deliverability health; hard stop thresholds in policy |
| **Reply sentiment mix** | GTM | "Who is this?" and "wrong person" replies = enrichment or ICP problem |
| **Duplicate-send attempts blocked** | Automation | Upstream bug in triggers |

## Outcome evals (the ones clients see)

Run at Day 0 / 30 / 60 / 90 on the **frozen** yardstick:

- Visibility split by query type (brand / niche / "best X"), 2–3 runs per prompt, through the real app interfaces, screenshots kept
- A change counts only if it beats run-to-run noise: `guardrails/visibility_stats.py::real_change`
- ₹ bridge on the same private data definition as Day 0
- GTM: reply rate, positive reply rate, meetings per 100 sends, with send volume and ICP mix held steady, otherwise you're comparing different campaigns

## Running

```bash
python evals/run_evals.py                 # all deterministic guards vs golden sets
python evals/run_evals.py --lane outreach # one lane
python evals/judge.py evals/judges/swap_test.md evals/datasets/content_drafts.jsonl  # needs ANTHROPIC_API_KEY
```

The runner exits non-zero if any guard's recall on must-block cases drops under the policy threshold, so it can gate CI.
