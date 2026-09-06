"""``aris2puml`` — convert ARIS EPC exports to PlantUML activity diagrams.

Exit codes: 0 converted (and, with --check, pumllint found nothing at or
above its --fail-on); 1 --check found issues; 2 an input could not be read
or structured, or usage error.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from aris2puml import __version__
from aris2puml.diagnose import diagnose
from aris2puml.emit import emit, slug
from aris2puml.model import REPORT_ONLY, Note, Process
from aris2puml.readers import READERS
from aris2puml.readers.json_ import ReadError
from aris2puml.report import Report
from aris2puml.structure import StructureError, structure


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="aris2puml",
        description="Convert ARIS EPC exports (intermediate JSON) to PlantUML activity diagrams.",
    )
    ap.add_argument("inputs", nargs="+", help="export file(s)")
    ap.add_argument("-o", "--out", default=".", help="output directory, or '-' for stdout")
    ap.add_argument("--from", dest="fmt", choices=sorted(READERS), default="json",
                    help="input format (default: json)")
    ap.add_argument("--check", action="store_true",
                    help="run pumllint on the written diagrams (needs pumllint installed)")
    ap.add_argument("-c", "--config", help="pumllint config for --check")
    ap.add_argument("--fail-on", help="pumllint --fail-on for --check")
    ap.add_argument("--notes", action="store_true",
                    help="put each function's information objects, documents and IT systems "
                         "in a `note right` (off by default: pumllint's GEN008 counts notes)")
    ap.add_argument("--no-lane", metavar="LABEL", default="",
                    help="label for the swimlane of functions that have no org unit, in a "
                         "process that has swimlanes; blank by default, which pumllint's "
                         "ACT005 flags — the sidecar counts them either way")
    ap.add_argument("--diagnose", action="store_true",
                    help="for each process refused by the structuring pass, also write "
                         "<name>.refused.puml: the EPC drawn as a graph with the offending "
                         "node(s) in red and the reason as a note")
    ap.add_argument("--strict", action="store_true",
                    help="refuse what would otherwise be approximated or dropped, instead of "
                         "warning: OR connectors, OR-joined start events, mid-flow triggers, "
                         "and a `backward` return path that loses events or an org unit")
    ap.add_argument("--report", metavar="PATH",
                    help="write a fidelity sidecar (JSON) here: what each process dropped, "
                         "approximated or refused; a refusal is recorded and the run goes on")
    ap.add_argument("--version", action="version", version=f"aris2puml {__version__}")
    return ap


def _stem(proc: Process, stems: Counter[str]) -> str:
    """The output name: the process name's slug — and, when another process
    in the run shares that name, the process id as well, for every holder,
    so that no two diagrams land in one file and none depends on input
    order for keeping the bare name."""
    stem = slug(proc.name)
    return stem if stems[stem] == 1 else f"{stem}-{slug(proc.id)}"


def _flagged(proc: Process) -> list[Note]:
    """Model defects the diagram shows as they are: a function with no org
    unit in a process that has them (drawn in the no-lane lane), an org
    unit with no name (drawn as a blank lane)."""
    flagged: list[Note] = []
    if any(n.lane for n in proc.nodes):
        for n in proc.nodes:
            if n.kind in ("function", "interface") and n.lane is None:
                flagged.append(Note("no-lane", n.id,
                                    f"{n.id}: {n.name!r} has no org unit; drawn in the no-lane lane"))
    for lane in proc.lanes:
        if not lane.name.strip():
            flagged.append(Note("unnamed-lane", lane.id,
                                f"{lane.id}: org unit has no name; drawn as a blank lane"))
    return flagged


def convert(inputs: list[str], fmt: str, out: str, collect: bool = False,
            strict: bool = False, diagnose_refusals: bool = False,
            notes: bool = False, no_lane: str = "") -> Report:
    """Convert every process in ``inputs`` and account for each one.

    Raises ReadError / StructureError with the offending file and node —
    unless ``collect`` is set, in which case a refusal is recorded on the
    report and the run continues to the next process. Every input is read
    before anything is written, so the output names can be settled first.
    """
    read = READERS[fmt]
    report = Report()
    docs: list[tuple[Path, list[Process] | ReadError, dict[str, list[Note]]]] = []
    for inp in inputs:
        path = Path(inp)
        report.inputs.append(path.as_posix())
        dropped: dict[str, list[Note]] = {}
        try:
            docs.append((path, read(inp, dropped), dropped))
        except ReadError as exc:
            if not collect:
                raise
            docs.append((path, exc, dropped))
    stems = Counter(slug(proc.name) for _, procs, _ in docs
                    if not isinstance(procs, ReadError) for proc in procs)
    for path, procs, dropped in docs:
        if isinstance(procs, ReadError):
            report.refused(path, str(procs))
            continue
        for proc in procs:
            stem = _stem(proc, stems)
            try:
                s = structure(proc, strict)
            except StructureError as exc:
                drawing: Path | None = None
                if diagnose_refusals:
                    drawing = Path(out) / f"{stem}.refused.puml"
                    drawing.parent.mkdir(parents=True, exist_ok=True)
                    drawing.write_text(diagnose(proc, exc, stem), encoding="utf-8", newline="\n")
                if not collect:
                    where = f" (see {drawing.as_posix()})" if drawing else ""
                    raise StructureError(f"{path.as_posix()} [{proc.id}]: {exc}{where}",
                                         *exc.nodes) from exc
                report.refused(path, str(exc), proc.id, proc.name, drawing)
                continue
            text = emit(proc, s, stem, notes, no_lane)
            target: Path | None = None
            if out == "-":
                sys.stdout.write(text)
            else:
                target = Path(out) / f"{stem}.puml"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8", newline="\n")
            omitted = [] if notes else [
                Note("data-omitted", d.id,
                     f"{d.id}: {d.kind} {d.name!r} on {d.node} is not drawn without --notes")
                for d in proc.data]
            report.converted(path, proc.id, proc.name, target,
                             dropped.get(proc.id, []) + omitted + _flagged(proc) + s.notes)
    return report


def _check(paths: list[Path], config: str | None, fail_on: str | None) -> int:
    try:
        from pumllint.cli import main as pumllint_main
    except ImportError:
        print('aris2puml: --check needs pumllint (pip install "aris2puml[check] @ '
              'git+https://github.com/fdurieux/aris2puml")', file=sys.stderr)
        return 2
    argv = [p.as_posix() for p in paths]
    if config:
        argv += ["-c", config]
    if fail_on:
        argv += ["--fail-on", fail_on]
    return pumllint_main(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    for flag in ("check", "diagnose"):
        if getattr(args, flag) and args.out == "-":
            print(f"aris2puml: --{flag} needs files, not '-'", file=sys.stderr)
            return 2
    try:
        report = convert(args.inputs, args.fmt, args.out, collect=bool(args.report),
                         strict=args.strict, diagnose_refusals=args.diagnose,
                         notes=args.notes, no_lane=args.no_lane)
    except (ReadError, StructureError) as exc:
        print(f"aris2puml: {exc}", file=sys.stderr)
        return 2
    for r in report.records:
        if r.status == "refused":
            where = f"{r.input} [{r.id}]: " if r.id is not None else ""
            see = f" (see {r.diagnostic})" if r.diagnostic else ""
            print(f"aris2puml: {where}{r.reason}{see}", file=sys.stderr)
            continue
        for n in r.notes:
            if n.code not in REPORT_ONLY:
                print(f"aris2puml: warning: {r.input} [{r.id}]: {n.text}", file=sys.stderr)
    for p in report.written:
        print(f"wrote {p.as_posix()}")
    if args.report:
        try:
            report.write(args.report)
        except OSError as exc:
            print(f"aris2puml: cannot write report: {exc}", file=sys.stderr)
            return 2
        print(f"wrote {Path(args.report).as_posix()}")
    if report.any_refused:
        return 2
    if args.check:
        return _check(report.written, args.config, args.fail_on)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
