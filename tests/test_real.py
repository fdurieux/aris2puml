"""The private fixture: the adopter's real ARIS exports, kept out of git.

``tests/fixtures/real/`` is git-ignored (ROADMAP A1, 2026-09-06: the
adopter's processes cannot be committed, and a private fixture counts
toward 1.0.0). Put the report script's JSON there and every process in it
must round-trip -- read as version-1 JSON, convert without a refusal, and
lint clean under the guide's conventions -- which is the 0.2.0 criterion
per process and, at three processes, the 1.0.0 one. With the directory
empty or absent this whole module skips, as it does without pumllint.

The wider corpus is not this directory: measure it with ``--report`` or
``tools/corpus/census.py`` wherever it lives, and write the row in
``tests/fixtures/corpus/README.md`` after it was measured.
"""

import contextlib
import io

import pytest

from aris2puml.cli import main
from aris2puml.readers.json_ import read_json
from tests.conftest import FIXTURES

REAL = FIXTURES / "real"
FILES = sorted(REAL.glob("*.json"))
if not FILES:
    pytest.skip("no private fixture: tests/fixtures/real/ holds no .json export",
                allow_module_level=True)
pumllint = pytest.importorskip("pumllint")
CONVENTIONS = FIXTURES / "conventions.toml"
IDS = [p.name for p in FILES]


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = main(argv)
    return rc, out.getvalue(), err.getvalue()


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_reads_as_version_1_json(path):
    procs = read_json(path)
    assert procs, f"{path.name}: no process in the document"
    for proc in procs:
        assert proc.validate() == [], f"{path.name} [{proc.id}]: {proc.validate()}"


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_round_trips_and_lints_clean_under_the_guide_conventions(path, tmp_path):
    """Exit 2 is a refusal (stderr names the node; ``--diagnose`` draws it),
    exit 1 is a pumllint finding, exit 0 with "No issues found" is the
    round trip."""
    rc, out, err = _run([str(path), "-o", str(tmp_path), "--check", "-c", str(CONVENTIONS)])
    assert rc != 2, f"{path.name}: refused -- {err.strip()}"
    assert rc == 0 and "No issues found" in out, f"{path.name}: findings --\n{out}"
