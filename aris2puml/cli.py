"""``aris2puml`` — convert ARIS EPC exports to PlantUML activity diagrams.

Exit codes: 0 converted (and, with --check, pumllint found nothing at or
above its --fail-on); 1 --check found issues; 2 an input could not be read
or structured, or usage error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aris2puml import __version__
from aris2puml.emit import emit, slug
from aris2puml.model import REPORT_ONLY, Note
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
    ap.add_argument("--strict", action="store_true",
                    help="refuse what would otherwise be approximated or dropped, instead of "
                         "warning: OR connectors, OR-joined start events, mid-flow triggers, "
                         "and a `backward` return path that loses events or an org unit")
    ap.add_argument("--report", metavar="PATH",
                    help="write a fidelity sidecar (JSON) here: what each process dropped, "
                         "approximated or refused; a refusal is recorded and the run goes on")
    ap.add_argument("--version", action="version", version=f"aris2puml {__version__}")
    return ap


def convert(inputs: list[str], fmt: str, out: str, collect: bool = False,
            strict: bool = False) -> Report:
    """Convert every process in ``inputs`` and account for each one.

    Raises ReadError / StructureError with the offending file and node —
    unless ``collect`` is set, in which case a refusal is recorded on the
    report and the run continues to the next process.
    """
    read = READERS[fmt]
    report = Report()
    for inp in inputs:
        path = Path(inp)
        report.inputs.append(path.as_posix())
        dropped: dict[str, list[Note]] = {}
        try:
            procs = read(inp, dropped)
        except ReadError as exc:
            if not collect:
                raise
            report.refused(path, str(exc))
            continue
        for proc in procs:
            try:
                s = structure(proc, strict)
            except StructureError as exc:
                if not collect:
                    raise StructureError(f"{path.as_posix()} [{proc.id}]: {exc}") from exc
                report.refused(path, str(exc), proc.id, proc.name)
                continue
            text = emit(proc, s)
            target: Path | None = None
            if out == "-":
                sys.stdout.write(text)
            else:
                target = Path(out) / f"{slug(proc.name)}.puml"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8", newline="\n")
            report.converted(path, proc.id, proc.name, target,
                             dropped.get(proc.id, []) + s.notes)
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
    if args.check and args.out == "-":
        print("aris2puml: --check needs files, not '-'", file=sys.stderr)
        return 2
    try:
        report = convert(args.inputs, args.fmt, args.out, collect=bool(args.report),
                         strict=args.strict)
    except (ReadError, StructureError) as exc:
        print(f"aris2puml: {exc}", file=sys.stderr)
        return 2
    for r in report.records:
        if r.status == "refused":
            where = f"{r.input} [{r.id}]: " if r.id is not None else ""
            print(f"aris2puml: {where}{r.reason}", file=sys.stderr)
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
