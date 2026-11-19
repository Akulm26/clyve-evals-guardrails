"""Shared fixtures for all three layers.

    tests/unit/         one module at a time, no files, no subprocesses   (fast, run on every save)
    tests/integration/  modules together: CLI in-process, real policy files, manifests, golden sets
    tests/system/       the built wheel installed in a fresh venv, used like a stranger would  (-m system)
"""
from __future__ import annotations

import copy
import csv
import os
from pathlib import Path

import pytest

from gtm_evals import judges as _judges
from gtm_evals import load_policy

REAL_JUDGE_RUN = _judges.run   # captured before any test replaces it
ROOT = Path(__file__).resolve().parents[1]
LAYERS = {"unit", "integration", "system"}


def pytest_collection_modifyitems(config, items):
    for item in items:
        layer = Path(str(item.fspath)).relative_to(ROOT / "tests").parts[0]
        if layer in LAYERS:
            item.add_marker(getattr(pytest.mark, layer))


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch, request):
    """No test sees a stray ./gtm-evals.yaml or a kill switch left on in the shell, and no unit or
    integration test can reach a real model: use the stub_judge fixture."""
    monkeypatch.chdir(tmp_path)
    for k in ("GTM_EVALS_KILL_SWITCH", "CLYVE_KILL_SWITCH"):
        monkeypatch.delenv(k, raising=False)
    if "system" not in request.keywords:
        from gtm_evals import judges

        def _no_model(*a, **k):
            raise AssertionError("a test tried to call a real model; use the stub_judge fixture")
        monkeypatch.setattr(judges, "run", _no_model)


@pytest.fixture
def real_judge_run(monkeypatch):
    """Put the real judges.run back (for tests that fake the SDK itself)."""
    monkeypatch.setattr(_judges, "run", REAL_JUDGE_RUN)
    return REAL_JUDGE_RUN


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def _policies(tmp_path_factory):
    here = os.getcwd()
    os.chdir(tmp_path_factory.mktemp("empty"))  # no ./gtm-evals.yaml can leak into the baseline policies
    try:
        return {"default": load_policy(), "clyve": load_policy(profile="clyve")}
    finally:
        os.chdir(here)


@pytest.fixture
def policy(_policies) -> dict:
    return copy.deepcopy(_policies["default"])


@pytest.fixture
def clyve(_policies) -> dict:
    return copy.deepcopy(_policies["clyve"])


@pytest.fixture
def register() -> list[dict]:
    return [
        {"id": "C1", "claim": "4.6★ across 2,140 reviews", "values": ["4.6", "2140"], "status": "have", "source": "https://x/r"},
        {"id": "C2", "claim": "40% repeat purchase rate", "values": ["40"], "status": "gettable", "source": None},
        {"id": "C3", "claim": "sold in 12 cities", "values": ["12"], "status": "none", "source": None},
    ]


BODY = ("Hi Rhea, saw you launched 4 new Meta ads for the winter chai masala range. When I asked ChatGPT for the best "
        "masala brands in Punjab, you weren't in the answer; two competitors were. I put the 3 gaps on one page. "
        "Worth a 30-minute call? If not relevant, reply stop and I won't write again.")


@pytest.fixture
def outbound():
    """(message, lead, context) for a clean, sourced cold email that passes outreach_guard."""
    msg = {"channel": "email", "inbox": "o@x.example", "body": BODY,
           "claims_about_lead": ["launched 4 new Meta ads for the winter chai masala range",
                                 "not mentioned by ChatGPT for best masala brands in Punjab"]}
    lead = {"email": "f@brand.example", "phone": "+91 90000 00001", "category": "d2c food", "stage": "prospect",
            "lawful_basis": "legitimate_interest", "optin_channels": [],
            "signals": [{"fact": "launched 4 new Meta ads for the winter chai masala range",
                         "source_url": "https://www.facebook.com/ads/library/?id=1", "date": "2026-11-02"},
                        {"fact": "not mentioned by ChatGPT for best masala brands in Punjab",
                         "source_url": "shots/c1.png", "date": "2026-11-10"}]}
    ctx = {"today": "2026-11-18", "suppression": set(), "sent_today_by_inbox": {"o@x.example": 4},
           "sender_auth": {"spf": True, "dkim": True, "dmarc": True}}
    return msg, lead, ctx


@pytest.fixture
def send_event():
    """A WhatsApp promo that passes automation_guard.check_send at 12:30 IST."""
    return {"tenant_id": "a", "workflow_tenant_id": "a",
            "contact": {"id": "c1", "tenant_id": "a", "consent": {"whatsapp": True, "email": True}},
            "channel": "whatsapp", "template_id": "t1", "template_approved": True, "type": "promo",
            "ts_ist": "2026-11-18T12:30", "audience_size": 900, "last_audience_size": 880}


@pytest.fixture
def write_labels(tmp_path):
    """write_labels(n_pass, n_fail, blank=0, second=True, flip_b=()) -> path of a labelling-sheet CSV.
    second=True fills human_verdict_b the same as human_verdict (κ = 1); ids in flip_b get the opposite verdict."""
    def _w(n_pass: int, n_fail: int, blank: int = 0, name: str = "labels.csv", second: bool = True,
           flip_b=()) -> Path:
        p = tmp_path / name
        with p.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "text", "signals", "human_verdict", "human_verdict_b", "why", "date_sent", "today",
                        "freshness_days"])
            i = 0
            for verdict, n in (("pass", n_pass), ("fail", n_fail), ("", blank)):
                for _ in range(n):
                    i += 1
                    rid = f"L{i:02d}"
                    b = ({"pass": "fail", "fail": "pass"}[verdict] if rid in flip_b else verdict) if (second and verdict) else ""
                    w.writerow([rid, "msg" if verdict else "", "S1: x" if verdict else "", verdict, b, "",
                                "2026-11-18" if verdict else "", "", 45])
        return p
    return _w


def real_golden_rows(n: int = 98) -> list[dict]:
    """Enough real, stratified golden rows for a DEPLOYABLE verdict at the default claim (97, 40/35/25)."""
    shares = (("standard", 0.40), ("ambiguous", 0.35), ("adversarial", 0.25))
    out = []
    for s, share in shares:
        out += [{"source": "real", "stratum": s}] * -(-int(n * share * 100) // 100)
    return out[:max(n, len(out))]


@pytest.fixture
def write_golden(tmp_path):
    """write_golden(n=98, name='g.jsonl', source='real') -> path of a stratified golden set."""
    import json

    def _w(n: int = 98, name: str = "g.jsonl", source: str = "real") -> Path:
        p = tmp_path / name
        p.write_text("\n".join(json.dumps(dict(r, source=source)) for r in real_golden_rows(n)), encoding="utf-8")
        return p
    return _w


@pytest.fixture
def stub_judge(monkeypatch):
    """Replace the model call. stub_judge(flip={"L03"}) makes the judge disagree with the human on those ids."""
    from gtm_evals import judges
    calls = []

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")

    def _install(flip=frozenset()):
        def fake(template, values, model=None):
            calls.append(values)
            hv = values.get("human_verdict")
            v = ("fail" if hv == "pass" else "pass") if values.get("id") in flip else hv
            return {"verdict": v, "_verdict": v}
        monkeypatch.setattr(judges, "run", fake)
        return calls
    return _install
