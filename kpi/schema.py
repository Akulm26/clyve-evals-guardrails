"""One metric = one record. The KPI page and the repo docs are both generated from these."""
from dataclasses import dataclass, field


@dataclass
class Metric:
    id: str
    src: str                 # space-separated source tags: PUBLIC RUNS FOUNDER CLIENT PLATFORM CLYVE
    title: str
    q: str
    chips: str               # "<rev> <role> <status>", e.g. "indirect headline locked"
    formula: str
    subs: list
    inputs: list             # (name, what, source tag, how)
    steps: list
    example: str
    stamp: tuple             # (label, note or None)
    watch: str | None = None
    kick: str | None = None
    layer: int = 0
    changed: str | None = None  # "new" | "changed" — for the changelog


def M(id, src, title, q, chips, formula, subs, inputs, steps, example, stamp, watch=None, kick=None):
    return Metric(id, src, title, q, chips, formula, subs, inputs, steps, example, stamp, watch, kick)
