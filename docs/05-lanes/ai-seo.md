# Lane · AI SEO (technical foundation + visibility measurement)

Manifests use `lane: ai_seo` (the old name `ai_visibility` still works). Required guards: `ai_seo_guard`, `visibility_stats`, `promise_guard`.

AI SEO has two halves, and both need guards:

1. **The technical foundation** (ContentOS E1 and E2): can AI search reach the site, read it without running JavaScript, and tell which entity it's about? This is the part Clyve can promise.
2. **The measurement** (A6, A7, E6): did the brand's presence in AI answers actually move?

## 1. Technical foundation

| Failure | Guard | Notes |
|---|---|---|
| robots.txt blocks a search or answer crawler (OAI-SearchBot, ChatGPT-User, Claude-SearchBot, Claude-User, PerplexityBot, Perplexity-User, Googlebot, Bingbot) | `ai_seo_guard.crawler_access(robots_txt, policy, path)` | RFC 9309 matching: the group that names the crawler wins over `*`, the longest rule wins, and Allow wins a tie. Checked per path, so `/products/` can fail while `/` passes |
| Training crawlers blocked (GPTBot, ClaudeBot, Google-Extended, Applebot-Extended, CCBot, meta-externalagent) | `ai_seo_guard.training_access()`, **report only** | The client's choice. Blocking training doesn't remove the brand from answers |
| Key facts only appear after JavaScript runs | `ai_seo_guard.raw_html(html, policy, must_contain=[...])` | Pass the HTML as served, not as rendered. Fails JS shells (under `min_words_without_js` visible words) and any `must_contain` phrase missing from the raw HTML |
| Page kept out of search | `raw_html` | `meta robots` noindex / nosnippet / none |
| Duplicate or ambiguous URL | `raw_html` | needs an absolute canonical link and a `<title>` |
| Missing or broken schema | `ai_seo_guard.schema(html, policy, required=[...])` | JSON-LD only; `@graph` and nested nodes are read; required fields per type in `ai_seo.schema_required_fields` |
| The brand is a different entity on each channel | `ai_seo_guard.entity_consistency(profiles, canonical, policy)` | name must be the canonical name or a listed alias; each description must use ≥ 60% of the canonical one-liner's words |

```bash
gtm-evals seo page.html --robots robots.txt --path /products/chai-masala \
          --must "winter chai masala" --schema Organization,Product --entity profiles.json
```

The guard never fetches anything itself: save robots.txt and the raw HTML (`curl -s URL > page.html`, no browser) and pass the files. Crawler names change, so they live in the policy (`ai_seo.answer_crawlers`, `ai_seo.training_crawlers`); check each vendor's crawler documentation when you update them.

## 2. Visibility measurement

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
| Blaming content when the site blocks AI crawlers | `ai_seo_guard.crawler_access` + `raw_html` before every baseline and re-score | Golden set `evals/lanes.jsonl` (seo01–seo17) |
| A report promises citations or rankings | `promise_guard` is required in this lane | — |
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
