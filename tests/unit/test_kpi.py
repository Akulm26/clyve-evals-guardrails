"""The KPI doc's worked examples must agree with the code that enforces them."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from gtm_evals import load_policy, visibility_stats  # noqa: E402
from kpi import ALL, LAYERS  # noqa: E402
from kpi.build_html import build  # noqa: E402

P = load_policy(profile="clyve")


def _rows(checkpoint, hits_per_pass, runs_per_pass=24):
    rows = []
    for run, h in enumerate(hits_per_pass, 1):
        for i in range(runs_per_pass):
            rows.append({"prompt_id": f"n{i}", "query_type": "niche", "engine": "pooled", "checkpoint": checkpoint,
                         "run": run, "mentioned": i < h})
    return rows


def test_o2_worked_example_is_flat():
    # KPI O2: Day 0 passes 2,3,4 of 24; Day 30 passes 3,4,5 of 24 → movement 4.2 pts, report flat.
    rows = _rows("day0", [2, 3, 4]) + _rows("day30", [3, 4, 5])
    r = visibility_stats.real_change(rows, "day0", "day30", "niche", P)
    assert round(r["delta"] * 100, 1) == 4.2
    assert round(r["noise"] * 100, 1) == 8.3
    assert round(r["z_band"] * 100, 1) == 11.5
    assert r["real"] is False


def test_c5_worked_example():
    assert round(visibility_stats.smallest_provable_move(24) * 100) == 28
    assert round(visibility_stats.smallest_provable_move(72) * 100) == 16


def test_kpi_registry_complete():
    ids = [m.id for m in ALL]
    assert len(ids) == len(set(ids)) == 76
    assert all(m.formula and m.steps and m.example for m in ALL)
    assert sum(len(ms) for *_, ms, _ in LAYERS) == 76


def test_page_renders():
    html = build()
    assert html.count('<article class="metric"') == 76
    assert "Q9" in html and "Chance band" in html
