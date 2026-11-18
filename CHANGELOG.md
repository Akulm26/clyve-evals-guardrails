# Changelog

## 0.1.1 — 18 Nov 2026
- **AI SEO lane** (`ai_seo`, was `ai_visibility`, old name still accepted): new `ai_seo_guard` with `crawler_access` (RFC 9309 robots.txt; answer crawlers must be allowed, training crawlers reported only), `raw_html` (readable without JavaScript, noindex, canonical, title), `schema` (JSON-LD types and required fields) and `entity_consistency`; `gtm-evals seo` command. The lane now requires `ai_seo_guard`, `visibility_stats` and `promise_guard`.
- **ContentOps:** new `claim_safety_guard` for regulated categories (food, supplements, health, personal care); `gtm-evals check --category`. The lane now also requires `claim_safety_guard`, `pii_guard` and `injection_guard`; any `publish` needs an `approval_log`, and a preview counts as its canary.
- **GTM engineering:** new `enrichment_guard` for CRM writes (sourced, dated, fresh, allowed fields, no protected attributes, consent for personal contact details); per-channel daily caps for InMail, LinkedIn and Instagram DMs in `outreach_guard`. A `gtm_engineering` workflow with `crm_update` must wire in `enrichment_guard`.
- Golden set `evals/lanes.jsonl` (36 cases) for the new guards; `workflows/ai-seo-technical.yaml` and `workflows/content-engine.yaml` for Clyve's own AI SEO and content work (both PILOT ONLY).
- Author credits: Akul Suhail Malhotra (@Akulm26) in package metadata, NOTICE, CITATION.cff, the Action and the container label.
- README rewritten around purpose (why it exists, three jobs, who should use it, what it is not) with six concrete examples; `tests/test_tour.py` keeps them in sync with `examples/tour.py`.
- `load_rows` reads CSV as well as JSONL, so a judge labelling sheet exported from a spreadsheet calibrates directly: `gtm-evals judge calibrate personalisation_factuality labels.csv`.
- Template `templates/evals/judge_labels.csv` for labelling the personalisation judge.
- Labelling sheets: `gtm-evals judge labels <judge>` makes a blank CSV for any judge; `gtm-evals judge status` counts labels; `gtm-evals judge calibrate … --update <manifest>` lists every disagreement and writes `{labelled_cases, agreement}` into the workflow manifest.
- Gate: a judge entry can name its `labels:` file, and the gate fails if the manifest claims more labelled cases than the file holds.
- `evals/labels/personalisation_factuality.csv` (Clyve's own, 30 rows to fill), `docs/templates/judge-labelling-sheet.xlsx`, `docs/13-judge-calibration.md`, and a `calibrate` workflow that re-runs on label changes when an `ANTHROPIC_API_KEY` secret is set.
- `judges.calibrate` skips unlabelled rows.
- Tests split into **unit** (462), **integration** (91) and **system** (20: built wheel in a fresh venv, container image); coverage 99%, CI gate at 95%. See TESTING.md.
- Fixed, found by the new tests: `gtm-evals eval` on a file in the wrong format crashed with a traceback (now exit 2 with a clear message); `judge calibrate` without an API key or the `[judges]` extra crashed (now exit 2 with what to install or set); `judge status`/`calibrate` with no label file crashed.

## 0.1.0 — 18 Nov 2026
First release.
- Guards: claims_gate, promise_guard, manipulation_guard, pii_guard, injection_guard, outreach_guard, automation_guard, visibility_stats, action_gate (risk tiers R0–R3).
- Deployment gate: rules each workflow DEPLOYABLE / PILOT ONLY / BLOCKED on safe, ethical and deployable tests.
- CLI: `gtm-evals init | gate | eval | check | visibility | judge | policy`.
- Six LLM judge templates (swap test, on-thesis, personalisation factuality, claim safety, description accuracy, promise check).
- Bundled default policy + `clyve` profile.
- Distribution: GitHub Release (wheel + sdist), GitHub Action (`uses: Akulm26/clyve-evals-guardrails@v0.1.0`), container on GitHub Packages (`ghcr.io/akulm26/gtm-evals`).
- Examples: outbound pre-send, content draft, lifecycle send.
