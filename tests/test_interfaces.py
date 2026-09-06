"""Roadmap B4: process interfaces as cross-process references.

The ``' aris: interface`` marker is a comment, which pumllint's parser
drops, so the id an interface links to also rides in the footer — one of
the carriers GEN007 and ``pumllint trace`` read — and ``--manifest`` writes
the converted processes with those ids as the inventory ``trace`` needs.
"""

import json
from pathlib import Path

from aris2puml.emit import emit
from aris2puml.report import Report
from aris2puml.structure import structure
from tests.conftest import build


def _footer(proc) -> str:
    return emit(proc, structure(proc)).splitlines()[2]


def test_the_footer_carries_every_linked_process_once_in_node_order():
    proc = build(
        [("e0", "event", "Received"), ("p1", "interface", "Check credit", None, "PROC-0051"),
         ("f", "function", "Book loan"), ("p2", "interface", "Notify sales", None, "PROC-0007"),
         ("p3", "interface", "Check credit again", None, "PROC-0051"), ("e1", "event", "Booked")],
        ["e0>p1", "p1>f", "f>p2", "p2>p3", "p3>e1"],
    )
    assert proc.interface_refs() == ["PROC-0051", "PROC-0007"]
    assert _footer(proc) == "footer owner: QA — ARIS process P-1 — interfaces: PROC-0051, PROC-0007"


def test_an_interface_with_no_link_and_a_process_with_none_leave_the_footer_alone():
    unlinked = build(
        [("e0", "event", "Received"), ("p1", "interface", "Elsewhere"), ("e1", "event", "Done")],
        ["e0>p1", "p1>e1"],
    )
    plain = build(
        [("e0", "event", "Received"), ("f", "function", "Do it"), ("e1", "event", "Done")],
        ["e0>f", "f>e1"],
    )
    for proc in (unlinked, plain):
        assert proc.interface_refs() == []
        assert _footer(proc) == "footer owner: QA — ARIS process P-1"


def test_the_manifest_is_the_converted_processes_with_their_links():
    r = Report()
    r.converted(Path("a.json"), "PROC-0042", "Order to cash", Path("out/order-to-cash.puml"), [],
                ["PROC-0051"])
    r.refused(Path("b.json"), "join j reached without passing through its split", "PROC-0051",
              "Handle enquiry")
    r.converted(Path("c.json"), "PROC-0007", "Notify", None, [])
    assert r.manifest() == [
        {"id": "PROC-0042", "name": "Order to cash", "output": "out/order-to-cash.puml",
         "interfaces": ["PROC-0051"]},
        {"id": "PROC-0007", "name": "Notify", "output": None, "interfaces": []},
    ]
    # the sidecar carries the same ids on the converted record, and nothing on a refusal
    docs = r.as_dict()["processes"]
    assert docs[0]["interfaces"] == ["PROC-0051"] and "interfaces" not in docs[1]


def test_the_manifest_file_is_a_json_array_trace_can_read(tmp_path):
    r = Report()
    r.converted(Path("a.json"), "PROC-0042", "Order to cash", None, [], ["PROC-0051"])
    out = tmp_path / "m.json"
    r.write_manifest(out)
    assert json.loads(out.read_text(encoding="utf-8")) == r.manifest()
    assert out.read_bytes().endswith(b"\n") and b"\r" not in out.read_bytes()
