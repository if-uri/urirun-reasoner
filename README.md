# urirun-reasoner

Intent → need → capability → URI plan, **headless-first**. Model the GOAL, not the app.

A missing GUI editor is one blocked method in a graph — not the end of the road. Asked to
"test office on lenovo", the reasoner does not stop at "no LibreOffice"; it reframes to
"produce a document artifact and verify it exists" and resolves it through the cheapest
feasible URI path.

## The resolution ladder (kernel decides, cheapest/safest first)

1. **direct** — a capability is already served on the node (headless)
2. **host_fallback** — a headless capability runs host-side + sync (no node change)
3. **install_then_run** — a connector provides it and the node can manage (install → rebuild → restart → smoke → use)
4. **gui** — a GUI capability, only as a last resort
5. **blocked** — nothing feasible → honest, with what was tried

GUI is never chosen when a headless path exists; connectors are never installed blindly.

## Layers

| module | role |
|---|---|
| `needs.py` | `NeedSpec` — the intent contract (goal, required outputs, preferred/acceptable capabilities, requires_gui) + a catalog |
| `capabilities.py` | `CapabilityMap` — capability → URI route templates + connectors (the layer between language and URIs) |
| `intent.py` | prompt → NeedSpec (rules first; LLM only names the intent, never invents URIs) |
| `planner.py` | the deterministic ladder + `resolve(need, ctx)` with a postcondition |

## Use

```python
from urirun_reasoner import Context, resolve_prompt
ctx = Context(node="lenovo", node_served=[...], host_served=["fs://host/file/command/write"],
              installable={"sheet"}, can_manage=True)
plan = resolve_prompt("przetestuj biuro na lenovo", ctx)
# → {"strategy": "host_fallback", "steps": [...], "postcondition": {...}}
```

Pairs with `urirun-fleet` (node readiness + execution) and the dispatch `_meta` provenance
(so the reasoner knows what is actually served). Part of the ifURI solution · Apache-2.0
