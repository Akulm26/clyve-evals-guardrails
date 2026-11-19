# Live rollout: shadow → canary → segment

Offline cases show a workflow *can* work. Only live traffic shows it *does*. Workflows with `send_bulk`, `activate_flow` or `client_crm_bulk_write` need a decision log before the gate will call them DEPLOYABLE.

## The stages

| Stage | Share of traffic | Clean days to move on | What happens |
|---|---|---|---|
| shadow | 0% | 7 | the workflow decides, nothing is sent; you compare its decisions with what you'd have done |
| canary | 5% | 7 | real sends to a small slice |
| segment | 25% | 14 | a full segment; DEPLOYABLE once the log has earned this stage |

A **clean day** has at least 20 items and no breach. A **breach** on any day drops the workflow back to shadow and resets the count:

- unsubscribes above 1% of sends, complaints above 0.1%, guards failing on more than 5% of items (policy defaults; set yours under `rollout.guard_metrics`)
- replies below `reply_rate_min`, if you set one
- the kill switch flipped
- cost per item or p95 latency over the manifest's `budgets`

Days with fewer than 20 items are "thin": they neither count nor breach.

## The manifest

```yaml
rollout:
  log: logs/decisions.jsonl
  stages:                                   # optional; these are the defaults
    - {name: shadow, share: 0.00, days: 7}
    - {name: canary, share: 0.05, days: 7}
    - {name: segment, share: 0.25, days: 14}
  guard_metrics: {reply_rate_min: 0.02, unsubscribe_rate_max: 0.01, complaint_rate_max: 0.001}
budgets:
  usd_per_item: 0.25
  p95_seconds: 90
  whatsapp_rates: {marketing: 0.0107, utility: 0.0014}   # your current rates; prices change, so the policy doesn't hard-code them
```

## The decision log

One JSON line per item the workflow handled:

```json
{"ts": "2026-11-18T10:02:00+05:30", "sent": true, "guard_passed": true, "replied": false,
 "unsubscribed": false, "complained": false, "cost_usd": 0.03, "latency_s": 41.2,
 "channel": "email", "category": null, "kill_switch": false}
```

A row with neither `sent` nor `guard_passed` counts as a guard failure. A step that logged nothing didn't pass.

Fill `replied`, `unsubscribed` and `complained` in later (a nightly job that reads the inbox or the ESP's webhooks) by rewriting the day's rows. WhatsApp rows without `cost_usd` are priced from `budgets.whatsapp_rates` by `category`.

### Python

```python
import json, time
from datetime import datetime, timezone

def log_decision(path, *, sent, guard_passed, cost_usd=None, latency_s=None, **extra):
    row = {"ts": datetime.now(timezone.utc).isoformat(), "sent": sent, "guard_passed": guard_passed,
           "cost_usd": cost_usd, "latency_s": latency_s, **extra}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")

t0 = time.monotonic()
verdict = combine([outreach_guard.check(msg, lead, ctx, policy), output_guard.check(msg["body"], policy, ctx)])
sent = bool(verdict) and send(msg)          # your sender
log_decision("logs/decisions.jsonl", sent=sent, guard_passed=bool(verdict),
             latency_s=round(time.monotonic() - t0, 1), channel=msg["channel"])
```

### n8n

After the step that calls the guard (`POST` to your guard service, or a Code node running the package), add a **Code** node:

```js
const v = $('Guard').item.json;            // { passed, violations }
return [{ json: {
  ts: new Date().toISOString(),
  sent: $('Send').item.json?.id ? true : false,
  guard_passed: v.passed,
  latency_s: ($now - $execution.startedAt) / 1000,
  channel: $json.channel,
} }];
```

then an **Append to file** (or a database insert) that writes one line to `logs/decisions.jsonl`.

## Check it

```bash
gtm-evals rollout status workflows/teardown-outreach.yaml
# Clyve teardown outreach: stage canary (shadow → canary → segment), 3/7 clean days
#   2026-11-10  shadow   advance  7 clean days
#   2026-11-13  canary   thin     12 items < 20
#   budgets: $0.031/item · p95 44s  ✅
```

Exit code 0 when the log has earned `segment`; 1 otherwise.
