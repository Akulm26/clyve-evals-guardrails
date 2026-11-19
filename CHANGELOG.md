# Changelog

## 0.2.0 — 19 Nov 2026

All six phases (0–5) of the adoption plan. Guardrails and evals ship together, one item on each track per phase.

### Phase 5 · AI SEO and claims + operations

Guardrails
- **AI SEO reality test.** `ai_seo_guard.fetch_results()`: what each answer crawler got from a key page. HTTP 403/429/503 or a challenge page fails, even with a clean robots.txt. `gtm-evals seo --fetch-plan URL` prints the curl commands that save the results; `--fetch-results fetch.json` checks them. A note reminds you that CDNs verify bots by IP, so confirm in the CDN's bot logs.
- **Site-wide checks.** `ai_seo_guard.check_site()` and `gtm-evals seo --site pages/`: readable without JavaScript, meta description, one H1, Open Graph, image alt text and heading order, each passing on ≥ 80% of pages; plus `/llms.txt` and an RSS or Atom feed.
- **`offer_guard` (new).** AI accuracy, earnings and "fully autonomous" claims need a test-evidence ID in the register (`[EV-2026-014]`). A "was ₹X" price must be the lowest price of the last 30 days†. MRP is checked against the printed MRP instead (Legal Metrology). Required in `content_ops`.

Evals
- **Incident drill.** Workflows with R2 or R3 actions need an incident playbook and a kill-switch drill in the last 90 days (`incident: {playbook, last_drill, breach_report_hours}`). With personal data, the plan must report to the Data Protection Board within 72 hours (DPDP Rule 7). See docs/16-incident-playbook.md.
- **Logs for a year.** Workflows that handle personal data need `retention_days ≥ 365` (DPDP Rules 2025).
- **Approver fatigue.** When `approval_log` is a file, an approver who passes ≥ 99% of at least 20 items with a median under 5 seconds keeps the workflow at PILOT ONLY.
- **Controls map.** docs/controls.md maps each guard to the OWASP LLM Top 10 (2025), NIST AI 600-1, ISO/IEC 42001 Annex A and MITRE ATLAS, and names the gaps.
- `gate.check(..., today=)` for reproducible drill checks.
- 10 golden cases (p5-01 to p5-10); 121 in `evals/lanes.jsonl`.

### Phase 4 · Agent safety + live proof

Guardrails
- **Provenance.** `provenance.check_record()`: each enriched value must appear in its saved source page. A contradiction is named ("source says 'seed', record says 'Series A'"); a partial match escalates. CRM writes in `gtm_engineering` now need `provenance` as well as `enrichment_guard`.
- **Tool use.** `provenance.check_trace()`: each claim in a research note must cite a page that a lookup in the agent's trace fetched. Manifests with `trace_required_for` need `provenance`.
- **`output_guard` (new).** Unfilled placeholders, a greeting that doesn't match the CRM name, links off the allowlist, raw HTML in plain-text channels, script markup. Required in `gtm_engineering` and `marketing_automation`; `gtm-evals check --lead-name --channel` runs it.
- **Isolation (new module).** Every retrieval filters on the client; memory an agent wrote is read back as untrusted; tools hold only the scopes the actions need (`action_gate.scope_tiers`). The gate checks `retrieval`, `memory` and `tools` when a manifest declares them.
- **Circuit breaker.** `ActionGate.record()` / `breaker_open()`: when guards fail on more than 20% of the last 50 items, every action above R0 stops.

Evals
- **As-of replay.** A golden row with `as_of` is run as it stood that day: later-dated signals and fields are hidden and `today` becomes `as_of`.
- **Shadow → canary → segment.** `rollout:` in the manifest plus a decision log. Clean days advance a stage; a breach (unsubscribes, complaints, guard failures, kill switch, budget) drops back to shadow. Workflows with `send_bulk`, `activate_flow` or `client_crm_bulk_write` need the log to have earned `segment` before they're DEPLOYABLE. `gtm-evals rollout status`. See docs/15-rollout.md.
- **Budgets.** `budgets: {usd_per_item, p95_seconds, whatsapp_rates}` checked against the log; a breach blocks.
- Clyve's teardown manifest now declares `rollout` and `budgets` (still PILOT ONLY: no live log yet).
- 12 golden cases (p4-01 to p4-12); 111 in `evals/lanes.jsonl`.

### Phase 3 · Coverage + test honesty

Guardrails
- **Proxies for protected traits.** Scoring on `pincode`, `surname`, `community` and similar (`deployment_gate.proxies.fields`) is blocked unless the manifest attaches a fairness test (`fairness_tests: {pincode: tests.csv}`). The test passes at an impact ratio ≥ 0.80 (four-fifths rule), with ≥ 30 rows in each of at least two groups. New module: `fairness`.
- **Hinglish and Hindi.** Romanised Hindi and Devanagari patterns in `claim_safety_guard` ("sardi ka ilaaj", "sugar khatam", "इलाज"), `manipulation_guard` ("sirf 2 slot bache", "aakhri mauka", "जल्दी करें") and `promise_guard` ("result pakka", "गारंटी").
- **Instagram.** No cold DMs: a reply within 24 hours of the person's last message, or one private reply to their comment within 7 days.
- **WhatsApp scope lock.** On WhatsApp, an off-scope request ("write my essay") must get `decline` or `escalate`. This is a cautious reading of Meta's terms in force since 15 Jan 2026.

Evals
- **Assertion cases.** Golden rows with `guard: assert` check an output against `must_demonstrate` and `must_avoid` patterns. Rows marked `human_review: true` are listed, not scored, and don't count as gate evidence.
- **Blind packets.** `gtm-evals judge packet <template> labels.csv [--id L01] [-o packet.md]` writes exactly what the judge sees: no labels, notes or expected answers. A template that would show the judge a hidden field is refused.
- **Bound evidence.** `calibrate --update` records `template_hash`, `labels_hash`, `model` and `commit`. Editing the template, relabelling or swapping the model sends the workflow back to PILOT ONLY (`evidence.require_bound_evidence`).
- **Red-team set.** `gtm-evals redteam init|score` builds a promptfoo config from the policy and scores its results. Workflows that reply to people need ≥ 50 tests and ≥ 95% passed; a leaked canary blocks.
- 15 golden cases (p3-01 to p3-15); 99 in `evals/lanes.jsonl`.

### Phase 2 · Honest social proof + honest judges

Guardrails
- `testimonial_guard` (new): quoted testimonials must match a registered entry word for word, with consent and a source. Reworded quotes escalate; unregistered ones block. AI-written reviews, undisclosed insider reviews, live-looking counters ("23 people are viewing this") and unsourced star ratings are caught.
- `likeness_guard` (new): a real face or voice needs a consent record that covers the use and hasn't expired. Synthetic image, video and audio need a visible AI label; synthetic audio discloses at the start. AI-written text needs no label (noted).
- `dark_pattern_guard` (new): reads checkout and flow specs for the patterns in India's 2023 dark-pattern guidelines: basket sneaking, false urgency, confirm-shaming, drip pricing, disguised ads, nagging, trick questions, forced action, interface interference and subscription traps.
- The `content_ops` lane, and Clyve's content-engine manifest, now require all three.

Evals
- Judges can abstain. `calibrate` scores right +1, abstain 0, wrong −1 and reports `net`; `agreement` is right ÷ answered.
- Each row is judged 3 times by default (`--runs`). The verdict is the majority (a tie counts as abstain), and `run_disagreement` is the share of rows whose runs split.
- Results are cached on disk by template, row, model and run (`--cache`, `--no-cache`), so a rerun costs nothing. `--max-calls` stops before the budget is spent.
- The gate needs each judge stable across 3 runs (≤ 5% of rows disagreeing) and a net score ≥ +0.70. `--update` writes `net`, `runs` and `run_disagreement` into the manifest.
- 18 golden cases (p2-01 to p2-18) across the three new guards; 84 in `evals/lanes.jsonl`.

### Phase 1 · India rules + proof size

- **Guardrails**
  - TRAI (TCCCPR as amended Feb 2025) in `automation_guard` for SMS and voice: no request to opt in again within 90 days of an opt-out; consent given during a transaction covers promotions for 7 days; SMS needs a DLT template ID whose category matches the message; sender header suffix must match the category (`trai.header_suffix`, to confirm against TRAI's text). Consent can now be `{"granted", "at", "source"}`.
  - New `dpdp_guard` (DPDP Act 2023 + Rules 2025): `check_campaign` blocks behavioural targeting where the audience may include minors and processing children's data without parental-consent records; `check_notice` checks a consent notice covers data, purpose, withdrawal, grievance contact and the Data Protection Board; `check_contact` requires a consent record ID when `dpdp.require_consent_record` is on. Required in the `marketing_automation` and `gtm_engineering` lanes.
- **Evals**
  - New `evidence` module: `required_cases()` (Cochran, with finite-population correction), `strata_shortfall()`, `cohen_kappa()`, `agreement()`.
  - The gate sizes the real cases a workflow needs from its `claims: {precision, margin}` (never below 30; 97 when no claim is stated) and requires a minimum share per stratum (40/35/25).
  - Two labellers: label sheets gain `human_verdict_b`; `gtm-evals judge agreement`; `calibrate` uses only agreed rows and reports κ; `--update` writes κ; the gate requires κ ≥ 0.80 (`evidence.require_two_labellers`).
  - Clyve's three workflows state `claims: {precision: 0.90, margin: 0.10}` (35 real cases each).
  - 16 golden cases for TRAI and DPDP; golden types `dpdp_campaign`, `dpdp_notice`.

### Phase 0 · Fixes to checks that were wrong or out of date

- **Guardrails**
  - `outreach_guard`: bulk senders (`context["bulk_sender"]`) need RFC 8058 one-click unsubscribe headers (`List-Unsubscribe` with an https URL + `List-Unsubscribe-Post: List-Unsubscribe=One-Click`), per Gmail's bulk-sender rules; `one_click_unsubscribe: bulk | always | never`.
  - DMARC must align with SPF or DKIM (`sender_auth.spf_aligned` / `dkim_aligned`); `p=none` is enough. Unknown alignment is a note.
  - `deliverability()`: complaints warn at 0.1% (a note) and stop at 0.3% (was a stop at 0.1%).
  - `claim_safety_guard`: "100%" / "100 per cent" blocked for food categories (FSSAI advisory, 30 May 2025).
  - Quiet hours stay 21:00–10:00 IST by default, documented as a cautious choice; transactional sends remain exempt.
- **Evals and reporting**
  - `Verdict.notes`: informational lines that never change `passed`; printed by the CLI and kept by `combine()`.
  - `ai_seo_guard`: answer crawlers are OAI-SearchBot, Claude-SearchBot, PerplexityBot, Googlebot, Bingbot. User-triggered fetchers (ChatGPT-User, Claude-User, Perplexity-User, Google-Agent) blocked in robots.txt are a note, since they may ignore it. Blocking Google-Extended is noted as affecting Gemini grounding.
  - `visibility_stats.validate_rows` rejects rank/position fields: AI answer lists rarely repeat, so only presence rate is reported.
  - Golden types `deliverability` and `visibility_rows`; 14 new cases in `evals/lanes.jsonl`, every row tagged with a `stratum`.

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
