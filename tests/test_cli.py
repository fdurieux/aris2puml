import contextlib
import io
import json
import re

import pytest

from aris2puml.cli import main
from tests.conftest import FIXTURES


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = main(argv)
    return rc, out.getvalue(), err.getvalue()


def test_writes_one_file_per_process_named_by_slug(tmp_path):
    rc, out, err = _run([str(FIXTURES / "order_to_cash.json"), str(FIXTURES / "order_to_cash_draft.json"),
                         "-o", str(tmp_path)])
    assert rc == 0 and err == ""
    assert sorted(p.name for p in tmp_path.iterdir()) == ["order-to-cash-first-draft.puml", "order-to-cash.puml"]
    assert "wrote" in out and "\\" not in out  # forward slashes on every platform


def test_stdout_mode_prints_the_diagram():
    rc, out, _ = _run([str(FIXTURES / "order_to_cash.json"), "-o", "-"])
    assert rc == 0 and out.startswith("@startuml order-to-cash\n") and out.endswith("@enduml\n")


def test_read_and_structure_errors_exit_2(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    rc, _, err = _run([str(bad), "-o", str(tmp_path)])
    assert rc == 2 and "bad.json" in err
    unstructured = tmp_path / "u.json"
    unstructured.write_text(
        '{"process": {"id": "U", "name": "U"}, "nodes": [{"id": "e", "kind": "event", "name": "S"},'
        ' {"id": "f", "kind": "function", "name": "F"}, {"id": "a", "kind": "function", "name": "A"},'
        ' {"id": "b", "kind": "function", "name": "B"}],'
        ' "edges": [{"from": "e", "to": "f"}, {"from": "f", "to": "a"}, {"from": "f", "to": "b"}]}',
        encoding="utf-8",
    )
    rc, _, err = _run([str(unstructured), "-o", str(tmp_path)])
    assert rc == 2 and "[U]" in err and "has 2 successors" in err
    assert not (tmp_path / "u.puml").exists()


def test_check_needs_files():
    rc, _, err = _run([str(FIXTURES / "order_to_cash.json"), "-o", "-", "--check"])
    assert rc == 2 and "needs files" in err


# --- --report: the fidelity sidecar ------------------------------------------

def test_report_writes_the_sidecar_and_leaves_the_exit_code_alone(tmp_path):
    side = tmp_path / "side.json"
    rc, out, err = _run([str(FIXTURES / "order_to_cash.json"), "-o", str(tmp_path / "out"),
                         "--report", str(side)])
    assert rc == 0 and err == ""
    assert f"wrote {side.as_posix()}" in out
    doc = json.loads(side.read_text(encoding="utf-8"))
    assert doc["version"] == 1 and doc["summary"]["converted"] == 1
    (rec,) = doc["processes"]
    assert rec["status"] == "converted" and rec["output"].endswith("/order-to-cash.puml")


def test_report_records_a_refusal_converts_the_rest_and_still_exits_2(tmp_path):
    bad = tmp_path / "u.json"
    bad.write_text(
        '{"process": {"id": "U", "name": "U"}, "nodes": ['
        '{"id": "e", "kind": "event", "name": "S"}, {"id": "f", "kind": "function", "name": "F"},'
        '{"id": "a", "kind": "function", "name": "A"}, {"id": "b", "kind": "function", "name": "B"}],'
        '"edges": [{"from": "e", "to": "f"}, {"from": "f", "to": "a"}, {"from": "f", "to": "b"}]}',
        encoding="utf-8",
    )
    side = tmp_path / "side.json"
    rc, out, err = _run([str(bad), str(FIXTURES / "order_to_cash.json"),
                         "-o", str(tmp_path / "out"), "--report", str(side)])
    assert rc == 2                                   # a refusal is still a 2
    assert "[U]" in err and "has 2 successors" in err  # and still said on stderr
    assert (tmp_path / "out" / "order-to-cash.puml").exists()  # the rest went on
    doc = json.loads(side.read_text(encoding="utf-8"))
    assert [r["status"] for r in doc["processes"]] == ["refused", "converted"]
    assert doc["summary"] == {"inputs": 2, "processes": 2, "converted": 1, "refused": 1,
                              "converted_percent": 50.0, "approximated": 0, "dropped": 0}


def test_exit_codes_do_not_move_with_report(tmp_path):
    """Whatever --report adds, the contract 0 / 2 stays where it is."""
    clean = [str(FIXTURES / "order_to_cash.json"), "-o", str(tmp_path / "a")]
    assert _run(clean)[0] == _run(clean + ["--report", str(tmp_path / "a.json")])[0] == 0
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    broken = [str(bad), "-o", str(tmp_path / "b")]
    assert _run(broken)[0] == _run(broken + ["--report", str(tmp_path / "b.json")])[0] == 2


def test_an_unwritable_report_path_is_an_output_error(tmp_path):
    rc, _, err = _run([str(FIXTURES / "order_to_cash.json"), "-o", str(tmp_path),
                       "--report", str(tmp_path / "no" / "such" / "dir" / "s.json")])
    assert rc == 2 and "cannot write report" in err


# --- the cross-repository pin: pumllint over the converter's output ----------

pumllint = pytest.importorskip("pumllint")
CONVENTIONS = FIXTURES / "conventions.toml"  # copy of pumllint's docs/process-demo/conventions.toml


def test_conforming_epc_lints_clean_under_the_guide_conventions(tmp_path):
    rc, out, _ = _run([str(FIXTURES / "order_to_cash.json"), "-o", str(tmp_path),
                       "--check", "-c", str(CONVENTIONS)])
    assert rc == 0 and "No issues found" in out


def test_draft_epc_reproduces_the_guide_findings(tmp_path):
    rc, out, _ = _run([str(FIXTURES / "order_to_cash_draft.json"), "-o", str(tmp_path),
                       "--check", "-c", str(CONVENTIONS), "--fail-on", "major"])
    assert rc == 1
    findings = sorted(re.findall(r"\[([A-Z]+\d+)/", out))
    assert findings == ["ACT002", "ACT003", "ACT005", "ACT005", "ACT006", "ACT006", "ACT006", "GEN006", "GEN007"]
