import pytest

from aris2puml.emit import emit
from aris2puml.readers import READERS
from aris2puml.readers.epml import read_epml
from aris2puml.readers.json_ import ReadError
from aris2puml.structure import structure

# Hand-written, not a corpus copy: two processes in one document, the
# first with a role tied to a function and a process interface, the
# second minimal. Names are broken across lines the way the SAP corpus
# breaks them.
DOC = """<?xml version="1.0" encoding="utf-8"?>
<epml>
 <epc epcId="7" name="Handle claim">
  <role id="r1"><name>Claims
desk</name></role>
  <event id="e1"><name>Claim
received</name></event>
  <function id="f1"><name>Register claim</name></function>
  <relation from="f1" to="r1" type="role"/>
  <xor id="x1"/>
  <event id="e2"><name>Claim valid</name></event>
  <event id="e3"><name>Claim invalid</name></event>
  <processInterface id="p1" linkToEpcId="9"><name>Settle claim</name></processInterface>
  <event id="e4"><name>Claim settled</name></event>
  <function id="f2"><name>Reject claim</name></function>
  <event id="e5"><name>Claim rejected</name></event>
  <dataField id="d1"><name>Claim form</name></dataField>
  <arc id="a1"><flow source="e1" target="f1"/></arc>
  <arc id="a2"><flow source="f1" target="x1"/></arc>
  <arc id="a3"><flow source="x1" target="e2"/></arc>
  <arc id="a4"><flow source="x1" target="e3"/></arc>
  <arc id="a5"><flow source="e2" target="p1"/></arc>
  <arc id="a6"><flow source="p1" target="e4"/></arc>
  <arc id="a7"><flow source="e3" target="f2"/></arc>
  <arc id="a8"><flow source="f2" target="e5"/></arc>
 </epc>
 <epc epcId="9" name="Settle claim">
  <event id="e1"><name>Start</name></event>
  <function id="f1"><name>Pay out</name></function>
  <event id="e2"><name>Paid</name></event>
  <arc id="a1"><flow source="e1" target="f1"/></arc>
  <arc id="a2"><flow source="f1" target="e2"/></arc>
 </epc>
</epml>
"""


@pytest.fixture
def doc(tmp_path):
    p = tmp_path / "claims.epml"
    p.write_text(DOC, encoding="utf-8")
    return p


def test_reader_is_registered():
    assert READERS["epml"] is read_epml


def test_reads_every_epc_with_lanes_interfaces_and_collapsed_names(doc):
    a, b = read_epml(doc)
    assert (a.id, a.name) == ("EPML-7", "Handle claim") and b.id == "EPML-9"
    assert [l.name for l in a.lanes] == ["Claims desk"]
    assert a.node("f1").lane == "r1" and a.node("f2").lane is None
    assert a.node("e1").name == "Claim received"  # line break collapsed
    assert a.node("p1").kind == "interface" and a.node("p1").ref == "9"
    assert all(n.id != "d1" for n in a.nodes)  # data objects dropped
    assert len(a.edges) == 8


def test_converts_to_the_same_shape_the_json_path_would(doc):
    a, _ = read_epml(doc)
    raw = emit(a, structure(a)).splitlines()
    assert raw[:3] == ["@startuml handle-claim", "title Handle claim", "footer ARIS process EPML-7"]
    lines = [l.strip() for l in raw]  # branch bodies are indented
    assert "|Claims desk|" in lines and ":Register claim;" in lines
    assert "if (Claim valid?) then (Claim valid)" in lines
    assert lines[lines.index(":Settle claim;") - 1] == "' aris: interface 9"


@pytest.mark.parametrize("text, fragment", [
    ("<epml/>", "no <epc> element"),
    ("<epml><epc epcId='1' name='x'><function id='f'><name></name></function></epc></epml>", "has no name"),
    ("<epml><epc epcId='1'", "unclosed token"),
])
def test_bad_documents_are_refused_naming_the_file(tmp_path, text, fragment):
    p = tmp_path / "bad.epml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(ReadError) as exc:
        read_epml(p)
    assert "bad.epml" in str(exc.value) and fragment in str(exc.value)
