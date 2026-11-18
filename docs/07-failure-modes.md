# 07 · Failure modes (MAST, translated for marketing systems)

The MAST taxonomy (Cemri et al., 2025) catalogued why multi-agent LLM systems fail. Here are the top modes, what they look like in marketing work, and the countermeasure in this repo.

| MAST mode | Approx. prevalence | Looks like in marketing | Countermeasure |
|---|---|---|---|
| Step repetition | 15.7% | Same follow-up sent twice; recon re-run on the same brand all day | Idempotency keys; persisted progress state (`automation_guard`) |
| Reasoning–action mismatch | 13.2% | Agent "decides" to skip an opted-out contact, then sends anyway | Gate checks the **action payload**, not the agent's stated plan (`action_gate`) |
| Unaware of stopping conditions | 12.4% | Enrichment loop keeps calling paid APIs on a dead lead | Budget + retry caps in policy; machine-checkable stop |
| Disobey task spec | 11.8% | Invents a stat; uses a retired term; adds a promise | Spec first in context; `claims_gate`, `promise_guard` |
| Incorrect verification | 9.1% | Judge approves a draft because it "reads well" | Judges always get ground truth (register, signals, competitors) |
| No / incomplete verification | 8.2% | "Email rendered" counted as success; nobody checked the facts | Multi-level: syntax → facts → objective ("does this get a call?") |
| Task derailment | 7.4% | Teardown turns into a full free audit | Scope rules in spec; evaluator checks scope (≤3 findings) |
| Fail to ask for clarification | 6.8% | Guesses the ICP when intake is missing | Clarification gate: missing required intake field → stop |
| Premature termination | 6.2% | Marks re-score "done" with one run per prompt | Stop only on verified criteria (≥2 runs, screenshots present) |

Also watch: **silent tool failures** (n8n "continue on fail"), **context saturation** (whole claims register pasted every call), **multi-turn drift** (long chat threads used as the spec), **error amplification** across parallel workers with no aggregation check.
