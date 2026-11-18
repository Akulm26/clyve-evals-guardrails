# Security

Please report security issues privately: open a GitHub **security advisory** on this repo
(Security → Report a vulnerability), not a public issue.

Especially relevant here:
- a way to make `action_gate` authorise an R2/R3 action without the evidence it requires
- an input that makes a guard crash (a crash must never become a pass)
- prompt-injection text that survives `injection_guard.wrap()` in a way that changes a judge's verdict

Maintainer: Akul Suhail Malhotra ([@Akulm26](https://github.com/Akulm26)). We aim to respond within 7 days.
