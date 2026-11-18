# Contributing

The most valuable contribution is **a real failure**: a case where an AI marketing system did something wrong and a guard here didn't catch it.

1. Add the case to the matching file in `evals/datasets/` with `expected_pass` and a one-line `why`. Anonymise it: no real brand names, people, emails or phone numbers.
2. Run `python evals/run_evals.py -v`. It should now show a MISS.
3. Fix the guard or the policy so it's caught, without new false alarms.
4. Open a PR with the before/after output.

Rules:
- Thresholds live in `src/gtm_evals/data/default.yaml`, not in code.
- Guards stay dependency-free and deterministic. Anything needing judgment goes in `src/gtm_evals/data/judges/` with a ground-truth input.
- Seeded golden sets are written by the people who wrote the guards, so they score well by design. Treat a perfect score as the floor. The real test is cases from production.
- Run `python -m pytest` (unit + integration) and `python -m pytest -m system` before a PR. Which layer a new test belongs in: [TESTING.md](TESTING.md).

## Adding a new automation

1. Write `workflows/<name>.yaml` (see `docs/12-deployment-gate.md`).
2. Run `gtm-evals gate workflows/<name>.yaml`.
3. BLOCKED → fix it before merging. PILOT ONLY → it may run only with a human checking every R2+ action.
4. Golden-set rows from real work get `"source": "real"`; synthetic rows don't.

## Releasing

1. Bump `version` in `pyproject.toml` and `__version__` in `src/gtm_evals/__init__.py`; add a CHANGELOG entry.
2. `git tag v0.1.1 && git push --tags`. The `release` workflow builds and publishes to PyPI (needs the one-time trusted-publisher setup described in `.github/workflows/release.yml`).
