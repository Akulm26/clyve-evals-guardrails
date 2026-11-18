"""Every workflow, the Action and every bundled YAML must parse, so a typo fails CI here
instead of failing silently on GitHub."""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
FILES = sorted([*ROOT.glob(".github/workflows/*.yml"), ROOT / "action.yml", *ROOT.glob("workflows/**/*.yaml"),
                *ROOT.glob("src/gtm_evals/data/**/*.yaml"), *ROOT.glob(".github/ISSUE_TEMPLATE/*.yml")])


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_yaml_parses(path):
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if path.name != "gtm-evals.yaml":   # the user config template is all comments on purpose
        assert doc is not None


@pytest.mark.parametrize("path", sorted(ROOT.glob(".github/workflows/*.yml")), ids=lambda p: p.name)
def test_github_workflow_shape(path):
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert "jobs" in doc and (True in doc or "on" in doc), "a workflow needs 'on' and 'jobs'"
    for name, job in doc["jobs"].items():
        assert "runs-on" in job and job.get("steps"), f"job {name} needs runs-on and steps"
