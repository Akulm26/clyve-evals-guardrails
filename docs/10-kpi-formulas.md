# 10 · KPI formulas (Clyve and ContentOS)

> Generated from `kpi/` — the same source that renders the KPI page in the Clyve project. Edit the data, not this file.
> 76 metrics. Provisional: freeze definitions at Day 0 of each engagement.

## How the guardrails map to the KPIs

| KPI | Enforced or measured by |
|---|---|
| O2 movement, C5 prompt-set power | `guardrails/visibility_stats.py` (`real_change`, `smallest_provable_move`) |
| A5 description accuracy | `evals/judges/description_accuracy.md`, gated by Q3 |
| G6 personalisation accuracy | `guardrails/outreach_guard.py` + `evals/judges/personalisation_factuality.md` |
| G7 bounce, G8 spam complaints | `outreach_guard.deliverability` stop thresholds in `policies/clyve_policy.yaml` |
| Q1 catch rate, Q2 false alarms | `evals/run_evals.py` |
| Q3 judge agreement | `evals/judge.py` |
| Q4 approver edit rate | approval log → new golden-set rows (`docs/08-operating-cadence.md`) |
| Q5 escalations, Q9 R3 incidents | `guardrails/action_gate.py` |
| Q6 duplicate sends, Q7 consent at send | `guardrails/automation_guard.py` |
| Q8 opt-out time | reply classifier (opt-out recall 1.0) + suppression log |

## All formulas

### Layer 1: Diagnostic tracks

Scored from public data, except D1 and D2, which only score after the founder call. These explain why content is not landing.

| ID | Metric | Formula | Data from |
|---|---|---|---|
| D1 | Thesis Clarity | No numeric formula is defined yet.<br>Score = rubric band assigned after the founder call (bands are provisional). | FOUNDER PUBLIC |
| D2 | ICP Precision | No numeric formula is defined yet.<br>Score = rubric band assigned after the founder call (bands are provisional). | CLIENT FOUNDER |
| D3 | Pre-flight: cadence fit | Decision, not a formula.<br>Output = FIT or MISMATCH, with a one-line reason. Settle it before any post-more or post-less advice. | FOUNDER PUBLIC |
| D4 | Message Ownership | Message Ownership (%) = on-thesis posts ÷ posts sampled × 100 | PUBLIC |
| D5 | Differentiation | Overlap with competitor c (%) = brand themes also used by c ÷ total brand themes × 100<br>Differentiation overlap (%) = average of the overlaps across the 2 to 3 competitors | CLIENT PUBLIC |
| D6 | Proof | Proof (%) = posts with specific evidence ÷ posts sampled × 100 | PUBLIC |
| D7 | Buyer Fit | Buyer Fit (%) = sampled engagers matching the ICP ÷ engagers sampled × 100<br>Reply rate (%) = comments with a brand reply ÷ comments received × 100 | FOUNDER PUBLIC |
| D8 | Founder-Brand Gap | Theme overlap (%) = themes on both accounts ÷ themes on either account × 100<br>Gap (%) = 100 − overlap | PUBLIC |
| D9 | Funnel-stage coverage | Stage share (%) = posts at stage s ÷ posts sampled × 100  (for each of the 3 stages) | PUBLIC |
| D10 | Cadence sustainability | Delivery rate (%) = posts actually published ÷ posts planned × 100  (per 4-week window)<br>Decay = delivery rate of the latest window − delivery rate of the first window | FOUNDER PUBLIC |
| D11 | Owned vs rented mix | Owned share (%) = email or SMS subscribers ÷ (subscribers + social followers) × 100 | CLIENT PUBLIC |
| D12 | Paid vs organic alignment | Alignment (%) = active ads carrying the thesis ÷ active ads sampled × 100 | PUBLIC |

### Layer 2: AI/Search Visibility

Computed from the run log. Every formula is per query type and per platform.

| ID | Metric | Formula | Data from |
|---|---|---|---|
| A1 | Mention rate | Mention rate (%) = runs that name the brand ÷ total runs in the segment × 100<br>Total runs in a segment = prompts in segment × runs per prompt K × platforms P | RUNS |
| A2 | Citation rate | Citation rate (%) = runs citing the brand's domain ÷ total runs that show sources × 100 | RUNS |
| A3 | Share of voice | Share of voice (%) = brand mentions ÷ all brand-name mentions across the same runs × 100 | RUNS |
| A4 | Position | Average position = sum of the brand's ranks ÷ runs where it appears in a ranked list<br>Lower is better. | RUNS |
| A5 **(updated)** | Description accuracy | Description accuracy (%) = runs whose description matches the fact list ÷ runs that name the brand × 100 | FOUNDER RUNS |
| A6 | Source map | Domain share (%) = citations to domain d ÷ total citations × 100<br>Third-party share (%) = citations to third-party domains ÷ total citations × 100 | RUNS |
| A7 | Competitor view | Displacement by competitor c (%) = runs naming c where the brand is absent ÷ runs where the brand is absent × 100 | RUNS |
| A8 | Generic-query citation share | Generic citation share (%) = generic-query runs citing the brand's domain ÷ generic-query runs that show sources × 100 | RUNS |
| C1 | Check: AI-crawler access | Access (%) = crawlers not blocked ÷ crawlers checked × 100<br>Pass only if every crawler on the list is allowed. | CLIENT PUBLIC |
| C2 | Check: raw-HTML renderability | Renderable (%) = key claims found in raw HTML ÷ key claims checked × 100 | FOUNDER PUBLIC |
| C3 | Check: schema validity | Schema coverage (%) = required types present and valid ÷ required types × 100 | CLYVE PUBLIC |
| C4 | Check: entity consistency | Consistency (%) = channels whose description matches the canonical one ÷ channels checked × 100 | FOUNDER PUBLIC |
| C5 **(new)** | Check: prompt-set power | Smallest provable move (points) = 1.96 × √(0.25 × 2 ÷ runs in segment) × 100<br>Runs in segment = prompts in segment × K (per platform) or × K × P (pooled across platforms).<br>Pass if the smallest provable move is at or below the move you plan to report as real. | RUNS |

### Layer 3: Outcome KPIs

Re-computed at Day 30, 60 and 90 against the Day 0 baseline.

| ID | Metric | Formula | Data from |
|---|---|---|---|
| O1 | ICP-qualified engagement rate | ICP-qualified engagement (%) = sampled engagers matching the ICP ÷ engagers sampled × 100<br>Sample: engagers on posts published in the checkpoint window. | PUBLIC |
| O2 **(updated)** | AI visibility movement | Movement (points) = metric at Day n − metric at Day 0<br>Noise band = highest pass rate − lowest pass rate across the K repeat passes<br>Chance band = 1.96 × √( p̄ × (1 − p̄) × (1 ÷ runs at Day 0 + 1 ÷ runs at Day n) ) × 100, where p̄ = pooled rate across both checkpoints<br>Real movement only if /movement/ > the larger noise band of the two checkpoints AND /movement/ > the chance band | RUNS |
| O3 | Proof density in new content | Proof density (%) = new posts with specific evidence ÷ new posts published in the window × 100 | PUBLIC |
| O4 | Founder-brand theme overlap | Theme overlap (%) = D8 recomputed on posts from the window | PUBLIC |
| O5 | Inbound enquiry volume and quality | Enquiry volume = count of enquiries in the window<br>Quality (%) = ICP-fit enquiries ÷ enquiries received × 100 | CLIENT |
| O6 | Website traffic and branded search | Branded clicks change (%) = (branded clicks in window − branded clicks in baseline window) ÷ baseline branded clicks × 100<br>Baseline window = the same length of time immediately before Day 0. | CLIENT |
| O7 | Follower-to-lead conversion | Follower-to-lead (%) = leads generated from social in the window ÷ average followers in the window × 100 | CLIENT PUBLIC |
| O8 | Reach and saves | Save rate (%) = saves ÷ accounts reached × 100 | CLIENT |

### Layer 4: Revenue bridge

Connects visibility to the client's revenue. All three are proposed and need client analytics access.

| ID | Metric | Formula | Data from |
|---|---|---|---|
| R1 | AI-referred sessions | AI-referred sessions = sessions whose source matches the AI referrer list<br>AI share (%) = AI-referred sessions ÷ total sessions × 100 | CLIENT |
| R2 | AI-referred conversion and revenue | Conversion (%) = orders (or leads) from AI-referred sessions ÷ AI-referred sessions × 100<br>Revenue per session = revenue from AI-referred sessions ÷ AI-referred sessions<br>Compare with organic search over the same window. | CLIENT |
| R3 | 'How did you hear' share | AI share (%) = responses choosing ChatGPT or AI assistant ÷ total responses × 100<br>Response rate (%) = responses ÷ orders or enquiries × 100 | CLIENT |

### Layer 5: Sales funnel

Clyve's own funnel from Teardown to retainer. All five are proposed.

| ID | Metric | Formula | Data from |
|---|---|---|---|
| B1 | Teardown to call rate | Teardown to call (%) = calls booked ÷ teardowns sent × 100 | CLYVE |
| B2 | Call to paid Audit rate | Call to Audit (%) = paid Audits sold ÷ calls held × 100 | CLYVE |
| B3 | Audit to Build rate | Audit to Build (%) = Builds sold ÷ Audits delivered × 100 | CLYVE |
| B4 | Adoption rate | Adoption (%) = shipped deliverables the client published ÷ deliverables shipped × 100 | CLYVE PUBLIC |
| B5 | Build to retainer rate | Build to retainer (%) = retainers started ÷ Builds completed × 100<br>Retainer offered only if, at Day 30: brand and niche queries moved beyond noise AND the client published what Clyve shipped. | CLYVE RUNS |

### Layer 6: Acquisition engine

Clyve's own LinkedIn and Instagram presence. The goal is inquiries from the right audience.

| ID | Metric | Formula | Data from |
|---|---|---|---|
| E1 | Inquiries | Inquiries = count of inbound inquiries in the window<br>Split by platform: LinkedIn, Instagram, other. | CLYVE |
| E2 | Right-audience share | Right-audience share (%) = inquiries from ICP-fit senders ÷ inquiries × 100 | CLYVE |
| E3 | Inquiries per 1,000 impressions | Inquiries per 1,000 impressions = inquiries ÷ impressions × 1,000<br>Impressions = LinkedIn impressions + Instagram impressions in the same window. | CLYVE PLATFORM |
| E4 | Engagement rate | Engagement rate (%) = (reactions + comments + shares + saves) ÷ impressions × 100<br>Compute per platform; never pool LinkedIn and Instagram. | PLATFORM |
| E5 | Post-attributed share | Post-attributed share (%) = inquiries that name a post, pillar or piece ÷ inquiries × 100 | CLYVE |
| E6 | Publishing consistency | Publishing consistency (%) = pieces published ÷ pieces planned × 100  (per 4-week window) | CLYVE PUBLIC |

### Layer 7: Lead gen

The second pillar. Sold when it comes up, so these have no baseline yet. Every qualified lead ships with a handoff package. G6 to G8 also run on Clyve's own teardown outreach.

| ID | Metric | Formula | Data from |
|---|---|---|---|
| G1 | Qualified leads delivered | Qualified leads delivered = leads that meet the client's qualification definition, per window | CLIENT CLYVE |
| G2 | Qualification rate | Qualification rate (%) = qualified leads ÷ leads sourced × 100 | CLYVE |
| G3 | Handoff completeness | Handoff completeness (%) = qualified leads with all 3 handoff items ÷ qualified leads × 100<br>The 3 items: why the lead qualified, what content triggered the interest, a ready-to-send opening message. | CLYVE |
| G4 | Reply rate | Reply rate (%) = replies to opening messages ÷ opening messages sent × 100 | CLIENT |
| G5 | Meeting rate | Meeting rate (%) = meetings booked ÷ opening messages sent × 100 | CLIENT |
| G6 **(new)** | Personalisation accuracy | Personalisation accuracy (%) = opening messages whose every lead-fact matches a stored, sourced signal ÷ opening messages checked × 100<br>A signal counts only if it has a source link and is within the freshness window (default 45 days). | CLYVE |
| G7 **(new)** | Bounce rate | Bounce rate (%) = bounced messages ÷ messages sent × 100  (per inbox, per day)<br>Stop sending from an inbox at 2% and fix the list before resuming. | PLATFORM |
| G8 **(new)** | Spam complaint rate | Spam complaint rate (%) = spam complaints ÷ messages delivered × 100<br>Gmail requires bulk senders to stay below 0.3%; Clyve stops at 0.1%. | PLATFORM |

### Layer 8: Product line

Gumroad resources, each tied to one goal: views, engagement or leads. Every resource is public-safe and evergreen.

| ID | Metric | Formula | Data from |
|---|---|---|---|
| P1 | Product page views | Product views = page views of product p in the window | PLATFORM |
| P2 | Product conversion | Conversion (%) = sales ÷ product views × 100 | PLATFORM |
| P3 | Product revenue | Product revenue = sum of sale values for product p in the window<br>Freeze whether this is gross or net of fees. | PLATFORM |
| P4 | Leads from products | Lead rate (%) = leads attributed to product p ÷ sales (or downloads) of p × 100 | CLYVE PLATFORM |
| P5 | Check: evergreen | Dependencies = count of items that name a platform feature, algorithm, regulation or tool version<br>Pass only if Dependencies = 0. | CLYVE |
| P6 | Check: public-safe and Audit-exclusive | Restricted items = count of client data, Clyve internal data, or Audit deliverables (scorecard, baseline report, fix order) found in the resource<br>Pass only if Restricted items = 0. | CLYVE |

### Layer 9: The firm

Revenue, delivery load and proof across the whole business.

| ID | Metric | Formula | Data from |
|---|---|---|---|
| F1 | Revenue | Revenue = sum of payments received in the window<br>Split by stage: Audit, Build, retainer, products. | CLYVE |
| F2 | Revenue mix | Revenue mix (%) = revenue from stream s ÷ total revenue × 100<br>Streams: content strategy engagements, lead gen, products. | CLYVE |
| F3 | Retainer MRR | Retainer MRR = sum of monthly fees of active retainers | CLYVE |
| F4 | Judgment hours and revenue per hour | Judgment hours = sum of Akul's logged hours on an engagement<br>Revenue per hour = engagement revenue ÷ Akul's logged hours | CLYVE |
| F5 | Audits completed | Audits completed = count of full Audits delivered<br>Validation gate = 3 to 5 completed Audits | CLYVE |
| F6 | Full case studies | Full case studies = count of engagements with Day 0 to Day 90 numbers, segmented by query type, ready to show | CLYVE |

### Layer 10: Guardrails and evals

Whether the system itself can be trusted: the QA gate, the judges, and every automated send. Covers content ops, AI visibility, GTM engineering and marketing automation.

| ID | Metric | Formula | Data from |
|---|---|---|---|
| Q1 **(new)** | Guard catch rate | Catch rate (%) = must-block cases blocked ÷ must-block cases × 100  (per guard, on its golden set)<br>Gate: ≥ 95% for every guard; 100% for invented numbers, invented personalisation and opt-outs. | CLYVE |
| Q2 **(new)** | False-alarm rate | False-alarm rate (%) = good cases blocked ÷ good cases × 100<br>Precision (%) = correct blocks ÷ all blocks × 100. Gate: precision ≥ 80%. | CLYVE |
| Q3 **(new)** | Judge agreement | Judge agreement (%) = judge verdicts matching the human label ÷ labelled cases × 100<br>Gate: ≥ 85% on at least 30 labelled cases before the judge marks any client-facing column (e.g. A5) or gates an R2 action. | CLYVE |
| Q4 **(new)** | Approver edit rate | Approver edit rate (%) = drafts edited before approval ÷ drafts approved × 100<br>Rejection rate (%) = drafts rejected ÷ drafts submitted × 100, with the reason tagged. | CLIENT CLYVE |
| Q5 **(new)** | Escalation rate | Escalation rate (%) = outputs escalated to a human ÷ outputs checked × 100<br>Report per lane and per reason. | CLYVE |
| Q6 **(new)** | Duplicate-send blocks | Duplicate-send rate (%) = duplicate sends blocked ÷ send attempts × 100<br>Duplicates that got through = sends with the same contact + template inside the dedupe window (target 0). | CLYVE CLIENT |
| Q7 **(new)** | Consent at send | Consent-at-send rate (%) = sends with valid channel consent checked at send time ÷ sends × 100<br>Target 100%. Consent is read from the source of truth at send time, never from a cached segment. | CLYVE CLIENT |
| Q8 **(new)** | Check: opt-out processing time | Opt-out time (hours) = time suppression took effect − time the opt-out arrived  (report the maximum in the window)<br>Pass only if the maximum is 48 hours or less (Gmail's rule for marketing mail). Aim for immediate. | CLYVE CLIENT |
| Q9 **(new)** | Check: R3 incidents | R3 incidents = count of R3 actions that shipped with a guard violation or without an approval ID<br>Pass only if R3 incidents = 0. This is the gate for every step of the automation scope ladder. | CLYVE |

## Open items

| # | Open item | What to do |
|---|---|---|
| 1 | Score bands are unvalidated until 3 to 5 real audits are complete. | Never sell an absolute score. |
| 2 | D1 and D2 have no written scoring rule yet. | Write one before the first audit. |
| 3 | The noise band from 2 to 3 passes is crude. Updated 18 Nov 2026: O2 now also requires the move to beat a chance band, and C5 states the smallest provable move per segment. | Use both bands now. After the first 3 audits, replace the chance-band assumption with the measured run-to-run variance. |
| 4 | Working definitions for D4, D5, D8, D10, D11 and A1 to A5 are proposed wording. | Confirm them, then freeze at Day 0 of each engagement. |
| 5 | R2 needs a minimum count before a rate can be quoted. | Until it is set, report raw counts. |
| 6 | B4 has no rule for what counts as 'published what Clyve shipped'. | Decide before the first Day 30 retainer decision. |
| 7 | The AI crawler list and the GA4 AI referrer list change over time. | Confirm both at the start of each audit. |
| 8 | API answers and real-interface answers diverge sharply. | Client reports use real interfaces with screenshots; any API trend track stays separate. |
| 9 | Terms for automating consumer chat interfaces are unchecked. | Check before automating any baseline. |
| 10 | Part B has no baselines or targets yet. | Track for 4 weeks, then set targets from what the numbers show. |
| 11 | Lead gen is not actively pushed, and its qualification rule is set per client. | Compare each client with itself, and set the rule before sourcing starts. |
| 12 | E5 undercounts, because many people find Clyve through content without saying so. | Ask 'how did you find Clyve?' in every first reply. |
| 13 | Confirm which fields Gumroad Analytics exposes, and whether revenue is gross or net. | Decide before the first product report. |
| 14 | There is no time log yet for F4. | Start logging hours per engagement from the first Audit. |
| 15 | With 20 to 30 prompts split three ways, each segment can only prove large moves (C5). More prompts means more manual runs. | Keep the set size. Weight prompts toward brand and niche when proof of smaller moves matters, and report anything under the C5 bar as direction. |
| 16 | No contact record yet stores lawful basis, source and channel opt-in (Q7). DPDP core obligations apply in full by May 2027. | Add the fields to the lead log and every client CRM touched in Build, now. |
| 17 | No model judge has been calibrated yet (Q3). | Label 30 real cases per judge before any judge marks A5 or gates an R2 action. |
| 18 | The promotional quiet-hours window (21:00 to 10:00 IST) follows TRAI's Service Explicit SMS band; WhatsApp and email have no statutory window. | Re-check TRAI rules quarterly. Keep the window for all promotional sends anyway. |
| 19 | Golden sets are seeded by the guard author (Q1, Q2). | Add every real rejection, edit and escalation as a row; review weekly. |
