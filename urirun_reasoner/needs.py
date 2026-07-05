# Author: Tom Sapletta · Part of the ifURI solution.
"""NeedSpec — the contract of an INTENT, not a URI. Models the goal, not the app.

"Test office on lenovo" is not "launch ONLYOFFICE" — it is "produce a document artifact
and verify it exists". Modeling the need (not the means) is what lets the planner reframe
away from a missing GUI editor to a headless path. Each need lists the capabilities that
would satisfy it (preferred → acceptable) and whether a GUI is genuinely required.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NeedSpec:
    id: str
    goal: str
    required_outputs: tuple[str, ...] = ()        # artifact/postcondition globs proving success
    preferred_capabilities: tuple[str, ...] = ()  # best (headless, verifiable) first
    acceptable_capabilities: tuple[str, ...] = ()  # fallbacks that still satisfy the goal
    forbidden_methods: tuple[str, ...] = ()
    requires_gui: bool = False
    destructive: bool = False

    def capabilities(self) -> list[str]:
        return list(self.preferred_capabilities) + list(self.acceptable_capabilities)


# --- the needs catalog -----------------------------------------------------------
OFFICE_DOCUMENT = NeedSpec(
    id="office.document.create",
    goal="Create a document-like artifact and verify it exists — no GUI editor required.",
    required_outputs=("artifact://*/documents/*", "fs://*/file/query/stat"),
    preferred_capabilities=("document.create", "sheet.write", "invoice.render"),
    acceptable_capabilities=("markdown.write", "html.write", "browser.document_edit"),
    requires_gui=False,
)

SPREADSHEET = NeedSpec(
    id="office.spreadsheet.create",
    goal="Create a spreadsheet artifact and read it back.",
    required_outputs=("artifact://*/documents/*.xlsx", "fs://*/file/query/stat"),
    preferred_capabilities=("sheet.write",),
    acceptable_capabilities=("markdown.write",),
    requires_gui=False,
)

SCREENSHOT = NeedSpec(
    id="desktop.screenshot",
    goal="Capture the screen of a node.",
    required_outputs=("artifact://*/screenshots/*",),
    preferred_capabilities=("screen.capture",),
    requires_gui=False,
)

CATALOG: dict[str, NeedSpec] = {n.id: n for n in (OFFICE_DOCUMENT, SPREADSHEET, SCREENSHOT)}


def get(need_id: str) -> NeedSpec | None:
    return CATALOG.get(need_id)
