"""Recipe 1 — check a cold email before your sending tool sends it.

Wire `presend()` in front of whatever sends: an Instantly/Smartlead webhook, an n8n Code node, a script.
    python examples/outbound_presend.py
"""
from gtm_evals import ActionGate, combine, load_policy, manipulation_guard, outreach_guard, promise_guard

policy = load_policy()
gate = ActionGate(policy)


def presend(message: dict, lead: dict, context: dict, judge_passed: bool = True) -> tuple[bool, list[str]]:
    checks = combine(
        outreach_guard.check(message, lead, context, policy),
        promise_guard.check(message["body"], policy),
        manipulation_guard.check(message["body"], policy),
    )
    decision = gate.authorize("send_single", checks=[checks], evaluator_passed=judge_passed)
    return decision.passed, decision.violations


if __name__ == "__main__":
    lead = {"email": "sam@example.com", "category": "d2c food", "stage": "prospect",
            "lawful_basis": "legitimate_interest", "optin_channels": [],
            "signals": [{"fact": "launched 4 new Meta ads for the winter range",
                         "source_url": "https://www.facebook.com/ads/library/?id=1", "date": "2026-11-02"}]}
    ctx = {"today": "2026-11-18", "suppression": set(), "sent_today_by_inbox": {},
           "sender_auth": {"spf": True, "dkim": True, "dmarc": True}}
    good = {"channel": "email", "inbox": "you@example.com",
            "body": "Hi Sam, saw you launched 4 new Meta ads for the winter range. Worth a quick call? If not, reply stop.",
            "claims_about_lead": ["launched 4 new Meta ads for the winter range"]}
    bad = dict(good, body=good["body"] + " Loved your Shark Tank episode! We guarantee 2x sales. Only 2 slots left.")
    for name, msg in (("good", good), ("bad", bad)):
        ok, why = presend(msg, lead, ctx)
        print(f"{name}: {'SEND' if ok else 'BLOCK'}")
        for w in why:
            print("   ", w)
