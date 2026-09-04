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
