# Author: Tom Sapletta · Part of the ifURI solution.
"""The deterministic resolution ladder — LLM proposes, the kernel decides.

Given a NeedSpec and a context (what the node serves, what the host serves, what is
installable, whether the node can be managed), pick the FIRST feasible strategy in cost
order — never install blindly, never reach for a GUI when a headless path exists:

    1. DIRECT        a capability is already served on the node        (cheapest, headless)
    2. HOST_FALLBACK a headless capability runs host-side + sync       (no node change)
    3. INSTALL       a connector provides it and the node can manage   (fixes the node)
    4. GUI           a GUI capability, only as a last resort
    5. BLOCKED       nothing feasible → honest, with what was tried

Every plan carries a postcondition (from the need's required_outputs) so the verifier
can confirm the artifact actually exists.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import capabilities as _caps
from . import needs as _needs


@dataclass
class Context:
    node: str
    node_served: list[str] = field(default_factory=list)
    host_served: list[str] = field(default_factory=list)
    installable: set = field(default_factory=set)
    can_manage: bool = False
    allow_gui: bool = False


def _postcondition(need: _needs.NeedSpec, node: str) -> dict | None:
    for out in need.required_outputs:
        if out.startswith("fs://") or out.startswith("artifact://"):
            return {"uri": out.replace("*", node, 1) if "{node}" not in out else out.replace("{node}", node),
                    "check": "exists"}
    return None


def _direct(need, ctx) -> dict | None:
    for cap_id in need.capabilities():
        cap = _caps.get(cap_id)
        if not cap or cap.gui:
            continue
        route = _caps.served_route(cap_id, ctx.node, ctx.node_served)
        if route:
            return {"strategy": "direct", "capability": cap_id,
                    "steps": [{"uri": route, "for": cap_id}]}
    return None


def _host_fallback(need, ctx) -> dict | None:
    for cap_id in need.capabilities():
        cap = _caps.get(cap_id)
        if not cap or cap.gui or not cap.host_ok:
            continue
        route = _caps.served_route(cap_id, "host", ctx.host_served)
        if route:
            return {"strategy": "host_fallback", "capability": cap_id,
                    "steps": [{"uri": route, "for": cap_id, "note": "run on host, then sync to node"}]}
    return None


def _install(need, ctx) -> dict | None:
    if not ctx.can_manage:
        return None
    for cap_id in need.capabilities():
        cap = _caps.get(cap_id)
        if not cap or cap.gui:
            continue
        for conn in cap.connectors:
            if conn in ctx.installable:
                n = ctx.node
                return {"strategy": "install_then_run", "capability": cap_id, "connector": conn,
                        "steps": [
                            {"uri": f"node://{n}/connector/command/install", "payload": {"id": conn}},
                            {"uri": f"node://{n}/registry/command/rebuild"},
                            {"uri": f"node://{n}/runtime/command/restart", "note": "drop stale workers"},
                            {"uri": f"node://{n}/smoke/command/run"},
                            {"uri": _caps.install_route(cap_id, n), "for": cap_id},
                        ]}
    return None


def _gui(need, ctx) -> dict | None:
    if not ctx.allow_gui:
        return None
    for cap_id in need.capabilities():
        cap = _caps.get(cap_id)
        if cap and cap.gui:
            route = _caps.served_route(cap_id, ctx.node, ctx.node_served)
            if route:
                return {"strategy": "gui", "capability": cap_id, "steps": [{"uri": route, "for": cap_id}]}
    return None


# strategy ladder, cheapest/safest first — GUI last, blind install never
_LADDER = (_direct, _host_fallback, _install, _gui)


def resolve(need: _needs.NeedSpec, ctx: Context) -> dict[str, Any]:
    """Walk the ladder; return the first feasible plan (+ postcondition), else blocked."""
    tried = []
    for strat in _LADDER:
        plan = strat(need, ctx)
        if plan:
            plan["need"] = need.id
            plan["postcondition"] = _postcondition(need, ctx.node)
            plan["resolved"] = True
            return plan
        tried.append(strat.__name__.lstrip("_"))
    return {"resolved": False, "need": need.id, "tried": tried,
            "reason": "no served route, no host fallback, no installable connector, GUI not allowed/available"}
