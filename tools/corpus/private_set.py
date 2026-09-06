#!/usr/bin/env python3
"""Print the corpus README's rows for the private set, once it is measured.

The adopter's exports live in ``tests/fixtures/real/`` and never reach git
(ROADMAP A1, 2026-09-06); what reaches the repository is a census row. This
prints that row, in the bucket names ``tests/fixtures/corpus/README.md``
uses, from the two instruments every other figure there comes from — the
census over the structuring pass and the ``--report`` sidecar — and stops
if the two disagree on the converted count::

    python tools/corpus/private_set.py            # over tests/fixtures/real/
    python tools/corpus/private_set.py DIR        # over any directory of exports

Paste the table under *The private set* with the date it was measured.
The round-trip claim (every process converts *and* lints clean) is
``tests/test_real.py``'s, not this script's.
"""

from __future__ import annotations

import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import census                                                    # noqa: E402
from aris2puml.cli import convert                                # noqa: E402
from aris2puml.readers.json_ import ReadError, read_json         # noqa: E402
from aris2puml.structure import StructureError, structure        # noqa: E402

DEFAULT = ROOT / "tests" / "fixtures" / "real"

# README row name -> the census labels it sums. Anything else is "smaller
# refusals", listed under the table so nothing is folded away silently.
ROWS = (
    ("unstructured join", ("unstructured join",)),
    ("loop shapes (B1 residual)", ("loop shape not supported (roadmap B1)",)),
    ("split/join kind mismatch", ("split/join kind mismatch",)),
    ("reader refused (unnamed or malformed element)", ("reader: unnamed element", "reader: other")),
    ("no way out: a cycle that never reaches an end event",
     ("no way out: a cycle that never reaches an end event",)),
)


def measure(directory: Path) -> tuple[Counter[str], dict, int]:
    """The census tally, the sidecar summary, and the file count — or exit 2
    when the two instruments disagree on how many processes converted."""
    files = sorted(directory.glob("*.json"))
    tally: Counter[str] = Counter()
    for path in files:
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
                tally[census.bucket(str(exc))] += 1
    with tempfile.TemporaryDirectory() as out:
        summary = convert([str(p) for p in files], "json", out, collect=True).summary()
    if summary["converted"] != tally["converts"]:
        raise SystemExit(f"census and sidecar disagree on converted: "
                         f"{tally['converts']} vs {summary['converted']}")
    return tally, summary, len(files)


def rows(tally: Counter[str], summary: dict, files: int) -> list[str]:
    total = sum(tally.values())

    def pct(n: int) -> str:
        return f"{100 * n / total:.1f} %"

    lines = [f"| the private set | {total} processes in {files} files |", "|---|---|",
             f"| converts | **{pct(tally['converts'])}** ({tally['converts']}) |"]
    seen = {"converts"}
    for name, labels in ROWS:
        n = sum(tally[label] for label in labels)
        seen.update(labels)
        if n:
            lines.append(f"| {name} | {pct(n)} |")
    rest = {label: n for label, n in tally.items() if label not in seen}
    if rest:
        lines.append(f"| smaller refusals | {pct(sum(rest.values()))} |")
    lines.append("| approximated / dropped / flagged over the converted (sidecar) | "
                 f"{summary['approximated']} / {summary['dropped']} / {summary['flagged']} |")
    if rest:
        lines += ["", "smaller refusals: " + "; ".join(f"{label} ×{n}" for label, n in sorted(rest.items()))]
    return lines


def main(argv: list[str]) -> int:
    if len(argv) > 2:
        print(__doc__, file=sys.stderr)
        return 2
    directory = Path(argv[1]) if len(argv) == 2 else DEFAULT
    if not any(directory.glob("*.json")):
        print(f"nothing to measure: {directory.as_posix()} holds no .json export", file=sys.stderr)
        return 2
    tally, summary, files = measure(directory)
    print("\n".join(rows(tally, summary, files)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
