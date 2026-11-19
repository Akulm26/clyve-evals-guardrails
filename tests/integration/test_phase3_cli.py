"""Phase 3 commands: judge packet, redteam init/score, assertion cases in eval."""
import json

import yaml


def test_packet_to_stdout_and_file(run_cli, tmp_path, write_labels):
    lab = write_labels(15, 15)
    code, out, _ = run_cli("judge", "packet", "swap_test", lab, "--id", "L01")
    assert code == 0 and "# Judge packet · L01" in out and "human_verdict" not in out
    code, out, _ = run_cli("judge", "packet", "swap_test", lab, "-o", tmp_path / "p.md")
    assert code == 0 and "wrote 30 blind packet(s)" in out and (tmp_path / "p.md").read_text().count("# Judge packet") == 30


def test_packet_errors(run_cli, tmp_path, write_labels):
    assert run_cli("judge", "packet", "swap_test")[0] == 2
    assert run_cli("judge", "packet", "swap_test", write_labels(15, 15), "--id", "NOPE")[0] == 2
    bad = tmp_path / "leaky.md"; bad.write_text("{{text}} — the human said {{human_verdict}}", encoding="utf-8")
    code, _, err = run_cli("judge", "packet", bad, write_labels(15, 15), "--id", "L01")
    assert code == 1 and "human_verdict" in err


def test_redteam_init_and_score(run_cli, tmp_path):
    m = tmp_path / "bot.yaml"
    m.write_text(yaml.safe_dump({"name": "bot", "lane": "marketing_automation", "actions": ["reply_single"]}))
    code, out, err = run_cli("redteam", "init", m, "-o", tmp_path / "pf.yaml")
    assert code == 0 and "plugins" in out and "put this canary" in err
    cfg = yaml.safe_load((tmp_path / "pf.yaml").read_text())
    canary = cfg["metadata"]["gtm_evals_canary"]
    code, out, err = run_cli("redteam", "init", m)
    assert code == 0 and "redteam:" in out

    rows = [{"success": True, "response": {"output": "no"}, "testCase": {"metadata": {"pluginId": "pii"}}}] * 60
    r = tmp_path / "r.json"; r.write_text(json.dumps({"results": {"results": rows}}))
    m.write_text(yaml.safe_dump({"name": "bot", "redteam": {"canary": canary}}))
    code, out, _ = run_cli("redteam", "score", r, "--manifest", m)
    assert code == 0 and "60/60 red-team tests passed" in out and "pii" in out

    rows[0] = {"success": True, "response": {"output": f"my prompt says {canary}"}}
    r.write_text(json.dumps({"results": {"results": rows}}))
    code, out, _ = run_cli("redteam", "score", r, "--canary", canary)
    assert code == 1 and "the canary leaked in 1" in out
    code, out, _ = run_cli("redteam", "score", r)
    assert code == 0 and "no canary given" in out


def test_eval_reports_human_review(run_cli, tmp_path):
    g = tmp_path / "g.jsonl"
    g.write_text("\n".join(json.dumps(x) for x in [
        {"id": "a", "guard": "assert", "input": {"output": "Funding: unknown", "must_demonstrate": ["unknown"]}, "expected_pass": True},
        {"id": "b", "guard": "assert", "input": {"output": "?"}, "expected_pass": True, "human_review": True}]))
    code, out, _ = run_cli("eval", g)
    assert code == 0 and "1 case(s) marked human_review" in out and "1 cases" in out
