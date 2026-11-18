# 13 · Calibrating a judge with a labelling sheet

An LLM judge is only evidence once you know how often it agrees with a careful human on **your** cases. That agreement rate is KPI Q3, and the deployment gate needs **≥ 30 labelled cases at ≥ 85% agreement** before a workflow that relies on the judge can be DEPLOYABLE.

```text
 real messages you sent ──► labelling sheet ──► CSV in evals/labels/ ──► gtm-evals judge calibrate
   (one per row)            human pass/fail        committed with           │
                                                   the workflow             ├─ agreement %, every disagreement
                                                                            └─ --update writes it into the manifest
                                                                                   │
                                                                                   ▼
                                                                     gtm-evals gate: PILOT ONLY → DEPLOYABLE
                                                                     (cross-checked against the label file)
```

## 1. Get a sheet

Pick whichever you prefer. All three have the same columns, and `load_rows` reads them by header name, so column order doesn't matter.

| Option | How |
|---|---|
| CSV for any judge | `gtm-evals judge labels personalisation_factuality` → `evals/labels/personalisation_factuality.csv` with 30 blank rows and one column per template variable |
| Excel / Google Sheets | [docs/templates/judge-labelling-sheet.xlsx](templates/judge-labelling-sheet.xlsx): pass/fail dropdown, auto-filled `today`, a progress counter and the labelling rules on a second tab |
| Starter rows | `gtm-evals init` copies `evals/judge_labels.csv` with one worked example |

Columns for `personalisation_factuality`:

| Column | What goes in it |
|---|---|
| `id` | L01, L02, … |
| `text` | the exact message as sent (email, DM or InMail), not the draft |
| `signals` | the facts on file about the recipient, one per line: `S1: fact (source, date)` |
| `human_verdict` | `pass` or `fail` |
| `why` | one line; for a fail, quote the statement that broke it |
| `lead`, `date_sent` | brand and send date, for your own reference |
| `today` | the send date (filled from `date_sent` if blank) |
| `freshness_days` | 45: signals older than this can't be called new or recent |

## 2. Label

- **pass** only if every statement about the recipient matches a signal and nothing implies private data (conversion rate, revenue, CAC, AOV) before intake. Anything stretched, unsupported or stale is **fail**.
- **Label before you see the judge's answer**, so it can't steer you.
- **Get a mix: at least 10 pass and 10 fail.** If 28 of 30 rows pass, a judge that always says "pass" scores 93%. Drafts the approver rejected count; label them as they were before the fix.
- When in doubt, fail it. The judge is meant to be strict.

```bash
gtm-evals judge status personalisation_factuality evals/labels/personalisation_factuality.csv
# 12/30 labelled · 9 pass · 3 fail · not ready (need 30, with ≥10 pass and ≥10 fail)
```

## 3. Calibrate

Needs `pip install "gtm-evals[judges]"` and `ANTHROPIC_API_KEY`. Unlabelled rows are skipped, so blank rows cost nothing.

```bash
gtm-evals judge calibrate personalisation_factuality evals/labels/personalisation_factuality.csv \
          --update workflows/teardown-outreach.yaml
# agreement 88% on 34 labelled cases (gate: ≥85% on ≥30)
#   disagree  L07: judge pass, human fail
#   disagree  L19: judge fail, human pass
#   ...
# updated workflows/teardown-outreach.yaml
```

Read every disagreement. Either the judge is wrong (tighten the template and re-run) or your label is (fix it, and note why). Don't fix labels to raise the score.

`--update` writes `calibration: {labelled_cases: 34, agreement: 0.88}` into the manifest's judge entry, keeping its comments. In CI, the **calibrate** workflow does the same on every change to `evals/labels/` when the repo has an `ANTHROPIC_API_KEY` secret, and posts the result to the run summary.

## 4. The gate checks your claim

A manifest's judge entry can name its label file:

```yaml
judges:
  - template: personalisation_factuality
    labels: evals/labels/personalisation_factuality.csv
    calibration: {labelled_cases: 34, agreement: 0.88}
```

The gate then fails if the manifest claims more labelled cases than the file holds, so a hand-edited calibration line can't pass on its own.

## Privacy

Messages name prospects and companies. Keep business facts only (brand, public signals, what was sent), never personal phone numbers or personal emails. Run `pii_guard.redact()` over the file if in doubt, or keep the file out of git in a private setup and pass it by path.
