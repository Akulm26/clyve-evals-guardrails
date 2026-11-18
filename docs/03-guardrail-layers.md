# 03 · Guardrail layers and risk tiers

## Four layers

```
┌──────────────────────────────────────────────────────────────┐
│ 1 INPUT      What enters the model                           │
│              PII redaction · injection scan · source tagging │
├──────────────────────────────────────────────────────────────┤
│ 2 CONTEXT    What the model is allowed to know and use       │
│              claims register only · tenant isolation ·       │
│              frozen prompt set · fresh signals only          │
├──────────────────────────────────────────────────────────────┤
│ 3 OUTPUT     What the model produced                         │
│              numbers traceable · stamps present · no promises│
│              personalisation factual · swap test · claim-safe│
├──────────────────────────────────────────────────────────────┤
│ 4 ACTION     What happens in the world                       │
│              risk tier · consent · caps · quiet hours ·      │
│              idempotency · human approval · kill switch      │
└──────────────────────────────────────────────────────────────┘
```

**Most teams build layer 3 only.** In marketing systems, layer 4 is where the money and the legal risk sit. Layer 2 is where the *quality* comes from: a model that can only use the claims register can't invent proof in the first place.

## Risk tiers

Tier = how bad it is if wrong × how hard it is to undo.

| Tier | Action | Examples | Required gates |
|---|---|---|---|
| **R0** | Internal draft, nobody external sees it | Recon notes, brief drafts, internal scoring | Input guards |
| **R1** | Internal write | CRM field update, ICP score, lead tag, report draft | + deterministic output guards |
| **R2** | External, one recipient | One teardown email, one DM, one AI reply in a thread | + evaluator pass + logged |
| **R3** | External, many recipients or public | Campaign send, lifecycle flow activation, publishing a post, writing to a client's CRM in bulk | + human approval ID + canary (5%, watch, then rest) + kill switch armed |

**If-then for new actions:** if you're not sure which tier, pick the higher one. Demoting a tier needs a week of clean logs.

## Who enforces what

| Check | Layer | Enforcement | File |
|---|---|---|---|
| Redact emails, Indian mobiles, PAN, Aadhaar before LLM calls | Input | Deterministic | `src/gtm_evals/pii_guard.py` |
| Flag instructions hidden in scraped text | Input | Deterministic + wrap as untrusted | `src/gtm_evals/injection_guard.py` |
| Every number traceable to a `have`-status claim | Output | Deterministic | `src/gtm_evals/claims_gate.py` |
| Every ₹ figure stamped; `ASSUMED` ₹ must be a range | Output | Deterministic | `src/gtm_evals/claims_gate.py` |
| No outcome promises / ranking guarantees | Output | Deterministic | `src/gtm_evals/promise_guard.py` |
| Personalisation facts match real, fresh signals | Output | Deterministic | `src/gtm_evals/outreach_guard.py` |
| No private-metric claims before intake | Output | Deterministic | `src/gtm_evals/outreach_guard.py` |
| On-thesis, swap test, claim safety | Output | LLM judge + reference | `src/gtm_evals/data/judges/*.md` |
| Consent per channel, suppression, unsubscribe, caps | Action | Deterministic | `src/gtm_evals/outreach_guard.py` |
| Idempotency, frequency cap, quiet hours, tenant match | Action | Deterministic | `src/gtm_evals/automation_guard.py` |
| Tier → required approvals, kill switch, budget | Action | Deterministic | `src/gtm_evals/action_gate.py` |
