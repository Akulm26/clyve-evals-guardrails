# 14 · Related work: GTM evals, benchmarks and skill packs

A registry of outside work on evaluating AI in go-to-market, read on 18 Nov 2026. Each entry says what it evaluates, how it decides right from wrong, and what gtm-evals can learn from it. **Nothing here is implemented yet**: the backlog at the end lists candidate changes. A machine-readable version is in [`related-work.yaml`](related-work.yaml).

Every entry is read through the same four questions:

```text
1. Ground truth   Does the checker compare against something real (labels, CRM history, a fixed answer),
                  or only against a rubric an LLM interprets?
2. Separation     Is the thing being graded kept apart from the thing grading it? Is the grader blind?
3. Coverage       Which lanes does it touch: marketing automation · GTM engineering · ContentOps · AI SEO?
4. Independence   Who ran it, and do they sell the system that scored best?
```

## At a glance

| # | Source | Type | Lanes | Ground truth | Grader | Independent? |
|---|---|---|---|---|---|---|
| 1 | Deepline · GTM-Bench 1.0 | benchmark | GTM engineering | rubric per eval, no answer key | LLM judge, blind, 3 runs averaged | ❌ vendor's tool scored best |
| 2 | Unify · How we build evals for AI agents | practice write-up | GTM engineering | human-labelled replies; structured answers | deterministic + LLM judge + human | n/a (internal practice) |
| 3 | RevSure · Evals for GTM agents | playbook | GTM engineering, marketing automation | 4 quarters of CRM history, replayed as of decision date | historical replay + human trace review | n/a (vendor playbook) |
| 4 | Cargo · LLM evals for revenue agents | playbook | GTM engineering | per-workflow test sets; historical routing outcomes | not specified | n/a (vendor blog) |
| 5 | Drevon · Benchmarking an AI research agent | method guide | GTM engineering | two experts label each account, κ ≥ 0.80 | deterministic + LLM faithfulness judge | ⚠️ vendor sells research agents |
| 6 | Blackpearl · GTM-Bench v1 | benchmark | GTM engineering | per-record match + audit grading | not detailed | ❌ vendor's system scored best |
| 7 | zarif3624/gtm-skills | skill pack + evals | GTM engineering (sales) | behavioural assertions per case | human or agent scoring of blind packets | ✅ open source, MIT |
| 8 | onvoyage-ai/gtm-engineer-skills | skill pack + evals | AI SEO, ContentOps | frozen fixtures; CSV contracts | deterministic audit + agent-scored rubric | ✅ open source, MIT |
| 9 | Ace-Hsu/AI-Go-To-Market-Engine | agent system | ContentOps | human scores fed back as examples | human GUI scoring (≥ 7.0 / ≥ 8.0) | ✅ open source |

---

## 1. Deepline · GTM-Bench 1.0

**Link:** https://deepline.com/benchmarks/gtm-bench · published 23 Oct 2026, updated 9 Nov 2026

- **Evaluates:** agents (a model plus a GTM data tool) on 8 single-turn evals across 5 jobs: account discovery, contact sourcing, contact enrichment, account research and signal tracking. It compares tools (Deepline, Treg, Monid, Freckle, Clay) against a model using web search alone.
- **How it grades:** an LLM judge scores each requested result: complete with evidence, partial, missing, or **wrong, which costs a point**. Each trial is judged three times and averaged. The judge doesn't see which model or tool produced the answer. There's no fixed answer key; the judge works from a rubric, and its agreement with labels from other model families is reported as within 0.05–0.08 on a 0–1 scale.
- **Metrics:** quality (average trial score) and time to final answer. No money or token cost.
- **Headline:** Deepline averaged 89.4% quality; the model alone averaged 38.3%.
- **Caveats (stated by the authors):** two runs per eval per model, live web data that changes between runs, run by the vendor whose tool scored best, single-turn only, no scoring, outbound or inbound routing yet. The run file (prompts, rubrics, judge config) is public; no licence is stated.
- **For gtm-evals:** a **wrong answer scores worse than a missing one** (−1 vs 0), the judge is **blind** to who produced the answer, and **repeat judging** averages out judge noise. Our `calibrate` runs the judge once per row and treats wrong and missing alike.

## 2. Unify · How we build evals for AI agents

**Link:** https://www.unifygtm.com/blog/how-we-build-evals-for-ai-agents · Kunal Rai, updated 22 Jun 2026

- **Evaluates:** a single-turn reply classifier (out-of-office, needs info, has a solution, tone) and multi-turn research agents that plan and call tools. The eval categories are firmographics and technographics, account qualification (growth, hiring, news, social, entity recognition), business understanding and writing.
- **How it grades:** accuracy against human-labelled email replies for classification. Structured answers (booleans, numbers, enums) are checked deterministically, plus **whether the required tool was actually used**. LLM judges score plan quality, business understanding and writing on 1–10 rubrics, with human review alongside; how judges are calibrated isn't described.
- **Metrics:** overall, importance-weighted and tone accuracy; plan quality; tool choice and diversity; efficiency (steps per task); **reliability as the spread of answers across 5 runs**; generalisability across tasks.
- **Failures it surfaced:** date comparisons, agents skipping tools and answering from memory, inconsistent runs, misuse of new tools.
- **For gtm-evals:** **reliability across repeated runs** as a metric, **tool-use checks** (did it actually look it up?), and **class-weighted accuracy** (missing an actionable reply is worse than missing a tone tag). Offline only, same as us.

## 3. RevSure · Evals for GTM agents

**Link:** https://www.revsure.ai/research-playbooks/evals-for-gtm-agents · 1 Jul 2026

- **Evaluates:** a fleet of GTM agents (pipeline, scoring, outreach) through five practices: backtesting against CRM history, weekly decision-trace review, guard metrics behind volume metrics, regression tests on model swaps, and calibration of timing.
- **How it grades:** replays **four quarters of CRM history as the data stood on each decision date**, not today's cleaned records. A frozen, redacted case set is the regression suite. Humans review sampled traces with verdicts: correct, correct for the wrong reasons, wrong, wrong but caught. No LLM judge is discussed. A human with domain context has to sign off before scores reach a system of record.
- **Metrics:** whether and how early a known outcome would have been caught; guard cohorts paired with every volume metric (meeting-to-opportunity, stage progression); calibration by week of quarter; per-workflow cost and margin for model swaps.
- **Stated limit:** backtests reward imitating past decisions and can't score new moves, so those need supervised live trials.
- **For gtm-evals:** **as-of-date replay** (our golden sets have no notion of "what was known then"), **"correct for the wrong reasons"** as its own verdict, **guard metrics next to volume metrics** in the manifest, and **autonomy that expands or shrinks per action class** based on evidence, which maps onto our R0–R3 tiers.

## 4. Cargo · LLM evals for revenue agents (2026)

**Link:** https://www.getcargo.ai/blog/llm-evals-for-revenue-agents-2026 · Aurelien Aubert, published 15 Dec 2025

- **Evaluates:** enrichment, routing, research briefs, outreach drafts and pipeline-risk flags.
- **How it grades:** four kinds of eval: offline test sets, online (shadow mode → canary → segment rollout), outcome (business impact, ideally A/B tested by segment) and safety (policy, PII, action boundaries, outreach claims). Who applies the rubrics, and how they're calibrated, isn't said.
- **Release checklist:** offline score above threshold, no regression in key segments, canary stable for 7–14 days, safety evals passing.
- **Metrics:** enrichment field precision, coverage and **citation rate**; routing true/false positives and time-to-action; research accuracy, relevance and actionability (1–5); outreach clarity, specificity and compliance; outcomes such as bounce, duplicates, connect rate, speed-to-lead and reply rate.
- **For gtm-evals:** an explicit **shadow → canary → segment** path (our gate stops at "PILOT ONLY"), **segment-level regression checks**, and **citation rate** for enriched fields. Start with 50–200 examples per workflow.

## 5. Drevon · Benchmark an AI research agent before you trust its leads

**Link:** https://www.drevon.dev/blogs/evals-for-gtm-how-to-benchmark-an-ai-research-agent-before-you-trust-its-leads · Akash Munshi, 20 Sep 2026 · vendor sells account research

- **Evaluates:** account-research agents that feed outbound.
- **Dataset:** **at least 385 accounts** (95% confidence, ±5% margin), or 323 for a 2,000-account TAM. Stratified 40% standard ICP, 35% ambiguous (M&A, rebrands), 25% adversarial (JS-heavy or bot-protected sites).
- **Ground truth:** **two domain experts label every account independently**, and the set is only used once Cohen's kappa reaches 0.80. Unverified third-party exports are never the baseline.
- **How it grades:** deterministic checks (URL validity, entity presence, JSON schema, rule filters) plus an LLM faithfulness judge. It warns that **schema validation alone doesn't stop invented values**. Offline tests use cached page snapshots; online tests run the full browser loop.
- **Thresholds:** signal precision ≥ 90%, **provenance rate ≥ 95%**, extraction recall ≥ 70%, negative-ICP rule compliance 100%, plus a scorecard with **cost < $0.25 per account** and **latency < 90 s per lead**. A failing check blocks CRM auto-sync.
- **For gtm-evals:** this is the most directly usable source. Our gate's **30 real cases is far below what proves a 90% precision claim**. Our labelling sheet has **one labeller**, with no agreement check. `enrichment_guard` checks that a source *exists*, not that it *supports* the value. And the manifest has no **cost or latency** thresholds.

## 6. Blackpearl · GTM-Bench v1

**Link:** https://www.blackpearl.com/gtm-bench · Jun 2026 · code at github.com/pearlengine/GTM.Bench

- **Evaluates:** end-to-end prospecting: inferring the seller's offer, writing an ICP, and returning a ranked prospect list with evidence. 72 tasks across 11 task types and 15 market categories, with the taxonomy clustered from about 60,000 real prospecting queries.
- **How it grades:** each record is judged on **match** (does it really fit?) and **audit** (is it the right real-world entity, with supported claims?). Grades are A (+1), B (0) or Sub-B (−1), summed into a **net score**, so weak rows pull the total down. The evaluator process isn't detailed on the page.
- **Headline:** the developer's own system came first; several general-purpose agents scored below zero.
- **Caveats:** no cost or latency reported, no formal limitations listed, run by the vendor whose system won. Code and artifacts are described as open; check the repo for the licence.
- **For gtm-evals:** **net scoring that penalises bad rows** is the honest way to score list-building. A list of 100 where 30 are wrong is worse than a list of 60 that are all right.

## 7. zarif3624/gtm-skills

**Link:** https://github.com/zarif3624/gtm-skills · MIT · last commit 11 Sep 2026

- **What it is:** 25 sales skills (ICP, account research, outbound, discovery, deal planning, forecasting, handoff) built around evidence-first output: facts, inferences and unknowns kept separate.
- **How it grades:** each skill has a case with the **consequential risk**, what the response **must demonstrate**, what it **must avoid**, and what needs **human review**. Cases run as **blind packets**: the agent sees the prompt and context but not the risk or the assertions. Every assertion is scored Pass, Partial or Fail with evidence from the response, and any prohibited behaviour is a critical failure. **Journey** cases test that "unknown" or "proposed" never turns into "verified" across a handoff between skills. Routing cases test that a request picks the right skill. Results are tied to the commit they tested, so stale evidence is detected.
- **Status:** its quality summary reports all 37 behavioural definitions passing in their latest runs.
- **For gtm-evals:** the **must-demonstrate / must-avoid / human-review** assertion format is richer than our single pass/fail label. **Blind packets** keep the grader from leaking the answer. **Evidence bound to a commit** would stop our calibration numbers going stale when a judge template changes. **Journey tests** match our pipeline test idea, applied to status upgrades.

## 8. onvoyage-ai/gtm-engineer-skills

**Link:** https://github.com/onvoyage-ai/gtm-engineer-skills · MIT · last commit 11 Oct 2026

- **What it is:** a pipeline of AEO/GEO skills: brand research, keyword and AI-prompt research, Reddit opportunities, content planning and writing, AI-readable charts, content audit, an A–F website AEO audit, and code fixes.
- **How it grades:** the website audit runs **16 deterministic checks** (title, meta description, canonical, one H1, JSON-LD present, recognised schema type, Open Graph, internal links, image alt text, 250+ words, no noindex, no nosnippet/noai, heading hierarchy, **llms.txt**, robots.txt not blocking 9 AI crawlers, RSS feed). A site-wide check passes when 80% of crawled pages pass. Half the final grade is the agent's own 0–5 rubric scores on six content dimensions, sanity-checked against heuristic signals. Offline evals cover CSV artifact contracts and the audit script against frozen fixtures.
- **For gtm-evals (AI SEO lane):** checks we don't have: **llms.txt, meta description, exactly one H1, Open Graph, image alt text, heading hierarchy, RSS**, and **site-wide aggregation** (80% of pages) rather than one page at a time. Where we're stricter: it treats any blocked AI crawler as a failure, while we separate answer crawlers (must be allowed) from training crawlers (the client's choice). It also lets the same agent that reads the pages score half the grade, which breaks generator/evaluator separation.

## 9. Ace-Hsu/AI-Go-To-Market-Engine

**Link:** https://github.com/Ace-Hsu/AI-Go-To-Market-Engine · last commit 11 Aug 2025 (initial release)

- **What it is:** a modular set of content agents (message house, personas, gap analysis, keywords, testimonials, social posts, website copy, consistency validation) with an orchestrator.
- **How it grades:** humans score outputs in a GUI; a phase-1 gate needs ≥ 7.0, and outputs scoring 8.0+ become reference examples the agents read next time, while low scores are kept as failure examples.
- **Risk to note:** the **testimonial agent writes testimonials in a "believable customer voice"**. Published as if real, those are fabricated reviews, which the ASCI code and most platform rules prohibit. gtm-evals has no guard for this today.
- **For gtm-evals:** a **fabricated-testimonial guard** for ContentOps. Its feedback loop (high-scoring outputs as examples) matches the "playbook from successes and failures" pattern, but without a separate evaluator or calibration the scores can drift.

---

## What gtm-evals already does that these don't

| gtm-evals | Seen elsewhere? |
|---|---|
| A deployment gate that blocks a workflow on **ethics** (lawful basis, minimisation, protected attributes, disclosure, opt-out time) | Only safety evals in general terms (Cargo) |
| **Promise and pressure-tactic** guards on outgoing copy | No |
| **Claims register**: every number traces to proof, ₹ estimates as stamped ranges | Provenance, but only for research output (Drevon) |
| India-specific consent rules (DPDP, TRAI quiet hours, WhatsApp opt-in) | No |
| Answer crawlers vs training crawlers treated differently | No (onvoyage fails on any blocked AI bot) |
| A gate that **can't be satisfied by a hand-edited calibration line** | Commit-bound evidence (gtm-skills) is the closest |

## Backlog: candidates to adopt (not implemented)

Ranked by how much each would change whether a workflow can honestly be called DEPLOYABLE.

| # | Idea | From | Lane | What it would change |
|---|---|---|---|---|
| 1 | **Sample size from the claim**: required real cases computed from the target rate and margin (e.g. 385 for ±5%), stratified into standard, ambiguous and adversarial cases | Drevon | all | Replaces the flat "30 real cases" with a number that actually proves the threshold |
| 2 | **Two labellers and an agreement check** (Cohen's κ ≥ 0.80) before a label file can calibrate a judge | Drevon | all | Calibration can't rest on one person's labels |
| 3 | **Provenance check**: the cited source must contain the value, not just exist | Drevon, Cargo | GTM | Turns `enrichment_guard`'s "has a source" into "the source says so" |
| 4 | **Wrong scores below missing** (−1 / 0 / +1) and **net score** in `gtm-evals eval` | Deepline, Blackpearl | GTM, all | A confident wrong answer stops looking as good as an honest "don't know" |
| 5 | **Repeat-run reliability**: run each judge 3× per row and report the spread | Unify, Deepline | all | Flaky judges show up before they're trusted |
| 6 | **Fabricated testimonial / review guard** | Ace-Hsu (risk) | ContentOps | Blocks invented customer quotes and reviews presented as real |
| 7 | **AI SEO checks**: llms.txt, meta description, one H1, Open Graph, image alt, heading hierarchy, RSS; **site-wide 80%-of-pages** aggregation | onvoyage | AI SEO | Brings the AI SEO lane level with the best open audit while keeping our crawler split |
| 8 | **Online stage in the manifest**: shadow → canary → segment, with canary stability days and guard metrics next to volume metrics | Cargo, RevSure | all | A path from PILOT ONLY to DEPLOYABLE that uses live evidence safely |
| 9 | **As-of-date replay** for golden sets built from CRM history | RevSure | GTM, automation | Tests what the agent could have known then, not what we know now |
| 10 | **Cost and latency thresholds** per run in the manifest | Drevon, RevSure | all | Puts "too expensive to run" next to "too risky to run" |
| 11 | **Assertion cases** (must demonstrate / must avoid / human review), **blind packets**, and evidence **bound to the commit and template version** | gtm-skills | all | Richer judge test cases, and calibration goes stale when the template changes |
| 12 | **Tool-use check**: an R2+ research step must show the lookup it relied on | Unify | GTM | Catches agents answering from memory |
