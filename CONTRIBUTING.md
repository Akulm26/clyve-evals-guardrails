# Contributing

The most valuable contribution is **a real failure**: a case where an AI marketing system did something wrong and a guard here didn't catch it.

1. Add the case to the matching file in `evals/datasets/` with `expected_pass` and a one-line `why`. Anonymise it: no real brand names, people, emails or phone numbers.
2. Run `python evals/run_evals.py -v`. It should now show a MISS.
3. Fix the guard or the policy so it's caught, without new false alarms.
4. Open a PR with the before/after output.

Rules:
- Thresholds live in `policies/clyve_policy.yaml`, not in code.
- Guards stay dependency-free and deterministic. Anything needing judgment goes in `evals/judges/` with a ground-truth input.
- Seeded golden sets are written by the people who wrote the guards, so they score well by design. Treat a perfect score as the floor. The real test is cases from production.
