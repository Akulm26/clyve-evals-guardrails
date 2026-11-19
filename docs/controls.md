# Controls map

Each guard and gate rule, mapped to the frameworks an auditor or a client's security team will ask about. This is a crosswalk, not a certification: it shows where a control helps, not that a framework is satisfied.

- **OWASP** = OWASP Top 10 for LLM Applications 2025
- **NIST** = NIST AI 600-1, the Generative AI Profile of the AI RMF (July 2024): its 12 risk categories
- **ISO** = ISO/IEC 42001:2023 Annex A controls (clause numbers: verify against your copy of the standard)
- **ATLAS** = MITRE ATLAS technique IDs, checked November 2026; ATLAS changes monthly, so confirm IDs before putting them in tooling

| Control | What it does | OWASP | NIST AI 600-1 | ISO 42001 | ATLAS |
|---|---|---|---|---|---|
| `injection_guard` | flags instruction-like text in scraped or inbound content; `wrap()` marks it untrusted | LLM01 Prompt Injection | Information Security | A.6.2.4 verification and validation | AML.T0051 (.000 direct, .001 indirect) |
| `pii_guard` | redacts personal data before model calls | LLM02 Sensitive Information Disclosure | Data Privacy | A.7 data for AI systems | AML.T0057 LLM Data Leakage |
| `redteam` (gate) | promptfoo attack set; a leaked canary blocks | LLM01, LLM07 System Prompt Leakage | Information Security | A.6.2.4 | AML.T0051, AML.T0054 LLM Jailbreak, AML.T0056 Extract LLM System Prompt |
| `output_guard` | unfilled placeholders, wrong names, off-allowlist links, raw HTML, scripts | LLM05 Improper Output Handling | Information Integrity | A.6.2.4 | — |
| `isolation` | client filter on retrieval; agent memory untrusted; least-privilege tool scopes | LLM08 Vector and Embedding Weaknesses, LLM06 Excessive Agency | Data Privacy, Information Security | A.6.2.6 operation and monitoring | AML.T0053 AI Agent Tool Invocation |
| `ActionGate` | R0–R3 tiers, approval, canary, kill switch, circuit breaker, token budget | LLM06 Excessive Agency, LLM10 Unbounded Consumption | Human-AI Configuration | A.9 use of AI systems | — |
| `claims_gate`, `promise_guard`, `offer_guard` | every number sourced; no outcome promises; AI claims need test evidence; honest reference prices | LLM09 Misinformation | Confabulation, Information Integrity | A.8 information for interested parties | — |
| `claim_safety_guard` | regulated categories: prohibited health claims block | LLM09 | Confabulation, Dangerous content | A.5 assessing impacts | — |
| `testimonial_guard`, `likeness_guard` | real, consented quotes and likenesses; AI labels on synthetic media | LLM09 | Information Integrity, Intellectual Property | A.8 | — |
| `manipulation_guard`, `dark_pattern_guard` | pressure tactics escalate; dark patterns in flows block | — | Human-AI Configuration, Harmful Bias | A.5 | — |
| `outreach_guard`, `automation_guard`, `dpdp_guard` | lawful basis, consent, opt-outs, channel rules, children's data | LLM02 | Data Privacy | A.7, A.5 | — |
| `enrichment_guard`, `provenance` | CRM fields sourced, dated, allowed; values found in their saved source; claims backed by the tool trace | LLM09 | Data Privacy, Information Integrity | A.7 data provenance and quality | — |
| proxies + `fairness` (gate) | no protected attribute or proxy for one without a four-fifths test | — | Harmful Bias and Homogenization | A.5 assessing impacts | — |
| `ai_seo_guard` | crawler access, firewall reality test, readable without JS, schema, site-wide 80% rule | — | Information Integrity | A.6.2.6 | — |
| `visibility_stats` | frozen prompt set, no blended numbers, change must beat noise | LLM09 | Confabulation | A.6.2.4 | — |
| judges: calibration, κ, net score, repeat runs, bound evidence, blind packets | an LLM grader is checked against two people, on the template and model in use | LLM09 | Confabulation, Human-AI Configuration | A.6.2.4 | — |
| deployment gate: golden set sized from the claim, strata | DEPLOYABLE needs enough real, stratified cases | — | Confabulation | A.6.2.4 | — |
| `rollout`, budgets | shadow → canary → segment; breaches drop to shadow; cost and latency budgets | LLM10 Unbounded Consumption | Human-AI Configuration | A.6.2.6 operation and monitoring | — |
| incident playbook + drill; logs ≥ 1 year with personal data; approver fatigue | the human side of the controls | — | Human-AI Configuration | A.6.2.8 event logs, A.3 internal organisation | — |

Gaps worth knowing: nothing here addresses model supply chain (OWASP LLM03) or training-data poisoning (LLM04, AML.T0020); gtm-evals assumes a hosted model and doesn't train one. NIST's CBRN, obscene-content and environmental categories are out of scope for marketing automation.
