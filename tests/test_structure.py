import pytest

from aris2puml.emit import emit
from aris2puml.structure import Decision, Loop, Parallel, StructureError, structure
from tests.conftest import build


def _lines(proc):
    return emit(proc, structure(proc)).splitlines()


def test_loop_becomes_repeat_with_both_outcomes_labelled():
    proc = build(
        [("e0", "event", "Dossier received"), ("f1", "function", "Receive dossier"),
         ("j1", "xor"), ("f2", "function", "Check dossier"), ("s1", "xor"),
         ("eb", "event", "Document missing"), ("eo", "event", "Dossier complete"),
         ("f3", "function", "Approve dossier"), ("ee", "event", "Dossier approved")],
        ["e0>f1", "f1>j1", "j1>f2", "f2>s1", "s1>eb", "eb>j1", "s1>eo", "eo>f3", "f3>ee"],
    )
    s = structure(proc)
    assert isinstance(s.blocks[2], Loop)
    body = _lines(proc)
    assert body[body.index("start"):] == [
        "start", "-> Dossier received;", ":Receive dossier;", "repeat", "  :Check dossier;",
        "repeat while (Document missing?) is (Document missing) not (Dossier complete)",
        ":Approve dossier;", "-> Dossier approved;", "stop", "@enduml",
    ]


def test_three_way_xor_becomes_a_switch_named_after_the_function():
    proc = build(
        [("e0", "event", "Claim received"), ("f1", "function", "Classify claim"), ("x", "xor"),
         ("a", "event", "Minor"), ("b", "event", "Major"), ("c", "event", "Fraud suspected"),
         ("fa", "function", "Settle claim"), ("fb", "function", "Assess claim"),
         ("fc", "function", "Refer claim"), ("ea", "event", "Claim settled"),
         ("eb", "event", "Claim assessed"), ("ec", "event", "Claim referred")],
        ["e0>f1", "f1>x", "x>a", "x>b", "x>c", "a>fa", "b>fb", "c>fc", "fa>ea", "fb>eb", "fc>ec"],
    )
    lines = _lines(proc)
    assert "switch (Classify claim outcome?)" in lines
    assert lines.count("case (Minor)") == 1 and "case (Fraud suspected)" in lines
    assert lines[-2:] == ["endswitch", "@enduml"]


def test_or_connector_is_a_fork_with_a_marker_and_a_warning():
    proc = build(
        [("e0", "event", "Start"), ("o1", "or"), ("f1", "function", "Do a"),
         ("f2", "function", "Do b"), ("o2", "or"), ("f3", "function", "Finish"), ("ee", "event", "Done")],
        ["e0>o1", "o1>f1", "o1>f2", "f1>o2", "f2>o2", "o2>f3", "f3>ee"],
    )
    s = structure(proc)
    assert isinstance(s.blocks[1], Parallel) and s.blocks[1].connector.kind == "or"
    assert s.warnings == ["o1: OR connector has no activity-diagram equivalent; emitted as fork"]
    lines = emit(proc, s).splitlines()
    assert lines[lines.index("fork") - 1].startswith("' epc: OR-split o1")


def test_a_flow_that_dangles_on_a_function_gets_no_stop():
    proc = build([("e0", "event", "Start"), ("f1", "function", "Do it")], ["e0>f1"])
    lines = _lines(proc)
    assert "stop" not in lines  # pumllint ACT002 will report it — by design


def test_implicit_merge_on_a_function_is_accepted():
    proc = build(
        [("e0", "event", "S"), ("x", "xor"), ("a", "event", "A"), ("b", "event", "B"),
         ("fa", "function", "Only on a"), ("m", "function", "Merge here"), ("ee", "event", "E")],
        ["e0>x", "x>a", "x>b", "a>fa", "fa>m", "b>m", "m>ee"],
    )
    s = structure(proc)
    assert isinstance(s.blocks[1], Decision)
    lines = _lines(proc)
    assert lines[lines.index("endif") + 1:] == [":Merge here;", "-> E;", "stop", "@enduml"]


@pytest.mark.parametrize(
    "nodes, edges, fragment",
    [
        # XOR split joined by an AND
        ([("e0", "event", "S"), ("x", "xor"), ("a", "function", "A"), ("b", "function", "B"),
          ("j", "and"), ("ee", "event", "E")],
         ["e0>x", "x>a", "x>b", "a>j", "b>j", "j>ee"], "split x (xor) joins at j (and)"),
        # two start events
        ([("e0", "event", "S1"), ("e1", "event", "S2"), ("j", "xor"), ("f", "function", "F")],
         ["e0>j", "e1>j", "j>f"], "2 start nodes"),
        # loop closing from a function, not an XOR split
        ([("e0", "event", "S"), ("j", "xor"), ("f", "function", "F")],
         ["e0>j", "j>f", "f>j"], "loops must leave from an XOR split"),
        # a function with two successors (a split without a connector)
        ([("e0", "event", "S"), ("f", "function", "F"), ("a", "function", "A"), ("b", "function", "B")],
         ["e0>f", "f>a", "f>b"], "has 2 successors"),
        # join entered from a branch of a *different* split (overlapping regions)
        ([("e0", "event", "S"), ("x1", "xor"), ("p", "event", "P"), ("q", "event", "Q"),
          ("x2", "xor"), ("r", "event", "R"), ("t", "event", "T"),
          ("j1", "xor"), ("j2", "xor"), ("fa", "function", "A"), ("fb", "function", "B"),
          ("ee", "event", "E")],
         ["e0>x1", "x1>p", "x1>q", "p>x2", "x2>r", "x2>t", "r>j1", "q>j1", "t>j2", "j1>fa",
          "fa>j2", "j2>fb", "fb>ee"], "reached without passing through its split"),
    ],
)
def test_unstructured_shapes_are_refused_naming_the_connector(nodes, edges, fragment):
    proc = build(nodes, edges)
    with pytest.raises(StructureError) as exc:
        structure(proc)
    assert fragment in str(exc.value)
