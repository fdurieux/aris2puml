"""``tools/corpus/private_set.py`` prints the corpus README's rows for the
private set, from the census and the sidecar, and refuses to print when
they disagree. Exercised over two committed models: one that converts,
one the structuring pass refuses."""

import shutil
import subprocess
import sys

from tests.conftest import FIXTURES, ROOT

TOOL = ROOT.parent / "tools" / "corpus" / "private_set.py"


def _run(directory):
    p = subprocess.run([sys.executable, str(TOOL), str(directory)], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def test_prints_the_readme_rows_for_a_directory_of_exports(tmp_path):
    shutil.copy(FIXTURES / "order_to_cash.json", tmp_path)
    shutil.copy(FIXTURES / "corpus" / "mortgage-application.json", tmp_path)
    rc, out, err = _run(tmp_path)
    assert rc == 0, err
    lines = out.splitlines()
    assert lines[0] == "| the private set | 2 processes in 2 files |"
    assert lines[2] == "| converts | **50.0 %** (1) |"
    assert "| unstructured join | 50.0 % |" in lines
    assert lines[-1].startswith("| approximated / dropped / flagged over the converted (sidecar) | ")


def test_an_empty_directory_is_nothing_to_measure(tmp_path):
    rc, out, err = _run(tmp_path)
    assert rc == 2 and out == "" and "nothing to measure" in err
