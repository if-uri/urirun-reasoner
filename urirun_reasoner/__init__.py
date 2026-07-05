# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""urirun-reasoner — intent → need → capability → URI plan, headless-first.

Model the GOAL, not the app. A missing GUI editor is one blocked method in a graph, not
the end of the road: the reasoner reframes "test office" into "produce a document
artifact" and resolves it through the cheapest feasible URI path (served route → host
fallback → install connector → GUI last). Deterministic core; LLM only where rules can't.
"""
from __future__ import annotations

from . import capabilities, intent, needs, planner
from .needs import NeedSpec
from .planner import Context, resolve

__all__ = ["capabilities", "intent", "needs", "planner", "NeedSpec", "Context", "resolve"]


def resolve_prompt(prompt: str, ctx: "Context", *, llm=None) -> dict:
    """One call: classify the prompt to a need, then resolve it to a URI plan."""
    need = intent.classify(prompt, llm=llm)
    if not need:
        return {"resolved": False, "reason": f"could not classify intent: {prompt!r}"}
    plan = resolve(need, ctx)
    plan["goal"] = need.goal
    return plan
