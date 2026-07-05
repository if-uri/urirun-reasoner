# Author: Tom Sapletta · Part of the ifURI solution.
"""CapabilityMap — the missing layer between a NEED and concrete URIs/connectors.

A capability (e.g. ``document.create``) maps to the routes that provide it and the
connectors that install it. This is what turns "I need to author a document" into
"call sheet://… , or install urirun-connector-sheet". Route templates use ``{node}``.
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Capability:
    id: str
    routes: tuple[str, ...]        # URI templates ({node} placeholder)
    connectors: tuple[str, ...] = ()  # connector ids that provide this capability
    gui: bool = False
    host_ok: bool = True           # can this run host-side as a fallback?


MAP: dict[str, Capability] = {
    "document.create": Capability("document.create",
        ("document://{node}/document/command/create", "odt://{node}/document/command/create"),
        ("document", "office"), host_ok=True),
    "sheet.write": Capability("sheet.write",
        ("sheet://{node}/workbook/command/write", "sheet://{node}/rows/command/write",
         "xlsx://{node}/workbook/command/write"),
        ("sheet",), host_ok=True),
    "invoice.render": Capability("invoice.render",
        ("invoice://{node}/invoice/command/render", "invoice://{node}/document/command/build"),
        ("invoice",), host_ok=True),
    "markdown.write": Capability("markdown.write",
        ("fs://{node}/file/command/write",), ("fs",), host_ok=True),
    "html.write": Capability("html.write",
        ("fs://{node}/file/command/write",), ("fs",), host_ok=True),
    "browser.document_edit": Capability("browser.document_edit",
        ("browser://{node}/page/command/navigate", "cdp://{node}/page/command/navigate"),
        ("browser", "cdp"), gui=True, host_ok=False),
    "screen.capture": Capability("screen.capture",
        ("screen://{node}/screen/query/capture", "kvm://{node}/screen/query/capture",
         "view://{node}/screenshot/query/capture"),
        ("kvm",), host_ok=False),
}


def get(cap_id: str) -> Capability | None:
    return MAP.get(cap_id)


def _served(route_tmpl: str, node: str, served: list[str]) -> str | None:
    """Return the concrete served route matching this template for ``node``, else None."""
    want = route_tmpl.replace("{node}", node)
    tail = want.split("://", 1)[-1]
    for r in served:
        if r == want or fnmatch.fnmatch(r.split("://", 1)[-1], tail) or \
           fnmatch.fnmatch(r.split("://", 1)[-1], route_tmpl.split("://", 1)[-1].replace("{node}", "*")):
            return r
    return None


def served_route(cap_id: str, node: str, served: list[str]) -> str | None:
    """Is this capability already served on the node? Return the concrete route or None."""
    cap = MAP.get(cap_id)
    if not cap:
        return None
    for tmpl in cap.routes:
        hit = _served(tmpl, node, served)
        if hit:
            return hit
    return None


def install_route(cap_id: str, node: str) -> str:
    """The concrete route to call once the capability's connector is installed."""
    cap = MAP.get(cap_id)
    return cap.routes[0].replace("{node}", node) if cap else ""


def providers(cap_id: str) -> tuple[str, ...]:
    cap = MAP.get(cap_id)
    return cap.connectors if cap else ()
