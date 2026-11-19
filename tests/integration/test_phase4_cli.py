"""Phase 4 commands: rollout status; output_guard flags on check."""
import yaml

from tests.conftest import clean_log


def manifest(tmp_path, **kw):
    m = {"name": "bulk", "rollout": {"log": "logs/d.jsonl"}, **kw}
    p = tmp_path / "wf.yaml"; p.write_text(yaml.safe_dump(m))
    return p


def test_rollout_status_earned(run_cli, tmp_path):
    (tmp_path / "logs").mkdir(); clean_log(tmp_path / "logs" / "d.jsonl")
    code, out, _ = run_cli("rollout", "status", manifest(tmp_path, budgets={"p95_seconds": 90}), "--base", tmp_path)
    assert code == 0 and "stage segment (shadow → canary → segment)" in out and "advance" in out and "p95 30s" in out


def test_rollout_status_not_yet(run_cli, tmp_path):
    (tmp_path / "logs").mkdir(); clean_log(tmp_path / "logs" / "d.jsonl", days=3, latency_s=200)
    code, out, _ = run_cli("rollout", "status", manifest(tmp_path, budgets={"p95_seconds": 90}), "--base", tmp_path)
    assert code == 1 and "stage shadow" in out and "breach" in out and "p95 latency 200s" in out


def test_rollout_status_errors(run_cli, tmp_path):
    p = tmp_path / "x.yaml"; p.write_text("name: x\n")
    assert run_cli("rollout", "status", p)[0] == 2
    code, out, _ = run_cli("rollout", "status", manifest(tmp_path), "--base", tmp_path)
    assert code == 1 and "hasn't logged any live decisions" in out


def test_check_output_flags(run_cli, tmp_path):
    d = tmp_path / "d.txt"; d.write_text("Hi Priya, here's <b>the</b> link.", encoding="utf-8")
    code, out, _ = run_cli("check", d, "--lead-name", "Rhea Kapoor", "--channel", "whatsapp")
    assert code == 1 and "CRM says this is Rhea Kapoor" in out and "raw HTML in a whatsapp message" in out
