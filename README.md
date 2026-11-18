# Clyve Guardrails & Evals

**Open playbook + runnable harness for keeping AI-run marketing systems honest: content ops, AI visibility, GTM engineering and marketing automation.**

Built by [Clyve](https://clyve.io) — *Content Strategy and Engineering. The clear next move.*

---

## The one idea

> **Guardrails decide what the system is *allowed* to do. Evals prove what it *actually* did.**
> Guardrails run on every single output, inline. Evals run on samples and datasets, offline and on a schedule.
> You need both, because a guardrail you never evaluate is a guess, and an eval with no guardrail behind it is just a report on damage already done.

Most "AI guardrails" content is about chatbots refusing bad questions. Marketing systems fail differently. The model rarely says something toxic. What it does is **confidently state a number nobody can prove**, **personalise an email with a fact it made up**, **send the same WhatsApp twice**, or **report "visibility up 40%" when it's just run-to-run noise**. This repo is built around those failures.

## The decision tree (start here)

```
For any check you want to add:

Can it be verified with code (regex, schema, lookup, math)?
├─ YES → Deterministic guard. Runs inline on 100% of outputs. Cheap, fast, no judgment.
└─ NO → Does it need judgment ("is this on-thesis?", "does this pass the swap test?")
        ├─ Is there a reference to judge against (claims register, rubric, golden answer)?
        │   ├─ YES → LLM judge with that reference + rubric. Calibrate against human labels first.
        │   └─ NO  → Write the reference first. A judge with no ground truth is a vibe check.
        └─ Is the action irreversible or external (send, publish, spend, write to a client's CRM)?
            └─ YES → Human gate, on top of whatever else runs. Logged approver ID, every time.
```

The rule underneath: **the more an action costs if it's wrong, and the harder it is to undo, the stronger the gate.** That's the risk tier system (`docs/03-guardrail-layers.md`).

## What's covered

| Lane | What the AI does | What goes wrong first | Guard in this repo |
|---|---|---|---|
| **Content ops** | Drafts posts, pages, briefs from a claims register | Unproven numbers, invented proof, generic copy that passes for any brand, promises Clyve can't keep | `claims_gate`, `promise_guard`, swap-test judge |
| **AI visibility** | Runs frozen prompt sets across ChatGPT / Perplexity / Gemini, scores mention, citation, accuracy | Calling noise a win, blending query types, changing prompts mid-engagement | `visibility_stats`, prompt-set hash lock |
| **GTM engineering** | Signal capture → enrichment → ICP scoring → personalised teardown outreach | Made-up personalisation, wrong person enriched, stale signals, burnt domains, sends without a lawful basis | `outreach_guard`, `pii_guard`, `injection_guard` |
| **Marketing automation** | Lifecycle email / WhatsApp, CRM sync, AI reply routing, n8n flows | Duplicate sends, consent not synced, AI auto-reply offering discounts, sends at 11pm, one client's data leaking into another's flow | `automation_guard`, `action_gate` |

**How the lanes relate to Clyve's offer:** content ops and AI visibility are the ContentOS core. GTM engineering is the lead-gen pillar, and it also runs Clyve's own teardown outreach. Marketing automation comes in step by step: Clyve's own follow-ups first, then a guard module for flows clients already run, then flows built and handed over during Build. Details in [docs/09-scope-ladder.md](docs/09-scope-ladder.md).

## Repo map

```
docs/
  00-mental-model.md          Guardrails vs evals, the 3 eval levels, where each lives
  01-clyve-system-map.md      End-to-end: how Clyve's business uses AI, and where it can break
  02-architecture.md          Tier choice, topology, generator/evaluator contract, token plan, failure audit
  03-guardrail-layers.md      4 layers × 3 enforcement types, risk tiers R0–R3
  04-eval-system.md           Golden sets, judges, calibration, online evals, business-outcome evals
  05-lanes/
    content-ops.md
    ai-visibility.md
    gtm-engineering.md
    marketing-automation.md
  06-compliance-india.md      DPDP Act + Rules, TRAI, WhatsApp, Gmail/Yahoo bulk-sender rules, ASCI/FSSAI
  07-failure-modes.md         MAST failure taxonomy mapped to marketing systems
  08-operating-cadence.md     What runs per output, per day, per week, per engagement
  09-scope-ladder.md          How GTM engineering + marketing automation enter Clyve, step by step
learn/                        3 hands-on break-and-fix exercises (start here if you're new)
guardrails/                   Deterministic guards (pure Python, no dependencies)
policies/clyve_policy.yaml    Every threshold in one file
evals/
  datasets/                   Seeded golden sets with expected verdicts
  judges/                     LLM-judge prompt templates (rubric + reference + output schema)
  run_evals.py                Runs every guard against its golden set, reports catch rate
tests/                        pytest suite
```

## Quickstart

```bash
git clone https://github.com/<you>/clyve-guardrails-evals
cd clyve-guardrails-evals
python -m pip install pyyaml pytest
python -m pytest -q                 # unit tests for every guard
python evals/run_evals.py           # guard catch-rate report against golden sets
```

No API key needed for the deterministic layer. LLM judges in `evals/judges/` are plain prompt templates: use them with any model, or run `evals/judge.py` with `ANTHROPIC_API_KEY` set.

## Principles (non-negotiable)

1. **No bare numbers.** Every score or ₹ figure carries a confidence stamp: `OBSERVED`, `OUR READ`, `ASSUMED · ±1`, `CAPTURED`.
2. **The generator never grades itself.** The checker gets ground truth (a claims register, a frozen prompt set, a lead's actual signals), not just the draft.
3. **Freeze the yardstick.** Prompt sets and rubrics are hashed at Day 0. A changed hash invalidates the comparison.
4. **Change must beat noise.** No "up X%" unless the move is bigger than run-to-run variation.
5. **External actions are tiered.** Draft → internal write → single send → bulk send/publish. Each tier adds a gate.
6. **Scraped content is data, never instructions.** Reviews, websites, inbound replies are wrapped and scanned before any model sees them.
7. **Promises are filtered.** If a line is only true when results go well, it's cut.

## License

Apache-2.0. Use it, fork it, ship it. If it helps your team, tell us what broke. That's how the golden sets get better.

## Honest note on the scores

The seeded golden sets were written alongside the guards, so they pass at 100% by design. Read that as the floor, not proof. The guards earn trust when real rejections, approver edits and escalations from live work become new rows (see `CONTRIBUTING.md`).
