import json

import pytest

from aris2puml.readers.json_ import ReadError, read_json
from tests.conftest import FIXTURES


def test_reads_the_order_to_cash_fixture():
    (proc,) = read_json(FIXTURES / "order_to_cash.json")
    assert proc.id == "PROC-0042" and proc.owner == "Sales Operations"
    assert [l.name for l in proc.lanes] == ["Sales", "Credit Control", "Warehouse & Logistics", "Finance"]
    assert proc.node("p1").kind == "interface" and proc.node("p1").ref == "PROC-0051"
    assert proc.successors("x1") == ["e1", "e2"]


def test_names_are_collapsed_to_one_line(tmp_path):
    doc = {"version": 1, "process": {"id": "P", "name": "N"},
           "nodes": [{"id": "f", "kind": "function", "name": "Validate\n   order  "}]}
    f = tmp_path / "p.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    (proc,) = read_json(f)
    assert proc.node("f").name == "Validate order"


def test_a_list_of_processes_is_accepted(tmp_path):
    one = {"process": {"id": "A", "name": "A"}, "nodes": [{"id": "e", "kind": "event", "name": "E"}]}
    two = {"process": {"id": "B", "name": "B"}, "nodes": [{"id": "e", "kind": "event", "name": "E"}]}
    f = tmp_path / "many.json"
    f.write_text(json.dumps({"version": 1, "processes": [one, two]}), encoding="utf-8")
    assert [p.id for p in read_json(f)] == ["A", "B"]


@pytest.mark.parametrize(
    "doc, fragment",
    [
        ({"version": 2, "process": {"id": "P", "name": "N"}}, "unsupported version"),
        ({"process": {"id": "P"}}, "malformed"),
        ({"process": {"id": "P", "name": "N"},
          "nodes": [{"id": "f", "kind": "function", "name": "F", "lane": "nope"}]}, "unknown lane"),
        ({"process": {"id": "P", "name": "N"},
          "nodes": [{"id": "f", "kind": "task", "name": "F"}]}, "unknown kind"),
        ({"process": {"id": "P", "name": "N"},
          "nodes": [{"id": "f", "kind": "function", "name": "F"}],
          "edges": [{"from": "f", "to": "ghost"}]}, "unknown node"),
        ({"process": {"id": "P", "name": "N"},
          "nodes": [{"id": "x", "kind": "xor"}, {"id": "y", "kind": "xor"}],
          "edges": [{"from": "x", "to": "y"}, {"from": "y", "to": "x"}]}, "no start node"),
        ([], "expected a JSON object"),
    ],
)
def test_malformed_documents_are_refused_with_the_file_named(tmp_path, doc, fragment):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ReadError) as exc:
        read_json(f)
    assert "bad.json" in str(exc.value) and fragment in str(exc.value)


def test_unreadable_file_is_a_read_error(tmp_path):
    with pytest.raises(ReadError):
        read_json(tmp_path / "missing.json")
