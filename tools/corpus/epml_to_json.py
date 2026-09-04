#!/usr/bin/env python3
"""EPML (EPC Markup Language) → the aris2puml intermediate JSON, version 1.

Corpus preparation only: this is not part of the ``aris2puml`` package and
is not an EPML reader for the CLI. It exists so that every file under
``tests/fixtures/corpus/`` can be regenerated from its upstream source —
see that directory's README for the download URLs.

    python tools/corpus/epml_to_json.py SAPModels.epml out/ 440 439

With no epcIds, every EPC in the document is written. Each EPC becomes
``out/<epcId>.json``; the EPC's ``name`` attribute (an ARIS model id in
the SAP reference model) is passed through as the process name untouched,
because the corpus invents nothing the source does not carry.
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

KINDS = {"function": "function", "event": "event",
         "xor": "xor", "and": "and", "or": "or"}


def convert(epc: ET.Element, prefix: str = "EPML") -> dict:
    nodes, edges = [], []
    for child in epc:
        kind = KINDS.get(child.tag)
        if kind:
            node = {"id": child.get("id"), "kind": kind}
            if kind in ("function", "event"):
                node["name"] = " ".join((child.findtext("name") or "").split())
            nodes.append(node)
        elif child.tag == "arc":
            flow = child.find("flow")
            if flow is not None:
                edges.append({"from": flow.get("source"), "to": flow.get("target")})
    return {
        "version": 1,
        "process": {"id": f"{prefix}-{epc.get('epcId')}",
                    "name": epc.get("name") or f"EPC {epc.get('epcId')}",
                    "owner": ""},
        "lanes": [],
        "nodes": nodes,
        "edges": edges,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    src, outdir, wanted = Path(argv[1]), Path(argv[2]), set(argv[3:])
    outdir.mkdir(parents=True, exist_ok=True)
    for epc in ET.parse(src).getroot().iter("epc"):
        if wanted and epc.get("epcId") not in wanted:
            continue
        path = outdir / f"{epc.get('epcId')}.json"
        path.write_text(json.dumps(convert(epc), indent=1) + "\n", encoding="utf-8")
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
