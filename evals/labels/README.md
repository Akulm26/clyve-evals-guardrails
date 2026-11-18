# Judge labels

Human labels used to calibrate the LLM judges (KPI Q3). One CSV per judge template.

| File | Judge | Used by |
|---|---|---|
| `personalisation_factuality.csv` | [personalisation_factuality](../../src/gtm_evals/data/judges/personalisation_factuality.md) | [workflows/teardown-outreach.yaml](../../workflows/teardown-outreach.yaml) |

Each row is one **real** message that was sent, the facts on file about the recipient, and a human `pass`/`fail`.

```bash
gtm-evals judge status    personalisation_factuality evals/labels/personalisation_factuality.csv
gtm-evals judge calibrate personalisation_factuality evals/labels/personalisation_factuality.csv \
          --update workflows/teardown-outreach.yaml
```

The gate cross-checks the manifest against this file: a workflow can't claim more labelled cases than the file holds.

**Before committing labels:** messages contain prospects' names and companies. Keep only business facts (brand, public signals, what was sent), never personal phone numbers or personal email addresses. Run `gtm-evals check` or `pii_guard.redact()` over the file if in doubt. For a private fork, the same file can stay out of git and be passed by path.

How to label: [docs/13-judge-calibration.md](../../docs/13-judge-calibration.md).
