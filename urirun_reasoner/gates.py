# Author: Tom Sapletta · Part of the ifURI solution.
"""Gates — the hard rules on what the system may NEVER do without a human.

A plan step is classified by its URI: publishing, paying, messaging a vendor, ordering,
or sending private files are ALWAYS human-gated; searching, drafting, packaging,
comparing, generating a document are autonomous. The planner inserts an
``approval://human/...`` gate before any gated step, or downgrades it to draft mode.
"""
from __future__ import annotations

# (matcher substring, gate reason) — a step whose URI contains the substring is gated
_GATED: list[tuple[str, str]] = [
    ("/command/publish", "public publication requires human approval"),
    ("/command/pay", "payment always requires human approval"),
    ("/command/schedule", "scheduling a public post requires human approval"),
    ("/message/command/send", "sending a message to a vendor requires human approval"),
    ("/email/command/send", "sending email requires human approval"),
    ("/order/command", "placing/ordering a service requires human approval"),
    ("/command/confirm", "confirmation of a paid/committed action requires a human"),
]

# autonomous-safe verbs (never gated) — for documentation / assertion
AUTONOMOUS = ("query/", "command/write", "command/draft", "command/package",
              "command/render", "command/create", "command/summarize", "command/extract",
              "command/compare", "command/search", "command/build")


def gate_for(uri: str) -> str | None:
    """Return the human-gate reason for a URI, or None if it is autonomous-safe."""
    u = str(uri)
    for needle, reason in _GATED:
        if needle in u:
            return reason
    return None


def apply(steps: list[dict], *, node_for_approval: str = "human") -> list[dict]:
    """Insert an approval:// gate before each gated step; leave autonomous steps as-is.

    Returns a new step list. A gated step also gets ``gate: "required"`` so an executor
    refuses to run it until the preceding approval is granted (draft-then-approve)."""
    out: list[dict] = []
    for step in steps:
        reason = gate_for(step.get("uri", ""))
        if reason:
            out.append({"uri": f"approval://{node_for_approval}/action/command/review",
                        "for": "gate", "reason": reason, "reviews": step.get("uri")})
            out.append({**step, "gate": "required"})
        else:
            out.append(step)
    return out


def has_ungated_risk(steps: list[dict]) -> list[str]:
    """Audit: return URIs of any gated step NOT immediately preceded by an approval.
    A safety net — the plan must never carry a bare publish/pay/send."""
    risky: list[str] = []
    prev_is_gate = False
    for step in steps:
        uri = step.get("uri", "")
        if gate_for(uri) and not prev_is_gate:
            risky.append(uri)
        prev_is_gate = uri.startswith("approval://")
    return risky
