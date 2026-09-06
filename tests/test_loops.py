"""Roadmap B1: loop shapes beyond the one v0.1.0 accepted.

The shape added here is the *test-at-top* loop: one XOR both merges the
retry and decides whether to take it, so everything on the way round is
the loop body and PlantUML's ``while``/``endwhile`` says it exactly.

Every shape below is a hand-written reproduction of one seen in the
public corpus, not a copy. The one it is drawn from is
``mortgage-application-variant.json``: check the application, and while
it comes back invalid, contact the customer and check it again.
"""

import pytest

from aris2puml.emit import emit
from aris2puml.structure import StructureError, While, structure
from tests.conftest import build


def _lines(proc):
    raw = emit(proc, structure(proc)).splitlines()
    return [l.strip() for l in raw[raw.index("start"):]]


def _rework():
    """The corpus shape: header `x` merges the retry and decides on it."""
    return build(
        [("e0", "event", "Application received"),
         ("f1", "function", "Check application"),
         ("x", "xor"),
         ("e2", "event", "Application invalid"),
         ("f3", "function", "Contact customer"),
         ("e4", "event", "Application resubmitted"),
         ("f5", "function", "Check application"),
         ("e6", "event", "Application valid"),
         ("f7", "function", "Register application"),
         ("e8", "event", "Application registered")],
        ["e0>f1", "f1>x", "x>e2", "e2>f3", "f3>e4", "e4>f5", "f5>x",
         "x>e6", "e6>f7", "f7>e8"],
    )


def test_test_at_top_loop_becomes_while_endwhile():
    assert _lines(_rework()) == [
        "start",
        "-> Application received;",
        ":Check application;",
        "while (Application invalid?) is (Application invalid)",
        ":Contact customer;",
        "-> Application resubmitted;",
        ":Check application;",
        "endwhile (Application valid)",
        ":Register application;",
        "-> Application registered;",
        "stop",
        "@enduml",
    ]


def test_the_loop_is_a_while_block_not_a_repeat():
    (block,) = [b for b in structure(_rework()).blocks if isinstance(b, While)]
    assert block.back_label == "Application invalid"
    assert block.exit_label == "Application valid"
    assert [type(b).__name__ for b in block.body] == ["Action", "EventArrow", "Action"]


def test_the_body_keeps_its_own_swimlanes():
    proc = build(
        [("e0", "event", "Application received"),
         ("f1", "function", "Check application", "desk"),
         ("x", "xor"),
         ("e2", "event", "Application invalid"),
         ("f3", "function", "Contact customer", "sales"),
         ("f5", "function", "Check application", "desk"),
         ("e6", "event", "Application valid"),
         ("f7", "function", "Register application", "desk"),
         ("e8", "event", "Application registered")],
        ["e0>f1", "f1>x", "x>e2", "e2>f3", "f3>f5", "f5>x", "x>e6", "e6>f7", "f7>e8"],
        lanes=[("desk", "Application desk"), ("sales", "Sales")],
    )
    lines = _lines(proc)
    assert "|Sales|" in lines and lines.count("|Application desk|") >= 2


def test_a_looping_outcome_with_no_event_gets_a_bare_while():
    """An outcome with no event is a defect ACT003 reports; it is not repaired."""
    proc = build(
        [("e0", "event", "Started"), ("f1", "function", "Try it"), ("x", "xor"),
         ("f3", "function", "Fix it"), ("e6", "event", "Worked"),
         ("f7", "function", "Finish it"), ("e8", "event", "Done")],
        ["e0>f1", "f1>x", "x>f3", "f3>x", "x>e6", "e6>f7", "f7>e8"],
    )
    lines = _lines(proc)
    # No event on the looping outcome, so the condition falls back to the exit
    # event — the same fallback `repeat` uses. ACT003 reports the missing one.
    assert "while (Worked?)" in lines
    assert "endwhile (Worked)" in lines


def test_a_loop_whose_exit_ends_the_flow_still_stops():
    proc = build(
        [("e0", "event", "Started"), ("f1", "function", "Try it"), ("x", "xor"),
         ("e2", "event", "Not yet"), ("f3", "function", "Wait for it"),
         ("e6", "event", "Gave up")],
        ["e0>f1", "f1>x", "x>e2", "e2>f3", "f3>x", "x>e6"],
    )
    # The exit event is named twice on purpose: once as the outcome label
    # `endwhile` carries, once as the end event the mapping table asks for.
    assert _lines(proc)[-4:] == ["endwhile (Gave up)", "-> Gave up;", "stop", "@enduml"]


def test_a_header_with_three_outcomes_is_refused_naming_it():
    proc = build(
        [("e0", "event", "Started"), ("f1", "function", "Try it"), ("x", "xor"),
         ("e2", "event", "Retry"), ("f3", "function", "Fix it"),
         ("e5", "event", "Done"), ("e6", "event", "Abandoned")],
        ["e0>f1", "f1>x", "x>e2", "e2>f3", "f3>x", "x>e5", "x>e6"],
    )
    with pytest.raises(StructureError, match="loop header x must have exactly 2 outcomes"):
        structure(proc)


def test_two_back_edges_into_one_header_are_refused():
    proc = build(
        [("e0", "event", "Started"), ("f1", "function", "Try it"), ("x", "xor"),
         ("e2", "event", "Retry"), ("f3", "function", "Fix it"),
         ("f4", "function", "Fix it again"), ("e6", "event", "Done")],
        ["e0>f1", "f1>x", "x>e2", "e2>f3", "f3>x", "f3>f4", "f4>x", "x>e6"],
    )
    with pytest.raises(StructureError, match="closes two loops"):
        structure(proc)


# --- work on the return path: `backward` -------------------------------------

def _rework_with_return_work(lanes=()):
    """The corpus shape behind `mortgage-application.json`: the split's
    outcome runs a function and an event before rejoining the header."""
    return build(
        [("e0", "event", "Loan application received"),
         ("h", "xor"),
         ("f1", "function", "Check loan application", *(("desk",) if lanes else ())),
         ("x", "xor"),
         ("e2", "event", "Customer information invalid"),
         ("f3", "function", "Contact customer", *(("sales",) if lanes else ())),
         ("e4", "event", "Loan application received"),
         ("e5", "event", "Customer information valid"),
         ("f6", "function", "Register customer information"),
         ("e7", "event", "Loan application registered")],
        ["e0>h", "h>f1", "f1>x", "x>e2", "e2>f3", "f3>e4", "e4>h",
         "x>e5", "e5>f6", "f6>e7"],
        lanes=lanes,
    )


def test_one_function_on_the_return_path_becomes_backward():
    assert _lines(_rework_with_return_work()) == [
        "start",
        "-> Loan application received;",
        "repeat",
        ":Check loan application;",
        "backward :Contact customer;",
        "repeat while (Customer information invalid?) is (Customer information invalid)"
        " not (Customer information valid)",
        ":Register customer information;",
        "-> Loan application registered;",
        "stop",
        "@enduml",
    ]


def test_events_on_the_return_path_are_dropped_with_a_warning():
    """`backward` takes one action and no arrow, so the event on the way
    round has nowhere to go. Dropped, and said out loud."""
    s = structure(_rework_with_return_work())
    assert s.warnings == [
        "x: `backward` carries one action and no arrow, so the return path's "
        "event(s) are dropped: Loan application received"
    ]


def test_a_swimlane_on_the_backward_function_is_dropped_with_a_warning():
    s = structure(_rework_with_return_work(lanes=[("desk", "Desk"), ("sales", "Sales")]))
    assert any("takes no swimlane" in w for w in s.warnings)
    assert "|Sales|" not in _lines(_rework_with_return_work(
        lanes=[("desk", "Desk"), ("sales", "Sales")]))


def test_two_functions_on_the_return_path_are_refused():
    """`backward` holds one action; two have no faithful form."""
    proc = build(
        [("e0", "event", "S"), ("h", "xor"), ("f1", "function", "Try it"), ("x", "xor"),
         ("e2", "event", "Again"), ("f3", "function", "Fix it"), ("f4", "function", "Log it"),
         ("e5", "event", "Done"), ("f6", "function", "Finish it"), ("e7", "event", "Finished")],
        ["e0>h", "h>f1", "f1>x", "x>e2", "e2>f3", "f3>f4", "f4>h",
         "x>e5", "e5>f6", "f6>e7"],
    )
    with pytest.raises(StructureError, match="exactly one function"):
        structure(proc)


def test_a_return_path_with_no_function_is_refused():
    proc = build(
        [("e0", "event", "S"), ("h", "xor"), ("f1", "function", "Try it"), ("x", "xor"),
         ("e2", "event", "Again"), ("e3", "event", "Still going"),
         ("e5", "event", "Done"), ("f6", "function", "Finish it"), ("e7", "event", "Finished")],
        ["e0>h", "h>f1", "f1>x", "x>e2", "e2>e3", "e3>h", "x>e5", "e5>f6", "f6>e7"],
    )
    with pytest.raises(StructureError, match="exactly one function"):
        structure(proc)


def test_a_connector_on_the_return_path_is_refused():
    proc = build(
        [("e0", "event", "S"), ("h", "xor"), ("f1", "function", "Try it"), ("x", "xor"),
         ("e2", "event", "Again"), ("a", "and"), ("f3", "function", "Fix it"),
         ("f4", "function", "Log it"), ("b", "and"),
         ("e5", "event", "Done"), ("f6", "function", "Finish it"), ("e7", "event", "Finished")],
        ["e0>h", "h>f1", "f1>x", "x>e2", "e2>a", "a>f3", "a>f4", "f3>b", "f4>b", "b>h",
         "x>e5", "e5>f6", "f6>e7"],
    )
    with pytest.raises(StructureError, match="exactly one function"):
        structure(proc)


def test_a_loop_whose_exit_has_no_event_gets_is_and_no_not():
    """`repeat while (…) is (E) not` — a bare `not` — is rejected by
    PlantUML. The exit label is missing, so the `not` half is too."""
    proc = build(
        [("e0", "event", "Started"), ("f0", "function", "Open it"), ("j", "xor"),
         ("f1", "function", "Do it"), ("x", "xor"),
         ("e2", "event", "Again"), ("f3", "function", "Finish it"), ("e3", "event", "Done")],
        ["e0>f0", "f0>j", "j>f1", "f1>x", "x>e2", "e2>j", "x>f3", "f3>e3"],
    )
    (tail,) = [l for l in _lines(proc) if l.startswith("repeat while")]
    assert tail == "repeat while (Again?) is (Again)"


def test_a_loop_whose_back_edge_has_no_event_gets_not_and_no_is():
    """`is not (X)` is accepted by PlantUML and mis-parsed: the condition
    swallows the text. The back label is missing, so the `is` half is too."""
    proc = build(
        [("e0", "event", "Started"), ("f0", "function", "Open it"), ("j", "xor"),
         ("f1", "function", "Do it"), ("x", "xor"), ("e3", "event", "Done")],
        ["e0>f0", "f0>j", "j>f1", "f1>x", "x>j", "x>e3"],
    )
    (tail,) = [l for l in _lines(proc) if l.startswith("repeat while")]
    assert tail == "repeat while (Done?) not (Done)"


def test_no_loop_tail_ends_on_a_dangling_keyword():
    for proc in (_rework_with_return_work(),):
        for l in _lines(proc):
            if l.startswith("repeat while"):
                assert not l.endswith((" is", " not"))


def test_the_repeat_shape_still_emits_repeat():
    """v0.1.0's loop: the split is below the header, not the header itself."""
    proc = build(
        [("e0", "event", "Started"), ("f0", "function", "Open it"), ("j", "xor"),
         ("f1", "function", "Do it"), ("x", "xor"),
         ("e2", "event", "Again"), ("e3", "event", "Done")],
        ["e0>f0", "f0>j", "j>f1", "f1>x", "x>e2", "e2>j", "x>e3"],
    )
    lines = _lines(proc)
    assert lines[lines.index(":Do it;") - 1] == "repeat"
    assert "repeat while (Again?) is (Again) not (Done)" in lines
