"""Roadmap B3: information objects, documents and IT systems as notes.

They are not control flow, so the diagram carries them only on request
(`--notes`): one `note right` per function listing what hangs on it — one,
not one per object, because pumllint's GEN008 counts notes.
"""

import json

import pytest

from aris2puml.emit import emit
from aris2puml.model import Data, Edge, Lane, Node, Process
from aris2puml.readers.json_ import ReadError, read_json
from aris2puml.structure import structure
from tests.conftest import FIXTURES, build


def _with_data(*data):
    proc = build(
        [("e0", "event", "Claim received"), ("f1", "function", "Register claim"),
         ("e1", "event", "Claim registered"), ("f2", "function", "Settle claim"),
         ("e2", "event", "Claim settled")],
        ["e0>f1", "f1>e1", "e1>f2", "f2>e2"],
    )
    return Process(proc.id, proc.name, proc.owner, proc.lanes, proc.nodes, proc.edges, list(data))


def _lines(proc, notes):
    raw = emit(proc, structure(proc), notes=notes).splitlines()
    return raw[raw.index("start"):]


def test_without_the_flag_data_changes_nothing():
    plain = _lines(_with_data(), False)
    assert _lines(_with_data(Data("d1", "document", "Claim form", "f1")), False) == plain
    assert not any(l.startswith("note") for l in plain)


def test_one_object_is_an_inline_note_after_its_action():
    lines = _lines(_with_data(Data("d1", "document", "Claim form", "f1")), True)
    i = lines.index(":Register claim;")
    assert lines[i + 1] == "note right: document: Claim form"
    assert lines[i + 2] == "-> Claim registered;"


def test_several_objects_are_one_block_note_with_roles_where_known():
    lines = _lines(_with_data(
        Data("d1", "document", "Claim form", "f1"),
        Data("s1", "system", "Claims system", "f1"),
        Data("i1", "information", "Customer record", "f1", "input"),
        Data("i2", "information", "Settlement", "f2", "output"),
    ), True)
    i = lines.index(":Register claim;")
    assert lines[i + 1:i + 6] == [
        "note right", "  document: Claim form", "  system: Claims system",
        "  input: Customer record", "end note",
    ]
    j = lines.index(":Settle claim;")
    assert lines[j + 1] == "note right: output: Settlement"


def test_a_note_follows_a_backward_action_too():
    from tests.test_loops import _rework_with_return_work
    base = _rework_with_return_work()
    proc = Process(base.id, base.name, base.owner, base.lanes, base.nodes, base.edges,
                   [Data("s1", "system", "CRM", "f3")])
    lines = _lines(proc, True)
    i = lines.index("backward :Contact customer;")
    assert lines[i + 1] == "note right: system: CRM"


def test_notes_keep_swimlanes_in_step():
    proc = build(
        [("e0", "event", "S"), ("f1", "function", "A", "desk"), ("f2", "function", "B", "sales"),
         ("e1", "event", "E")],
        ["e0>f1", "f1>f2", "f2>e1"], lanes=[("desk", "Desk"), ("sales", "Sales")],
    )
    proc = Process(proc.id, proc.name, proc.owner, proc.lanes, proc.nodes, proc.edges,
                   [Data("d", "document", "Form", "f1")])
    lines = _lines(proc, True)
    assert lines[lines.index(":A;") + 1] == "note right: document: Form"
    assert lines[lines.index("note right: document: Form") + 1] == "|Sales|"


# --- the contract: "data" -------------------------------------------------

def _doc(data):
    return {"process": {"id": "P", "name": "P"},
            "nodes": [{"id": "e", "kind": "event", "name": "S"}, {"id": "f", "kind": "function", "name": "F"},
                      {"id": "d", "kind": "event", "name": "D"}],
            "edges": [{"from": "e", "to": "f"}, {"from": "f", "to": "d"}], "data": data}


def test_the_reader_carries_data_and_validates_it(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps(_doc([{"id": "x", "kind": "system", "name": "ERP", "node": "f", "role": "input"}])),
                 encoding="utf-8")
    (proc,) = read_json(p)
    assert proc.data == [Data("x", "system", "ERP", "f", "input")]
    assert proc.data_of("f") == proc.data and proc.data_of("e") == []


@pytest.mark.parametrize("item, problem", [
    ({"id": "x", "kind": "blob", "name": "ERP", "node": "f"}, "unknown data kind 'blob'"),
    ({"id": "x", "kind": "system", "name": "ERP", "node": "e"}, "which is not a function"),
    ({"id": "x", "kind": "system", "name": "ERP", "node": "nope"}, "which is not a function"),
    ({"id": "x", "kind": "system", "name": "", "node": "f"}, "has no name"),
    ({"id": "x", "kind": "system", "name": "ERP", "node": "f", "role": "sideways"}, "unknown role"),
])
def test_bad_data_is_a_read_error_naming_the_object(tmp_path, item, problem):
    p = tmp_path / "p.json"
    p.write_text(json.dumps(_doc([item])), encoding="utf-8")
    with pytest.raises(ReadError, match=f"x: .*{problem}"):
        read_json(p)


def test_the_corpus_fixture_with_systems_draws_three_notes_pumllint_does_not_mind(tmp_path):
    """`project-financing-to-be.json` carries three ERP-system objects. With
    --notes they are three notes; pumllint reports the model's own naming
    defects (a German student model), never GEN008."""
    pytest.importorskip("pumllint")
    import contextlib
    import io
    from aris2puml.cli import main
    out = tmp_path / "out"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = main([str(FIXTURES / "corpus" / "project-financing-to-be.json"), "-o", str(out),
                   "--notes", "--check", "-c", str(FIXTURES / "conventions.toml")])
    assert rc == 1 and "ACT006" in buf.getvalue() and "GEN008" not in buf.getvalue()
    (puml,) = out.glob("*.puml")
    assert puml.read_text(encoding="utf-8").count("note right: system: ERP System") == 3
