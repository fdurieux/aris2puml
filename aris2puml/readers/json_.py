"""The intermediate JSON contract (version 1) → Process.

This is the format the shipped ARIS report script (aris/export_epc.js)
writes, and the one any other front-end should target::

    {
      "version": 1,
      "process": {"id": "PROC-0042", "name": "Order to cash", "owner": "Sales Operations"},
      "lanes":   [{"id": "ou1", "name": "Sales"}],
      "nodes":   [{"id": "f1", "kind": "function",  "name": "Receive order", "lane": "ou1"},
                  {"id": "e1", "kind": "event",     "name": "Order received"},
                  {"id": "x1", "kind": "xor"},
                  {"id": "p1", "kind": "interface", "name": "Handle complaint", "ref": "PROC-0051"}],
      "edges":   [{"from": "e1", "to": "f1"}, {"from": "f1", "to": "x1"}]
    }

A file may also carry a list of such documents under ``"processes"``.
"""

from __future__ import annotations

import json
from pathlib import Path

from aris2puml.model import Edge, Lane, Node, Process


class ReadError(ValueError):
    pass


def _one(doc: dict, source: str) -> Process:
    if doc.get("version") not in (None, 1):
        raise ReadError(f"{source}: unsupported version {doc.get('version')!r} (expected 1)")
    try:
        meta = doc["process"]
        proc = Process(
            id=str(meta["id"]),
            name=str(meta["name"]),
            owner=str(meta.get("owner", "")),
            lanes=[Lane(str(l["id"]), str(l["name"])) for l in doc.get("lanes", [])],
            nodes=[
                Node(
                    id=str(n["id"]),
                    kind=str(n["kind"]),
                    name=" ".join(str(n.get("name", "")).split()),
                    lane=None if n.get("lane") is None else str(n["lane"]),
                    ref=None if n.get("ref") is None else str(n["ref"]),
                )
                for n in doc.get("nodes", [])
            ],
            edges=[Edge(str(e["from"]), str(e["to"])) for e in doc.get("edges", [])],
        )
    except (KeyError, TypeError) as exc:
        raise ReadError(f"{source}: malformed document ({exc})") from exc
    problems = proc.validate()
    if problems:
        raise ReadError(f"{source}: " + "; ".join(problems))
    return proc


def read_json(path: str | Path) -> list[Process]:
    path = Path(path)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReadError(f"{path.as_posix()}: {exc}") from exc
    source = path.as_posix()
    if isinstance(doc, dict) and "processes" in doc:
        return [_one(d, source) for d in doc["processes"]]
    if isinstance(doc, dict):
        return [_one(doc, source)]
    raise ReadError(f"{source}: expected a JSON object")
