# gtm-evals

[![ci](https://github.com/Akulm26/clyve-evals-guardrails/actions/workflows/evals.yml/badge.svg)](https://github.com/Akulm26/clyve-evals-guardrails/actions/workflows/evals.yml)
[![release](https://img.shields.io/github/v/release/Akulm26/clyve-evals-guardrails?label=release)](https://github.com/Akulm26/clyve-evals-guardrails/releases)
[![python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](pyproject.toml)
[![license](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![container](https://img.shields.io/badge/ghcr.io-akulm26%2Fgtm--evals-purple)](https://github.com/Akulm26/clyve-evals-guardrails/pkgs/container/gtm-evals)

**Evals and guardrails for AI GTM engineering.** Stop your AI outbound, content and marketing automations from inventing facts, making promises, spamming, leaking data or acting without a human, *before* they reach a real person.

## Install

| Route | Command |
|---|---|
| **pip (pinned release)** | `pip install "git+https://github.com/Akulm26/clyve-evals-guardrails@v0.1.0"` |
| **pip (wheel from the release)** | `pip install https://github.com/Akulm26/clyve-evals-guardrails/releases/download/v0.1.0/gtm_evals-0.1.0-py3-none-any.whl` |
| **GitHub Action** | `uses: Akulm26/clyve-evals-guardrails@v0.1.0` (see below) |
| **Docker (GitHub Packages)** | `docker run --rm -v "$PWD:/work" ghcr.io/akulm26/gtm-evals:0.1.0 --help` |
| **with LLM judges** | add `[judges]`: `pip install "gtm-evals[judges] @ git+https://github.com/Akulm26/clyve-evals-guardrails@v0.1.0"` |

## Quickstart

```bash
gtm-evals init                       # config, a workflow manifest, a sample golden set
gtm-evals check draft.txt            # ❌ promise language: 'guarantee' · unsourced number '50,000'
gtm-evals eval evals/golden.jsonl    # recall / precision per guard on your own cases
gtm-evals gate workflows/*.yaml      # DEPLOYABLE · PILOT ONLY · BLOCKED
```

## Use it in your CI (GitHub Action)

Block a merge when any automation in the repo isn't deployable, safe and ethical:

```yaml
# .github/workflows/gtm-evals.yml
on: [push, pull_request]
jobs:
  gtm-evals:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Akulm26/clyve-evals-guardrails@v0.1.0
        with:
          command: gate                 # gate | eval | check
          args: "workflows/*.yaml"
      - uses: Akulm26/clyve-evals-guardrails@v0.1.0
        with:
          command: eval
          args: "evals/golden.jsonl"
```

The report shows up in the run's summary. The step fails if a workflow is BLOCKED or a guard falls below its recall/precision threshold.

Pure Python, one dependency (`pyyaml`), no API key needed. LLM judges are optional (`pip install "gtm-evals[judges]"`).

Built by [Clyve](https://clyve.io), a boutique AI consulting firm: *Content Strategy and Engineering.*

---

## Why

Marketing AI rarely says anything toxic. It fails in quieter, more expensive ways:

| It… | Example | Caught by |
|---|---|---|
| states a number nobody can prove | "Trusted by 50,000 kitchens" | `claims_gate` |
| promises what nobody controls | "You'll rank #1 on ChatGPT in 30 days" | `promise_guard` |
| invents personalisation | "Loved your Shark Tank episode!" (there wasn't one) | `outreach_guard` |
| pressures people | "Only 2 slots left, last chance" | `manipulation_guard` |
| follows instructions hidden in a review | "Ignore previous instructions and…" | `injection_guard` |
| sends personal data to a model | phone numbers, emails, PAN, Aadhaar | `pii_guard` |
| sends the same WhatsApp twice, at 11pm, to someone who opted out | | `automation_guard` |
| auto-replies "sure, 50% off!" to an angry customer | | `automation_guard` (allowlist replies) |
| bulk-sends with nobody watching | | `ActionGate` (R3: approval + canary + kill switch) |
| reports "visibility up 30%" that's just noise | | `visibility_stats` |

## The objective: deployable, safe, ethical

Every automation gets a manifest. The gate rules it:

```
Any SAFE or ETHICAL check fails?  → BLOCKED      don't run it
Evidence still synthetic?         → PILOT ONLY   a human checks every action that reaches a real person
Otherwise                         → DEPLOYABLE
```

| | The question | Checked |
|---|---|---|
| **Safe** | Can it do damage at scale? | risk tier per action · required guards for the lane · kill switch · named approver + canary for bulk · logs ≥ 90 days · token budget |
| **Ethical** | Is it honest and fair to the people it touches? | lawful basis + consent at send · data minimisation · opt-outs ≤ 48 h · no protected attributes in scoring/targeting · automated replies disclose + offer a human · no promises · pressure tactics flagged |
| **Deployable** | Is there real evidence it works? | ≥ 30 real golden cases · every judge calibrated (≥ 30 labels, ≥ 85% agreement) · named owner |

Details: [docs/12-deployment-gate.md](docs/12-deployment-gate.md).

## Use it in code

```python
from gtm_evals import load_policy, claims_gate, outreach_guard, ActionGate, combine

policy = load_policy()                       # defaults (+ ./gtm-evals.yaml if present)

v = claims_gate.check(draft, claims_register, policy)
if not v:
    print(v.violations)                      # ["unsourced number '50,000' — not in claims register"]

gate = ActionGate(policy)
ok = gate.authorize("send_bulk", checks=[v], evaluator_passed=True,
                    approval_id="AK-1118-01", canary_done=True)
```

Every guard returns a `Verdict`: truthy when it passes, with `.violations` and `.escalate`.

| Module | What it checks |
|---|---|
| `claims_gate` | every number traces to a proven claim; every ₹/Rs/INR figure is stamped; assumed figures are ranges |
| `promise_guard` | outcome, ranking and timeline promises (negations like "we can't guarantee" pass) |
| `manipulation_guard` | false urgency/scarcity, fear, guilt → escalate to a human |
| `outreach_guard` | lawful basis, suppression, channel opt-in, unsubscribe, sender auth, ICP exclusions, sourced + fresh personalisation, undeclared facts, private metrics before intake, caps; `deliverability()` stop rules |
| `automation_guard` | tenant isolation, consent at send, idempotency, frequency caps, quiet hours, mixed-content = promotional, audience-size sanity; replies are allowlisted |
| `injection_guard` | flags instruction-like text; `wrap()` marks scraped/inbound text as untrusted data |
| `pii_guard` | email, Indian mobile, PAN, Aadhaar; `redact()` / `restore()` around model calls |
| `visibility_stats` | frozen prompt-set hash, no blended numbers, app vs API separation, `real_change()` (noise + chance band), `smallest_provable_move()` |
| `ActionGate` | R0–R3 risk tiers, required evidence per tier, kill switch, token budget |
| `gate` | the deployment gate above |
| `judges` | 6 LLM-judge templates: swap test, on-thesis, personalisation factuality, claim safety, description accuracy, promise check |

## Configure

`gtm-evals init` writes `gtm-evals.yaml`. Any key overrides the bundled default (see them all with `gtm-evals policy`). Presets:

```yaml
profile: clyve          # founder-led D2C, India: ICP exclusions, Clyve kill switch
outreach:
  excluded_categories: ["trading", "real estate"]
```

## Golden sets (your own test cases)

```json
{"id": "c1", "guard": "claims", "input": {"text": "Trusted by 50,000 kitchens.", "register": "claims_register.json"},
 "expected_pass": false, "source": "real", "why": "invented number"}
```

`guard` is one of `claims · promise · manipulation · injection · pii · outreach · automation_send · automation_reply`. Only `"source": "real"` rows count as deployment evidence. Every approver rejection or edit should become a row.

## How good are the guards? (honest numbers)

| | Result |
|---|---|
| Held-out adversarial set, code only | 13/25 before fixes → **20/25** after |
| Held-out, code + judges | 25/25, with the judges simulated, not calibrated |
| End-to-end pipeline scenarios | 8/8 |
| Bugs found by simulation and fixed | 17, including 3 high-severity action-gate bugs |

Pattern-matching code catches what someone thought of in advance. New phrasings get past it, which is why the judge layer exists and why judges must be calibrated on *your* labels before you trust them. Full report: [docs/11-simulation-report.md](docs/11-simulation-report.md).

## Recipes

| File | What it shows |
|---|---|
| [examples/outbound_presend.py](examples/outbound_presend.py) | check a cold email before your sending tool sends it |
| [examples/content_draft.py](examples/content_draft.py) | gate an AI-written post against the brand's claims register, then hand off to the swap-test judge |
| [examples/lifecycle_send.py](examples/lifecycle_send.py) | quiet hours, consent, and AI auto-replies on WhatsApp |

## Learn it by breaking it

```bash
git clone https://github.com/Akulm26/clyve-evals-guardrails && cd clyve-evals-guardrails
pip install -e ".[dev]"
python learn/check.py 1     # sneak a fake number past the gate, then fix it
python learn/check.py 2     # is that AI-visibility jump a win or noise?
python learn/check.py 3     # catch a stretched personalisation
```

## The playbook

The `docs/` folder is the thinking behind the code:

```
00-mental-model.md        guardrails vs evals; the 3 eval levels
01-clyve-system-map.md    a real business end to end, and where AI breaks it
02-architecture.md        tier choice, generator/evaluator contract, context + token plan
03-guardrail-layers.md    4 layers × 3 enforcement types; risk tiers R0–R3
04-eval-system.md         golden sets, judges, calibration, online + outcome evals
05-lanes/                 content ops · AI visibility · GTM engineering · marketing automation
06-compliance-india.md    DPDP, TRAI, WhatsApp, Gmail/Yahoo bulk-sender rules (sourced)
07-failure-modes.md       MAST failure taxonomy for marketing systems
08-operating-cadence.md   what runs per output / day / week / engagement
09-scope-ladder.md        bringing automation in step by step
10-kpi-formulas.md        76 KPI formulas (generated from kpi/)
11-simulation-report.md   what was stress-tested, what broke
12-deployment-gate.md     deployable / safe / ethical
```

## Repo layout

```
src/gtm_evals/        the library (guards, gate, runner, judges, CLI, bundled policy + templates)
workflows/            manifests for Clyve's own automations (+ examples/ that must stay BLOCKED)
evals/datasets/       golden sets for this repo
sim/                  adversarial fuzz, held-out set, end-to-end pipeline, judge simulation
kpi/                  Clyve / ContentOS KPI formulas as code
learn/                break-and-fix exercises
examples/             copy-paste recipes
action.yml            the GitHub Action
Dockerfile            the ghcr.io image
tests/                pytest
```

## Contributing

The most valuable contribution is **a real failure** the guards missed. Add it as a golden-set row, show the miss, fix the guard without new false alarms. See [CONTRIBUTING.md](CONTRIBUTING.md).

Not legal advice: the compliance mappings help engineers build the right checks. Confirm with counsel for your category and market.

## License

Apache-2.0.
