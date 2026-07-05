# Author: Tom Sapletta · Part of the ifURI solution.
"""urirun-reasoner CLI: resolve a prompt to a headless-first URI plan."""
from __future__ import annotations
import argparse, json
from . import Context, resolve_prompt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="urirun-reasoner")
    ap.add_argument("prompt")
    ap.add_argument("--node", default="host")
    ap.add_argument("--node-served", nargs="*", default=[])
    ap.add_argument("--host-served", nargs="*", default=[])
    ap.add_argument("--installable", nargs="*", default=[])
    ap.add_argument("--can-manage", action="store_true")
    ap.add_argument("--allow-gui", action="store_true")
    a = ap.parse_args(argv)
    ctx = Context(node=a.node, node_served=a.node_served, host_served=a.host_served,
                  installable=set(a.installable), can_manage=a.can_manage, allow_gui=a.allow_gui)
    print(json.dumps(resolve_prompt(a.prompt, ctx), indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
