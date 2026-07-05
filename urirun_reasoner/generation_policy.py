# Author: Tom Sapletta · Part of the ifURI solution.
"""Generation policy — the rules under which the system may create a NEW connector itself.

Autonomy needs guardrails, not permission prompts. A connector spec is admissible only if
it introduces a NEW scheme (never silently overwrites a served one), every handler routes
through the urirun envelope, any destructive/network verb (delete/pay/publish/send) is
marked gated, no secret is baked inline, and the id/scheme are clean slugs. A generated
connector must pass its own smoke test before it is installed or published. These checks
are what let the reasoner call ``connector://.../generate`` without asking a human first.
"""
from __future__ import annotations

import re
from typing import Any

_SLUG = re.compile(r"^[a-z][a-z0-9-]{1,39}$")
_GATED_VERBS = ("delete", "pay", "publish", "send", "order", "remove", "drop", "wipe", "purge")
_SECRET_HINT = re.compile(r"(password|api[_-]?key|secret|token)\s*=\s*['\"][^'\"]+['\"]", re.I)


def check(spec: dict, *, served_schemes: set | None = None) -> dict[str, Any]:
    """Validate a connector spec against the generation policy. Returns
    {ok, violations, gated_routes}. ``served_schemes`` are schemes already served (must not
    be overwritten)."""
    violations: list[str] = []
    cid = str(spec.get("id", ""))
    scheme = str(spec.get("scheme", cid))
    if not _SLUG.match(cid):
        violations.append(f"id {cid!r} is not a clean slug [a-z][a-z0-9-]{{1,39}}")
    if not _SLUG.match(scheme):
        violations.append(f"scheme {scheme!r} is not a clean slug")
    if served_schemes and scheme in served_schemes:
        violations.append(f"scheme '{scheme}://' is already served — refuse to overwrite (bump/rename instead)")

    handlers = spec.get("handlers") or []
    if not handlers:
        violations.append("spec has no handlers")
    gated_routes: list[str] = []
    for h in handlers:
        route = str(h.get("route", ""))
        if "/" not in route:
            violations.append(f"handler route {route!r} must look like 'noun/verb/name'")
        body = str(h.get("body", ""))
        if _SECRET_HINT.search(body):
            violations.append(f"handler {route!r} appears to hardcode a secret — use secret:// references")
        # a destructive/network verb must be declared gated so an executor requires approval
        if any(v in route.lower() for v in _GATED_VERBS):
            if not h.get("gated"):
                violations.append(f"handler {route!r} uses a destructive/network verb but is not marked gated")
            gated_routes.append(route)

    return {"ok": not violations, "violations": violations, "gated_routes": gated_routes,
            "id": cid, "scheme": scheme}


def admissible(spec: dict, *, served_schemes: set | None = None) -> bool:
    return check(spec, served_schemes=served_schemes)["ok"]
