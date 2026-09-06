"""The no-lane lane.

Once a diagram uses swimlanes PlantUML wants one before `start` and rejects
`||`; and a function with no org unit used to inherit the previous lane
silently. So in a process that uses lanes every action is drawn in its own,
and "no org unit" is a lane of its own — blank unless `--no-lane` says
otherwise, and counted in the sidecar either way.
"""

import contextlib
import io
import json

import pytest

from aris2puml.cli import main
from aris2puml.emit import emit
from aris2puml.model import Lane, Node, Process
from aris2puml.structure import structure
from tests.conftest import FIXTURES, build


def _lines(proc, **kw):
    raw = emit(proc, structure(proc), **kw).splitlines()
    return [l.strip() for l in raw[4:]]  # after @startuml, title, footer, blank


def _mixed():
    """First function unowned, then Sales, then unowned again."""
    return build(
        [("e0", "event", "Order received"), ("f1", "function", "Analyse order"),
         ("f2", "function", "Talk to customer", "sales"), ("f3", "function", "Close order"),
         ("e1", "event", "Order closed")],
        ["e0>f1", "f1>f2", "f2>f3", "f3>e1"], lanes=[("sales", "Sales")],
    )


def test_an_unowned_function_gets_the_blank_lane_before_start_and_after_a_real_one():
    assert _lines(_mixed()) == [
        "| |", "start", "-> Order received;", ":Analyse order;",
        "|Sales|", ":Talk to customer;",
        "| |", ":Close order;",
        "-> Order closed;", "stop", "@enduml",
    ]


def test_the_label_is_configurable_and_lands_only_on_the_no_lane_lane():
    lines = _lines(_mixed(), no_lane="Owner TBD")
    assert lines.count("|Owner TBD|") == 2 and "| |" not in lines
    assert lines[0] == "|Owner TBD|" and "|Sales|" in lines


def test_an_org_unit_with_no_name_is_a_blank_lane_whatever_the_label():
    proc = build(
        [("e0", "event", "S"), ("f1", "function", "A", "x"), ("f2", "function", "B"), ("e1", "event", "E")],
        ["e0>f1", "f1>f2", "f2>e1"], lanes=[("x", "")],
    )
    lines = _lines(proc, no_lane="Owner TBD")
    assert lines[0] == "| |"                       # the model's own defect, drawn as it is
    assert "|Owner TBD|" in lines                  # the unowned function, as asked
    assert "||" not in "\n".join(lines)


def test_a_fully_owned_process_and_a_lane_less_process_are_unchanged():
    owned = build(
        [("e0", "event", "S"), ("f1", "function", "A", "x"), ("f2", "function", "B", "y"), ("e1", "event", "E")],
        ["e0>f1", "f1>f2", "f2>e1"], lanes=[("x", "Desk"), ("y", "Sales")],
    )
    assert _lines(owned)[:2] == ["|Desk|", "start"] and "| |" not in _lines(owned)
    bare = build([("e0", "event", "S"), ("f1", "function", "A"), ("e1", "event", "E")], ["e0>f1", "f1>e1"])
    assert not any(l.startswith("|") for l in _lines(bare, no_lane="Owner TBD"))


def test_a_backward_action_still_takes_no_lane():
    from tests.test_loops import _rework_with_return_work
    lines = _lines(_rework_with_return_work(lanes=[("desk", "Desk"), ("sales", "Sales")]))
    i = lines.index("backward :Contact customer;")
    assert not lines[i - 1].startswith("|")


def test_an_interface_keeps_its_marker_right_above_its_action():
    proc = build(
        [("e0", "event", "S"), ("f1", "function", "A", "x"), ("p", "interface", "Bill", None, "PROC-2"),
         ("e1", "event", "E")],
        ["e0>f1", "f1>p", "p>e1"], lanes=[("x", "Desk")],
    )
    lines = _lines(proc)
    i = lines.index(":Bill;")
    assert lines[i - 1] == "' aris: interface PROC-2" and lines[i - 2] == "| |"


# --- the sidecar counts them, whatever the picture says ---------------------

def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = main(argv)
    return rc, out.getvalue(), err.getvalue()


MIXED = {"process": {"id": "M", "name": "Mixed"},
         "lanes": [{"id": "sales", "name": "Sales"}, {"id": "x", "name": ""}],
         "nodes": [{"id": "e0", "kind": "event", "name": "S"},
                   {"id": "f1", "kind": "function", "name": "Analyse order"},
                   {"id": "f2", "kind": "function", "name": "Talk to customer", "lane": "sales"},
                   {"id": "f3", "kind": "function", "name": "Close order", "lane": "x"},
                   {"id": "e1", "kind": "event", "name": "E"}],
         "edges": [{"from": "e0", "to": "f1"}, {"from": "f1", "to": "f2"}, {"from": "f2", "to": "f3"},
                   {"from": "f3", "to": "e1"}]}


@pytest.mark.parametrize("label", ["", "Owner TBD"])
def test_flagged_in_the_sidecar_and_off_stderr_whatever_the_label(tmp_path, label):
    src = tmp_path / "m.json"
    src.write_text(json.dumps(MIXED), encoding="utf-8")
    side = tmp_path / "s.json"
    rc, _, err = _run([str(src), "-o", str(tmp_path / "out"), "--report", str(side), "--no-lane", label])
    assert rc == 0 and err == ""
    doc = json.loads(side.read_text(encoding="utf-8"))
    (rec,) = doc["processes"]
    assert [(n["code"], n["node"]) for n in rec["flagged"]] == [("no-lane", "f1"), ("unnamed-lane", "x")]
    assert rec["dropped"] == [] and rec["approximated"] == []
    assert doc["summary"]["flagged"] == 2


def test_strict_does_not_refuse_a_model_defect_the_diagram_shows(tmp_path):
    src = tmp_path / "m.json"
    src.write_text(json.dumps(MIXED), encoding="utf-8")
    rc, _, _ = _run([str(src), "-o", str(tmp_path / "out"), "--strict"])
    assert rc == 0


def test_pumllint_flags_the_blank_lane_and_nothing_else(tmp_path):
    pytest.importorskip("pumllint")
    src = tmp_path / "m.json"
    src.write_text(json.dumps(MIXED), encoding="utf-8")
    rc, out, err = _run([str(src), "-o", str(tmp_path / "out"), "--check", "-c",
                         str(FIXTURES / "conventions.toml")])
    text = out + err
    assert rc == 1 and "ACT005" in text and "Swimlane ''" in text
    assert not any(code in text for code in ("ACT001", "ACT002", "ACT004"))
