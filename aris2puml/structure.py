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
  to an XOR join that is the loop header;
* several start events: joined before the first function they become an
  *entry region* — nested if/switch/fork blocks whose outcomes are the
  start events (grouped by the join each reaches, chains of XOR joins
  flattened, group labels derived by joining the event names with the
  join's word); a start event that instead enters the flow at a join fed
  from inside the process is a *mid-flow trigger*, folded into the arrow
  label at that join with a marker and a warning.

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
class Trigger:
    join: Node              # the connector where external start events enter
    label: str              # their names, joined by the connector's word


JOINWORD = {"xor": " or ", "and": " and ", "or": " and/or "}


@dataclass
class Structured:
    blocks: list
    warnings: list[str] = field(default_factory=list)


# -- graph helpers ---------------------------------------------------------

def _post_dominators(proc: Process) -> tuple[dict[str, str | None], dict[str, set[str]]]:
    """Immediate post-dominator of every node (``None`` for the exit) and
    the full post-dominator sets, on the graph with a virtual exit that
    every sink flows into."""
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
    return ipdom, pdom


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
        self.ipdom, self.pdom = _post_dominators(proc)
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
                    split_blocks, cur = self._split(n, succs)
                    blocks.extend(split_blocks)
                elif len(preds) > 1:
                    trigger = self._trigger(cur, n)
                    if trigger is None:
                        raise StructureError(
                            f"join {cur} reached without passing through its split (unstructured)"
                        )
                    blocks.append(trigger)
                    cur = self._single_succ(cur)
                else:
                    cur = self._single_succ(cur)
            else:  # pragma: no cover - model.validate() rejects unknown kinds
                raise StructureError(f"{cur}: unknown kind {n.kind}")
        return blocks, cur

    # -- entries: start events ----------------------------------------------
    def _is_join(self, nid: str | None) -> bool:
        if nid is None or nid == EXIT:
            return False
        n = self.p.node(nid)
        return n.kind in CONNECTORS and len(self.p.predecessors(nid)) > 1

    def _upstream(self, nid: str) -> set[str]:
        seen: set[str] = set()
        stack = [nid]
        while stack:
            u = stack.pop()
            for q in self.p.predecessors(u):
                if q not in seen:
                    seen.add(q)
                    stack.append(q)
        return seen

    def _from_inside(self, p: str, join: str) -> bool:
        """``p`` is fed from inside the flow: a split, a consumed node or
        ``join`` itself lies upstream of it."""
        up = self._upstream(p) | {p}
        if join in up:
            return True
        return any(
            u in self.seen or (self.p.node(u).kind in CONNECTORS and len(self.p.successors(u)) > 1)
            for u in up
        )

    def _entry_only(self, p: str, join: str) -> bool:
        """``p`` and everything upstream of it is a tree of start events and
        joins only — the shape that can be folded into a label without
        losing a function."""
        if self._from_inside(p, join):
            return False
        return all(self.p.node(u).kind not in ("function", "interface")
                   for u in self._upstream(p) | {p})

    def _is_trigger(self, s: str) -> bool:
        """A start whose forward path meets a join fed from inside the flow
        before any function or split: folded there, not an entry."""
        cur: str | None = s
        path: set[str] = set()
        while cur is not None and cur not in path:
            path.add(cur)
            n = self.p.node(cur)
            if n.kind in ("function", "interface"):
                return False
            if n.kind in CONNECTORS and len(self.p.successors(cur)) > 1:
                return False
            preds = self.p.predecessors(cur)
            if len(preds) > 1 and any(
                self._from_inside(q, cur) for q in preds if q not in path
            ):
                return True
            succs = self.p.successors(cur)
            cur = succs[0] if succs else None
        return False

    def _tree_label(self, nid: str) -> str:
        """Name for an entry-only tree: the event nearest the flow, or the
        names of the trees behind a join, joined by that join's word."""
        n = self.p.node(nid)
        preds = self.p.predecessors(nid)
        if not preds:
            return n.name
        if len(preds) == 1:
            return n.name if n.kind == "event" and n.name else self._tree_label(preds[0])
        return JOINWORD[n.kind].join(self._tree_label(q) for q in preds)

    def _trigger(self, cur: str, n: Node, from_branches: bool = False) -> Trigger | None:
        """External start events entering at join ``cur``: every predecessor
        not consumed by the flow must be a pure entry tree. Reached from a
        single branch (the default) exactly one predecessor is the flow's;
        reached as a split's own join, all consumed ones are."""
        preds = self.p.predecessors(cur)
        entry = [q for q in preds if self._entry_only(q, cur)]
        expected = len([q for q in preds if q not in self.seen]) if from_branches else len(preds) - 1
        if not entry or len(entry) != expected:
            return None
        for q in entry:
            for u in self._upstream(q) | {q}:
                self._mark(u)
        label = JOINWORD[n.kind].join(self._tree_label(q) for q in entry)
        self.warnings.append(f"{cur}: external trigger joins mid-process ({n.kind}): {label}")
        return Trigger(n, label)

    def _nearest(self, cands: set[str]) -> str | None:
        for c in cands:
            if all(o == c or o in self.pdom[c] for o in cands):
                return c
        return None

    def _common_join(self, starts: list[str]) -> str:
        common = set.intersection(*(self.pdom[s] for s in starts))
        return self._nearest(common) or EXIT

    def _after_join(self, join: str) -> str | None:
        if self._is_join(join):
            self._mark(join)
            return self._single_succ(join)
        return join  # implicit merge on a non-connector node: continue at it

    def _walk_to(self, start: str | None, stop: str | None, via: str) -> list:
        body, reached = self.walk(start, stop)
        if stop is not None and reached != stop:
            raise StructureError(f"entry via {via} does not reach the entry join {stop}")
        return body

    def _region(self, starts: list[str], join: str) -> tuple[object, list[str]]:
        """The entry region of ``starts``, which meet at ``join`` (or never,
        when ``join`` is the exit): one Decision (XOR-kind) or Parallel
        (AND/OR-kind) block, plus one label per branch for the parent."""
        stop = None if join == EXIT else join
        kind = self.p.node(join).kind if self._is_join(join) else "xor"
        groups: dict[str, list[str]] = {}
        for s in starts:
            c = s
            while self.ipdom.get(c) not in (join, None):
                c = self.ipdom[c]  # type: ignore[assignment]
            groups.setdefault(c, []).append(s)
        branches: list[Branch] = []
        bodies: list[list] = []
        labels: list[str] = []
        for group in groups.values():
            if len(group) == 1:
                s = group[0]
                if kind == "xor":
                    label, start, ends = self._branch_start(s, "xor")
                    body = [Stop(self.p.node(s))] if ends else self._walk_to(start, stop, s)
                    branches.append(Branch(label, body))
                    labels.append(label or self.p.node(s).name)
                else:
                    bodies.append(self._walk_to(s, stop, s))
                    labels.append(self.p.node(s).name)
                continue
            inner = self._common_join(group)
            if inner in (join, EXIT):
                raise StructureError(
                    f"start events {', '.join(group)} share no join below {join}"
                )
            inner_kind = self.p.node(inner).kind if self._is_join(inner) else "xor"
            block, inner_labels = self._region(group, inner)
            if kind == "xor" and inner_kind == "xor" and self.p.successors(inner) == [join]:
                # a chain of XOR joins is one decision: splice, do not nest
                self._mark(inner)
                branches.extend(block.branches)  # type: ignore[attr-defined]
                labels.extend(inner_labels)
                continue
            rest = self._walk_to(self._after_join(inner), stop, group[0])
            label = JOINWORD[inner_kind].join(inner_labels)
            if kind == "xor":
                branches.append(Branch(label, [block] + rest))
            else:
                bodies.append([block] + rest)
            labels.append(label)
        virtual = Node(id="$start", kind=kind)
        if kind == "xor":
            return Decision(virtual, "Trigger?", branches), labels
        if kind == "or":
            self.warnings.append("start: OR-joined start events have no activity-diagram equivalent; emitted as fork")
        return Parallel(virtual, bodies), labels

    def entry(self) -> tuple[list, str | None]:
        """Blocks for the whole process, from its start events."""
        real = [s for s in self.starts if not self._is_trigger(s)]
        if not real:
            raise StructureError("every start event is a mid-process trigger: no entry into the flow")
        if len(real) == 1:
            return self.walk(real[0], None)
        join = self._common_join(real)
        block, _ = self._region(real, join)
        if join == EXIT:
            return [block], None
        rest, reached = self.walk(self._after_join(join), None)
        return [block] + rest, reached

    def _branch_start(self, s: str, kind: str) -> tuple[str | None, str | None, bool]:
        """For an XOR branch head: (label, first body node, ends_immediately)."""
        sn = self.p.node(s)
        if kind == "xor" and sn.kind == "event":
            self._mark(s)
            nxt = self._single_succ(s)
            return sn.name, nxt, nxt is None
        return None, s, False

    def _split(self, n: Node, succs: list[str]) -> tuple[list, str | None]:
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
            return [block], None
        jn = self.p.node(join)
        if jn.kind in CONNECTORS and len(self.p.predecessors(join)) > 1:
            if jn.kind != n.kind:
                raise StructureError(f"split {n.id} ({n.kind}) joins at {join} ({jn.kind})")
            self._mark(join)
            blocks: list = [block]
            trigger = self._trigger(join, jn, from_branches=True)
            if trigger is not None:
                blocks.append(trigger)
            return blocks, self._single_succ(join)
        return [block], join  # implicit merge on a non-connector node

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
    blocks, reached = w.entry()
    if reached is not None:
        raise StructureError(f"walk stopped on {reached} without consuming it")
    unreached = [n.id for n in proc.nodes if n.id not in w.seen]
    if unreached:
        raise StructureError("unreachable nodes: " + ", ".join(unreached))
    return Structured(blocks, w.warnings)
