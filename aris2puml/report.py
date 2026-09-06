"""The fidelity sidecar: what each conversion dropped, approximated or refused.

A converted diagram is a *view* of the EPC. This module keeps the account
of what the view could not carry, per process, so that "it converted"
becomes a number a process owner can read and a record the roadmap can be
prioritised against. The CLI writes it with ``--report sidecar.json``.

Shape (version 1)::

    {
      "version": 1,
      "tool": "aris2puml 0.1.0",
      "summary": {"inputs": 2, "processes": 9, "converted": 6, "refused": 3,
                  "converted_percent": 66.7, "approximated": 4, "dropped": 5,
                  "flagged": 2},
      "processes": [
        {"input": "corpus/a.json", "id": "PROC-0042", "name": "Order to cash",
         "status": "converted", "output": "out/order-to-cash.puml",
         "approximated": [{"code": "or-connector", "node": "o1", "detail": "…"}],
         "dropped": [],
         "flagged": [{"code": "no-lane", "node": "f3", "detail": "…"}]},
        {"input": "corpus/b.json", "id": "EPML-459", "name": "1Tr_gfmu",
         "status": "refused", "reason": "join 31 reached without …",
         "diagnostic": "out/1tr-gfmu.refused.puml"}
      ]
    }

A document the reader refuses yields one record with ``"id": null``: both
readers are all-or-nothing per document, so the document is the unit.
``diagnostic`` is present when ``--diagnose`` drew the refused process.
``flagged`` holds model defects the diagram shows as they are (a function
with no org unit, an org unit with no name): neither dropped nor bent.
Every path is POSIX, on every platform, like the CLI's own output.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from aris2puml import __version__
from aris2puml.model import APPROXIMATED, DROPPED, FLAGGED, Note

VERSION = 1


@dataclass
class Record:
    input: str                          # POSIX path of the source file
    id: str | None                      # None when the whole input was refused
    name: str | None
    status: str                         # "converted" | "refused"
    output: str | None = None           # POSIX path of the .puml, when one was written
    notes: list[Note] = field(default_factory=list)
    reason: str | None = None           # the refusal, verbatim
    diagnostic: str | None = None       # POSIX path of the --diagnose drawing, when one was written
    interfaces: list[str] = field(default_factory=list)  # ids the process interfaces link to

    @property
    def approximated(self) -> list[Note]:
        return [n for n in self.notes if n.code in APPROXIMATED]

    @property
    def dropped(self) -> list[Note]:
        return [n for n in self.notes if n.code in DROPPED]

    @property
    def flagged(self) -> list[Note]:
        return [n for n in self.notes if n.code in FLAGGED]

    def as_dict(self) -> dict:
        d: dict = {"input": self.input, "id": self.id, "name": self.name, "status": self.status}
        if self.status == "converted":
            d["output"] = self.output
            d["interfaces"] = list(self.interfaces)
            d["approximated"] = [_note(n) for n in self.approximated]
            d["dropped"] = [_note(n) for n in self.dropped]
            d["flagged"] = [_note(n) for n in self.flagged]
        else:
            d["reason"] = self.reason
            if self.diagnostic:
                d["diagnostic"] = self.diagnostic
        return d


def _note(n: Note) -> dict:
    return {"code": n.code, "node": n.node, "detail": n.text}


@dataclass
class Report:
    """Everything one run did, in the order it did it."""
    inputs: list[str] = field(default_factory=list)
    records: list[Record] = field(default_factory=list)

    def converted(self, inp: Path, pid: str, name: str, output: Path | None,
                  notes: list[Note], interfaces: list[str] = ()) -> Record:
        r = Record(inp.as_posix(), pid, name, "converted",
                   output.as_posix() if output else None, list(notes),
                   interfaces=list(interfaces))
        self.records.append(r)
        return r

    def refused(self, inp: Path, reason: str, pid: str | None = None,
                name: str | None = None, diagnostic: Path | None = None) -> Record:
        r = Record(inp.as_posix(), pid, name, "refused", reason=reason,
                   diagnostic=diagnostic.as_posix() if diagnostic else None)
        self.records.append(r)
        return r

    @property
    def written(self) -> list[Path]:
        return [Path(r.output) for r in self.records if r.output]

    @property
    def any_refused(self) -> bool:
        return any(r.status == "refused" for r in self.records)

    def summary(self) -> dict:
        conv = [r for r in self.records if r.status == "converted"]
        ref = [r for r in self.records if r.status == "refused"]
        total = len(self.records)
        return {
            "inputs": len(self.inputs),
            "processes": total,
            "converted": len(conv),
            "refused": len(ref),
            "converted_percent": round(100 * len(conv) / total, 1) if total else 0.0,
            "approximated": sum(len(r.approximated) for r in conv),
            "dropped": sum(len(r.dropped) for r in conv),
            "flagged": sum(len(r.flagged) for r in conv),
        }

    def as_dict(self) -> dict:
        return {
            "version": VERSION,
            "tool": f"aris2puml {__version__}",
            "summary": self.summary(),
            "processes": [r.as_dict() for r in self.records],
        }

    def write(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.as_dict(), indent=1, ensure_ascii=False) + "\n",
                              encoding="utf-8", newline="\n")

    def manifest(self) -> list[dict]:
        """The converted processes and the ids their interfaces link to — a
        JSON array of objects with an ``id``, which is the inventory form
        ``pumllint trace --requirements`` reads (the other keys ride along).
        A refused process has no diagram and is left out on purpose: a
        reference to it is then an unknown reference, which is the finding."""
        return [{"id": r.id, "name": r.name, "output": r.output, "interfaces": list(r.interfaces)}
                for r in self.records if r.status == "converted"]

    def write_manifest(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.manifest(), indent=1, ensure_ascii=False) + "\n",
                              encoding="utf-8", newline="\n")
