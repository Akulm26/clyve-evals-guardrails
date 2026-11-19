# Module reference

Every module in `gtm_evals`, what it checks, and how it is used. Import them from `gtm_evals` (`from gtm_evals import claims_gate, ActionGate`).

Every guard returns a `Verdict`: truthy when it passes, with `.violations` and `.escalate`.

| Module | What it checks |
|---|---|
| `claims_gate` | every number traces to a proven claim; every ₹/Rs/INR figure is stamped; assumed figures are ranges |
| `promise_guard` | outcome, ranking and timeline promises (negations like "we can't guarantee" pass) |
| `manipulation_guard` | false urgency/scarcity, fear, guilt → escalate to a human |
| `outreach_guard` | lawful basis, suppression, channel opt-in, unsubscribe, sender auth, ICP exclusions, sourced + fresh personalisation, undeclared facts, private metrics before intake, daily caps per inbox and per channel (InMail, LinkedIn, Instagram DMs, WhatsApp); bulk senders need RFC 8058 one-click unsubscribe headers; DMARC must align with SPF or DKIM; `deliverability()` warns at 0.1% complaints and stops at 0.3% |
| `automation_guard` | tenant isolation, consent at send, idempotency, frequency caps, quiet hours, mixed-content = promotional, audience-size sanity; replies are allowlisted |
| `injection_guard` | flags instruction-like text; `wrap()` marks scraped/inbound text as untrusted data |
| `pii_guard` | email, Indian mobile, PAN, Aadhaar; `redact()` / `restore()` around model calls |
| `visibility_stats` | frozen prompt-set hash, no blended numbers, app vs API separation, `real_change()` (noise + chance band), `smallest_provable_move()` |
| `ai_seo_guard` | `crawler_access()` (RFC 9309 robots.txt; answer crawlers must be allowed, user-triggered fetchers and Google-Extended are noted, training crawlers reported), `raw_html()` (readable without JavaScript, noindex, canonical, title), `schema()` (JSON-LD types and required fields), `entity_consistency()` (one name and description across channels), `check_page()`, `fetch_results()` (what each answer crawler got past the firewall), `check_site()` (site-wide, 80% rule; llms.txt, feed) |
| `claim_safety_guard` | regulated categories (food, supplements, health, personal care): prohibited claims block (including "100%" for food, per FSSAI), claims that need proof escalate; superlatives and named competitors need proof in any category |
| `enrichment_guard` | CRM writes: every field sourced, dated, fresh and confident; forbidden fields and protected attributes never stored; personal contact details need consent; no PII in free text |
| `dpdp_guard` | India's DPDP Act + Rules: no behavioural targeting where minors may be in the audience, parental-consent records, consent-notice checker, consent record per contact (opt-in) |
| `testimonial_guard` | every quoted testimonial matches a registered, consented, sourced entry word for word (reworded quotes escalate); no AI-written or undisclosed insider reviews; social-proof counters and star ratings need a live source (ASCI; FTC 16 CFR 465) |
| `likeness_guard` | real faces and voices need a consent record that covers the use and hasn't expired; synthetic image, video and audio need a visible AI label (audio: at the start); synthetic people can't pose as customers (MeitY 2026 rules; ASCI AI-ad guidelines) |
| `dark_pattern_guard` | checkout and flow specs against India's 2023 dark-pattern guidelines: pre-selected add-ons, fake countdowns, confirm-shaming, drip pricing, disguised ads, nagging, trick questions, forced actions, subscription traps |
| `offer_guard` | AI accuracy, earnings and autonomy claims need a registered test-evidence ID; "was ₹X" must be the 30-day low; MRP must match the pack |
| `output_guard` | the last look before sending: unfilled placeholders (`{{first_name}}`, `*|FNAME|*`), a greeting that doesn't match the CRM name, links off the allowlist, raw HTML in plain-text channels, script markup |
| `provenance` | `check_record()`: each enriched value appears in its saved source page (contradictions named); `check_trace()`: each claim in a research note cites a page a lookup in the trace actually fetched |
| `isolation` | `check_retrieval()` (client filter on every lookup), `check_memory()` (agent-written notes are untrusted data), `check_tools()` (no tool scope above what the actions need) |
| `rollout` | `status()`: shadow → canary → segment from the decision log, with breach rules; `budget_status()`: cost per item and p95 latency, WhatsApp priced by category |
| `fairness` | `impact_ratio()`: the four-fifths test for a feature that could stand in for a protected group |
| `redteam` | a promptfoo red-team config generated from the policy (prompt extraction, indirect injection, competitors, excessive agency, hijacking, PII, policy rules), and `score()` for its results, with a canary for system-prompt leaks |
| `evidence` | `required_cases()` (Cochran, from the claimed rate and margin), `strata_shortfall()`, `cohen_kappa()`, `agreement()` for two labellers |
| `ActionGate` | R0–R3 risk tiers, required evidence per tier, kill switch, token budget, circuit breaker (stops when guards fail on > 20% of the last 50 items) |
| `gate` | the deployment gate above |
| `judges` | 6 LLM-judge templates: swap test, on-thesis, personalisation factuality, claim safety, description accuracy, promise check. `calibrate()` scores right +1, "can't tell" 0, wrong −1, runs each row 3 times and caches results by template, row and model. `packet()` writes only what the judge may see; `evidence_binding()` records the template, labels and model a calibration was measured on |
