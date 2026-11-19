"""Isolation between clients, and between the agent's own notes and the truth (OWASP LLM02, LLM08).

    check_retrieval(request, workflow_tenant)  — every vector or CRM lookup filters on the client
    check_memory(items)                        — notes an agent wrote for itself are data, never instructions
    check_tools(tools, actions, policy)        — no tool holds a scope the workflow's actions don't need
"""
from __future__ import annotations

from . import injection_guard
from .core import Verdict

_TENANT_KEYS = ("tenant_id", "client_id", "brand_id", "workspace_id")


def check_retrieval(request: dict, workflow_tenant: str) -> Verdict:
    f = request.get("filter") or request.get("where") or {}
    found = {k: f[k] for k in _TENANT_KEYS if k in f}
    v = []
    if not found:
        v.append("retrieval has no client filter: one client's data can surface in another's output")
    elif any(str(x) != str(workflow_tenant) for x in found.values()):
        v.append(f"retrieval filters on {found}, but this workflow belongs to '{workflow_tenant}'")
    return Verdict.from_violations("isolation", v)


def check_memory(items: list[dict]) -> Verdict:
    """items: [{"text", "written_by": "agent" | "human", "wrapped": bool}]. Agent-written memory is untrusted input."""
    v = []
    for i, it in enumerate(items or []):
        if it.get("written_by", "agent") != "human":
            if not it.get("wrapped"):
                v.append(f"memory item {i} was written by an agent and isn't wrapped as untrusted data")
            if not injection_guard.check(it.get("text", "")):
                v.append(f"memory item {i} contains instruction-like text")
    return Verdict.from_violations("isolation", v)


def check_tools(tools: list[dict], actions: list[str], policy: dict) -> Verdict:
    """tools: [{"name": "crm", "scopes": ["read", "write"]}]. A scope's tier can't exceed the highest action tier."""
    order = ["R0", "R1", "R2", "R3"]
    at = policy["action_gate"]
    top = max((order.index(at["action_tiers"].get(a, "R3")) for a in actions), default=0)
    v = []
    for t in tools or []:
        for s in t.get("scopes") or []:
            need = order.index(at["scope_tiers"].get(s, "R3"))
            if need > top:
                v.append(f"tool '{t.get('name')}' holds '{s}' ({order[need]}), more than this workflow's actions need "
                         f"(highest {order[top]})")
    return Verdict.from_violations("isolation", v)
