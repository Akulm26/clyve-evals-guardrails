"""System tests use the package the way a stranger does: build the wheel, install it into a brand-new
virtualenv, and drive the `gtm-evals` command from an empty folder. Nothing imports from src/.

    python -m pytest -m system            (slow: builds and installs once per session)
"""
from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd} failed:\n{r.stdout}\n{r.stderr}")
    return r


@pytest.fixture(scope="session")
def dist(tmp_path_factory):
    out = tmp_path_factory.mktemp("dist")
    _sh([sys.executable, "-m", "build", "--outdir", str(out), str(ROOT)])
    wheel = next(out.glob("*.whl"))
    sdist = next(out.glob("*.tar.gz"))
    return {"wheel": wheel, "sdist": sdist}


@pytest.fixture(scope="session")
def env(tmp_path_factory, dist):
    """A fresh venv with only the wheel (and its one dependency) installed."""
    home = tmp_path_factory.mktemp("venv")
    venv.create(home, with_pip=True, clear=True)
    bindir = home / ("Scripts" if os.name == "nt" else "bin")
    py = bindir / "python"
    _sh([str(py), "-m", "pip", "install", "-q", str(dist["wheel"])])
    clean = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "VIRTUAL_ENV")}
    clean["PATH"] = f"{bindir}{os.pathsep}{clean.get('PATH', '')}"
    for k in ("GTM_EVALS_KILL_SWITCH", "CLYVE_KILL_SWITCH", "ANTHROPIC_API_KEY"):
        clean.pop(k, None)
    return {"python": py, "cli": bindir / "gtm-evals", "env": clean}


@pytest.fixture
def project(tmp_path):
    """An empty folder outside the repo."""
    d = tmp_path / "project"
    d.mkdir()
    return d


@pytest.fixture
def gtm(env, project):
    """gtm(*args) -> CompletedProcess, run as the installed console script inside the project folder."""
    def _run(*args, input=None, check_code=None):
        r = subprocess.run([str(env["cli"]), *map(str, args)], cwd=project, env=env["env"],
                           capture_output=True, text=True, input=input)
        if check_code is not None:
            assert r.returncode == check_code, f"exit {r.returncode}\n{r.stdout}\n{r.stderr}"
        return r
    return _run


@pytest.fixture
def py(env, project):
    """py(code) -> CompletedProcess, the venv's python running a snippet inside the project folder."""
    def _run(code, check_code=0):
        r = subprocess.run([str(env["python"]), "-c", code], cwd=project, env=env["env"], capture_output=True, text=True)
        assert r.returncode == check_code, f"exit {r.returncode}\n{r.stdout}\n{r.stderr}"
        return r
    return _run
