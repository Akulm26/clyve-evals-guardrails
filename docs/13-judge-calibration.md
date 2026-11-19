# 13 · Calibrating a judge with a labelling sheet

An LLM judge is only evidence once you know how often it agrees with a careful human on **your** cases. That agreement rate is KPI Q3, and the deployment gate needs **≥ 30 labelled cases at ≥ 85% agreement** before a workflow that relies on the judge can be DEPLOYABLE. Those labels must come from **two people labelling independently** who agree well (Cohen's κ ≥ 0.80), and only the rows they agree on count.

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

## 2b. A second labeller

A second person fills `human_verdict_b` for the same rows **without looking at `human_verdict`**. Then:

```bash
gtm-evals judge agreement personalisation_factuality evals/labels/personalisation_factuality.csv
# ✅ κ 0.86 on 34 rows both labelled (need ≥ 0.80); they agree on 32
#   disagree  L07: settle it with a third person, or drop the row
```

Rows the two disagree on are left out of calibration. Settle them with a third person if they matter, or drop them. A κ below 0.80 usually means the rule is unclear: tighten the "how to label" rules and relabel, rather than averaging the disagreement away.

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

## 3b. Can't-tell beats a guess, and one run isn't enough

A judge may answer `abstain` (or `unsure`, `insufficient_evidence`). Scoring: right +1, abstain 0, wrong −1. `net` = (right − wrong) ÷ rows, so a judge that guesses scores below one that admits it can't tell. The gate needs `net ≥ +0.70`.

Each row is judged 3 times. The row's verdict is the majority; a tie counts as abstain. If the runs split on more than 5% of rows, the judge isn't stable enough to gate on.

```
gtm-evals judge calibrate personalisation_factuality labels.csv --update workflows/teardown-outreach.yaml
agreement 94% on 32 labelled cases (gate: ≥85% on ≥30)
net score +0.88 (right +1, can't-tell 0, wrong −1; gate ≥ +0.70); 0 abstained
3 run(s) per row; runs disagreed on 0% of rows (gate ≤ 5%); 96 model calls
```

Results are cached in `.gtm-evals-cache/judges/` by template, row, model and run, so rerunning after you fix one label only pays for that row. `--no-cache` forces fresh calls; `--max-calls N` stops before spending more than N.

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
