"""Roadmap A3: the fidelity sidecar.

What a conversion could not carry faithfully — dropped elements, approximated
shapes, refused processes — as a versioned JSON record, so that "it
converted" is a number and the refusals are a list. Every shape here is a
hand-written reproduction of one seen in the public corpus, not a copy.
"""

import json
from pathlib import Path

from aris2puml.cli import convert
from aris2puml.model import APPROXIMATED, DROPPED, Note
from aris2puml.readers.epml import read_epml
from aris2puml.report import VERSION, Record, Report
from aris2puml.structure import structure
from tests.conftest import FIXTURES, build
from tests.test_epml import DOC


# --- the record and the report ---------------------------------------------

def test_a_clean_conversion_is_one_converted_record_with_nothing_lost():
    proc = build(
        [("e0", "event", "Started"), ("f", "function", "Do it"), ("e1", "event", "Done")],
        ["e0>f", "f>e1"],
    )
    s = structure(proc)
    r = Report()
    r.inputs.append("in.json")
    r.converted(Path("in.json"), proc.id, proc.name, Path("out/test.puml"), s.notes)
    (rec,) = r.records
    assert rec.status == "converted" and rec.approximated == [] and rec.dropped == []
    assert r.summary() == {
        "inputs": 1, "processes": 1, "converted": 1, "refused": 0,
        "converted_percent": 100.0, "approximated": 0, "dropped": 0,
    }


def test_an_or_connector_is_recorded_as_an_approximation_with_its_node():
    proc = build(
        [("e0", "event", "S"), ("o", "or"), ("a", "function", "A"), ("b", "function", "B"),
         ("j", "or"), ("ee", "event", "E")],
        ["e0>o", "o>a", "o>b", "a>j", "b>j", "j>ee"],
    )
    s = structure(proc)
    r = Report()
    rec = r.converted(Path("in.json"), proc.id, proc.name, None, s.notes)
    (note,) = rec.approximated
    assert note.code == "or-connector" and note.node == "o"
    assert rec.dropped == []
    assert rec.as_dict()["approximated"] == [
        {"code": "or-connector", "node": "o",
         "detail": "o: OR connector has no activity-diagram equivalent; emitted as fork"}
    ]


def test_a_backward_return_path_records_the_dropped_event():
    proc = build(
        [("e0", "event", "Received"), ("h", "xor"), ("f1", "function", "Check it"),
         ("x", "xor"), ("e2", "event", "Invalid"), ("f3", "function", "Contact customer"),
         ("e4", "event", "Received again"), ("e5", "event", "Valid"),
         ("f6", "function", "Record it"), ("e7", "event", "Recorded")],
        ["e0>h", "h>f1", "f1>x", "x>e2", "e2>f3", "f3>e4", "e4>h", "x>e5", "e5>f6", "f6>e7"],
    )
    rec = Report().converted(Path("in.json"), "P", "P", None, structure(proc).notes)
    (note,) = rec.dropped
    assert note.code == "return-path-events" and note.node == "x"
    assert "Received again" in note.text


def test_every_note_code_belongs_to_exactly_one_category():
    """A code that is neither dropped nor approximated would vanish from the
    sidecar without anyone noticing."""
    assert not set(APPROXIMATED) & set(DROPPED)
    for code in ("mid-flow-trigger", "or-start-events", "or-connector",
                 "return-path-events", "return-path-lane",
                 "unsupported-element", "unused-lane"):
        assert code in APPROXIMATED or code in DROPPED, code


def test_a_refused_process_keeps_its_reason_and_no_output():
    r = Report()
    rec = r.refused(Path("in.json"), "join j reached without passing through its split", "P-9", "Nine")
    assert rec.as_dict() == {
        "input": "in.json", "id": "P-9", "name": "Nine", "status": "refused",
        "reason": "join j reached without passing through its split",
    }
    assert r.any_refused and r.written == []


def test_a_refused_document_is_a_record_with_no_process_id():
    r = Report()
    r.inputs.append("bad.json")
    rec = r.refused(Path("bad.json"), "bad.json: Expecting value")
    assert rec.id is None and rec.name is None
    assert r.summary()["processes"] == 1 and r.summary()["converted_percent"] == 0.0


def test_the_document_is_versioned_and_names_the_tool():
    d = Report().as_dict()
    assert d["version"] == VERSION == 1
    assert d["tool"].startswith("aris2puml ")
    assert d["processes"] == [] and d["summary"]["processes"] == 0


# --- the reader's half: what the EPML reader drops -------------------------

def test_the_epml_reader_records_the_data_object_it_drops(tmp_path):
    p = tmp_path / "claims.epml"
    p.write_text(DOC, encoding="utf-8")
    notes: dict[str, list[Note]] = {}
    procs = read_epml(p, notes)
    assert set(notes) == {proc.id for proc in procs}
    (d1,) = [n for ns in notes.values() for n in ns]
    assert d1.code == "unsupported-element" and d1.node == "d1"
    assert "<dataField>" in d1.text and "Claim form" in d1.text
    # and without the channel the reader is exactly as before
    assert [pr.id for pr in read_epml(p)] == [pr.id for pr in procs]


# --- convert(): the whole run, collecting ----------------------------------

def _write(tmp_path, name, doc):
    p = tmp_path / name
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


REFUSES = {"process": {"id": "U", "name": "Unstructured"},
           "nodes": [{"id": "e", "kind": "event", "name": "S"},
                     {"id": "f", "kind": "function", "name": "F"},
                     {"id": "a", "kind": "function", "name": "A"},
                     {"id": "b", "kind": "function", "name": "B"}],
           "edges": [{"from": "e", "to": "f"}, {"from": "f", "to": "a"}, {"from": "f", "to": "b"}]}


def test_collecting_continues_past_a_refusal_and_still_records_it(tmp_path):
    bad = _write(tmp_path, "u.json", REFUSES)
    report = convert([str(bad), str(FIXTURES / "order_to_cash.json")], "json",
                     str(tmp_path / "out"), collect=True)
    assert [r.status for r in report.records] == ["refused", "converted"]
    assert report.records[0].id == "U" and "has 2 successors" in report.records[0].reason
    assert report.records[1].output.endswith("/order-to-cash.puml")
    assert (tmp_path / "out" / "order-to-cash.puml").exists()
    assert report.any_refused
    assert report.summary()["converted_percent"] == 50.0


def test_not_collecting_raises_exactly_as_before(tmp_path):
    import pytest
    from aris2puml.structure import StructureError
    bad = _write(tmp_path, "u.json", REFUSES)
    with pytest.raises(StructureError, match=r"u\.json \[U\]: f: function has 2 successors"):
        convert([str(bad)], "json", str(tmp_path / "out"))
    assert not (tmp_path / "out").exists()


def test_every_path_in_the_sidecar_is_posix(tmp_path):
    report = convert([str(FIXTURES / "order_to_cash.json")], "json", str(tmp_path), collect=True)
    doc = report.as_dict()
    for r in doc["processes"]:
        assert "\\" not in r["input"] and "\\" not in (r["output"] or "")
    out = tmp_path / "s.json"
    report.write(out)
    assert json.loads(out.read_text(encoding="utf-8")) == doc
