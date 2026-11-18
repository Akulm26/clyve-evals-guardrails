"""The evidence loop end to end: label sheet → calibrate --update → manifest → gate verdict."""
import shutil

import yaml


def setup_repo(root, tmp_path, labels_src):
    repo = tmp_path / "repo"
    (repo / "workflows").mkdir(parents=True)
    (repo / "evals" / "labels").mkdir(parents=True)
    wf = repo / "workflows" / "teardown-outreach.yaml"
    shutil.copy(root / "workflows" / "teardown-outreach.yaml", wf)
    shutil.copy(labels_src, repo / "evals" / "labels" / "personalisation_factuality.csv")
    gs = repo / "evals" / "datasets" / "outreach_messages.jsonl"
    gs.parent.mkdir(parents=True)
    gs.write_text("\n".join('{"source": "real"}' for _ in range(30)), encoding="utf-8")
    return repo, wf


def verdict(run_cli, wf, repo):
    return run_cli("gate", wf, "--base", repo, "--profile", "clyve")[1]


def test_good_labels_flip_pilot_to_deployable(run_cli, root, tmp_path, write_labels, stub_judge):
    repo, wf = setup_repo(root, tmp_path, write_labels(20, 12))
    assert "→  PILOT ONLY" in verdict(run_cli, wf, repo)
    stub_judge(flip={"L05"})
    code, out, _ = run_cli("judge", "calibrate", "personalisation_factuality",
                           repo / "evals/labels/personalisation_factuality.csv", "--update", wf)
    assert code == 0, out
    assert "→  DEPLOYABLE" in verdict(run_cli, wf, repo)


def test_poor_agreement_stays_pilot(run_cli, root, tmp_path, write_labels, stub_judge):
    repo, wf = setup_repo(root, tmp_path, write_labels(20, 12))
    stub_judge(flip={f"L{i:02d}" for i in range(1, 9)})
    assert run_cli("judge", "calibrate", "personalisation_factuality",
                   repo / "evals/labels/personalisation_factuality.csv", "--update", wf)[0] == 1
    assert yaml.safe_load(wf.read_text())["judges"][0]["calibration"]["agreement"] == 0.75
    assert "→  PILOT ONLY" in verdict(run_cli, wf, repo)


def test_hand_edited_claim_is_caught(run_cli, root, tmp_path, write_labels):
    repo, wf = setup_repo(root, tmp_path, write_labels(3, 2))
    wf.write_text(wf.read_text().replace("calibration: {labelled_cases: 0, agreement: 0}",
                                         "calibration: {labelled_cases: 40, agreement: 0.95}"), encoding="utf-8")
    out = verdict(run_cli, wf, repo)
    assert "→  PILOT ONLY" in out and "claims 40, file has 5 labelled" in out


def test_shipped_label_file_matches_the_manifest(root):
    """The repo's own label file and manifest must agree today (both empty)."""
    from gtm_evals.gate import check
    from gtm_evals import load_policy
    m = yaml.safe_load((root / "workflows/teardown-outreach.yaml").read_text())
    res = check(m, load_policy(profile="clyve"), base_dir=root)
    assert all(ok for ok, msg in res["deployable"] if "matches its label file" in msg)
