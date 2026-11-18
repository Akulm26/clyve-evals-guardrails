# Changelog

## 0.1.1 — 18 Nov 2026
- Author credits: Akul S. Malhotra (@Akulm26) in package metadata, NOTICE, CITATION.cff, the Action and the container label.
- README rewritten around purpose (why it exists, three jobs, who should use it, what it is not) with six concrete examples; `tests/test_tour.py` keeps them in sync with `examples/tour.py`.
- `load_rows` reads CSV as well as JSONL, so a judge labelling sheet exported from a spreadsheet calibrates directly: `gtm-evals judge calibrate personalisation_factuality labels.csv`.
- Template `templates/evals/judge_labels.csv` for labelling the personalisation judge.
- Labelling sheets: `gtm-evals judge labels <judge>` makes a blank CSV for any judge; `gtm-evals judge status` counts labels; `gtm-evals judge calibrate … --update <manifest>` lists every disagreement and writes `{labelled_cases, agreement}` into the workflow manifest.
- Gate: a judge entry can name its `labels:` file, and the gate fails if the manifest claims more labelled cases than the file holds.
- `evals/labels/personalisation_factuality.csv` (Clyve's own, 30 rows to fill), `docs/templates/judge-labelling-sheet.xlsx`, `docs/13-judge-calibration.md`, and a `calibrate` workflow that re-runs on label changes when an `ANTHROPIC_API_KEY` secret is set.
- `judges.calibrate` skips unlabelled rows.

## 0.1.0 — 18 Nov 2026
First release.
- Guards: claims_gate, promise_guard, manipulation_guard, pii_guard, injection_guard, outreach_guard, automation_guard, visibility_stats, action_gate (risk tiers R0–R3).
- Deployment gate: rules each workflow DEPLOYABLE / PILOT ONLY / BLOCKED on safe, ethical and deployable tests.
- CLI: `gtm-evals init | gate | eval | check | visibility | judge | policy`.
- Six LLM judge templates (swap test, on-thesis, personalisation factuality, claim safety, description accuracy, promise check).
- Bundled default policy + `clyve` profile.
- Distribution: GitHub Release (wheel + sdist), GitHub Action (`uses: Akulm26/clyve-evals-guardrails@v0.1.0`), container on GitHub Packages (`ghcr.io/akulm26/gtm-evals`).
- Examples: outbound pre-send, content draft, lifecycle send.
