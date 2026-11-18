# 08 · Operating cadence

| When | What runs | Who looks |
|---|---|---|
| **Every output** | Input guards → output guards → judge (R2+) → action gate | Nobody, unless it escalates |
| **Every R3 action** | Dry run, approval ID, canary, kill switch armed | Approver |
| **Every code / prompt / model change** | `pytest` + `run_evals.py` in CI; judge re-calibration if the model changed | Builder |
| **Daily** | Deliverability (bounce, complaints), escalation queue, blocked-action log | Akul, 10 min |
| **Weekly** | Approver edit-distance trend; new golden-set rows from rejections; reply-classifier spot check (20 replies) | Akul, 30 min |
| **Monthly** | ICP calibration (score decile vs positive reply); enrichment precision per provider; policy review | Akul |
| **Day 0 / 30 / 60 / 90** | Frozen visibility runs (×3, app interfaces, screenshots), `real_change`, ₹ bridge | Client report |
| **Quarterly** | Compliance page re-check; retire stale rules from the playbook | Akul + counsel if needed |

## The weekly loop that makes the system better

```
Rejections + edits + escalations this week
   → tag the reason (unsourced number / generic / wrong fact / tone / scope)
   → each reason with ≥ 3 hits becomes:
        a golden-set row (so it's tested forever)
        + a playbook line (so the generator learns it)
        + a guard rule, if it can be written as code
```
