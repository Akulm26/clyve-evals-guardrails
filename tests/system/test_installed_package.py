"""The built package, installed in a fresh venv, used end to end."""
import json
import re
import subprocess
import tarfile
import zipfile

import pytest

from gtm_evals import __version__

VERSION = re.search(r'^version = "([^"]+)"', (__import__("pathlib").Path(__file__).resolve().parents[2]
                                              / "pyproject.toml").read_text(), re.M).group(1)


class TestArtifacts:
    def test_versions_agree(self, dist):
        assert VERSION == __version__
        assert dist["wheel"].name == f"gtm_evals-{VERSION}-py3-none-any.whl"

    def test_wheel_ships_package_data(self, dist):
        names = set(zipfile.ZipFile(dist["wheel"]).namelist())
        must = ["gtm_evals/py.typed", "gtm_evals/data/default.yaml", "gtm_evals/data/profiles/clyve.yaml",
                "gtm_evals/data/templates/gtm-evals.yaml", "gtm_evals/data/templates/evals/golden.jsonl",
                "gtm_evals/data/templates/evals/judge_labels.csv", "gtm_evals/data/templates/workflows/outreach.yaml",
                "gtm_evals/ai_seo_guard.py", "gtm_evals/claim_safety_guard.py", "gtm_evals/enrichment_guard.py",
                *[f"gtm_evals/data/judges/{j}.md" for j in ("swap_test", "on_thesis", "personalisation_factuality",
                                                             "claim_safety", "description_accuracy", "promise_check")]]
        assert not [m for m in must if m not in names]
        assert any(n.endswith("licenses/NOTICE") for n in names) and any(n.endswith("licenses/LICENSE") for n in names)

    def test_wheel_does_not_ship_repo_internals(self, dist):
        names = zipfile.ZipFile(dist["wheel"]).namelist()
        assert not [n for n in names if n.startswith(("tests/", "sim/", "kpi/", "evals/", "workflows/", "docs/"))]

    def test_sdist_builds_the_same_package(self, dist):
        names = tarfile.open(dist["sdist"]).getnames()
        assert any(n.endswith("src/gtm_evals/cli.py") for n in names) and any(n.endswith("README.md") for n in names)


class TestInstalled:
    def test_console_script(self, gtm):
        r = gtm("--version", check_code=0)
        assert r.stdout.strip() == f"gtm-evals {VERSION}"

    def test_metadata_credits_the_author(self, py):
        out = py("from importlib.metadata import metadata as m; d = m('gtm-evals'); print(d['Author-email']); print(d['License-Expression'] or d['License'])").stdout
        assert "Akul Suhail Malhotra" in out and "Apache-2.0" in out

    def test_imports_from_the_venv_not_the_repo(self, py, env):
        out = py("import gtm_evals, sys; print(gtm_evals.__file__)").stdout
        assert "site-packages" in out and "/src/gtm_evals" not in out

    def test_only_pyyaml_is_required(self, py):
        out = py("from importlib.metadata import requires; print(requires('gtm-evals'))").stdout
        assert "pyyaml" in out.lower() and "anthropic" in out and "extra" in out   # anthropic only as an extra
        py("import importlib.util as u; assert u.find_spec('anthropic') is None")


class TestNewUserJourney:
    """README quickstart, step by step, in an empty folder."""

    def test_quickstart(self, gtm, project):
        assert "made  gtm-evals.yaml" in gtm("init", check_code=0).stdout

        out = gtm("eval", "evals/golden.jsonl", check_code=0).stdout
        assert "13 cases" in out and "❌" not in out

        (project / "draft.txt").write_text("We guarantee you'll rank #1. Trusted by 50,000 brands.", encoding="utf-8")
        out = gtm("check", "draft.txt", "--register", "claims_register.json", check_code=1).stdout
        assert "unsourced number '50,000'" in out and "promise language" in out

        out = gtm("gate", "workflows/outreach.yaml", check_code=1).stdout
        assert "BLOCKED" in out
        wf = project / "workflows" / "outreach.yaml"
        wf.write_text(wf.read_text().replace('owner: ""', 'owner: "me"').replace('human_approver: ""', 'human_approver: "me"'))
        assert "PILOT ONLY" in gtm("gate", "workflows/outreach.yaml", check_code=0).stdout

    def test_ai_seo_check_on_saved_files(self, gtm, project):
        (project / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
        (project / "page.html").write_text('<html><head><title>x</title></head><body><div id="root"></div></body></html>')
        r = gtm("seo", "page.html", "--robots", "robots.txt")
        assert r.returncode == 1 and "PerplexityBot is blocked" in r.stdout and "JavaScript" in r.stdout

    def test_regulated_claims_from_stdin(self, gtm):
        r = gtm("check", "-", "--category", "supplement", input="Clinically proven immunity booster.")
        assert r.returncode == 1 and "claim_safety_guard" in r.stdout

    def test_stdin_and_json(self, gtm):
        r = gtm("check", "-", "--json", input="Only 2 slots left!")
        d = json.loads(r.stdout)
        assert r.returncode == 1 and d["escalate"] is True

    def test_labelling_sheet_journey(self, gtm, project):
        gtm("judge", "labels", "personalisation_factuality", check_code=0)
        sheet = project / "evals/labels/personalisation_factuality.csv"
        assert sheet.read_text().splitlines()[0] == "id,text,signals,today,freshness_days,human_verdict,why"
        assert "0/30 labelled" in gtm("judge", "status", "personalisation_factuality", sheet, check_code=1).stdout
        r = gtm("judge", "calibrate", "personalisation_factuality", sheet)
        assert r.returncode == 1 and "agreement 0% on 0" in r.stdout          # no labels: nothing to run, no key needed

    def test_calibrate_without_extra_is_a_clear_error(self, gtm, project):
        gtm("init", check_code=0)
        r = gtm("judge", "calibrate", "personalisation_factuality", "evals/judge_labels.csv")
        assert r.returncode == 2 and "ANTHROPIC_API_KEY" in r.stderr and "Traceback" not in r.stderr

    def test_bad_input_never_shows_a_traceback(self, gtm, project):
        (project / "bad.jsonl").write_text('{"id": "x"}\n', encoding="utf-8")
        for args in (("eval", "bad.jsonl"), ("eval", "missing.jsonl"), ("judge", "render"), ("nope",)):
            r = gtm(*args)
            assert r.returncode == 2 and "Traceback" not in r.stderr, args

    def test_user_config_is_picked_up(self, gtm, project):
        (project / "gtm-evals.yaml").write_text("profile: clyve\noutreach: {max_words: 42}\n", encoding="utf-8")
        out = gtm("policy", "--show", check_code=0).stdout
        assert "max_words: 42" in out and "real estate" in out


class TestLibraryAPI:
    def test_readme_snippet(self, py):
        py("""
from gtm_evals import load_policy, claims_gate, ActionGate
policy = load_policy()
v = claims_gate.check("Trusted by 50,000 kitchens", [], policy)
assert not v and "50,000" in v.violations[0]
ok = claims_gate.check("Spices ground fresh.", [], policy)
gate = ActionGate(policy)
assert gate.authorize("send_bulk", checks=[ok], evaluator_passed=True, approval_id="AK-1", canary_done=True)
assert not gate.authorize("send_bulk", checks=[ok], evaluator_passed=True)
""")

    def test_tour_example_runs_against_the_installed_package(self, env, project):
        from pathlib import Path
        tour = Path(__file__).resolve().parents[2] / "examples" / "tour.py"
        r = subprocess.run([str(env["python"]), str(tour)], cwd=project, env=env["env"], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert "real movement" in r.stdout and "kill switch is on" in r.stdout

    def test_kill_switch_from_the_environment(self, env, project):
        e = dict(env["env"], GTM_EVALS_KILL_SWITCH="1")
        code = ("from gtm_evals import ActionGate, load_policy; from gtm_evals.core import Verdict;"
                "print(ActionGate(load_policy()).authorize('crm_update', checks=[Verdict('x', True)]).violations)")
        r = subprocess.run([str(env["python"]), "-c", code], cwd=project, env=e, capture_output=True, text=True)
        assert "kill switch is on" in r.stdout


@pytest.mark.skipif(subprocess.run(["sh", "-c", "docker info >/dev/null 2>&1"]).returncode != 0, reason="no docker daemon")
def test_container_image(project):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    subprocess.run(["docker", "build", "-q", "-t", "gtm-evals:systest", str(root)], check=True, capture_output=True)
    r = subprocess.run(["docker", "run", "--rm", "gtm-evals:systest", "--version"], capture_output=True, text=True)
    assert r.stdout.strip() == f"gtm-evals {VERSION}"
    (project / "d.txt").write_text("We guarantee it.", encoding="utf-8")
    r = subprocess.run(["docker", "run", "--rm", "-v", f"{project}:/work", "gtm-evals:systest", "check", "d.txt"],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "promise language" in r.stdout
