"""Provenance (#3) and tool use (#12): a fact must be in the page it cites, and the agent must have looked.

    check_record(record, pages, policy)  — each enriched value appears in its saved source page
    check_trace(claims, trace, policy)   — each claim in a research note is backed by a lookup in the trace

pages = {"https://…/about": "saved page text", ...}           # saved at fetch time; this library never fetches
claims = [{"text": "Raised a seed round in 2025", "source": "https://…/news"}]
trace  = [{"tool": "web_fetch", "url": "https://…/news"}, {"tool": "search", "query": "…", "results": ["https://…"]}]
"""
from __future__ import annotations

import re

from .core import Verdict


def _norm(s: str) -> str:
    s = re.sub(r"(?<=\d),(?=\d)", "", str(s).lower())
    return re.sub(r"\s+", " ", re.sub(r"[^\w₹%.$ ]+", " ", s)).strip()


def _tokens(s: str) -> set[str]:
    return {w for w in _norm(s).split() if len(w) > 2}


def check_record(record: dict, pages: dict, policy: dict) -> Verdict:
    cfg = policy["provenance"]
    v: list[str] = []
    escalate = False
    for name, f in (record.get("fields") or {}).items():
        src, val = f.get("source"), f.get("value")
        if not src or val in (None, "") or isinstance(val, bool):
            continue
        page = pages.get(src)
        if page is None:
            if cfg["require_saved_page"]:
                v.append(f"'{name}': source page {src} wasn't saved, so the value can't be checked")
            continue
        np_, nv = _norm(page), _norm(val)
        if nv and nv in np_:
            continue
        vocab = next((vs for vs in cfg["vocabularies"].values() if nv in [_norm(x) for x in vs]), None)
        other = [x for x in (vocab or []) if _norm(x) != nv and re.search(rf"\b{re.escape(_norm(x))}\b", np_)]
        if other:
            v.append(f"'{name}': source says '{other[0]}', record says '{val}'")
            continue
        tv = _tokens(val)
        share = len(tv & _tokens(page)) / len(tv) if tv else 0
        if share >= cfg["partial_overlap"]:
            escalate = True
            v.append(f"'{name}': '{val}' is only partly in its source; a person (or the judge) should confirm")
        else:
            v.append(f"'{name}': '{val}' doesn't appear in its source page")
    return Verdict.from_violations("provenance", v, escalate=escalate)


def _looked_up(trace: list[dict], tools: list[str]) -> set[str]:
    seen = set()
    for step in trace or []:
        if step.get("tool") not in tools:
            continue
        if step.get("url"):
            seen.add(step["url"])
        seen.update(step.get("results") or [])
    return seen


def check_trace(claims: list[dict], trace: list[dict], policy: dict) -> Verdict:
    cfg = policy["provenance"]
    seen = _looked_up(trace, cfg["lookup_tools"])
    v = []
    for c in claims or []:
        text = (c.get("text") or "")[:60]
        if not c.get("source"):
            v.append(f"claim has no source: '{text}'")
        elif c["source"] not in seen:
            v.append(f"claim cites {c['source']} but no lookup in the trace fetched it: '{text}'")
    return Verdict.from_violations("tool_use", v)
