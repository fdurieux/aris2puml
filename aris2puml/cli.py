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
from aris2puml.readers import READERS
from aris2puml.readers.json_ import ReadError
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
    ap.add_argument("--version", action="version", version=f"aris2puml {__version__}")
    return ap


def convert(inputs: list[str], fmt: str, out: str) -> tuple[list[Path], list[str]]:
    """Convert every process in ``inputs``; returns (written paths, warnings).
    Raises ReadError / StructureError with the offending file and node."""
    read = READERS[fmt]
    written: list[Path] = []
    warnings: list[str] = []
    for inp in inputs:
        for proc in read(inp):
            try:
                s = structure(proc)
            except StructureError as exc:
                raise StructureError(f"{Path(inp).as_posix()} [{proc.id}]: {exc}") from exc
            text = emit(proc, s)
            warnings += [f"{Path(inp).as_posix()} [{proc.id}]: {w}" for w in s.warnings]
            if out == "-":
                sys.stdout.write(text)
            else:
                target = Path(out) / f"{slug(proc.name)}.puml"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8", newline="\n")
                written.append(target)
    return written, warnings


def _check(paths: list[Path], config: str | None, fail_on: str | None) -> int:
    try:
        from pumllint.cli import main as pumllint_main
    except ImportError:
        print("aris2puml: --check needs pumllint (pip install aris2puml[check])", file=sys.stderr)
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
        written, warnings = convert(args.inputs, args.fmt, args.out)
    except (ReadError, StructureError) as exc:
        print(f"aris2puml: {exc}", file=sys.stderr)
        return 2
    for w in warnings:
        print(f"aris2puml: warning: {w}", file=sys.stderr)
    for p in written:
        print(f"wrote {p.as_posix()}")
    if args.check:
        return _check(written, args.config, args.fail_on)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
