# Author: Tom Sapletta · Part of the ifURI solution.
"""Intent classification — prompt → NeedSpec. Rules first, LLM only as a fallback.

Most needs are recognizable by keyword (deterministic, no model call). An injected LLM
resolves novel prompts to a known need id; it never invents URIs, only names the intent —
"LLM proposes the need, the kernel maps it to capabilities and decides the method."
"""
from __future__ import annotations

from typing import Any, Callable

from . import needs as _needs

Completer = Callable[[str], str]

# keyword → need id (rule-based, cheap path)
_RULES: list[tuple[tuple[str, ...], str]] = [
    (("arkusz", "spreadsheet", "xlsx", "excel", "tabela"), "office.spreadsheet.create"),
    (("dokument", "document", "artykuł", "article", "biuro", "office", "notatk", "pismo",
      "edytor", "editor", "napisz", "write", "libreoffice", "onlyoffice", "faktur", "invoice"),
     "office.document.create"),
    (("zrzut", "screenshot", "ekran", "screen capture", "capture"), "desktop.screenshot"),
]


def classify(prompt: str, llm: Completer | None = None) -> _needs.NeedSpec | None:
    """Return the NeedSpec for a prompt. Rule-based first; LLM fallback names the need id."""
    low = (prompt or "").lower()
    for keywords, need_id in _RULES:
        if any(k in low for k in keywords):
            return _needs.get(need_id)
    if llm:
        try:
            catalog = ", ".join(_needs.CATALOG)
            reply = llm(f"Map this request to ONE need id from [{catalog}] or 'none'. "
                        f"Reply with only the id.\nRequest: {prompt}").strip().strip('"')
            return _needs.get(reply)
        except Exception:  # noqa: BLE001 - a bad LLM reply just means 'unclassified'
            return None
    return None
