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


## Added in 0.1.1

| Failure | Guard |
|---|---|
| A food, supplement, health or personal-care post makes a claim it can't make ("cures", "treats diabetes", "no side effects") | `claim_safety_guard`: blocks |
| A claim that needs proof the approver hasn't seen ("clinically proven", "immunity booster", "100% natural", "India's No. 1", naming a competitor) | `claim_safety_guard`: escalates to the approver |
| Scraped reviews or customer quotes steer the content engine, or carry personal data into a post | `injection_guard` and `pii_guard` are now required in this lane |
| A post goes live without a recorded sign-off | the gate needs `approval_log` for any `publish` action, and a preview (`preview_before_publish: true`) in place of a canary |

`gtm-evals check draft.txt --category food --competitor "Brand X"` runs the regulated-claims pass from the command line. Patterns follow the ASCI code and FSSAI advertising rules as a starting point; they're not legal advice, so review them per category.


## Added in 0.2.0

| Failure | Guard |
|---|---|
| A post quotes a "customer" who never said it, rewords a real review, or shows "23 people are viewing this" | `testimonial_guard`: unregistered quotes and counters block, reworded quotes escalate |
| An ad uses a real person's face or voice without consent, or an AI image with no label | `likeness_guard` |
| A landing page or checkout pre-ticks an add-on, hides a fee until the last step, or shames people who decline | `dark_pattern_guard` |

Keep the testimonial register next to the claims register: `id`, `quote` (exact), `author`, `source`, `date`, `consent`, and `ai_generated` / `insider` flags. The likeness register holds `id`, `name`, `consent`, `scope` (e.g. `ads`, `social`) and `expires`.
| "98% accurate AI", "earn ₹50,000 a month with AI" | `offer_guard`: needs a registered test-evidence ID |
| "Was ₹799, now ₹549" when it sold at ₹549 all month | `offer_guard`: the reference price must be the 30-day low; MRP is checked against the pack |
