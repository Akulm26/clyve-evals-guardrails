# gtm-evals

[![ci](https://github.com/Akulm26/clyve-evals-guardrails/actions/workflows/evals.yml/badge.svg)](https://github.com/Akulm26/clyve-evals-guardrails/actions/workflows/evals.yml)
[![release](https://img.shields.io/github/v/release/Akulm26/clyve-evals-guardrails?label=release)](https://github.com/Akulm26/clyve-evals-guardrails/releases)
[![python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](pyproject.toml)
[![license](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![container](https://img.shields.io/badge/ghcr.io-akulm26%2Fgtm--evals-purple)](https://github.com/Akulm26/clyve-evals-guardrails/pkgs/container/gtm-evals)

**Guardrails and evals for AI that talks to your customers.** Cold email, content, WhatsApp, auto-replies, CRM enrichment, AI SEO.

An LLM that drafts a message can be fluent and still wrong: an invented statistic, a promise nobody controls, a contact who never opted in. Content filters don't see any of that. gtm-evals does. It checks every output before it goes out, and rules on every automation before it goes live: **DEPLOYABLE**, **PILOT ONLY** or **BLOCKED**.

Pure Python. One dependency. No API key. It decides; your stack sends.

```text
$ cat draft.txt
Hi Rhea, we guarantee you will rank #1 on ChatGPT in 30 days. Trusted by 50,000 brands. Only 2 slots left this week, reply now.

$ gtm-evals check draft.txt --register claims_register.json
❌ 4 issue(s) · escalate to a human
   [claims_gate] unsourced number '50,000' — not in claims register
   [promise_guard] promise language: 'guarantee'
   [promise_guard] promise language: 'rank #1'
   [manipulation_guard] pressure tactic — verify it is true and sourced: 'Only 2 slots'

$ echo $?
1
```

Exit code 1, so it fails a CI job or stops an n8n branch. Nine more scenarios with real output: [docs/examples.md](docs/examples.md).

## Why this exists

- **One invented statistic across 2,000 cold emails** isn't a typo. It's 2,000 false claims under your brand.
- **A bot that replies "sure, 50% off!"** to an angry customer has made an offer someone must honour.
- **A WhatsApp blast to people who never opted in** is a consent problem (DPDP, TRAI, Meta's terms), not a copy problem.
- **"AI visibility up 30%"** that is really run-to-run noise sells a client a result that never happened.

Marketing AI rarely fails by being toxic. It fails by being **confidently wrong, overpromising, or acting without permission**. Those are business failures, and this is built for them.

## Three jobs

```text
                    your AI drafts something
                              │
 1. GUARDRAILS   ─────────────┤  inline, on every output · milliseconds
    "is this okay to say?"    │  invented numbers · promises · fake personalisation · pressure
                              │  health claims · fake testimonials · consent · PII · injection
                              ▼
 2. ACTION GATE  ─────────────┤  just before anything is sent or changed
    "is this okay to do?"     │  risk tier R0–R3 · bulk sends need a named approver,
                              │  a canary batch and a working kill switch
                              ▼
                     reaches a real person

 3. EVALS + DEPLOYMENT GATE      offline, in CI, before an automation goes live
    "can we prove it works?"     your real cases → recall and precision per guard
                                 → DEPLOYABLE · PILOT ONLY · BLOCKED
```

Guardrails and evals carry equal weight. A guard nobody has measured is a guess, and an eval with nothing to enforce is a report.

## Install

```bash
pip install "git+https://github.com/Akulm26/clyve-evals-guardrails@v0.2.0"
```

| Other routes | Command |
|---|---|
| **Wheel from the release** | `pip install https://github.com/Akulm26/clyve-evals-guardrails/releases/download/v0.2.0/gtm_evals-0.2.0-py3-none-any.whl` |
| **Docker** | `docker run --rm -v "$PWD:/work" ghcr.io/akulm26/gtm-evals:0.2.0 --help` |
| **GitHub Action** | `uses: Akulm26/clyve-evals-guardrails@v0.2.0` ([below](#block-a-merge-in-ci)) |
| **With LLM judges** | `pip install "gtm-evals[judges] @ git+https://github.com/Akulm26/clyve-evals-guardrails@v0.2.0"` |

```bash
gtm-evals init                       # config, a workflow manifest, a sample golden set
gtm-evals check draft.txt            # run the guards on a draft ('-' reads stdin)
gtm-evals eval evals/golden.jsonl    # recall / precision per guard on your own cases
gtm-evals gate workflows/*.yaml      # DEPLOYABLE · PILOT ONLY · BLOCKED
```

## What it catches

| Your AI… | Example | Caught by |
|---|---|---|
| states a number nobody can prove | "Trusted by 50,000 kitchens" | `claims_gate` |
| promises what nobody controls | "You'll rank #1 on ChatGPT in 30 days" | `promise_guard` |
| pressures people, in English, Hinglish or Hindi | "Only 2 slots left", "sirf 2 slot bache" | `manipulation_guard` |
| makes a claim a food or supplement can't make | "cures colds", "clinically proven", "100%" | `claim_safety_guard` |
| invents a testimonial or a live counter | "— Priya" with no such review; "23 people are viewing this" | `testimonial_guard` |
| uses a face or voice without consent | a cricketer's likeness in an ad; an AI image with no label | `likeness_guard` |
| tricks people at checkout | a pre-ticked ₹49 gift wrap; a fee that appears at the last step | `dark_pattern_guard` |
| claims "98% accurate AI" or a "was ₹799" price it never charged | no test evidence; a reference above the 30-day low | `offer_guard` |
| invents personalisation | "Loved your Shark Tank episode!" (there wasn't one) | `outreach_guard` |
| sends without consent, at 11pm, twice, or as a cold Instagram DM | a contact who opted out; a first DM to a stranger | `automation_guard`, `outreach_guard` |
| auto-replies with an offer it can't make | "sure, 50% off!" to an angry customer | `automation_guard.check_reply` |
| ships a template mistake | `Hi {{first_name}}`; "Hi Priya" to Rhea; a made-up bit.ly link | `output_guard` |
| bulk-sends with nobody watching | `send_bulk` with no approver, no canary | `ActionGate` |
| follows instructions hidden in a review or reply | "Ignore previous instructions and…" | `injection_guard` |
| sends personal data to a model | phone numbers, emails, PAN, Aadhaar | `pii_guard` |
| writes made-up data to the CRM | a funding stage with no source; "Series A" from a page that says "seed" | `enrichment_guard`, `provenance` |
| lets one client's data into another's output | a vector search with no client filter | `isolation` |
| targets children, or skips the consent notice | interest targeting on a kids' snacks campaign | `dpdp_guard` |
| scores leads on a stand-in for caste or religion | `scoring_features: [pincode]` with no fairness test | the gate (`fairness`) |
| blocks or hides the site from AI search | `Disallow: /products/`; an empty `<div id="root">`; a firewall that challenges PerplexityBot | `ai_seo_guard` |
| reports "visibility up 30%" that's noise | 24% → 28% on 75 runs | `visibility_stats` |

Every module with its checks: [docs/reference.md](docs/reference.md). Thresholds, crawler names, quiet hours and the rest live in one policy file (`gtm-evals policy` prints it), so you can change them.

## The verdict

Every automation gets a short YAML manifest: lane, actions, data used, owner, evidence. The gate rules on it.

```text
Any SAFE or ETHICAL check fails?   → BLOCKED      don't run it
Evidence still synthetic?          → PILOT ONLY   a human checks every action that reaches a real person
Otherwise                          → DEPLOYABLE
```

| | The question | Checked |
|---|---|---|
| **Safe** | Can it do damage at scale? | risk tier per action · required guards for the lane · kill switch · named approver and canary for bulk · logs kept · token budget · incident playbook and a kill-switch drill |
| **Ethical** | Is it honest and fair to the people it touches? | lawful basis and consent at send · data minimisation · opt-outs within 48 h · no protected attributes in scoring · replies say they are automated and reach a human · no promises · no pressure |
| **Deployable** | Is there evidence it works? | enough real cases to prove what it claims, split across standard, ambiguous and adversarial · every judge calibrated on labels two people agree on · red-team results for bots · a live log that has moved shadow → canary → segment |

An unsafe WhatsApp win-back flow (`gtm-evals gate workflows/examples/bad-lifecycle-flow.yaml`, trimmed):

```text
Example — unsafe WhatsApp win-back flow  →  BLOCKED
  SAFE
    ❌ all required guards for the lane are wired in (missing: ['pii_guard', 'injection_guard', 'manipulation_guard', 'dpdp_guard', 'output_guard'])
    ❌ kill switch declared (none)
    ❌ R3 actions have a named human approver
    ❌ logs kept ≥ 365 days (personal data: DPDP Rules require a year)
  ETHICAL
    ❌ consent checked at send time, not from a cached list
    ❌ no protected attribute is used to score, rank or target people (found: ['gender', 'age'])
    ❌ automated replies say they are automated
  …
```

And Clyve's own outreach workflow (`gtm-evals gate workflows/teardown-outreach.yaml`, trimmed):

```text
Clyve teardown outreach  →  PILOT ONLY
  SAFE        ✅ 12 of 12
  ETHICAL     ✅ 7 of 7
  DEPLOYABLE
    ❌ ≥ 35 real cases to show 90% ±10% at 95% confidence (has 0)
    ❌ judge 'personalisation_factuality' calibrated (≥30 labels, ≥85% agreement)
    ❌ judge 'personalisation_factuality' labels agreed by two labellers (κ ≥ 0.80, no second labeller)
    ❌ kill-switch drill in the last 90 days (none on record)
    ❌ live rollout log attached (rollout: {log, stages}); offline cases alone can't make it DEPLOYABLE
```

That second verdict is deliberate. It is safe and ethical by design, and still PILOT ONLY, because nothing real stands behind it yet. The gate holds its author to the same bar as everyone else.

Lanes and the guards each must wire in: marketing automation, GTM engineering, content ops, AI SEO. Details: [docs/12-deployment-gate.md](docs/12-deployment-gate.md).

## Use it

### Block a merge in CI

```yaml
# .github/workflows/gtm-evals.yml
on: [push, pull_request]
jobs:
  gtm-evals:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Akulm26/clyve-evals-guardrails@v0.2.0
        with: { command: gate, args: "workflows/*.yaml" }
      - uses: Akulm26/clyve-evals-guardrails@v0.2.0
        with: { command: eval, args: "evals/golden.jsonl" }
```

The report lands in the run summary. The step fails if a workflow is BLOCKED or a guard drops below its recall or precision threshold.

### Call it from code

```python
from gtm_evals import load_policy, claims_gate, ActionGate

policy = load_policy()                    # bundled defaults, plus ./gtm-evals.yaml if present

v = claims_gate.check(draft, claims_register, policy)
if not v:
    print(v.violations)                   # ["unsourced number '50,000' — not in claims register"]

gate = ActionGate(policy)
ok = gate.authorize("send_bulk", checks=[v], evaluator_passed=True,
                    approval_id="AK-1118-01", canary_done=True)
```

Every guard returns a `Verdict`: truthy when it passes, with `.violations` and `.escalate`. It works anywhere that can run Python or a CLI: n8n code nodes, a script in front of Clay or Instantly, your own service. Recipes: [`examples/`](examples/).

### Your own cases

A golden set is a JSONL file of cases you've seen go wrong. Every approver rejection should become a row.

```json
{"id": "c1", "guard": "claims", "input": {"text": "Trusted by 50,000 kitchens.", "register": "claims_register.json"},
 "expected_pass": false, "source": "real", "why": "invented number"}
```

Only `"source": "real"` rows count as deployment evidence. The number you need comes from your claim: 35 real cases to show 90% ±10%, 97 when the workflow states no claim.

### Calibrate the judges

Pattern guards catch what someone thought of in advance. LLM judges cover the rest, and they count as evidence only after they agree with humans on your cases: at least 30 labels, at least 85% agreement, on labels two people gave independently and agree on (Cohen's κ ≥ 0.80).

```bash
gtm-evals judge labels personalisation_factuality       # a blank 30-row labelling sheet
gtm-evals judge agreement personalisation_factuality evals/labels/personalisation_factuality.csv
gtm-evals judge calibrate personalisation_factuality evals/labels/personalisation_factuality.csv \
          --update workflows/teardown-outreach.yaml     # writes the result into the manifest
```

Judges can abstain (right +1, abstain 0, wrong −1). Each row runs 3 times. The evidence is bound to the template, labels and model it was measured on, so editing any of them sends the workflow back to PILOT ONLY. Guide: [docs/13-judge-calibration.md](docs/13-judge-calibration.md).

## How good is it? Honest numbers

| | Result |
|---|---|
| Tests | **936**: 807 unit, 109 integration, 20 system (the built wheel in a fresh venv, plus the container). Coverage 99%, CI fails below 95%. No test calls a real model |
| Adversarial fuzz | 46 / 46 correct, 0 misses, 0 false alarms |
| End-to-end pipeline | 8 / 8 scenarios |
| Held-out set, code only | **20 / 25 (80%)**. The 5 misses are known: "Nearly half our buyers reorder", "Our repeat rate doubled last year", "within a fortnight", "will definitely increase your sales", "Congrats on the Shark Tank feature!" |

The held-out misses are the point: code finds what someone thought of in advance, and a new phrasing gets past it. That is why the judge layer exists.

**Not proven yet.** Every golden case in this repo is synthetic (178 of them). The LLM judges haven't been calibrated against human labels (the label sheet is blank). None of Clyve's workflows has a live log. So the gate rules Clyve's own workflows PILOT ONLY, and says why. What the repo proves is the machinery: the checks run, the numbers are computed correctly, and the gate won't say DEPLOYABLE on a hand-typed number. What it can't prove is how your traffic will behave. Run it on your own cases before you trust it on them.

The compliance checks are India-first (DPDP Act and Rules 2025, TRAI, WhatsApp, Gmail and Yahoo bulk-sender rules, ASCI, FSSAI, the 2023 dark-pattern guidelines). Rules change and some readings here are cautious; [docs/06-compliance-india.md](docs/06-compliance-india.md) names the sources and was last checked on 18 Nov 2026. **Not legal advice. Confirm with counsel.** Full stress-test report: [docs/11-simulation-report.md](docs/11-simulation-report.md).

## Is it for you?

```text
Does an LLM write or send anything a customer, prospect or the public will see?
├─ No  → You don't need this.
└─ Yes
   ├─ A human reads every single output before it goes out
   │    → Run the guards as a pre-check. Your reviewer catches more, faster,
   │      and every rejection becomes a test case.
   └─ Some outputs go out with no human reading them
      (bulk sends, auto-replies, scheduled posts, enrichment that writes to a CRM)
        → This is what gtm-evals is for: guards inline, ActionGate before send,
          deployment gate in CI.
```

For GTM engineers, growth and marketing-ops teams, and agencies or consultancies shipping AI automations for clients.

**What it is not:** a toxicity or moderation filter (pair it with one), a sending tool or CRM (it decides, you send), set-and-forget (the guards need your cases and your labels), or legal advice.

## Learn it by breaking it

```bash
git clone https://github.com/Akulm26/clyve-evals-guardrails && cd clyve-evals-guardrails
pip install -e ".[dev]"
python examples/tour.py     # every guard on nine scenarios
python learn/check.py 1     # sneak a fake number past the gate, then fix it
python learn/check.py 2     # is that AI-visibility jump a win or noise?
python learn/check.py 3     # catch a stretched personalisation
python -m pytest            # 916 tests, no API key needed
```

## The playbook

`docs/` is the thinking behind the code.

| Start here | |
|---|---|
| [00-mental-model](docs/00-mental-model.md) · [02-architecture](docs/02-architecture.md) | guardrails vs evals; why the gate is deterministic |
| [03-guardrail-layers](docs/03-guardrail-layers.md) · [04-eval-system](docs/04-eval-system.md) | four guard layers, risk tiers R0–R3; golden sets, judges, online evals |
| [05-lanes/](docs/05-lanes) | content ops · AI SEO · GTM engineering · marketing automation |
| [06-compliance-india](docs/06-compliance-india.md) · [controls](docs/controls.md) | the rules, sourced; each guard mapped to OWASP LLM Top 10, NIST AI 600-1, ISO 42001, MITRE ATLAS |
| [12-deployment-gate](docs/12-deployment-gate.md) · [13-judge-calibration](docs/13-judge-calibration.md) | how the verdict is decided; labelling sheet → agreement → manifest |
| [15-rollout](docs/15-rollout.md) · [16-incident-playbook](docs/16-incident-playbook.md) | shadow → canary → segment; the first hour and the 72-hour breach report |
| [examples](docs/examples.md) · [reference](docs/reference.md) · [07 failure modes](docs/07-failure-modes.md) · [14 related work](docs/14-related-work.md) | nine worked scenarios; every module; where marketing systems break; nine outside projects and what to adopt |

## Contributing

The most valuable contribution is **a real failure** the guards missed. Add it as a golden-set row, show the miss, then fix the guard without new false alarms. See [CONTRIBUTING.md](CONTRIBUTING.md) and [TESTING.md](TESTING.md). Security reports: [SECURITY.md](SECURITY.md).

## Author

Created by **[Akul Suhail Malhotra](https://github.com/Akulm26)**, founder of [Clyve](https://clyve.io), a boutique AI consulting firm (*Content Strategy and Engineering*). It began as the gate for Clyve's own client automations and is open-sourced so anyone shipping AI into GTM can use the same bar. [LinkedIn](https://linkedin.com/in/malhotraakulsuhail/).

If it helps you, a ⭐ or a citation ([CITATION.cff](CITATION.cff)) is appreciated.

## License

Apache-2.0 © 2026 Akul Suhail Malhotra.
