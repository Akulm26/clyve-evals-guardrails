"""Keeps the README's concrete examples honest: they must match what examples/tour.py prints."""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_tour_output_matches_readme():
    out = subprocess.run([sys.executable, str(ROOT / "examples" / "tour.py")], capture_output=True,
                         text=True, check=True, env={"PYTHONPATH": str(ROOT / "src")}).stdout
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for line in out.splitlines():
        line = line.rstrip()
        if line.startswith("   - ") or " PASS" in line or " FAIL" in line or "→" in line:
            assert line in readme, f"README example out of date: {line!r}"
