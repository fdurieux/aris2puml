#!/usr/bin/env python3
"""BPMAI EPC models (Oryx JSON) → the aris2puml intermediate JSON, version 1.

Corpus preparation only: this is not part of the ``aris2puml`` package.
It exists so that every file under ``tests/fixtures/corpus/`` can be
regenerated from its upstream source — see that directory's README for
the download URL.

    python tools/corpus/bpmai_to_json.py bpmai/models out/ 504129192

With no model ids, every model in the directory whose stencil set is EPC
is converted. Each model becomes ``out/<modelId>.json``.

Mapping: Function → function, Event → event, Xor/And/OrConnector →
xor/and/or, ProcessInterface → interface, ControlFlow → edge,
Organization → lane (assigned to a function through the Relation edge
that ties the two together). Information objects (Data), IT systems
(System) and annotations are dropped, as the JSON contract has no place
for them.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

KINDS = {"Function": "function", "Event": "event", "XorConnector": "xor",
         "AndConnector": "and", "OrConnector": "or",
         "ProcessInterface": "interface"}


def _shapes(shape: dict):
    for child in shape.get("childShapes", []):
        yield child
        yield from _shapes(child)


def _source_of(edge_id: str, by_id: dict) -> str | None:
    for rid, shape in by_id.items():
        if any(o.get("resourceId") == edge_id for o in shape.get("outgoing", [])):
            return rid
    return None


def convert(doc: dict, name: str, pid: str) -> dict:
    by_id = {s["resourceId"]: s for s in _shapes(doc)}
    stencil = {rid: s.get("stencil", {}).get("id") for rid, s in by_id.items()}

    lanes = {rid: " ".join(str(s["properties"].get("title", "")).split())
             for rid, s in by_id.items() if stencil[rid] == "Organization"}
    lane_of: dict[str, str] = {}
    for rid, shape in by_id.items():
        if stencil[rid] != "Relation":
            continue
        ends = (_source_of(rid, by_id), (shape.get("target") or {}).get("resourceId"))
        for a, b in (ends, ends[::-1]):
            if a in lanes and stencil.get(b) == "Function":
                lane_of[b] = a

    nodes, edges = [], []
    for rid, shape in by_id.items():
        kind = KINDS.get(stencil[rid])
        if not kind:
            continue
        node = {"id": rid, "kind": kind}
        if kind in ("function", "event", "interface"):
            node["name"] = " ".join(str(shape["properties"].get("title", "")).split())
        if rid in lane_of:
            node["lane"] = lane_of[rid]
        nodes.append(node)
        for out in shape.get("outgoing", []):
            edge = by_id.get(out.get("resourceId"))
            if edge is None or stencil.get(edge["resourceId"]) != "ControlFlow":
                continue
            target = (edge.get("target") or {}).get("resourceId")
            if target in by_id:
                edges.append({"from": rid, "to": target})

    used = set(lane_of.values())
    return {
        "version": 1,
        "process": {"id": pid, "name": name, "owner": ""},
        "lanes": [{"id": rid, "name": nm} for rid, nm in lanes.items() if rid in used],
        "nodes": nodes,
        "edges": edges,
    }


def _is_epc(doc: dict) -> bool:
    return "stencilset/epc" in (doc.get("stencilset", {}) or {}).get("namespace", "")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    src, outdir, wanted = Path(argv[1]), Path(argv[2]), set(argv[3:])
    outdir.mkdir(parents=True, exist_ok=True)
    ids = sorted(wanted) or sorted(p.stem for p in src.glob("*.json")
                                   if not p.name.endswith(".meta.json"))
    for mid in ids:
        doc = json.loads((src / f"{mid}.json").read_text(encoding="utf-8"))
        if not _is_epc(doc):
            continue
        meta = json.loads((src / f"{mid}.meta.json").read_text(encoding="utf-8"))
        name = " ".join(str(meta["model"]["modelName"]).split())
        path = outdir / f"{mid}.json"
        path.write_text(json.dumps(convert(doc, name, f"BPMAI-{mid}"),
                                   indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
