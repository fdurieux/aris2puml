#!/usr/bin/env python3
"""EPML (EPC Markup Language) → the aris2puml intermediate JSON, version 1.

Corpus preparation only: this is not part of the ``aris2puml`` package.
The mapping itself lives in ``aris2puml.readers.epml`` (the CLI's
``--from epml``); this script only writes what that reader produces, so
the corpus fixtures and the reader cannot drift apart. It exists so that
every file under ``tests/fixtures/corpus/`` can be regenerated from its
upstream source — see that directory's README for the download URLs.

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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from aris2puml.readers.epml import convert_epc  # noqa: E402


def convert(epc: ET.Element, prefix: str = "EPML") -> dict:
    proc = convert_epc(epc, prefix)
    nodes = []
    for n in proc.nodes:
        node = {"id": n.id, "kind": n.kind}
        if n.kind in ("function", "event", "interface"):
            node["name"] = n.name
        if n.lane is not None:
            node["lane"] = n.lane
        if n.ref is not None:
            node["ref"] = n.ref
        nodes.append(node)
    return {
        "version": 1,
        "process": {"id": proc.id, "name": proc.name, "owner": proc.owner},
        "lanes": [{"id": l.id, "name": l.name} for l in proc.lanes],
        "nodes": nodes,
        "edges": [{"from": e.src, "to": e.dst} for e in proc.edges],
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
