"""Recipe 2 — gate an AI-written post or page against the brand's claims register.

    python examples/content_draft.py
"""
from gtm_evals import claims_gate, combine, load_policy, manipulation_guard, promise_guard
from gtm_evals.judges import load_template, render

policy = load_policy()
register = [
    {"id": "C1", "claim": "4.6★ across 2,140 reviews", "values": ["4.6", "2140"], "status": "have"},
    {"id": "C2", "claim": "40% repeat purchase rate", "values": ["40"], "status": "gettable"},
]


def check_draft(text: str):
    v = combine(claims_gate.check(text, register, policy), promise_guard.check(text, policy),
                manipulation_guard.check(text, policy))
    return v


if __name__ == "__main__":
    for draft in ["Rated 4.6★ across 2,140 reviews, ground in small batches.",
                  "40% of buyers come back. Trusted by 50k kitchens. Guaranteed to be the top answer on ChatGPT."]:
        v = check_draft(draft)
        print(("PASS  " if v else "BLOCK ") + draft)
        for x in v.violations:
            print("   ", x)
    # The code layer can't judge "is this generic?". Render the swap-test judge for your model of choice:
    system, user = render(load_template("swap_test"), {"text": "We make spices with love.", "brand": "Example Co",
                                                        "competitors": "Competitor A, Competitor B", "claims_register": register})
    print("\nSwap-test judge prompt ready:", len(system) + len(user), "chars (send to any LLM, or use gtm-evals judge calibrate)")
