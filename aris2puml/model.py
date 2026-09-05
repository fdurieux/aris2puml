"""The notation-neutral process graph every reader produces.

Deliberately small: what the PlantUML mapping needs and nothing else. An
EPC, a BPMN process and an ARIS report-script dump all reduce to this.
"""

from __future__ import annotations

from dataclasses import dataclass, field

KINDS = ("function", "event", "xor", "and", "or", "interface")


@dataclass(frozen=True)
class Lane:
    id: str
    name: str


@dataclass(frozen=True)
class Node:
    id: str
    kind: str                 # one of KINDS
    name: str = ""            # empty for connectors
    lane: str | None = None   # Lane.id; functions and interfaces only
    ref: str | None = None    # interface: the linked process id


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str


@dataclass(frozen=True)
class Note:
    """One thing a reader or the structuring pass could not carry over.

    ``code`` is a stable machine-readable name for the fidelity sidecar;
    ``text`` is the sentence the CLI prints. A *drop* loses an element
    outright; an *approximation* keeps the shape and bends its meaning.
    """
    code: str      # e.g. "or-connector", "return-path-events", "unsupported-element"
    node: str      # the element concerned; "start" for the entry region
    text: str


APPROXIMATED = ("mid-flow-trigger", "or-start-events", "or-connector")
DROPPED = ("unsupported-element", "unused-lane", "return-path-events", "return-path-lane")
# Reader drops are the contract working as documented, not a per-run surprise:
# they go into the sidecar and stay off stderr.
REPORT_ONLY = ("unsupported-element", "unused-lane")
# What --strict refuses: every loss the structuring pass records. Reader
# drops are the contract, not a fidelity choice, so they stay out.
STRICT = tuple(c for c in APPROXIMATED + DROPPED if c not in REPORT_ONLY)


@dataclass
class Process:
    id: str
    name: str
    owner: str = ""
    lanes: list[Lane] = field(default_factory=list)
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    # -- derived views -----------------------------------------------------
    def node(self, node_id: str) -> Node:
        for n in self.nodes:
            if n.id == node_id:
                return n
        raise KeyError(node_id)

    def lane_name(self, lane_id: str | None) -> str | None:
        if lane_id is None:
            return None
        for lane in self.lanes:
            if lane.id == lane_id:
                return lane.name
        raise KeyError(lane_id)

    def successors(self, node_id: str) -> list[str]:
        return [e.dst for e in self.edges if e.src == node_id]

    def predecessors(self, node_id: str) -> list[str]:
        return [e.src for e in self.edges if e.dst == node_id]

    def validate(self) -> list[str]:
        """Referential and shape checks a reader cannot guarantee. Returns
        problems as strings; empty means sound."""
        problems: list[str] = []
        ids = [n.id for n in self.nodes]
        if len(ids) != len(set(ids)):
            problems.append("duplicate node ids")
        idset = set(ids)
        laneset = {lane.id for lane in self.lanes}
        for n in self.nodes:
            if n.kind not in KINDS:
                problems.append(f"{n.id}: unknown kind {n.kind!r}")
            if n.kind in ("function", "event", "interface") and not n.name.strip():
                problems.append(f"{n.id}: {n.kind} has no name")
            if n.lane is not None and n.lane not in laneset:
                problems.append(f"{n.id}: unknown lane {n.lane!r}")
        for e in self.edges:
            if e.src not in idset or e.dst not in idset:
                problems.append(f"edge {e.src}->{e.dst}: unknown node")
        if self.nodes and not any(not self.predecessors(n.id) for n in self.nodes):
            problems.append("no start node (every node has a predecessor)")
        return problems
