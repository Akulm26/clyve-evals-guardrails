"""Phase 5 commands: seo --site / --fetch-results / --fetch-plan."""
import json

from tests.unit.test_phase5 import GOOD_PAGE, results


def test_seo_site(run_cli, tmp_path):
    d = tmp_path / "site"; d.mkdir()
    for i in range(5):
        (d / f"p{i}.html").write_text(GOOD_PAGE, encoding="utf-8")
    (d / "llms.txt").write_text("# Example Masala", encoding="utf-8")
    code, out, _ = run_cli("seo", "--site", d)
    assert code == 0 and "site-wide (5 pages, 80% rule)" in out
    (d / "llms.txt").unlink()
    code, out, _ = run_cli("seo", "--site", d)
    assert code == 1 and "no /llms.txt" in out


def test_seo_fetch(run_cli, tmp_path):
    f = tmp_path / "fetch.json"; f.write_text(json.dumps(results(PerplexityBot={"status": 403})))
    code, out, _ = run_cli("seo", "--fetch-results", f)
    assert code == 1 and "PerplexityBot got HTTP 403" in out and "crawler's IP" in out
    code, out, _ = run_cli("seo", "--fetch-plan", "https://example.in/")
    assert code == 0 and out.count("curl ") == 5


def test_seo_needs_something(run_cli):
    code, _, err = run_cli("seo")
    assert code == 2 and "--site" in err
