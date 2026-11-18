"""Render the formulas as markdown for the repo. python -m kpi.build_md > docs/10-kpi-formulas.md"""
from . import ALL, LAYERS, OPEN_ITEMS


def build():
    out = ["# 10 · KPI formulas (Clyve and ContentOS)",
           "",
           "> Generated from `kpi/` — the same source that renders the KPI page in the Clyve project. Edit the data, not this file.",
           f"> {len(ALL)} metrics. Provisional: freeze definitions at Day 0 of each engagement.",
           "",
           "## How the guardrails map to the KPIs",
           "",
           "| KPI | Enforced or measured by |",
           "|---|---|",
           "| O2 movement, C5 prompt-set power | `src/gtm_evals/visibility_stats.py` (`real_change`, `smallest_provable_move`) |",
           "| A5 description accuracy | `src/gtm_evals/data/judges/description_accuracy.md`, gated by Q3 |",
           "| G6 personalisation accuracy | `src/gtm_evals/outreach_guard.py` + `src/gtm_evals/data/judges/personalisation_factuality.md` |",
           "| G7 bounce, G8 spam complaints | `outreach_guard.deliverability` stop thresholds in `src/gtm_evals/data/default.yaml` |",
           "| Q1 catch rate, Q2 false alarms | `evals/run_evals.py` |",
           "| Q3 judge agreement | `evals/judge.py` |",
           "| Q4 approver edit rate | approval log → new golden-set rows (`docs/08-operating-cadence.md`) |",
           "| Q5 escalations, Q9 R3 incidents | `src/gtm_evals/action_gate.py` |",
           "| Q6 duplicate sends, Q7 consent at send | `src/gtm_evals/automation_guard.py` |",
           "| Q8 opt-out time | reply classifier (opt-out recall 1.0) + suppression log |",
           "",
           "## All formulas", ""]
    for num, _, title, lead, ms, _ in LAYERS:
        out += [f"### {title}", "", lead, "", "| ID | Metric | Formula | Data from |", "|---|---|---|---|"]
        for m in ms:
            flag = " **(new)**" if m.changed == "new" else " **(updated)**" if m.changed else ""
            f = m.formula + ("<br>" + "<br>".join(m.subs) if m.subs else "")
            out.append(f"| {m.id}{flag} | {m.title} | {f.replace('|', '/')} | {m.src} |")
        out.append("")
    out += ["## Open items", "", "| # | Open item | What to do |", "|---|---|---|"]
    out += [f"| {i} | {a} | {b} |" for i, (a, b) in enumerate(OPEN_ITEMS, 1)]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    print(build(), end="")
