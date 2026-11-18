# Lane · AI visibility measurement

**What the AI does:** runs a frozen set of 20–30 buyer prompts across ChatGPT, Perplexity and Gemini, detects whether the brand is mentioned, cited and described accurately, and compares checkpoints.

Here the guardrails protect **the measurement itself**. A bad measurement is worse than none, because it turns into a claim in front of a client.

## Failure → guard → eval

| Failure | Guard | Eval |
|---|---|---|
| Prompt set edited after Day 0 | SHA-256 hash of the prompt set stored at Day 0; `visibility_stats.check_frozen` refuses comparison on mismatch | — |
| One blended "visibility score" | `visibility_stats.rates` refuses rows with no `query_type`; reports brand / niche / best-X separately | — |
| Noise reported as a win | `visibility_stats.real_change`: change must beat run-to-run spread **and** a binomial interval | Seeded noisy dataset must return `real: false` |
| Brand alias missed ("Clyve" vs "clyve.io" vs "Clyve OS") | Alias list per brand in the intake sheet | Mention-detection golden set (hand-labelled answers) |
| Description judged "accurate" with nothing to check against | Accuracy judge gets the canonical one-liner + claims register | `judges/description_accuracy.md`, calibrated |
| API answers mixed into an interface-based client report | Every row has `surface: app|api`; report builder refuses mixing | — |
| Blaming content when the site blocks AI crawlers | Pre-check: robots.txt for GPTBot, ClaudeBot, PerplexityBot; raw-HTML readability | Checklist item at A7 |
| No screenshot at collection time | Row without `screenshot_path` is invalid | — |

## The noise rule, in plain words

Run every prompt 3 times. At Day 0 the brand shows up in, say, 30%, 40% and 35% of answers. That 10-point spread is your noise. At Day 30 it's 45%. Is that real? Only if the jump (about 10 points) is bigger than the spread *and* bigger than what chance alone would explain with this many prompts. Otherwise the report says "no clear movement yet." That's an honest finding too.

## How big a set do you need?

The smallest move you can prove depends on how many prompts there are per query type. This assumes 3 runs per prompt, a mention rate near 50%, and runs that agree with each other (real run-to-run spread makes it worse).

| Prompts per query type | Smallest provable move |
|---|---|
| 8 | ~28 pts |
| 10 | ~25 pts |
| 15 | ~21 pts |
| 20 | ~18 pts |
| 30 | ~15 pts |
| 40 | ~13 pts |

**Implication for A6:** a 20–30 prompt set split across brand / niche / best-X gives about 8–10 prompts per type, which can only prove moves of about 25 points or more. If you need to show smaller wins:
- **If** brand and niche are where movement is promised → put most of the prompts there (e.g. 20 brand + 20 niche + 10 best-X).
- **If** the set has to stay small → report small moves as "direction, not yet proven," never as a number.

`learn/` exercise 2 walks through the math.

## What you can and can't claim

- Brand and niche queries: movement as a direction, typically weeks.
- Generic "best X" queries: never a promise or a timeline. They depend on third-party coverage.
- No answer positions or rankings promised, ever. `promise_guard` enforces this in copy.
