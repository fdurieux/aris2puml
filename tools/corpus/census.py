#!/usr/bin/env python3
"""Count what a directory of intermediate-JSON processes does to the
structuring pass: how many convert, and what the refusals are.

Corpus preparation only. Point it at the output of one of the converters
beside it to reproduce the census quoted in
``tests/fixtures/corpus/README.md``::

    python tools/corpus/bpmai_to_json.py bpmai/models /tmp/all
    python tools/corpus/census.py /tmp/all
"""

from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from aris2puml.readers.json_ import ReadError, read_json          # noqa: E402
from aris2puml.structure import StructureError, structure         # noqa: E402

BUCKETS = (
    ("every start event is a mid-process trigger", "no entry: every start is a mid-flow trigger (A2 residual)"),
    ("share no join below", "start events without a common join (A2 residual)"),
    ("does not reach the entry join", "entry branch misses the entry join (A2 residual)"),
    ("start node", "multiple start events (roadmap A2)"),
    ("back edge", "loop shape not supported (roadmap B1)"),
    ("loops must", "loop shape not supported (roadmap B1)"),
    ("loop split", "loop shape not supported (roadmap B1)"),
    ("closes two loops", "loop shape not supported (roadmap B1)"),
    ("without passing through its split", "unstructured join"),
    ("joins at", "split/join kind mismatch"),
    ("does not reach join", "branch does not reach the join"),
    ("reached twice", "unstructured cycle or jump"),
    ("unreachable nodes", "unreachable nodes"),
)


def bucket(message: str) -> str:
    for needle, label in BUCKETS:
        if needle in message:
            return label
    return re.sub(r"\b[\w-]*[0-9A-F]{6,}[\w-]*\b", "#", message)[:60]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    tally: collections.Counter[str] = collections.Counter()
    total = 0
    for path in sorted(Path(argv[1]).glob("*.json")):
        total += 1
        try:
            procs = read_json(path)
        except ReadError as exc:
            tally["reader: " + ("unnamed element" if "no name" in str(exc) else "other")] += 1
            continue
        for proc in procs:
            try:
                structure(proc)
                tally["converts"] += 1
            except StructureError as exc:
                tally[bucket(str(exc))] += 1
            except RecursionError:
                tally["recursion limit"] += 1
    print(f"{total} files")
    for label, count in tally.most_common():
        print(f"{count:6} ({100 * count / max(total, 1):4.1f}%)  {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
