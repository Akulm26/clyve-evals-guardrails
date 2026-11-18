# 12 · The deployment gate: deployable, safe, ethical

**No Clyve AI automation or workflow runs on real people or real data until it passes this gate.**

Every workflow ships with a manifest in `workflows/`. The checker reads it and rules:

```
python gate/check_workflow.py workflows/<name>.yaml

Any SAFE or ETHICAL test fails? ──YES──▶ BLOCKED      do not run it
        │ NO
        ▼
Is the evidence real?
(≥30 real golden cases, every judge calibrated) ──NO──▶ PILOT ONLY   run with a human checking every R2+ action
        │ YES
        ▼
    DEPLOYABLE   run it; the guards and the action gate stay on every output
```

## What each word means here

| | The question | Tested by |
|---|---|---|
| **Safe** | Can it do damage at scale? | Every action has a risk tier · the lane's guards are wired in · kill switch · named approver + canary for R3 · gate log kept ≥ 90 days · token budget |
| **Ethical** | Is it honest and fair to the people it touches? | Lawful basis + consent checked at send (DPDP) · only permitted personal data · opt-outs within 48 h · **no protected attribute used to score or target people** · automated replies say they're automated and always offer a human · no outcome promises · pressure tactics (false urgency, false scarcity) escalated |
| **Deployable** | Do we have evidence it works? | Golden set with ≥ 30 **real** cases (`"source": "real"`) · every judge calibrated (≥ 30 labels, ≥ 85% agreement; KPI Q3) · named owner |

Safe and ethical failures **block**. Missing evidence only limits the workflow to a **pilot**. That's deliberate: a workflow can be safe before it's proven, but it can never be proven while it's unsafe.

## The manifest

```yaml
name: Clyve teardown outreach
owner: Akul
lane: gtm_engineering          # content_ops | ai_visibility | gtm_engineering | marketing_automation
actions: [score_lead, crm_update, send_single, send_bulk]   # tiers come from the policy file
guards: [outreach_guard, promise_guard, pii_guard, injection_guard, manipulation_guard, claims_gate]
judges: [{template: personalisation_factuality, calibration: {labelled_cases: 0, agreement: 0}}]
golden_set: evals/datasets/outreach_messages.jsonl
human_approver: Akul
canary_percent: 5
kill_switch: CLYVE_KILL_SWITCH
token_budget: 200000
logging: {gate_log: true, retention_days: 365}
data: {personal_data: true, fields: [name, work_email, company, role], lawful_basis_field: true, consent_checked_at_send: true, opt_out_hours: 0}
scoring_features: [category, price_band, active_meta_ads, ai_answer_absence, city]
automated_replies: {discloses_automation: true, human_escalation_path: "reply HUMAN or call +91…"}   # if it replies on its own
```

## Current status

| Workflow | Verdict | Why |
|---|---|---|
| Clyve teardown outreach | **PILOT ONLY** | Safe and ethical. 0 real golden cases; personalisation judge not calibrated |
| Example unsafe win-back flow | **BLOCKED** | 18 failures (kept as a regression test) |

## Moving a workflow from PILOT ONLY to DEPLOYABLE

1. Log every real rejection, edit and escalation as a golden-set row with `"source": "real"`.
2. Label 30 real cases for each judge it uses, run `evals/judge.py`, and record the agreement in the manifest.
3. Re-run the gate. CI runs it on every push and fails the build if any workflow is BLOCKED.
