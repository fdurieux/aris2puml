"""The structure diagnostic: the refused EPC, drawn as the graph it is.

An activity diagram cannot show why a process was refused — the refusal
*is* the finding that the graph has no block structure, so any activity
diagram of it would be invented structure. What can be drawn is the EPC
itself: PlantUML's component dialect draws any directed graph. Events are
ellipses, functions rounded rectangles, connectors labelled circles; the
node(s) the refusal names are red and the reason hangs off the first of
them as a note. Swimlanes are left out: the diagnostic is about control
flow, and the org unit does not move the fix.

``!pragma layout smetana`` is pinned so the file renders wherever the
activity diagrams do, with or without Graphviz.
"""

from __future__ import annotations

from aris2puml.model import Process
from aris2puml.structure import CONNECTORS, StructureError

SHAPE = {"event": "usecase", "function": "rectangle", "interface": "rectangle"}


def _label(text: str) -> str:
    return text.replace('"', "'")


def diagnose(proc: Process, exc: StructureError, name: str) -> str:
    """The diagnostic diagram for ``proc``, refused with ``exc``; ``name`` is
    the output stem the activity diagram would have had."""
    alias = {n.id: f"n{i + 1}" for i, n in enumerate(proc.nodes)}
    red = [n for n in exc.nodes if n in alias]
    lines = [
        f"@startuml {name}-refused",
        "!pragma layout smetana",
        f"title {_label(proc.name)} — refused",
        "skinparam rectangleRoundCorner 12",
        "skinparam defaultTextAlignment center",
        "",
    ]
    for n in proc.nodes:
        if n.kind in CONNECTORS:
            shape, label = "storage", f"{n.kind.upper()}\\n{_label(n.id)}"
        else:
            shape = SHAPE[n.kind]
            label = _label(n.name)
            if n.kind == "interface" and n.ref:
                label += f"\\n→ {_label(n.ref)}"
        colour = " #red" if n.id in red else ""
        lines.append(f'{shape} "{label}" as {alias[n.id]}{colour}')
    lines.append("")
    for e in proc.edges:
        lines.append(f"{alias[e.src]} --> {alias[e.dst]}")
    lines.append("")
    if red:
        lines += [f"note right of {alias[red[0]]} #ffdddd", f"  refused: {_label(str(exc))}", "end note"]
    else:
        lines += ["note as refusal #ffdddd", f"  refused: {_label(str(exc))}", "end note"]
    lines += [f"footer ARIS process {_label(proc.id)} — aris2puml --diagnose", "@enduml"]
    return "\n".join(lines) + "\n"
