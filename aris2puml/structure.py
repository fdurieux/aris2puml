"""Process graph → nested single-entry/single-exit blocks.

An EPC is a graph; a PlantUML activity diagram is block-structured. This
module finds the structure when it is there and refuses, naming the
connector, when it is not — it never invents structure the EPC lacks.

Supported shapes:

* function / interface / event chains — only an end event terminates a
  flow; a flow that dangles on a function gets no ``stop`` so that
  pumllint's ACT002 reports the missing end event;
* XOR split → labelled branches → matching XOR join, or branches that each
  run to their own end event (no join);
* AND / OR split → parallel branches → matching join of the same kind;
* one back edge per loop, from an XOR split (directly, or via one event)
  to an XOR join that is the loop header.

Everything else raises :class:`StructureError`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aris2puml.model import Node, Process

CONNECTORS = ("xor", "and", "or")
EXIT = "$exit"


class StructureError(ValueError):
    pass


# -- block types -----------------------------------------------------------

@dataclass
class Action:
    node: Node              # function or interface


@dataclass
class EventArrow:
    node: Node              # an event on the flow, rendered as an arrow label


@dataclass
class Stop:
    event: Node | None      # the end event, if the flow ended on one


@dataclass
class Branch:
    label: str | None       # the XOR outcome event, if any
    body: list


@dataclass
class Decision:
    connector: Node
    condition: str
    branches: list[Branch]


@dataclass
class Parallel:
    connector: Node         # kind "and" or "or"
    branches: list[list]


@dataclass
class Loop:
    header: Node
    body: list
    condition: str
    back_label: str | None
    exit_label: str | None


@dataclass
class Structured:
    blocks: list
    warnings: list[str] = field(default_factory=list)


# -- graph helpers ---------------------------------------------------------

def _post_dominators(proc: Process) -> dict[str, str | None]:
    """Immediate post-dominator of every node, on the graph with a virtual
    exit that every sink flows into. ``None`` for the exit itself."""
    ids = [n.id for n in proc.nodes] + [EXIT]
    succ = {i: list(proc.successors(i)) for i in ids if i != EXIT}
    for i in list(succ):
        if not succ[i]:
            succ[i] = [EXIT]
    succ[EXIT] = []
    full = set(ids)
    pdom: dict[str, set[str]] = {i: (set(full) if i != EXIT else {EXIT}) for i in ids}
    changed = True
    while changed:
        changed = False
        for i in ids:
            if i == EXIT:
                continue
            new = {i}
            common = None
            for s in succ[i]:
                common = set(pdom[s]) if common is None else common & pdom[s]
            new |= common or set()
            if new != pdom[i]:
                pdom[i] = new
                changed = True
    ipdom: dict[str, str | None] = {}
    for i in ids:
        cands = pdom[i] - {i}
        best = None
        for c in cands:
            if all(o == c or o in pdom[c] for o in cands):
                best = c
                break
        ipdom[i] = best
    return ipdom


def _back_edges(proc: Process, starts: list[str]) -> list[tuple[str, str]]:
    colour: dict[str, int] = {}
    back: list[tuple[str, str]] = []

    def dfs(u: str) -> None:
        colour[u] = 1
        for v in proc.successors(u):
            c = colour.get(v, 0)
            if c == 1:
                back.append((u, v))
            elif c == 0:
                dfs(v)
        colour[u] = 2

    for s in starts:
        if colour.get(s, 0) == 0:
            dfs(s)
    return back


# -- the walk ----------------------------------------------------------------

class _Walker:
    def __init__(self, proc: Process):
        self.p = proc
        self.warnings: list[str] = []
        self.starts = [n.id for n in proc.nodes if not proc.predecessors(n.id)]
        if not self.starts:
            raise StructureError("no start node: every node has a predecessor")
        if len(self.starts) > 1:
            names = ", ".join(self.starts)
            raise StructureError(
                f"{len(self.starts)} start nodes ({names}); v1 supports exactly one start event"
            )
        self.ipdom = _post_dominators(proc)
        # loop tails: split S -> (header, back-event-or-None)
        self.loops: dict[str, tuple[str, str | None]] = {}
        self.headers: set[str] = set()
        for u, v in _back_edges(proc, self.starts):
            un = proc.node(u)
            if un.kind == "event":
                preds = proc.predecessors(u)
                if len(preds) != 1 or proc.node(preds[0]).kind != "xor":
                    raise StructureError(f"back edge {u}->{v}: event {u} is not an XOR outcome")
                split, back_event = preds[0], u
            elif un.kind == "xor":
                split, back_event = u, None
            else:
                raise StructureError(f"back edge {u}->{v}: loops must leave from an XOR split")
            hn = proc.node(v)
            if hn.kind != "xor" or len(proc.predecessors(v)) < 2:
                raise StructureError(f"back edge {u}->{v}: loop header {v} is not an XOR join")
            if split in self.loops:
                raise StructureError(f"split {split} closes two loops")
            self.loops[split] = (v, back_event)
            self.headers.add(v)
        self.seen: set[str] = set()

    # helpers
    def _single_succ(self, nid: str) -> str | None:
        s = self.p.successors(nid)
        if len(s) > 1:
            raise StructureError(f"{nid}: {self.p.node(nid).kind} has {len(s)} successors")
        return s[0] if s else None

    def _mark(self, nid: str) -> None:
        if nid in self.seen:
            raise StructureError(f"{nid} is reached twice: unstructured cycle or jump")
        self.seen.add(nid)

    def walk(self, cur: str | None, stop: str | None) -> tuple[list, str | None]:
        """Consume nodes from ``cur`` until ``stop`` (not consumed) or a
        sink. Returns the blocks and the node the walk stopped on."""
        blocks: list = []
        while cur is not None and cur != stop:
            n = self.p.node(cur)
            if cur in self.headers:
                blocks.append(self._loop(cur))
                cur = self._after_loop
                continue
            self._mark(cur)
            if n.kind in ("function", "interface"):
                blocks.append(Action(n))
                cur = self._single_succ(cur)
                # no successor: the flow dangles. Deliberately no Stop — the
                # EPC lacks an end event and pumllint's ACT002 should say so.
            elif n.kind == "event":
                nxt = self._single_succ(cur)
                if nxt is None:
                    blocks.append(Stop(n))
                    cur = None
                else:
                    blocks.append(EventArrow(n))
                    cur = nxt
            elif n.kind in CONNECTORS:
                succs = self.p.successors(cur)
                preds = self.p.predecessors(cur)
                if len(succs) > 1:
                    if cur in self.loops:
                        raise StructureError(f"loop split {cur} reached outside its loop")
                    block, cur = self._split(n, succs)
                    blocks.append(block)
                elif len(preds) > 1:
                    raise StructureError(
                        f"join {cur} reached without passing through its split (unstructured)"
                    )
                else:
                    cur = self._single_succ(cur)
            else:  # pragma: no cover - model.validate() rejects unknown kinds
                raise StructureError(f"{cur}: unknown kind {n.kind}")
        return blocks, cur

    def _branch_start(self, s: str, kind: str) -> tuple[str | None, str | None, bool]:
        """For an XOR branch head: (label, first body node, ends_immediately)."""
        sn = self.p.node(s)
        if kind == "xor" and sn.kind == "event":
            self._mark(s)
            nxt = self._single_succ(s)
            return sn.name, nxt, nxt is None
        return None, s, False

    def _split(self, n: Node, succs: list[str]) -> tuple[object, str | None]:
        join = self.ipdom[n.id]
        stop = None if join == EXIT else join
        if n.kind == "xor":
            branches: list[Branch] = []
            for s in succs:
                label, start, ends = self._branch_start(s, "xor")
                if ends:
                    body: list = [Stop(self.p.node(s))]
                else:
                    body, reached = self.walk(start, stop)
                    if stop is not None and reached != stop:
                        raise StructureError(f"branch of {n.id} via {s} does not reach join {stop}")
                branches.append(Branch(label, body))
            block: object = Decision(n, self._condition(n, branches), branches)
        else:
            bodies: list[list] = []
            for s in succs:
                body, reached = self.walk(s, stop)
                if stop is not None and reached != stop:
                    raise StructureError(f"branch of {n.id} via {s} does not reach join {stop}")
                bodies.append(body)
            if n.kind == "or":
                self.warnings.append(
                    f"{n.id}: OR connector has no activity-diagram equivalent; emitted as fork"
                )
            block = Parallel(n, bodies)
        if stop is None:
            return block, None
        jn = self.p.node(join)
        if jn.kind in CONNECTORS and len(self.p.predecessors(join)) > 1:
            if jn.kind != n.kind:
                raise StructureError(f"split {n.id} ({n.kind}) joins at {join} ({jn.kind})")
            self._mark(join)
            return block, self._single_succ(join)
        return block, join  # implicit merge on a non-connector node

    def _condition(self, n: Node, branches: list[Branch]) -> str:
        labels = [b.label for b in branches if b.label]
        if len(branches) == 2 and labels:
            return labels[0] + "?"
        preds = self.p.predecessors(n.id)
        if preds and self.p.node(preds[0]).kind in ("function", "interface"):
            return self.p.node(preds[0]).name + " outcome?"
        return "Outcome?"

    def _loop(self, header: str) -> Loop:
        self._mark(header)
        split = next(s for s, (h, _) in self.loops.items() if h == header)
        hn = self.p.node(header)
        body, reached = self.walk(self._single_succ(header), split)
        if reached != split:
            raise StructureError(f"loop at {header} never reaches its split {split}")
        self._mark(split)
        _, back_event = self.loops[split]
        succs = self.p.successors(split)
        if len(succs) != 2:
            raise StructureError(f"loop split {split} must have exactly 2 outcomes, has {len(succs)}")
        back_head = back_event if back_event is not None else header
        exits = [s for s in succs if s != back_head]
        if len(exits) != 1:
            raise StructureError(f"loop split {split}: cannot tell the exit from the back edge")
        back_label = None
        if back_event:
            self._mark(back_event)
            back_label = self.p.node(back_event).name
        label, start, ends = self._branch_start(exits[0], "xor")
        self._after_loop = None if ends else start
        cond = (back_label or label or hn.name or "Again") + "?"
        loop = Loop(hn, body, cond, back_label, label)
        if ends:
            loop.body_end = Stop(self.p.node(exits[0]))  # type: ignore[attr-defined]
        return loop


def structure(proc: Process) -> Structured:
    w = _Walker(proc)
    blocks, reached = w.walk(w.starts[0], None)
    if reached is not None:
        raise StructureError(f"walk stopped on {reached} without consuming it")
    unreached = [n.id for n in proc.nodes if n.id not in w.seen]
    if unreached:
        raise StructureError("unreachable nodes: " + ", ".join(unreached))
    return Structured(blocks, w.warnings)
