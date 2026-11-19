"""The last look at what's about to be sent: is it the message you meant, to the person you meant?

OWASP LLM05 (improper output handling) for marketing: a template variable nobody filled, a greeting
to the wrong name, a link the model invented, raw HTML in a plain-text channel.

    check(text, policy, context={"lead_name": "Rhea Kapoor", "channel": "email", "link_allowlist": ["clyve.in"]})
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from .core import Verdict

_URL = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)
_GREETING = re.compile(r"^\s*(?:hi|hey|hello|dear|namaste|hii+)\s+([A-Z][\w'-]+)\b", re.IGNORECASE | re.MULTILINE)


def _host_ok(host: str, allow: list[str]) -> bool:
    host = host.lower().split(":")[0]
    return any(host == a or host.endswith("." + a) for a in (x.lower() for x in allow))


def check(text: str, policy: dict, context: dict | None = None) -> Verdict:
    cfg = policy["output"]
    ctx = context or {}
    v: list[str] = []
    spans: list[tuple[int, int]] = []
    for pat in cfg["unfilled_patterns"]:
        for m in re.finditer(pat, text or "", re.IGNORECASE):
            if any(m.start() < e and s < m.end() for s, e in spans):
                continue   # inside a placeholder already reported ({first_name} within {{first_name}})
            spans.append(m.span())
            v.append(f"unfilled placeholder: '{m.group(0)}'")
    name = (ctx.get("lead_name") or "").split()
    if name:
        for m in _GREETING.finditer(text or ""):
            said = m.group(1).lower()
            if said not in {n.lower() for n in name} and said not in cfg["generic_greetings"]:
                v.append(f"greets '{m.group(1)}' but the CRM says this is {' '.join(name)}")
    allow = list(ctx.get("link_allowlist") or cfg.get("link_allowlist") or [])
    if allow:
        for m in _URL.finditer(text or ""):
            host = urlparse(m.group(0)).netloc
            if not _host_ok(host, allow):
                v.append(f"link to {host} isn't on the allowlist")
    channel = ctx.get("channel")
    if channel in cfg["plain_text_channels"] and re.search(cfg["html_pattern"], text or "", re.IGNORECASE):
        v.append(f"raw HTML in a {channel} message")
    if re.search(cfg["script_pattern"], text or "", re.IGNORECASE):
        v.append("script or event-handler markup in the output")
    return Verdict.from_violations("output_guard", v)
