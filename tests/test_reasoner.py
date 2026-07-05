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
