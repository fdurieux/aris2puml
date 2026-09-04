"""Roadmap A2: several start events.

Joined before the first function they form an *entry region* (nested
if/switch/fork blocks whose outcomes are the start events); a start that
enters the flow at a join fed from inside the process is a *mid-flow
trigger*, folded into the arrow label there. Every shape here is a
hand-written reproduction of one seen in the public corpus, not a copy.
"""

import pytest

from aris2puml.emit import emit
from aris2puml.structure import Decision, Parallel, StructureError, Trigger, structure
from tests.conftest import build


def _lines(proc):
    raw = emit(proc, structure(proc)).splitlines()
    return raw[raw.index("start"):]


def test_two_starts_joined_by_xor_become_an_empty_if_else():
    proc = build(
        [("e1", "event", "Order received"), ("e2", "event", "Order changed"), ("j", "xor"),
         ("f", "function", "Check order"), ("ee", "event", "Order checked")],
        ["e1>j", "e2>j", "j>f", "f>ee"],
    )
    assert _lines(proc) == [
        "start", "if (Trigger?) then (Order received)", "else (Order changed)", "endif",
        ":Check order;", "-> Order checked;", "stop", "@enduml",
    ]


def test_three_starts_become_a_switch():
    proc = build(
        [("a", "event", "A"), ("b", "event", "B"), ("c", "event", "C"), ("j", "xor"),
         ("f", "function", "Do it"), ("ee", "event", "Done")],
        ["a>j", "b>j", "c>j", "j>f", "f>ee"],
    )
    lines = _lines(proc)
    assert lines[1:6] == ["switch (Trigger?)", "case (A)", "case (B)", "case (C)", "endswitch"]


def test_and_joined_starts_become_a_fork_of_arrow_labels():
    proc = build(
        [("a", "event", "Goods arrived"), ("b", "event", "Invoice arrived"), ("j", "and"),
         ("f", "function", "Post receipt"), ("ee", "event", "Posted")],
        ["a>j", "b>j", "j>f", "f>ee"],
    )
    assert _lines(proc)[:6] == [
        "start", "fork", "  -> Goods arrived;", "fork again", "  -> Invoice arrived;", "end fork",
    ]


def test_starts_with_functions_before_the_join_keep_their_bodies():
    proc = build(
        [("a", "event", "Web order"), ("fa", "function", "Import order"),
         ("b", "event", "Phone order"), ("fb", "function", "Type order"),
         ("j", "xor"), ("f", "function", "Check order"), ("ee", "event", "Checked")],
        ["a>fa", "fa>j", "b>fb", "fb>j", "j>f", "f>ee"],
    )
    assert _lines(proc)[1:6] == [
        "if (Trigger?) then (Web order)", "  :Import order;", "else (Phone order)", "  :Type order;", "endif",
    ]


def test_xor_chain_is_flattened_into_one_switch():
    proc = build(
        [("a", "event", "A"), ("b", "event", "B"), ("j1", "xor"), ("c", "event", "C"), ("j2", "xor"),
         ("f", "function", "Do it"), ("ee", "event", "Done")],
        ["a>j1", "b>j1", "j1>j2", "c>j2", "j2>f", "f>ee"],
    )
    lines = _lines(proc)
    assert lines[1:6] == ["switch (Trigger?)", "case (A)", "case (B)", "case (C)", "endswitch"]


def test_xor_group_inside_and_join_gets_a_derived_label():
    proc = build(
        [("a", "event", "A"), ("b", "event", "B"), ("j1", "xor"), ("c", "event", "C"), ("j2", "and"),
         ("f", "function", "Do it"), ("ee", "event", "Done")],
        ["a>j1", "b>j1", "j1>j2", "c>j2", "j2>f", "f>ee"],
    )
    s = structure(proc)
    assert isinstance(s.blocks[0], Parallel) and s.blocks[0].connector.id == "$start"
    lines = _lines(proc)
    assert lines[1:8] == [
        "fork", "  if (Trigger?) then (A)", "  else (B)", "  endif", "fork again", "  -> C;", "end fork",
    ]


def test_and_group_inside_xor_join_gets_the_and_label():
    proc = build(
        [("a", "event", "A"), ("b", "event", "B"), ("j1", "and"), ("c", "event", "C"), ("j2", "xor"),
         ("f", "function", "Do it"), ("ee", "event", "Done")],
        ["a>j1", "b>j1", "j1>j2", "c>j2", "j2>f", "f>ee"],
    )
    lines = _lines(proc)
    assert lines[1] == "if (Trigger?) then (A and B)"
    assert lines[2:7] == ["  fork", "    -> A;", "  fork again", "    -> B;", "  end fork"]
    assert lines[7] == "else (C)"


def test_starts_that_never_meet_each_run_to_their_own_stop():
    proc = build(
        [("a", "event", "A"), ("fa", "function", "Do a"), ("ea", "event", "A done"),
         ("b", "event", "B"), ("fb", "function", "Do b"), ("eb", "event", "B done")],
        ["a>fa", "fa>ea", "b>fb", "fb>eb"],
    )
    assert _lines(proc) == [
        "start", "if (Trigger?) then (A)", "  :Do a;", "  -> A done;", "  stop",
        "else (B)", "  :Do b;", "  -> B done;", "  stop", "endif", "@enduml",
    ]


def test_mid_flow_trigger_at_an_and_join_is_folded_with_a_warning():
    # 10.json in the SAP set: a branch's event and an external "Budget to be
    # updated" both feed the AND join before "Update".
    proc = build(
        [("e0", "event", "Order created"), ("x", "or"),
         ("f1", "function", "Procure"), ("e1", "event", "Procured"), ("j", "and"),
         ("f2", "function", "Update budget"), ("e2", "event", "Budget updated"),
         ("t", "event", "Budget to be updated"),
         ("f3", "function", "Analyse"), ("e3", "event", "Analysed")],
        ["e0>x", "x>f1", "f1>e1", "e1>j", "t>j", "j>f2", "f2>e2", "x>f3", "f3>e3"],
    )
    s = structure(proc)
    assert any(isinstance(b, Trigger) for body in s.blocks[1].branches for b in body)
    assert "j: external trigger joins mid-process (and): Budget to be updated" in s.warnings
    lines = _lines(proc)
    i = lines.index("  ' epc: external trigger at j (and)")
    assert lines[i - 1] == "  :Procure;"
    assert lines[i + 1] == "  -> Procured and Budget to be updated;"  # one arrow, merged
    assert lines[i + 2] == "  :Update budget;"


def test_mid_flow_trigger_at_an_xor_join_uses_or():
    # fed from inside: the join sits on a branch of the AND split
    proc = build(
        [("e0", "event", "S"), ("x", "and"), ("f1", "function", "Prepare"), ("e1", "event", "Prepared"),
         ("j", "xor"), ("t", "event", "Rush request"), ("f2", "function", "Dispatch"),
         ("e2", "event", "Dispatched"), ("f3", "function", "Bill"), ("e3", "event", "Billed")],
        ["e0>x", "x>f1", "f1>e1", "e1>j", "t>j", "j>f2", "f2>e2", "x>f3", "f3>e3"],
    )
    lines = [l.strip() for l in _lines(proc)]
    assert "-> Prepared or Rush request;" in lines
    assert "' epc: external trigger at j (xor)" in lines


def test_a_start_tree_feeding_a_mid_flow_join_is_labelled_by_its_joins():
    proc = build(
        [("e0", "event", "S"), ("x", "and"), ("f1", "function", "Prepare"), ("e1", "event", "Prepared"),
         ("j", "and"), ("t1", "event", "T1"), ("t2", "event", "T2"), ("tj", "xor"),
         ("f2", "function", "Finish"), ("e2", "event", "Finished"),
         ("f3", "function", "Bill"), ("e3", "event", "Billed")],
        ["e0>x", "x>f1", "f1>e1", "e1>j", "t1>tj", "t2>tj", "tj>j", "j>f2", "f2>e2", "x>f3", "f3>e3"],
    )
    assert "-> Prepared and T1 or T2;" in [l.strip() for l in _lines(proc)]


def test_trigger_at_a_splits_own_join_is_folded_after_the_block():
    proc = build(
        [("e0", "event", "S1"), ("e1", "event", "S2"), ("x", "xor"), ("a", "function", "A"),
         ("ea", "event", "A done"), ("eb", "event", "Skipped"), ("j", "xor"), ("f", "function", "F"),
         ("ee", "event", "Done")],
        ["e0>x", "x>ea", "ea>a", "a>j", "x>eb", "eb>j", "e1>j", "j>f", "f>ee"],
    )
    lines = _lines(proc)
    i = lines.index("' epc: external trigger at j (xor)")
    assert lines[i - 1] == "endif" and lines[i + 1] == "-> S2;" and lines[i + 2] == ":F;"


def test_an_alternative_entry_with_its_own_function_is_an_entry_not_a_trigger():
    proc = build(
        [("e0", "event", "Web order"), ("f0", "function", "Import order"),
         ("e1", "event", "Phone order"), ("j", "xor"), ("f", "function", "Check order"),
         ("ee", "event", "Checked")],
        ["e0>f0", "f0>j", "e1>j", "j>f", "f>ee"],
    )
    assert _lines(proc)[1:5] == [
        "if (Trigger?) then (Web order)", "  :Import order;", "else (Phone order)", "endif",
    ]


def test_every_start_being_a_trigger_is_refused():
    proc = build(
        [("e0", "event", "S1"), ("e1", "event", "S2"), ("j", "xor"), ("k", "xor"), ("f", "function", "F")],
        ["e0>j", "e1>j", "j>k", "k>j", "k>f"],
    )
    with pytest.raises(StructureError) as exc:
        structure(proc)
    assert "every start event is a mid-process trigger" in str(exc.value)


def test_bare_case_is_emitted_as_empty_parentheses():
    proc = build(
        [("e0", "event", "S"), ("f", "function", "Classify"), ("x", "xor"),
         ("a", "event", "Minor"), ("fa", "function", "Settle"), ("fb", "function", "Escalate"),
         ("fc", "function", "Reject"), ("ea", "event", "Ea"), ("eb", "event", "Eb"), ("ec", "event", "Ec")],
        ["e0>f", "f>x", "x>a", "a>fa", "x>fb", "x>fc", "fa>ea", "fb>eb", "fc>ec"],
    )
    lines = _lines(proc)
    assert "case (Minor)" in lines and lines.count("case ()") == 2
