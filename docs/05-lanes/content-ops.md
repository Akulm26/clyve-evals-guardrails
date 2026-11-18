# Lane · Content ops

**What the AI does:** turns a founder's claims register into drafts (posts, pages, briefs, teardowns) that a named approver signs off.

## Failure → guard → eval

| Failure | Guard (inline) | Eval (offline) |
|---|---|---|
| Number not in the claims register ("40% repeat rate") | `claims_gate`: every number must match a `have` claim | Golden set with seeded invented stats; recall must be 1.0 |
| Claim exists but is only `gettable` / `none` | `claims_gate`: flags as unproven | Same |
| ₹ figure with no stamp, or a point estimate stamped `ASSUMED` | `claims_gate` stamp + range rules | Same |
| Promises: "guaranteed", "rank #1 on ChatGPT", "cited in 30 days" | `promise_guard` | Adversarial set with promises hidden mid-sentence |
| Generic copy that fits any competitor | — (needs judgment) | `judges/swap_test.md` with 2–3 named competitors |
| Off-thesis | — | `judges/on_thesis.md` with the one-sentence thesis |
| Regulated claims (food, health, supplements, comparatives) | Route to claim-safety judge when `regulated: true` | `judges/claim_safety.md`; human always signs off |
| Voice drift over weeks | — | **Approver edit distance** trend (online) |

## The gate, as code order

```
draft
 → claims_gate      (fail → regenerate with the violation list, max 2)
 → promise_guard    (fail → regenerate)
 → swap-test judge  (fail → regenerate with "the line that fits any brand: …")
 → on-thesis judge
 → [regulated?] claim-safety judge
 → approver (R3 for publish), approval ID logged
```

## If-then

- If the draft needs a fact the register doesn't have → **don't write it.** Raise an evidence request to the founder (proof-first tree: have → write, gettable → sprint, none → skip).
- If the approver edits the same kind of line three times → add a rule to the playbook and a row to the golden set.
- If the swap-test judge and the approver disagree more than ~15% of the time → recalibrate the judge before trusting it again.
