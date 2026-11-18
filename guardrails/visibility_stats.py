"""Honest AI-visibility measurement: frozen prompts, split by query type, change must beat noise.

A run row:
  {"prompt_id": "p01", "query_type": "brand"|"niche"|"best_x", "engine": "chatgpt",
   "surface": "app"|"api", "checkpoint": "day0", "run": 1, "mentioned": bool,
   "screenshot_path": "shots/..."}
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict


def prompt_set_hash(prompts: list[dict]) -> str:
    canon = json.dumps(sorted(prompts, key=lambda p: p["id"]), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canon.encode()).hexdigest()


def check_frozen(prompts: list[dict], day0_hash: str) -> None:
    if prompt_set_hash(prompts) != day0_hash:
        raise ValueError("prompt set changed since Day 0 — comparison invalid. Re-baseline or restore the set.")


def validate_rows(rows: list[dict], policy: dict) -> list[str]:
    qt = set(policy["visibility"]["query_types"])
    problems = []
    surfaces = {r.get("surface") for r in rows}
    if len(surfaces) > 1:
        problems.append(f"mixed surfaces {sorted(map(str, surfaces))} — keep app and API in separate reports")
    for i, r in enumerate(rows):
        if r.get("query_type") not in qt:
            problems.append(f"row {i}: missing/unknown query_type — blended numbers not allowed")
        if r.get("surface") == "app" and not r.get("screenshot_path"):
            problems.append(f"row {i}: no screenshot")
    runs = defaultdict(set)
    for r in rows:
        runs[(r.get("checkpoint"), r.get("engine"), r.get("prompt_id"))].add(r.get("run"))
    thin = [k for k, v in runs.items() if len(v) < policy["visibility"]["min_runs_per_prompt"]]
    if thin:
        problems.append(f"{len(thin)} prompt/engine/checkpoint cells have < "
                        f"{policy['visibility']['min_runs_per_prompt']} runs")
    return problems


def run_rates(rows: list[dict], checkpoint: str, query_type: str, engine: str | None = None) -> list[float]:
    """Mention rate per run index (each run = one pass over the prompt set)."""
    by_run = defaultdict(list)
    for r in rows:
        if r["checkpoint"] == checkpoint and r["query_type"] == query_type and (engine is None or r["engine"] == engine):
            by_run[r["run"]].append(1.0 if r["mentioned"] else 0.0)
    return [sum(v) / len(v) for _, v in sorted(by_run.items()) if v]


def smallest_provable_move(runs_in_segment: int, z: float = 1.96, p: float = 0.5) -> float:
    """KPI C5. Smallest move (0–1) a segment of this size can prove, at the worst-case rate p = 0.5."""
    return z * math.sqrt(p * (1 - p) * 2 / runs_in_segment)


def real_change(rows: list[dict], before: str, after: str, query_type: str, policy: dict,
                engine: str | None = None) -> dict:
    a = run_rates(rows, before, query_type, engine)
    b = run_rates(rows, after, query_type, engine)
    if not a or not b:
        raise ValueError("no data for one of the checkpoints")
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    noise = max(max(a) - min(a), max(b) - min(b))
    n_a = sum(1 for r in rows if r["checkpoint"] == before and r["query_type"] == query_type
              and (engine is None or r["engine"] == engine))
    n_b = sum(1 for r in rows if r["checkpoint"] == after and r["query_type"] == query_type
              and (engine is None or r["engine"] == engine))
    p = (ma * n_a + mb * n_b) / (n_a + n_b)
    se = math.sqrt(max(p * (1 - p), 1e-9) * (1 / n_a + 1 / n_b))
    z_band = policy["visibility"]["z"] * se
    delta = mb - ma
    real = abs(delta) > noise and abs(delta) > z_band
    return {"query_type": query_type, "before": round(ma, 3), "after": round(mb, 3), "delta": round(delta, 3),
            "noise": round(noise, 3), "z_band": round(z_band, 3), "real": real,
            "verdict": ("real movement" if real else "no clear movement yet — within noise")}
