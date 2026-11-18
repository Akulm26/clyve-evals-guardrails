# Testing gtm-evals

A library that decides whether an automation may reach real people has to be tested harder than the automations it checks. Tests come in three layers, plus the evals that measure the guards themselves.

```text
                 ┌──────────────────────────────────────────────┐
  system   20    │ built wheel → fresh venv → `gtm-evals` from   │  slowest · what a stranger sees
                 │ an empty folder · container image             │
                 ├──────────────────────────────────────────────┤
  integration 91 │ CLI in-process · real policy files · repo     │  modules together
                 │ manifests · pipeline · label sheet → gate     │
                 ├──────────────────────────────────────────────┤
  unit    462    │ one module at a time · every guard rule ·     │  fastest · run on every save
                 │ every gate rule · edge cases                  │
                 └──────────────────────────────────────────────┘
  evals          golden sets, adversarial fuzz, held-out set: how good the guards are, not whether the code runs
```

## Run them

```bash
pip install -e ".[dev]"

python -m pytest                       # unit + integration (system is skipped by default), ~3 s
python -m pytest -m unit               # just unit
python -m pytest -m integration        # just integration
python -m pytest -m system             # builds the wheel, installs it in a fresh venv, ~10 s
python -m pytest --cov=gtm_evals       # coverage (CI fails below 95% on unit + integration)
```

## What each layer covers

| Layer | Folder | Rule | Examples |
|---|---|---|---|
| **Unit** | `tests/unit/` | One module, in memory. No subprocesses, no network, no files outside `tmp_path`. | every promise pattern and its negation; robots.txt matching per RFC 9309 (named group beats `*`, longest rule wins, `*` and `$`); JS-only pages; JSON-LD in `@graph`; `founder_religion` vs `page_views`; Aadhaar vs a 12-digit order ID; quiet-hours boundaries at 21:00 and 10:00; R3 approval IDs that are blank or whitespace; each of the 18 safe/ethical gate rules blocking on its own; judge JSON buried in prose |
| **Integration** | `tests/integration/` | Modules together, with the repo's real policy files, manifests and datasets. CLI runs in-process so coverage sees it. | every CLI command and exit code, including `seo` and `check --category`; the lane golden set (`evals/lanes.jsonl`) meets thresholds; all three Clyve workflows gate PILOT ONLY; `gtm-evals.yaml` auto-discovery; scraped text → PII redact → model → restore → guards → ActionGate; label sheet → `calibrate --update` → gate flips PILOT ONLY → DEPLOYABLE; README examples match `examples/tour.py`; every YAML in the repo parses |
| **System** | `tests/system/` | The package as shipped. Build the wheel, install it in a new venv, run the console script from an empty folder. Nothing imports from `src/`. | version and author metadata; package data in the wheel and repo internals kept out; README quickstart step by step; no traceback on bad input; missing `[judges]` extra or API key gives a clear message; container image (when Docker is available) |

## Rules every test follows

- **No real model calls.** A fixture replaces `judges.run` for every unit and integration test, and fails the test if anything reaches it. Use `stub_judge(flip={...})` to make the judge disagree with a human on chosen rows.
- **No leaks between tests.** Each test runs in its own temp folder, with no `./gtm-evals.yaml` and no kill switch left on in the shell.
- **Shared data lives in `tests/conftest.py`:** `policy`, `clyve`, `register`, `outbound` (a clean cold email that passes), `send_event` (a WhatsApp promo that passes at 12:30), `write_labels(n_pass, n_fail, blank)`.
- **Fixtures pass by default; each test breaks one thing.** That way a failure points at the rule, not at the fixture.

## Exit codes the CLI promises (tested)

| Code | Meaning |
|---|---|
| 0 | passed: text is clean, guards meet thresholds, no workflow BLOCKED, judge calibrated |
| 1 | a real "no": issues found, a guard below threshold, a workflow BLOCKED, calibration below the bar |
| 2 | you used it wrong: bad file, wrong format, missing label file, missing API key or `[judges]` extra |

## CI

`.github/workflows/evals.yml` runs:

1. **unit** on Python 3.10, 3.11, 3.12 and 3.13
2. **integration** with the 95% coverage gate, then the golden sets, the adversarial fuzz, the pipeline simulation and the gate on this repo's workflows
3. **system**: wheel, fresh venv and container image
4. **action-self-test**: the repo's own GitHub Action, used the way others will use it

## Adding a test

- **A guard missed something real:** add it to a golden set first (that's the eval), then a unit test for the rule you fix. See [CONTRIBUTING.md](CONTRIBUTING.md).
- **A new CLI option:** an integration test in `tests/integration/test_cli.py`, with the exit code.
- **Anything a user installs or runs:** a system test.
