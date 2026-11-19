"""Every CLI command, run in-process against real files in a temp project."""
import io
import json
import sys

import pytest
import yaml

from gtm_evals import __version__


def test_version(run_cli):
    code, out, _ = run_cli("--version")
    assert code == 0 and __version__ in out


def test_no_command_is_an_error(run_cli):
    assert run_cli()[0] == 2


class TestInit:
    def test_scaffolds_project(self, run_cli, tmp_path):
        code, out, _ = run_cli("init")
        assert code == 0
        for f in ("gtm-evals.yaml", "workflows/outreach.yaml", "evals/golden.jsonl", "evals/judge_labels.csv", "claims_register.json"):
            assert (tmp_path / f).exists(), f
        assert "Next:" in out and "judge labels" in out

    def test_does_not_overwrite_without_force(self, run_cli, tmp_path):
        run_cli("init")
        (tmp_path / "gtm-evals.yaml").write_text("mine", encoding="utf-8")
        _, out, _ = run_cli("init")
        assert "skip  gtm-evals.yaml" in out and (tmp_path / "gtm-evals.yaml").read_text() == "mine"
        run_cli("init", "--force")
        assert (tmp_path / "gtm-evals.yaml").read_text() != "mine"

    def test_into_a_directory(self, run_cli, tmp_path):
        run_cli("init", "proj")
        assert (tmp_path / "proj" / "evals" / "golden.jsonl").exists()


class TestCheck:
    def write(self, tmp_path, text):
        p = tmp_path / "d.txt"; p.write_text(text, encoding="utf-8"); return p

    def test_clean_draft(self, run_cli, tmp_path):
        code, out, _ = run_cli("check", self.write(tmp_path, "Happy to share the page if useful."))
        assert code == 0 and "passes all text guards" in out and "no --register" in out

    def test_bad_draft(self, run_cli, tmp_path):
        code, out, _ = run_cli("check", self.write(tmp_path, "We guarantee results. Only 2 slots left. Mail a@b.io"))
        assert code == 1 and "3 issue(s) · escalate to a human" in out
        assert "[promise_guard]" in out and "[manipulation_guard]" in out and "[pii_guard]" in out

    def test_register_enables_claims(self, run_cli, tmp_path, register):
        reg = tmp_path / "r.json"; reg.write_text(json.dumps(register), encoding="utf-8")
        code, out, _ = run_cli("check", self.write(tmp_path, "Trusted by 50,000 kitchens"), "--register", reg)
        assert code == 1 and "unsourced number '50,000'" in out and "no --register" not in out

    def test_json(self, run_cli, tmp_path):
        code, out, _ = run_cli("check", self.write(tmp_path, "We guarantee it"), "--json")
        d = json.loads(out)
        assert code == 1 and d["passed"] is False and d["guard"] == "combined"

    def test_stdin(self, run_cli, monkeypatch):
        monkeypatch.setattr(sys, "stdin", io.StringIO("We guarantee it"))
        assert run_cli("check", "-")[0] == 1

    def test_policy_file_changes_the_rules(self, run_cli, tmp_path):
        cfg = tmp_path / "strict.yaml"
        cfg.write_text('promise:\n  banned: ["\\\\bmeasure\\\\b"]\n', encoding="utf-8")
        d = self.write(tmp_path, "We guarantee it; we'll measure it.")
        _, out, _ = run_cli("check", d, "--policy", cfg)
        assert "'measure'" in out and "'guarantee'" not in out   # lists replace, not merge


class TestCheckCategory:
    def test_regulated_claims_added_with_category(self, run_cli, tmp_path):
        d = tmp_path / "d.txt"; d.write_text("Our kadha cures colds. Clinically proven.", encoding="utf-8")
        assert run_cli("check", d)[0] == 0                       # no category: health rules don't apply
        code, out, _ = run_cli("check", d, "--category", "food")
        assert code == 1 and "[claim_safety_guard] prohibited for 'food': 'cures'" in out and "escalate" in out

    def test_food_100_percent(self, run_cli, tmp_path):
        d = tmp_path / "d.txt"; d.write_text("100% pure haldi.", encoding="utf-8")
        code, out, _ = run_cli("check", d, "--category", "spice")
        assert code == 1 and "prohibited for food (FSSAI): '100%'" in out

    def test_competitor_flag(self, run_cli, tmp_path):
        d = tmp_path / "d.txt"; d.write_text("Fresher than Everest.", encoding="utf-8")
        code, out, _ = run_cli("check", d, "--competitor", "Everest")
        assert code == 1 and "names competitor Everest" in out


class TestSeo:
    WORDS = " ".join(["Stone-ground winter chai masala from Ludhiana, made in small batches."] * 15)

    def files(self, tmp_path, robots="User-agent: *\nAllow: /\n", body=None, ld=True):
        (tmp_path / "robots.txt").write_text(robots, encoding="utf-8")
        org = ('<script type="application/ld+json">{"@type":"Organization","name":"X","url":"https://x.in",'
               '"logo":"https://x.in/l.png","sameAs":["https://instagram.com/x"]}</script>') if ld else ""
        html = (f'<html><head><title>Chai</title><link rel="canonical" href="https://x.in/chai">{org}</head>'
                f'<body>{body if body is not None else "<p>" + self.WORDS + "</p>"}</body></html>')
        (tmp_path / "p.html").write_text(html, encoding="utf-8")
        return tmp_path / "p.html", tmp_path / "robots.txt"

    def test_clean_site(self, run_cli, tmp_path):
        page, robots = self.files(tmp_path)
        code, out, _ = run_cli("seo", page, "--robots", robots, "--must", "winter chai masala")
        assert code == 0 and out.count("✅") == 3 and "training crawlers" in out and "all allowed" in out

    def test_blocked_and_js_only(self, run_cli, tmp_path):
        page, robots = self.files(tmp_path, robots="User-agent: *\nDisallow: /products/\n", body='<div id="root"></div>', ld=False)
        code, out, _ = run_cli("seo", page, "--robots", robots, "--path", "/products/chai", "--schema", "Organization,Product")
        assert code == 1 and "OAI-SearchBot is blocked from /products/chai" in out
        assert "words readable without JavaScript" in out and "no Product schema" in out

    def test_training_block_is_info_not_failure(self, run_cli, tmp_path):
        _, robots = self.files(tmp_path, robots="User-agent: GPTBot\nDisallow: /\n")
        code, out, _ = run_cli("seo", "--robots", robots)
        assert code == 0 and "blocked: GPTBot" in out

    def test_user_triggered_block_prints_a_note_and_passes(self, run_cli, tmp_path):
        _, robots = self.files(tmp_path, robots="User-agent: ChatGPT-User\nDisallow: /\n")
        code, out, _ = run_cli("seo", "--robots", robots)
        assert code == 0 and "ℹ️  ChatGPT-User is blocked in robots.txt" in out

    def test_entity_file(self, run_cli, tmp_path):
        e = tmp_path / "e.json"
        e.write_text(json.dumps({"canonical": {"name": "Example Masala", "description": "spice blends from Ludhiana"},
                                 "profiles": {"linkedin": {"name": "Example Foods", "description": "spice blends from Ludhiana"}}}))
        code, out, _ = run_cli("seo", "--entity", e)
        assert code == 1 and "linkedin: name 'Example Foods'" in out

    def test_json(self, run_cli, tmp_path):
        page, robots = self.files(tmp_path)
        d = json.loads(run_cli("seo", page, "--robots", robots, "--json")[1])
        assert d["AI search crawlers"]["passed"] and "schema (JSON-LD)" in d

    def test_nothing_to_check(self, run_cli):
        code, _, err = run_cli("seo")
        assert code == 2 and "give a page" in err


class TestEval:
    def test_bundled_golden_set_passes(self, run_cli, tmp_path):
        run_cli("init")
        code, out, _ = run_cli("eval", "evals/golden.jsonl")
        assert code == 0 and "13 cases (0 real)" in out

    def test_failing_guard_exits_1(self, run_cli, tmp_path):
        g = tmp_path / "g.jsonl"
        g.write_text(json.dumps({"id": "x", "guard": "promise", "input": {"text": "we'll measure"}, "expected_pass": False}),
                     encoding="utf-8")
        code, out, _ = run_cli("eval", g)
        assert code == 1 and "misses: ['x']" in out

    def test_lane_golden_set_meets_thresholds(self, run_cli, root):
        code, out, _ = run_cli("eval", root / "evals/lanes.jsonl")
        assert code == 0, out
        for g in ("ai_seo_crawlers", "ai_seo_page", "ai_seo_entity", "claim_safety", "enrichment"):
            assert f"✅ {g}" in out

    def test_wrong_format_is_a_clear_error_not_a_traceback(self, run_cli, root):
        # the repo's own datasets use the older per-guard layout read by evals/run_evals.py
        code, _, err = run_cli("eval", root / "evals/datasets/automation_events.jsonl")
        assert code == 2 and "not a golden-set row" in err

    def test_missing_file(self, run_cli):
        code, _, err = run_cli("eval", "nope.jsonl")
        assert code == 2 and "nope.jsonl" in err

    def test_missing_expected_pass(self, run_cli, tmp_path):
        g = tmp_path / "g.jsonl"
        g.write_text(json.dumps({"id": "x", "guard": "pii", "input": {"text": "hi"}}), encoding="utf-8")
        code, _, err = run_cli("eval", g)
        assert code == 2 and "missing 'expected_pass'" in err


class TestGate:
    def test_repo_workflows(self, run_cli, root):
        code, out, _ = run_cli("gate", root / "workflows/teardown-outreach.yaml", root / "workflows/examples/bad-lifecycle-flow.yaml",
                               "--base", root, "--profile", "clyve")
        assert code == 1   # one BLOCKED workflow fails the run
        assert "Clyve teardown outreach  →  PILOT ONLY" in out and "→  BLOCKED" in out

    def test_every_clyve_workflow_is_at_least_pilot(self, run_cli, root):
        code, out, _ = run_cli("gate", *sorted((root / "workflows").glob("*.yaml")), "--base", root, "--profile", "clyve")
        assert code == 0 and out.count("→  PILOT ONLY") == 3
        for name in ("Clyve AI SEO technical check", "Clyve content engine", "Clyve teardown outreach"):
            assert name in out

    def test_pilot_only_does_not_fail_the_run(self, run_cli, root):
        assert run_cli("gate", root / "workflows/teardown-outreach.yaml", "--base", root)[0] == 0

    def test_json(self, run_cli, root):
        code, out, _ = run_cli("gate", root / "workflows/teardown-outreach.yaml", "--base", root, "--json")
        d = json.loads(out)
        assert d[0]["verdict"] == "PILOT ONLY" and {"ok", "check"} <= set(d[0]["safe"][0])

    def test_init_manifest_blocked_until_owner_set(self, run_cli, tmp_path):
        run_cli("init")
        assert run_cli("gate", "workflows/outreach.yaml")[0] == 1
        wf = tmp_path / "workflows/outreach.yaml"
        wf.write_text(wf.read_text().replace('owner: ""', 'owner: "me"').replace('human_approver: ""', 'human_approver: "me"'))
        code, out, _ = run_cli("gate", "workflows/outreach.yaml")
        assert code == 0 and "PILOT ONLY" in out


class TestVisibility:
    def write(self, tmp_path, before, after):
        rows = []
        for cp, rates in (("day0", before), ("day30", after)):
            for run, rate in enumerate(rates):
                for i in range(25):
                    rows.append({"checkpoint": cp, "query_type": "brand", "engine": "chatgpt", "prompt_id": f"b{i}", "run": run,
                                 "mentioned": i < round(rate * 25), "surface": "app", "screenshot_path": "s.png"})
        p = tmp_path / "runs.jsonl"
        p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        return p

    def test_real_movement(self, run_cli, tmp_path):
        code, out, _ = run_cli("visibility", self.write(tmp_path, [0.2, 0.24], [0.6, 0.64]))
        assert "brand" in out and "real movement" in out

    def test_noise(self, run_cli, tmp_path):
        _, out, _ = run_cli("visibility", self.write(tmp_path, [0.2, 0.28], [0.24, 0.32]))
        assert "within noise" in out

    def test_missing_checkpoint_reported(self, run_cli, tmp_path):
        _, out, _ = run_cli("visibility", self.write(tmp_path, [0.2, 0.2], [0.3, 0.3]), "--after", "day90")
        assert "no data" in out


class TestJudge:
    def test_list(self, run_cli):
        code, out, _ = run_cli("judge", "list")
        assert code == 0 and "personalisation_factuality" in out.split()

    def test_template_required(self, run_cli):
        assert run_cli("judge", "render")[0] == 2

    def test_render_with_vars(self, run_cli, tmp_path):
        f = tmp_path / "msg.txt"; f.write_text("Hi Rhea", encoding="utf-8")
        code, out, err = run_cli("judge", "render", "personalisation_factuality", "--var", "today=2026-11-18", "--var-file", f"text={f}")
        assert code == 0 and "### SYSTEM" in out and "Hi Rhea" in out and "2026-11-18" in out
        assert "unfilled: freshness_days, signals" in err

    def test_labels_status_calibrate_update(self, run_cli, tmp_path, root, stub_judge):
        code, out, _ = run_cli("judge", "labels", "personalisation_factuality", "--rows", "5")
        sheet = tmp_path / "evals/labels/personalisation_factuality.csv"
        assert code == 0 and sheet.exists() and len(sheet.read_text().splitlines()) == 6
        assert ",45," in sheet.read_text()                                    # freshness default from policy
        assert run_cli("judge", "labels", "personalisation_factuality")[0] == 1   # no overwrite
        assert run_cli("judge", "labels", "personalisation_factuality", "--force")[0] == 0

        code, out, _ = run_cli("judge", "status", "personalisation_factuality", sheet)
        assert code == 1 and "0/30 labelled" in out

    def test_calibrate_flow(self, run_cli, tmp_path, root, stub_judge, write_labels):
        labels = write_labels(18, 14, blank=4)
        wf = tmp_path / "wf.yaml"
        wf.write_text((root / "workflows/teardown-outreach.yaml").read_text(encoding="utf-8"), encoding="utf-8")
        code, out, _ = run_cli("judge", "status", "personalisation_factuality", labels)
        assert code == 0 and "32/30 labelled · 18 pass · 14 fail · ready" in out

        calls = stub_judge(flip={"L01", "L20"})
        code, out, _ = run_cli("judge", "calibrate", "personalisation_factuality", labels, "--update", wf)
        assert code == 0 and "agreement 94% on 32" in out and len(calls) == 96       # 3 runs per row
        assert "net score +0.88" in out and "runs disagreed on 0% of rows" in out and "96 model calls" in out
        assert "disagree  L01: judge fail, human pass" in out and f"updated {wf}" in out
        assert yaml.safe_load(wf.read_text())["judges"][0]["calibration"] == {"labelled_cases": 32, "agreement": 0.94, "kappa": 1.0,
                                                                         "net": 0.88, "runs": 3, "run_disagreement": 0.0}
        calls.clear()   # a rerun reads the cache: no model calls
        code, out, _ = run_cli("judge", "calibrate", "personalisation_factuality", labels)
        assert code == 0 and len(calls) == 0

    def test_agreement(self, run_cli, write_labels):
        code, out, _ = run_cli("judge", "agreement", "swap_test", write_labels(15, 15, flip_b={"L01"}))
        assert code == 0 and "κ 0.93 on 30 rows both labelled" in out and "disagree  L01" in out

    def test_agreement_too_low(self, run_cli, write_labels):
        flips = {f"L{i:02d}" for i in range(1, 6)} | {f"L{i:02d}" for i in range(16, 19)}
        code, out, _ = run_cli("judge", "agreement", "swap_test", write_labels(15, 15, flip_b=flips))
        assert code == 1 and "need ≥ 0.80" in out

    def test_agreement_without_second_labeller(self, run_cli, write_labels):
        code, out, _ = run_cli("judge", "agreement", "swap_test", write_labels(5, 5, second=False))
        assert code == 1 and "no second labeller yet" in out

    def test_calibrate_uses_only_agreed_rows(self, run_cli, stub_judge, write_labels):
        calls = stub_judge()
        code, out, _ = run_cli("judge", "calibrate", "swap_test", write_labels(16, 16, flip_b={"L01", "L02"}))
        assert len(calls) == 90 and "κ 0.88; 2 rows they disagree on were left out" in out

    def test_calibrate_runs_flags(self, run_cli, stub_judge, write_labels):
        calls = stub_judge()
        code, out, _ = run_cli("judge", "calibrate", "swap_test", write_labels(15, 15), "--runs", "1", "--no-cache")
        assert code == 0 and len(calls) == 30 and "1 run(s) per row" in out
        calls.clear()
        code, out, _ = run_cli("judge", "calibrate", "swap_test", write_labels(15, 15), "--runs", "2", "--max-calls", "10",
                               "--no-cache")
        assert code == 1 and len(calls) == 10 and "stopped at --max-calls 10" in out

    def test_calibrate_below_bar_exits_1(self, run_cli, stub_judge, write_labels):
        stub_judge(flip={f"L{i:02d}" for i in range(1, 8)})
        code, out, _ = run_cli("judge", "calibrate", "personalisation_factuality", write_labels(15, 15))
        assert code == 1 and "agreement 77%" in out

    def test_calibrate_too_few_labels_exits_1(self, run_cli, stub_judge, write_labels):
        stub_judge()
        assert run_cli("judge", "calibrate", "swap_test", write_labels(5, 5))[0] == 1

    def test_update_unknown_judge(self, run_cli, tmp_path, stub_judge, write_labels):
        stub_judge()
        wf = tmp_path / "wf.yaml"; wf.write_text("judges: []\n", encoding="utf-8")
        _, out, _ = run_cli("judge", "calibrate", "swap_test", write_labels(15, 15), "--update", wf)
        assert "no judge entry for this template" in out


class TestJudgeErrors:
    def test_calibrate_without_api_key(self, run_cli, write_labels, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        code, _, err = run_cli("judge", "calibrate", "swap_test", write_labels(1, 1))
        assert code == 2 and "ANTHROPIC_API_KEY" in err

    def test_calibrate_without_judges_extra(self, run_cli, write_labels, monkeypatch, real_judge_run):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
        monkeypatch.setitem(sys.modules, "anthropic", None)    # import anthropic -> ImportError
        code, _, err = run_cli("judge", "calibrate", "swap_test", write_labels(1, 1))
        assert code == 2 and 'pip install "gtm-evals[judges]"' in err

    @pytest.mark.parametrize("action", ["status", "calibrate"])
    def test_label_file_required(self, run_cli, action):
        code, _, err = run_cli("judge", action, "swap_test")
        assert code == 2 and "needs a label file" in err


class TestPolicy:
    def test_profiles(self, run_cli):
        code, out, _ = run_cli("policy", "--profiles")
        assert code == 0 and "clyve" in out

    def test_effective_policy_layers(self, run_cli, tmp_path):
        (tmp_path / "gtm-evals.yaml").write_text("profile: clyve\noutreach: {max_words: 99}\n", encoding="utf-8")
        p = yaml.safe_load(run_cli("policy", "--show")[1])
        assert p["outreach"]["max_words"] == 99 and "real estate" in p["outreach"]["excluded_categories"]
