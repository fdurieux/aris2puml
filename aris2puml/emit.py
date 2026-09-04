"""Blocks → PlantUML activity-diagram text.

Follows the mapping table in pumllint's docs/business-processes.md §2:
functions are single-line actions, org units are swimlanes, events ride
on arrow labels and XOR branch labels, AND/OR is a fork, the process
interface is an action preceded by an ``' aris: interface`` marker, and
the governance tags live in the footer.
"""

from __future__ import annotations

import re

from aris2puml.model import Process
from aris2puml.structure import (
    JOINWORD, Action, Branch, Decision, EventArrow, Loop, Parallel, Stop, Structured, Trigger,
    While,
)


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "process"


class _Emitter:
    def __init__(self, proc: Process):
        self.p = proc
        self.lines: list[str] = []
        self.lane: str | None = None

    def out(self, depth: int, text: str) -> None:
        self.lines.append("  " * depth + text)

    def _lane(self, depth: int, lane_id: str | None) -> None:
        if lane_id is None:
            return
        name = self.p.lane_name(lane_id)
        if name != self.lane:
            self.out(depth, f"|{name}|")
            self.lane = name

    @staticmethod
    def _first_action(blocks: list):
        for b in blocks:
            if isinstance(b, Action):
                return b
            if isinstance(b, Decision):
                for br in b.branches:
                    a = _Emitter._first_action(br.body)
                    if a:
                        return a
            if isinstance(b, Parallel):
                for body in b.branches:
                    a = _Emitter._first_action(body)
                    if a:
                        return a
            if isinstance(b, (Loop, While)):
                a = _Emitter._first_action(b.body)
                if a:
                    return a
        return None

    def blocks(self, blocks: list, depth: int) -> None:
        for b in blocks:
            if isinstance(b, Action):
                if b.node.kind == "interface":
                    self.out(depth, f"' aris: interface {b.node.ref or '?'}")
                self._lane(depth, b.node.lane)
                self.out(depth, f":{b.node.name};")
            elif isinstance(b, EventArrow):
                self.out(depth, f"-> {b.node.name};")
            elif isinstance(b, Stop):
                if b.event is not None:
                    self.out(depth, f"-> {b.event.name};")
                self.out(depth, "stop")
            elif isinstance(b, Decision):
                self.decision(b, depth)
            elif isinstance(b, Parallel):
                self.parallel(b, depth)
            elif isinstance(b, Loop):
                self.loop(b, depth)
            elif isinstance(b, While):
                self.while_(b, depth)
            elif isinstance(b, Trigger):
                self.trigger(b, depth)
            else:  # pragma: no cover
                raise TypeError(type(b))

    def trigger(self, t: Trigger, depth: int) -> None:
        # An external start event entering the flow here. Two arrow labels
        # in a row would leave only the second visible, so merge with a
        # preceding event label into one arrow.
        label = t.label
        prev = self.lines[-1].strip() if self.lines else ""
        if prev.startswith("-> ") and prev.endswith(";"):
            self.lines.pop()
            label = prev[3:-1] + JOINWORD[t.join.kind] + label
        self.out(depth, f"' epc: external trigger at {t.join.id} ({t.join.kind})")
        self.out(depth, f"-> {label};")

    @staticmethod
    def _label(label: str | None) -> str:
        return f" ({label})" if label else ""

    def decision(self, d: Decision, depth: int) -> None:
        if len(d.branches) == 2:
            a, b = d.branches
            self.out(depth, f"if ({d.condition}) then{self._label(a.label)}")
            self.lane = None
            self.blocks(a.body, depth + 1)
            self.out(depth, f"else{self._label(b.label)}")
            self.lane = None
            self.blocks(b.body, depth + 1)
            self.out(depth, "endif")
        else:
            self.out(depth, f"switch ({d.condition})")
            for br in d.branches:
                # a bare `case` is a PlantUML syntax error; `case ()` renders
                # (and shows the missing outcome event, as ACT003 does for if)
                self.out(depth, f"case ({br.label or ''})")
                self.lane = None
                self.blocks(br.body, depth + 1)
            self.out(depth, "endswitch")
        self.lane = None

    def parallel(self, p: Parallel, depth: int) -> None:
        if p.connector.kind == "or":
            self.out(depth, f"' epc: OR-split {p.connector.id} — no activity-diagram equivalent, remodel")
        self.out(depth, "fork")
        for i, body in enumerate(p.branches):
            if i:
                self.out(depth, "fork again")
            self.lane = None
            self.blocks(body, depth + 1)
        self.out(depth, "end fork")
        self.lane = None

    def loop(self, lp: Loop, depth: int) -> None:
        self.out(depth, "repeat")
        self.lane = None
        self.blocks(lp.body, depth + 1)
        if lp.backward is not None:
            # One action, no swimlane and no arrow label: `backward` takes
            # nothing else. structure.py warns about what that costs.
            self.out(depth, f"backward :{lp.backward.name};")
            self.lane = None
        tail = f"repeat while ({lp.condition})"
        if lp.back_label or lp.exit_label:
            tail += f" is{self._label(lp.back_label)} not{self._label(lp.exit_label)}"
        self.out(depth, tail)
        self.lane = None
        end = getattr(lp, "body_end", None)
        if end is not None:
            self.blocks([end], depth)

    def while_(self, w: While, depth: int) -> None:
        head = f"while ({w.condition})"
        if w.back_label:
            head += f" is{self._label(w.back_label)}"
        self.out(depth, head)
        self.lane = None
        self.blocks(w.body, depth + 1)
        self.out(depth, f"endwhile{self._label(w.exit_label)}")
        self.lane = None
        end = getattr(w, "body_end", None)
        if end is not None:
            self.blocks([end], depth)

    def render(self, s: Structured) -> str:
        p = self.p
        self.out(0, f"@startuml {slug(p.name)}")
        self.out(0, f"title {p.name}")
        parts = ([f"owner: {p.owner}"] if p.owner else []) + [f"ARIS process {p.id}"]
        self.out(0, "footer " + " — ".join(parts))
        self.out(0, "")
        first = self._first_action(s.blocks)
        if first is not None:
            self._lane(0, first.node.lane)
        self.out(0, "start")
        self.blocks(s.blocks, 0)
        self.out(0, "@enduml")
        return "\n".join(self.lines) + "\n"


def emit(proc: Process, structured: Structured) -> str:
    return _Emitter(proc).render(structured)
