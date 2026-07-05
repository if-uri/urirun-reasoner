# Author: Tom Sapletta · Part of the ifURI solution.
"""The reasoner contract: model the goal not the app, and walk the ladder cheapest-first.
GUI is the LAST resort; a missing editor never ends the process."""
from urirun_reasoner import Context, intent, needs, planner, resolve, resolve_prompt


def test_intent_maps_office_words_to_document_need():
    assert intent.classify("napisz artykuł w edytorze tekstu").id == "office.document.create"
    assert intent.classify("przetestuj biuro na lenovo").id == "office.document.create"
    assert intent.classify("stwórz arkusz z danymi").id == "office.spreadsheet.create"
    assert intent.classify("zupełnie coś innego") is None


def test_direct_when_capability_already_served():
    ctx = Context(node="laptop", node_served=["sheet://laptop/workbook/command/write"])
    p = planner.resolve(needs.OFFICE_DOCUMENT, ctx)
    assert p["resolved"] and p["strategy"] == "direct" and p["capability"] == "sheet.write"
    assert p["steps"][0]["uri"] == "sheet://laptop/workbook/command/write"


def test_host_fallback_before_install_when_node_lacks_it():
    # node serves nothing useful; host can write files → host_fallback beats installing
    ctx = Context(node="laptop", node_served=["kvm://laptop/screen/query/capture"],
                  host_served=["fs://host/file/command/write"],
                  installable={"sheet"}, can_manage=True)
    p = planner.resolve(needs.OFFICE_DOCUMENT, ctx)
    assert p["strategy"] == "host_fallback" and p["capability"] == "markdown.write"
    assert p["steps"][0]["uri"] == "fs://host/file/command/write"


def test_install_when_no_direct_and_no_host_fallback():
    # nothing served anywhere, but a connector is installable and the node can manage
    ctx = Context(node="laptop", node_served=[], host_served=[],
                  installable={"sheet"}, can_manage=True)
    p = planner.resolve(needs.OFFICE_DOCUMENT, ctx)
    assert p["strategy"] == "install_then_run" and p["connector"] == "sheet"
    uris = [s["uri"] for s in p["steps"]]
    assert uris[0] == "node://laptop/connector/command/install"
    assert "node://laptop/runtime/command/restart" in uris  # drop stale workers
    assert uris[-1].startswith("sheet://laptop/")            # then actually use it


def test_gui_is_last_resort_only_when_allowed_and_nothing_else():
    ctx = Context(node="laptop", node_served=["browser://laptop/page/command/navigate"],
                  host_served=[], installable=set(), can_manage=False, allow_gui=True)
    p = planner.resolve(needs.OFFICE_DOCUMENT, ctx)
    assert p["strategy"] == "gui" and p["capability"] == "browser.document_edit"


def test_gui_not_chosen_when_headless_exists():
    # both a served browser (gui) AND a served sheet (headless) → headless wins
    ctx = Context(node="laptop",
                  node_served=["browser://laptop/page/command/navigate",
                               "sheet://laptop/workbook/command/write"],
                  allow_gui=True)
    p = planner.resolve(needs.OFFICE_DOCUMENT, ctx)
    assert p["strategy"] == "direct" and p["capability"] == "sheet.write"


def test_blocked_is_honest_with_what_was_tried():
    ctx = Context(node="laptop", node_served=[], host_served=[], installable=set(),
                  can_manage=False, allow_gui=False)
    p = planner.resolve(needs.OFFICE_DOCUMENT, ctx)
    assert p["resolved"] is False and set(p["tried"]) >= {"direct", "host_fallback", "install", "gui"}


def test_plan_carries_postcondition():
    ctx = Context(node="laptop", node_served=["sheet://laptop/workbook/command/write"])
    p = planner.resolve(needs.OFFICE_DOCUMENT, ctx)
    assert p["postcondition"] and p["postcondition"]["check"] == "exists"


def test_resolve_prompt_office_on_lenovo_reframes_to_headless():
    # THE flagship case: "test office on lenovo" with no GUI → headless host fallback
    ctx = Context(node="lenovo", node_served=["kvm://lenovo/screen/query/capture"],
                  host_served=["fs://host/file/command/write"], installable={"sheet"},
                  can_manage=True, allow_gui=True)
    p = resolve_prompt("przetestuj biuro na lenovo", ctx)
    assert p["resolved"] and p["strategy"] == "host_fallback"
    assert p["need"] == "office.document.create" and not p["strategy"] == "gui"


# --- gates: risky actions are never ungated -------------------------------------
def test_gate_classifies_risky_verbs():
    from urirun_reasoner import gates
    assert gates.gate_for("linkedin://user/post/command/publish")
    assert gates.gate_for("fiverr://user/order/command/pay")
    assert gates.gate_for("email://user/message/command/send")
    assert gates.gate_for("fs://host/file/command/write") is None      # autonomous
    assert gates.gate_for("sheet://host/workbook/command/write") is None


def test_gate_inserts_approval_before_publish():
    from urirun_reasoner import gates
    steps = [{"uri": "llm://host/social/command/write-linkedin-post"},
             {"uri": "linkedin://user/post/command/publish"}]
    out = gates.apply(steps)
    assert out[0]["uri"].endswith("social/command/write-linkedin-post")   # autonomous kept
    assert out[1]["uri"].startswith("approval://human/")                  # gate inserted
    assert out[2]["gate"] == "required"
    assert gates.has_ungated_risk(out) == []                              # audit clean


def test_audit_catches_bare_payment():
    from urirun_reasoner import gates
    risky = gates.has_ungated_risk([{"uri": "fiverr://user/order/command/pay"}])
    assert risky == ["fiverr://user/order/command/pay"]


def test_generator_scaffolds_a_valid_connector(tmp_path):
    from urirun_reasoner import generator
    spec = {"id": "demo", "scheme": "demo", "summary": "x",
            "handlers": [{"route": "thing/query/list", "params": "", "body": 'return _ok(action="x")'}]}
    r = generator.generate(spec, tmp_path)
    assert r["ok"] and r["routes"] == ["thing/query/list"]
    core = (tmp_path / "urirun-connector-demo" / "urirun_connector_demo" / "core.py").read_text()
    assert 'scheme="demo"' in core and "def thing_query_list" in core
    assert (tmp_path / "urirun-connector-demo" / "pyproject.toml").is_file()
    assert (tmp_path / "urirun-connector-demo" / "tests" / "test_demo.py").is_file()
