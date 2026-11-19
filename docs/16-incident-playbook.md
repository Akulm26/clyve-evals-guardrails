# Incident playbook

What to do when an automation does something it shouldn't: a wrong message to a list, a claim that went live, personal data in the wrong place. The gate checks that this playbook exists for every workflow with R2 or R3 actions, and that the kill switch was drilled in the last 90 days.

## The first hour

| Minute | Do | Why |
|---|---|---|
| 0 | **Flip the kill switch** (`GTM_EVALS_KILL_SWITCH=1`, or the workflow's own `kill_switch`) | every action above R0 stops; drafts still work |
| 5 | Note the time you became aware | DPDP's clock starts here if personal data is involved |
| 10 | Pull the decision log rows since the last clean day (`gtm-evals rollout status <manifest>`) | what went out, to whom, which guard passed it |
| 20 | Decide: does this touch personal data? | if yes, the breach steps below apply |
| 30 | Tell the client's named approver what happened, what's stopped, and what's next | before they hear it from a customer |
| 60 | Write the first incident note: what, when, how many people, which guard missed it | the record the next steps build on |

## If personal data is involved (DPDP Act and Rules 2025)

- **Without delay:** tell the Data Protection Board and each affected person what happened, how far it went, when, and the likely consequences. Rule 7 gives no fixed hours for this first step.
- **Within 72 hours** of becoming aware: the detailed report to the Board, covering facts, cause, mitigation, findings about the person responsible where known, and what you've told the people affected. The Board can extend this on written request.
- **Logs:** the Rules require personal data, traffic data and processing logs to be kept for at least a year, so the gate asks for `retention_days ≥ 365` when a workflow handles personal data.

This is a reading for engineers, not legal advice. For a client brand, the client is usually the data fiduciary; agree in the contract who sends what.

## After the fix

1. Add the case that got through to the golden set (`source: real`, with the stratum it belongs to).
2. Add or tighten the guard pattern; run `gtm-evals eval` until the new case is caught.
3. Restart the rollout from shadow. The gate will want the clean days again.
4. Write the postmortem: timeline, what the guards saw, why they passed it, the fix, the new case ID.

## The drill (every 90 days)

1. In a pilot workflow, start a canary send to a test list.
2. Flip the kill switch mid-run.
3. Confirm: no further sends, `ActionGate.authorize()` refuses with "kill switch is on", the decision log shows the stop.
4. Time it. Record the date in the manifest:

```yaml
incident:
  playbook: docs/16-incident-playbook.md
  last_drill: 2026-11-19
  breach_report_hours: 72
```

The gate counts days from `last_drill`; after 90, the workflow drops to PILOT ONLY until the next drill.
