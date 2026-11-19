"""Phase 5: AI SEO reality test + site-wide checks, AI and price claims | incident drill, logs, approver fatigue."""
import json

import pytest

from gtm_evals import ai_seo_guard as seo
from gtm_evals import offer_guard, rollout
from gtm_evals.gate import check
from tests.conftest import drilled

GOOD_PAGE = """<html><head><title>Example Masala</title><meta name="description" content="Stone-ground spices from Ludhiana.">
<meta property="og:title" content="Example Masala"><meta property="og:description" content="Stone-ground spices.">
<link rel="canonical" href="https://example.in/"><link rel="alternate" type="application/rss+xml" href="/feed.xml"></head>
<body><h1>Example Masala</h1><h2>Our spices</h2><h3>Haldi</h3><img src="a.jpg" alt="Haldi">
<p>""" + "Stone-ground haldi and garam masala, made in small batches in Ludhiana since 2019. " * 12 + "</p></body></html>"


# ---------- the reality test ----------
def results(**override):
    r = {b: {"agent": b, "status": 200, "body": "<title>Example</title>"} for b in
         ["OAI-SearchBot", "Claude-SearchBot", "PerplexityBot", "Googlebot", "Bingbot"]}
    for k, v in override.items():
        r[k.replace("_", "-")] = dict(r[k.replace("_", "-")], **v)
    return list(r.values())


def test_all_crawlers_get_content(policy):
    v = seo.fetch_results(results(), policy)
    assert v and any("crawler's IP" in n for n in v.notes)


@pytest.mark.parametrize("bot,res,msg", [("PerplexityBot", {"status": 403}, "HTTP 403 (blocked by the firewall"),
                                         ("Googlebot", {"status": 500}, "HTTP 500"),
                                         ("OAI_SearchBot", {"body": "<title>Just a moment...</title>"}, "challenge page")])
def test_firewall_failures(bot, res, msg, policy):
    v = seo.fetch_results(results(**{bot: res}), policy)
    assert not v and msg in v.violations[0]


def test_missing_bot_is_a_note(policy):
    v = seo.fetch_results(results()[:4], policy)
    assert v and "no fetch result for Bingbot" in v.notes


def test_fetch_plan_has_every_bot(policy):
    plan = seo.fetch_plan("https://example.in/", policy)
    assert plan.count("curl ") == 5 and "PerplexityBot/1.0" in plan and plan.strip().endswith("echo ']' >> fetch.json")


# ---------- site-wide ----------
def test_page_checks_good(policy):
    assert all(seo.page_checks(GOOD_PAGE, policy).values())


@pytest.mark.parametrize("swap,check_name", [
    ('<meta name="description" content="Stone-ground spices from Ludhiana.">', "meta_description"),
    ("<h2>Our spices</h2>", "single_h1"),
    ('<meta property="og:title" content="Example Masala">', "open_graph"),
    ('alt="Haldi"', "image_alt"),
])
def test_page_checks_each(swap, check_name, policy):
    html = GOOD_PAGE.replace(swap, "<h1>Second</h1>" if check_name == "single_h1" else "")
    assert not seo.page_checks(html, policy)[check_name]


def test_heading_order(policy):
    assert not seo.page_checks(GOOD_PAGE.replace("<h2>Our spices</h2>", ""), policy)["heading_order"]   # h1 → h3


def test_eighty_percent_rule(policy):
    bad = GOOD_PAGE.replace('<meta name="description" content="Stone-ground spices from Ludhiana.">', "")
    files = {"llms.txt": "# Example Masala"}
    nine_one = {f"p{i}.html": GOOD_PAGE for i in range(9)} | {"bad.html": bad}
    v = seo.check_site(nine_one, policy, files)
    assert v and any("meta description: 1 page(s) fail (bad.html)" in n for n in v.notes)
    seven_three = {f"p{i}.html": GOOD_PAGE for i in range(7)} | {f"bad{i}.html": bad for i in range(3)}
    v = seo.check_site(seven_three, policy, files)
    assert not v and "meta description: 70% of pages pass, need 80%" in v.violations[0]


def test_site_files(policy):
    v = seo.check_site({"a.html": GOOD_PAGE.replace("application/rss+xml", "text/html")}, policy, {})
    assert "no /llms.txt" in v.violations and any("RSS or Atom" in x for x in v.violations)
    assert seo.check_site({"a.html": GOOD_PAGE.replace("application/rss+xml", "text/html")}, policy,
                          {"/llms.txt": "x", "feed.xml": "<rss></rss>"})


def test_no_pages(policy):
    assert not seo.check_site({}, policy)


# ---------- AI and price claims ----------
H = [{"date": "2026-11-01", "price": 549}, {"date": "2026-10-25", "price": 599}, {"date": "2026-09-01", "price": 399}]


@pytest.mark.parametrize("text", ["98% accurate AI picks your best leads", "Our AI model is 95% accurate",
                                  "Earn ₹50,000 a month with AI", "Our AI guarantees qualified leads",
                                  "Fully autonomous AI for your WhatsApp"])
def test_ai_claims_need_evidence(text, policy):
    assert not offer_guard.check(text, policy)


def test_ai_claim_with_registered_evidence(policy):
    assert offer_guard.check("Our model is 95% accurate on 400 real leads [EV-2026-014]", policy, {"EV-2026-014"})
    r = offer_guard.check("Our model is 95% accurate [EV-9]", policy, {"EV-2026-014"})
    assert not r and "not in the register: EV-9" in r.violations[0]


def test_honest_ai_line_passes(policy):
    assert offer_guard.check("We use AI to draft; a person approves every post.", policy)


@pytest.mark.parametrize("text,ok", [("Was ₹549, now ₹449", True), ("Was ₹599, now ₹449", False),
                                     ("Originally Rs. 799 – now 449", False), ("~~₹549~~ ₹449", True)])
def test_reference_price_is_the_30_day_low(text, ok, policy):
    assert bool(offer_guard.check(text, policy, price_history=H, today="2026-11-18")) is ok


def test_reference_price_needs_history(policy):
    r = offer_guard.check("Was ₹599, now ₹449", policy)
    assert not r and r.escalate
    r = offer_guard.check("Was ₹599", policy, price_history=[{"date": "2026-01-01", "price": 1}], today="2026-11-18")
    assert r.escalate and "no prices recorded" in r.violations[0]


def test_mrp(policy):
    assert offer_guard.check("MRP ₹699, our price ₹549", policy, mrp=699)
    assert "doesn't match the printed MRP" in offer_guard.check("MRP ₹799", policy, mrp=699).violations[0]
    assert offer_guard.check("M.R.P. ₹699", policy).escalate


# ---------- incident drill, logs, approver fatigue ----------
BASE = {"name": "wf", "owner": "A", "lane": "ai_seo", "actions": ["send_single"], "guards": ["ai_seo_guard", "visibility_stats",
        "promise_guard", "manipulation_guard"], "kill_switch": "K", "token_budget": 1,
        "logging": {"gate_log": True, "retention_days": 365}}


def dep(res):
    return {msg: ok for ok, msg in res["deployable"]}


def test_drill_required_for_r2(policy, tmp_path):
    d = dep(check(dict(BASE), policy))
    assert d["incident playbook exists (none)"] is False and any("(none on record)" in m for m in d)
    d = dep(check(dict(BASE, incident=drilled(tmp_path)), policy))
    assert all(ok for m, ok in d.items() if "drill" in m or "playbook" in m)


def test_stale_drill(policy, tmp_path):
    d = dep(check(dict(BASE, incident=drilled(tmp_path, days_ago=120)), policy))
    assert any("120 days ago" in m and not ok for m, ok in d.items())


def test_today_param(policy, tmp_path):
    inc = dict(drilled(tmp_path), last_drill="2026-09-01")
    assert all(ok for m, ok in dep(check(dict(BASE, incident=inc), policy, today="2026-11-19")).items() if "drill" in m)
    assert not all(ok for m, ok in dep(check(dict(BASE, incident=inc), policy, today="2027-01-19")).items() if "drill" in m)


def test_r0_r1_need_no_drill(policy):
    assert not any("drill" in m for m in dep(check(dict(BASE, actions=["draft", "score_lead"]), policy)))


def test_breach_clock_with_personal_data(policy, tmp_path):
    m = dict(BASE, data={"personal_data": True, "lawful_basis_field": True, "consent_checked_at_send": True,
                         "opt_out_hours": 1}, incident=dict(drilled(tmp_path), breach_report_hours=96))
    assert any("72 h" in k and not ok for k, ok in dep(check(m, policy)).items())


def test_log_retention_for_personal_data(policy):
    m = dict(BASE, data={"personal_data": True}, logging={"gate_log": True, "retention_days": 180})
    assert any("DPDP Rules require a year" in msg and not ok for ok, msg in check(m, policy)["safe"])
    assert all(ok for ok, msg in check(dict(BASE, logging={"gate_log": True, "retention_days": 180}), policy)["safe"]
               if "logs kept" in msg)


def approvals(path, n=30, approved=True, seconds=2.0, who="Akul"):
    path.write_text("\n".join(json.dumps({"approver": who, "approved": approved if i else True, "seconds": seconds})
                              for i in range(n)), encoding="utf-8")
    return path


def test_approver_fatigue(policy, tmp_path):
    tired = rollout.approver_fatigue(rollout.read_log(approvals(tmp_path / "a.jsonl")), policy)
    assert tired == [{"approver": "Akul", "items": 30, "approval_rate": 1.0, "median_seconds": 2.0}]
    assert not rollout.approver_fatigue(rollout.read_log(approvals(tmp_path / "b.jsonl", seconds=40)), policy)
    assert not rollout.approver_fatigue(rollout.read_log(approvals(tmp_path / "c.jsonl", n=10)), policy)
    assert not rollout.approver_fatigue([{"approved": True}], policy)


def test_fatigue_in_gate(policy, tmp_path):
    m = dict(BASE, approval_log=str(approvals(tmp_path / "a.jsonl")))
    assert any("rubber stamps (Akul: 100% approved, median 2s over 30)" in k and not ok for k, ok in dep(check(m, policy)).items())
    m = dict(BASE, approval_log="logs/none.jsonl")
    assert not any("rubber" in k for k in dep(check(m, policy)))


def test_controls_map_covers_every_guard(root):
    from gtm_evals.gate import GUARD_FILES
    text = (root / "docs/controls.md").read_text(encoding="utf-8")
    missing = [g for g in GUARD_FILES - {"action_gate"} if f"`{g}`" not in text]
    assert not missing, missing
