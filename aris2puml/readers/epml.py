"""EPML (EPC Markup Language) → Process.

EPML is the one open interchange format for EPCs (Mendling & Nüttgens,
2005); ProM, EPC Tools, bflow* and the academic model collections speak
it, and the 604-process SAP reference model is published in it. The
mapping is the same one ``tools/corpus/epml_to_json.py`` uses for corpus
preparation — that tool delegates here so the two cannot drift.

Recognised, per ``<epc epcId name>``: ``<event>``, ``<function>`` (label
from ``<name>``, whitespace collapsed to one line — the SAP corpus breaks
labels across lines), ``<xor>``/``<and>``/``<or>``, ``<processInterface>``
(→ interface), ``<arc><flow source target/></arc>`` (→ edge), and an
organisational ``<role>``/``<participant>`` tied to a function by a
``<relation type="role">`` (→ lane), and a ``<dataField>`` (→ information)
or ``<application>`` (→ system) tied to a function by any other
``<relation>`` (→ data, emitted only with ``--notes``). A data element tied
to no function, and the graphical ``<graphics>`` blocks, are dropped: the
contract has no place for them. Names pass through untouched; an empty
label is the modeller's defect, reported by the reader like any other.

A document may hold several EPCs (the SAP corpus is one file, 604 of
them); every one is returned, in document order.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from aris2puml.model import Data, Edge, Lane, Node, Note, Process
from aris2puml.readers.json_ import ReadError

KINDS = {"function": "function", "event": "event",
         "xor": "xor", "and": "and", "or": "or",
         "processInterface": "interface"}
LANE_TAGS = ("role", "participant")
DATA_TAGS = {"dataField": "information", "application": "system"}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _label(el: ET.Element) -> str:
    return " ".join((el.findtext("name") or "").split())


def convert_epc(epc: ET.Element, prefix: str = "EPML",
                notes: list[Note] | None = None) -> Process:
    """One ``<epc>`` element → Process (unvalidated; callers validate).

    ``notes``, when given, receives one :class:`Note` per element the
    contract has no place for — the fidelity sidecar's record of what was
    dropped. Without it, dropping is silent, as before.
    """
    epc_id = epc.get("epcId") or "?"
    lanes: dict[str, str] = {}
    nodes: list[Node] = []
    edges: list[Edge] = []
    lane_of: dict[str, str] = {}
    data_el: dict[str, ET.Element] = {}
    data_rel: list[tuple[str, str, str | None]] = []   # (from, to, type)
    for child in epc:
        tag = _local(child.tag)
        if tag in LANE_TAGS:
            lanes[child.get("id", "")] = _label(child)
        elif tag in DATA_TAGS:
            data_el[child.get("id", "")] = child
        elif tag == "relation" and child.get("type") == "role":
            a, b = child.get("from", ""), child.get("to", "")
            lane_of[b] = a
            lane_of[a] = b  # either direction; resolved below
        elif tag == "relation":
            data_rel.append((child.get("from", ""), child.get("to", ""), child.get("type")))
        elif tag == "arc":
            flow = child.find("flow")
            if flow is not None:
                edges.append(Edge(flow.get("source", ""), flow.get("target", "")))
    for child in epc:
        tag = _local(child.tag)
        kind = KINDS.get(tag)
        if kind is None:
            # Data fields, applications, graphics, relations, arcs: the
            # structural ones were consumed above; the rest have no place.
            if notes is not None and tag not in ("arc", "relation", "graphics", *LANE_TAGS, *DATA_TAGS):
                nid = child.get("id", "") or tag
                notes.append(Note("unsupported-element", nid,
                                  f"{nid}: <{tag}> {_label(child) or ''}".rstrip()
                                  + " has no place in the contract; dropped"))
            continue
        nid = child.get("id", "")
        lane = None
        if kind == "function":
            other = lane_of.get(nid)
            if other in lanes:
                lane = other
        nodes.append(Node(
            id=nid, kind=kind,
            name=_label(child) if kind in ("function", "event", "interface") else "",
            lane=lane,
            ref=child.get("linkToEpcId") if kind == "interface" else None,
        ))
    used = {n.lane for n in nodes if n.lane}
    functions = {n.id for n in nodes if n.kind in ("function", "interface")}
    data: list[Data] = []
    for a, b, ty in data_rel:
        for did, fid in ((a, b), (b, a)):
            if did in data_el and fid in functions:
                el = data_el[did]
                role = ty if ty in ("input", "output") else None
                data.append(Data(did, DATA_TAGS[_local(el.tag)], _label(el), fid, role))
    if notes is not None:
        for lid, nm in lanes.items():
            if lid not in used:
                notes.append(Note("unused-lane", lid,
                                  f"{lid}: org unit {nm!r} is tied to no function; dropped"))
        attached = {d.id for d in data}
        for did, el in data_el.items():
            if did not in attached:
                notes.append(Note("unattached-data", did,
                                  f"{did}: <{_local(el.tag)}> {_label(el)!r} is tied to no function; dropped"))
    return Process(
        id=f"{prefix}-{epc_id}",
        name=epc.get("name") or f"EPC {epc_id}",
        owner="",
        lanes=[Lane(i, nm) for i, nm in lanes.items() if i in used],
        nodes=nodes,
        edges=edges,
        data=data,
    )


def read_epml(path: str | Path,
              notes: dict[str, list[Note]] | None = None) -> list[Process]:
    """``notes``, when given, is filled per process id with what that EPC's
    conversion dropped — a document may hold many EPCs, so one flat list
    could not say which."""
    path = Path(path)
    source = path.as_posix()
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise ReadError(f"{source}: {exc}") from exc
    epcs = [el for el in root.iter() if _local(el.tag) == "epc"]
    if not epcs:
        raise ReadError(f"{source}: no <epc> element")
    out: list[Process] = []
    bad: list[str] = []
    for epc in epcs:
        dropped: list[Note] = []
        proc = convert_epc(epc, notes=dropped)
        if notes is not None:
            notes[proc.id] = dropped
        problems = proc.validate()
        if problems:
            bad.append(f"[{proc.id}] " + "; ".join(problems))
        out.append(proc)
    if bad:
        # All or nothing, like the JSON reader: a document is one input.
        # Every offending EPC is named so a multi-EPC file is fixed in one
        # pass rather than one refusal at a time.
        raise ReadError(f"{source}: {len(bad)} of {len(epcs)} EPCs malformed — " + " | ".join(bad))
    return out
