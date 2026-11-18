import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_golden_sets_meet_thresholds():
    r = subprocess.run([sys.executable, str(ROOT / "evals" / "run_evals.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
