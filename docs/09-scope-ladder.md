# 09 · Scope ladder: how GTM engineering and marketing automation enter Clyve

Clyve's positioning has two pillars: **content strategy** (the active focus) and **lead gen** (a stable second). RevOps and paid-ads management are out of scope, and the client's own team runs whatever Clyve builds.

GTM engineering and marketing automation are both in this repo. Neither one is a bet made on day one. Each moves up a ladder, and **every rung is unlocked by evidence from the rung below it**, the same way the retainer is unlocked by a Day 30 re-score.

```
                       ┌──────────────────────────────────────────────┐
  STEP 4  SERVICE      │ Sold as its own line (lead gen first,         │  unlock: 3 clients running
                       │ automation only if clients keep asking)       │  steps 2–3 cleanly for 90 days
                       └──────────────────────────────────────────────┘
                       ┌──────────────────────────────────────────────┐
  STEP 3  INSIDE BUILD │ Flows built during E4–E5, run by the          │  unlock: guard module adopted
                       │ client's team after handover                  │  by 1 client, zero R3 incidents
                       └──────────────────────────────────────────────┘
                       ┌──────────────────────────────────────────────┐
  STEP 2  GUARD MODULE │ Guards + rulebook handed over for automation  │  unlock: step 1 ran 60 days,
                       │ the client already has                        │  deliverability inside limits
                       └──────────────────────────────────────────────┘
                       ┌──────────────────────────────────────────────┐
  STEP 1  DOGFOOD      │ Clyve's own teardown outreach + follow-up     │  start here (now)
                       │ ladder runs on these guards                   │
                       └──────────────────────────────────────────────┘
```

## Step by step

| Step | GTM engineering | Marketing automation | Evidence needed to move up |
|---|---|---|---|
| **1 · Dogfood** | Signals → enrichment → ICP score → teardown → outreach, for Clyve's own pipeline | The no-reply follow-up ladder (Day 3–7, Day 30, park) | 60 days of logs: bounce < 2%, complaints < 0.1%, zero invented-personalisation incidents, ICP score that predicts replies |
| **2 · Guard module** | Offered under the lead-gen pillar: the guarded pipeline, set up for the client | `automation_guard` + `action_gate` + rulebook added to flows the client **already runs** | One client adopts it; their team runs a full cycle without Clyve |
| **3 · Inside Build** | Lead-gen setup bundled with content when the brand needs both | Lifecycle flows (welcome, win-back, launch) built in E4, handed over in E5 with the rulebook. Their team runs them | Zero R3 incidents across handovers; client team passes the handover gate |
| **4 · Service** | Lead gen sold on its own (it's already a pillar, so this mostly means packaging and pricing) | Only if 3+ clients ask for ongoing automation help. Then it goes into the retainer tiers (A/B/C), not a new practice | Repeatable demand, not one request |

## If-then

- **If** a prospect wants "automation" at step 1 → sell the content work. Note the automation need in the intake as a Build candidate.
- **If** a client wants Clyve to run their flows forever → that's RevOps. Offer the guard module and the handover. Don't take operations.
- **If** step 1 logs show deliverability trouble → stop climbing. Fix your own pipeline before you put it near a client's.
- **If** a rung's evidence isn't there after its window → stay on that rung. The ladder has no deadline.

## Why this order

1. **Dogfooding makes the case study.** The first public proof that these guards work comes from Clyve's own outreach numbers.
2. **Guards before flows.** Selling safety for automation a client already has is lower risk and faster to deliver than building new flows.
3. **Handover keeps the positioning intact.** At steps 2 and 3, the client's team owns and runs everything. Clyve designs and builds.
