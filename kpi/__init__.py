"""Clyve and ContentOS KPI formulas — single source of truth.

    python -m kpi.build_html  > Clyve_and_ContentOS_KPI_Formulas.html
    python -m kpi.build_md    > docs/10-kpi-formulas.md
"""
from .metrics_a import LAYER1, LAYER2, LAYER3, LAYER4
from .metrics_b import LAYER5, LAYER6, LAYER7, LAYER8, LAYER9
from .metrics_c import LAYER10

LAYERS = [
    # (num, anchor, title, lead, metrics, part)
    (1, "layer1", "Layer 1: Diagnostic tracks", "Scored from public data, except D1 and D2, which only score after the founder call. These explain why content is not landing.", LAYER1, "A"),
    (2, "layer2", "Layer 2: AI/Search Visibility", "Computed from the run log. Every formula is per query type and per platform.", LAYER2, "A"),
    (3, "layer3", "Layer 3: Outcome KPIs", "Re-computed at Day 30, 60 and 90 against the Day 0 baseline.", LAYER3, "A"),
    (4, "layer4", "Layer 4: Revenue bridge", "Connects visibility to the client's revenue. All three are proposed and need client analytics access.", LAYER4, "A"),
    (5, "layer5", "Layer 5: Sales funnel", "Clyve's own funnel from Teardown to retainer. All five are proposed.", LAYER5, "B"),
    (6, "layer6", "Layer 6: Acquisition engine", "Clyve's own LinkedIn and Instagram presence. The goal is inquiries from the right audience.", LAYER6, "B"),
    (7, "layer7", "Layer 7: Lead gen", "The second pillar. Sold when it comes up, so these have no baseline yet. Every qualified lead ships with a handoff package. G6 to G8 also run on Clyve's own teardown outreach.", LAYER7, "B"),
    (8, "layer8", "Layer 8: Product line", "Gumroad resources, each tied to one goal: views, engagement or leads. Every resource is public-safe and evergreen.", LAYER8, "B"),
    (9, "layer9", "Layer 9: The firm", "Revenue, delivery load and proof across the whole business.", LAYER9, "B"),
    (10, "layer10", "Layer 10: Guardrails and evals", "Whether the system itself can be trusted: the QA gate, the judges, and every automated send. Covers content ops, AI visibility, GTM engineering and marketing automation.", LAYER10, "C"),
]

NEW = {"C5", "G6", "G7", "G8", "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9"}
CHANGED = {"O2", "A5"}

for num, _, _, _, ms, _ in LAYERS:
    for m in ms:
        m.layer = num
        m.changed = "new" if m.id in NEW else "changed" if m.id in CHANGED else None

ALL = [m for *_, ms, _ in LAYERS for m in ms]

OPEN_ITEMS = [
    ("Score bands are unvalidated until 3 to 5 real audits are complete.", "Never sell an absolute score."),
    ("D1 and D2 have no written scoring rule yet.", "Write one before the first audit."),
    ("The noise band from 2 to 3 passes is crude. Updated 18 Nov 2026: O2 now also requires the move to beat a chance band, and C5 states the smallest provable move per segment.", "Use both bands now. After the first 3 audits, replace the chance-band assumption with the measured run-to-run variance."),
    ("Working definitions for D4, D5, D8, D10, D11 and A1 to A5 are proposed wording.", "Confirm them, then freeze at Day 0 of each engagement."),
    ("R2 needs a minimum count before a rate can be quoted.", "Until it is set, report raw counts."),
    ("B4 has no rule for what counts as 'published what Clyve shipped'.", "Decide before the first Day 30 retainer decision."),
    ("The AI crawler list and the GA4 AI referrer list change over time.", "Confirm both at the start of each audit."),
    ("API answers and real-interface answers diverge sharply.", "Client reports use real interfaces with screenshots; any API trend track stays separate."),
    ("Terms for automating consumer chat interfaces are unchecked.", "Check before automating any baseline."),
    ("Part B has no baselines or targets yet.", "Track for 4 weeks, then set targets from what the numbers show."),
    ("Lead gen is not actively pushed, and its qualification rule is set per client.", "Compare each client with itself, and set the rule before sourcing starts."),
    ("E5 undercounts, because many people find Clyve through content without saying so.", "Ask 'how did you find Clyve?' in every first reply."),
    ("Confirm which fields Gumroad Analytics exposes, and whether revenue is gross or net.", "Decide before the first product report."),
    ("There is no time log yet for F4.", "Start logging hours per engagement from the first Audit."),
    ("With 20 to 30 prompts split three ways, each segment can only prove large moves (C5). More prompts means more manual runs.", "Keep the set size. Weight prompts toward brand and niche when proof of smaller moves matters, and report anything under the C5 bar as direction."),
    ("No contact record yet stores lawful basis, source and channel opt-in (Q7). DPDP core obligations apply in full by May 2027.", "Add the fields to the lead log and every client CRM touched in Build, now."),
    ("No model judge has been calibrated yet (Q3).", "Label 30 real cases per judge before any judge marks A5 or gates an R2 action."),
    ("The promotional quiet-hours window (21:00 to 10:00 IST) follows TRAI's Service Explicit SMS band; WhatsApp and email have no statutory window.", "Re-check TRAI rules quarterly. Keep the window for all promotional sends anyway."),
    ("Golden sets are seeded by the guard author (Q1, Q2).", "Add every real rejection, edit and escalation as a row; review weekly."),
]
