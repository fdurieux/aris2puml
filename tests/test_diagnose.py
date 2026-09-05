"""Roadmap B5: where it refused, drawn.

An activity diagram cannot show a refusal — the refusal is the finding
that there is no block structure — so the diagnostic draws the EPC itself
as a graph, the node(s) the refusal names in red, the reason as a note.
"""

import pytest

from aris2puml.diagnose import diagnose
from aris2puml.structure import StructureError, structure
from tests.conftest import build


def _unstructured():
    """The corpus shape behind `mortgage-application.json`: a join fed by
    outcomes of two different splits."""
    return build(
        [("e0", "event", "S"), ("x1", "xor"), ("p", "event", "P"), ("q", "event", "Q"),
         ("x2", "xor"), ("r", "event", "R"), ("t", "event", "T"),
         ("j1", "xor"), ("j2", "xor"), ("fa", "function", "A"), ("fb", "function", "B"),
         ("ee", "event", "E")],
        ["e0>x1", "x1>p", "x1>q", "p>x2", "x2>r", "x2>t", "r>j1", "q>j1", "t>j2", "j1>fa",
         "fa>j2", "j2>fb", "fb>ee"],
    )


def _refusal(proc, strict=False):
    with pytest.raises(StructureError) as exc:
        structure(proc, strict)
    return exc.value


def test_the_diagnostic_draws_every_node_and_arc_and_marks_the_join():
    proc = _unstructured()
    exc = _refusal(proc)
    text = diagnose(proc, exc, "unstructured")
    lines = text.splitlines()
    assert lines[0] == "@startuml unstructured-refused"
    assert "!pragma layout smetana" in lines               # renders without Graphviz
    assert lines.count("-->") == 0 and sum(" --> " in l for l in lines) == len(proc.edges)
    assert sum(l.startswith(("usecase ", "rectangle ", "storage ")) for l in lines) == len(proc.nodes)
    assert 'storage "XOR\\nj1" as n8 #red' in lines          # the join the message names, and only it
    assert sum(l.endswith("#red") for l in lines) == 1
    i = lines.index("note right of n8 #ffdddd")
    assert lines[i + 1] == "  refused: join j1 reached without passing through its split (unstructured)"
    assert lines[-2] == "footer ARIS process P-1 — aris2puml --diagnose" and lines[-1] == "@enduml"


def test_events_are_ellipses_functions_boxes_and_interfaces_name_their_target():
    proc = build(
        [("e0", "event", "Order received"), ("f", "function", "Check order"),
         ("i", "interface", "Billing", None, "PROC-BILL"), ("x", "xor")],
        ["e0>f", "f>i", "i>x", "x>x"],
    )
    text = diagnose(proc, _refusal(proc), "order")
    assert 'usecase "Order received" as n1' in text
    assert 'rectangle "Check order" as n2' in text
    assert 'rectangle "Billing\\n→ PROC-BILL" as n3' in text


@pytest.mark.parametrize("nodes, edges, expected", [
    # unstructured join: the join
    (None, None, ("j1",)),
    # kind mismatch: the split and the join
    ([("e0", "event", "S"), ("x", "xor"), ("a", "function", "A"), ("b", "function", "B"),
      ("j", "and"), ("ee", "event", "E")],
     ["e0>x", "x>a", "x>b", "a>j", "b>j", "j>ee"], ("x", "j")),
    # a back edge with no XOR to leave from: both its ends
    ([("e0", "event", "S"), ("j", "xor"), ("f", "function", "F"), ("a", "and"), ("ee", "event", "E")],
     ["e0>j", "j>f", "f>a", "a>j", "a>ee"], ("a", "j")),
])
def test_the_error_names_its_nodes(nodes, edges, expected):
    proc = _unstructured() if nodes is None else build(nodes, edges)
    assert _refusal(proc).nodes == expected


def test_a_strict_refusal_marks_the_approximated_node():
    proc = build(
        [("e0", "event", "Start"), ("o1", "or"), ("f1", "function", "Do a"),
         ("f2", "function", "Do b"), ("o2", "or"), ("f3", "function", "Finish"), ("ee", "event", "Done")],
        ["e0>o1", "o1>f1", "o1>f2", "f1>o2", "f2>o2", "o2>f3", "f3>ee"],
    )
    assert _refusal(proc, strict=True).nodes == ("o1",)


def test_a_double_quote_in_a_name_cannot_break_the_label():
    proc = build([("e0", "event", 'Say "hi"'), ("f", "function", "F"), ("x", "xor")],
                 ["e0>f", "f>x", "x>x"])
    text = diagnose(proc, _refusal(proc), "hi")
    assert "usecase \"Say 'hi'\" as n1" in text and '"hi"' not in text
