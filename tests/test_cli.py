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


UNSTRUCTURED = {"process": {"id": "U", "name": "Unstructured"},
                "nodes": [{"id": "e0", "kind": "event", "name": "S"}, {"id": "x1", "kind": "xor"},
                          {"id": "p", "kind": "event", "name": "P"}, {"id": "q", "kind": "event", "name": "Q"},
                          {"id": "x2", "kind": "xor"}, {"id": "r", "kind": "event", "name": "R"},
                          {"id": "t", "kind": "event", "name": "T"}, {"id": "j1", "kind": "xor"},
                          {"id": "j2", "kind": "xor"}, {"id": "fa", "kind": "function", "name": "A"},
                          {"id": "fb", "kind": "function", "name": "B"}, {"id": "ee", "kind": "event", "name": "E"}],
                "edges": [{"from": a, "to": b} for a, b in
                          [("e0", "x1"), ("x1", "p"), ("x1", "q"), ("p", "x2"), ("x2", "r"), ("x2", "t"),
                           ("r", "j1"), ("q", "j1"), ("t", "j2"), ("j1", "fa"), ("fa", "j2"), ("j2", "fb"),
                           ("fb", "ee")]]}

OR_PROCESS = {"process": {"id": "O", "name": "With an OR"},
              "nodes": [{"id": "e0", "kind": "event", "name": "Start"}, {"id": "o1", "kind": "or"},
                        {"id": "f1", "kind": "function", "name": "Do a"},
                        {"id": "f2", "kind": "function", "name": "Do b"}, {"id": "o2", "kind": "or"},
                        {"id": "f3", "kind": "function", "name": "Finish"},
                        {"id": "ee", "kind": "event", "name": "Done"}],
              "edges": [{"from": "e0", "to": "o1"}, {"from": "o1", "to": "f1"}, {"from": "o1", "to": "f2"},
                        {"from": "f1", "to": "o2"}, {"from": "f2", "to": "o2"}, {"from": "o2", "to": "f3"},
                        {"from": "f3", "to": "ee"}]}


def test_strict_turns_the_or_warning_into_a_refusal(tmp_path):
    src = tmp_path / "or.json"
    src.write_text(json.dumps(OR_PROCESS), encoding="utf-8")
    rc, out, err = _run([str(src), "-o", str(tmp_path / "out")])
    assert rc == 0 and "warning: " in err and "emitted as fork" in err
    rc, out, err = _run([str(src), "-o", str(tmp_path / "strict"), "--strict"])
    assert rc == 2 and out == ""
    assert err == "aris2puml: or.json [O]: o1: OR connector has no activity-diagram equivalent (refused under --strict)\n".replace("or.json", src.as_posix())
    assert not (tmp_path / "strict").exists()


def test_strict_with_a_report_records_the_refusal_and_its_reason(tmp_path):
    src = tmp_path / "or.json"
    src.write_text(json.dumps(OR_PROCESS), encoding="utf-8")
    side = tmp_path / "s.json"
    rc, _, _ = _run([str(src), str(FIXTURES / "order_to_cash.json"), "-o", str(tmp_path / "out"),
                     "--strict", "--report", str(side)])
    doc = json.loads(side.read_text(encoding="utf-8"))
    assert rc == 2 and doc["summary"]["converted"] == 1 and doc["summary"]["refused"] == 1
    refused, = [r for r in doc["processes"] if r["status"] == "refused"]
    assert refused["id"] == "O" and refused["reason"].endswith("(refused under --strict)")


def _named(pid, name):
    return {"process": {"id": pid, "name": name},
            "nodes": [{"id": "e", "kind": "event", "name": "S"}, {"id": "f", "kind": "function", "name": "F"},
                      {"id": "d", "kind": "event", "name": "D"}],
            "edges": [{"from": "e", "to": "f"}, {"from": "f", "to": "d"}]}


def test_two_processes_sharing_a_name_each_get_their_id_in_the_file_name(tmp_path):
    """Neither keeps the bare name, so which one owns it never depends on
    input order; the diagram's own @startuml name is the file stem."""
    a = tmp_path / "a.json"; a.write_text(json.dumps(_named("PROC-1", "New process")), encoding="utf-8")
    b = tmp_path / "b.json"; b.write_text(json.dumps(_named("PROC-2", "New process")), encoding="utf-8")
    c = tmp_path / "c.json"; c.write_text(json.dumps(_named("PROC-3", "Old process")), encoding="utf-8")
    side = tmp_path / "s.json"
    rc, out, err = _run([str(a), str(b), str(c), "-o", str(tmp_path / "out"), "--report", str(side)])
    assert rc == 0 and err == ""
    names = sorted(p.name for p in (tmp_path / "out").iterdir())
    assert names == ["new-process-proc-1.puml", "new-process-proc-2.puml", "old-process.puml"]
    for n in names:
        assert (tmp_path / "out" / n).read_text(encoding="utf-8").startswith(f"@startuml {n[:-5]}\n")
    outputs = [r["output"] for r in json.loads(side.read_text(encoding="utf-8"))["processes"]]
    assert len(set(outputs)) == 3


def test_a_bad_later_input_aborts_before_anything_is_written(tmp_path):
    """Every input is read before the first file is written (the output
    names need the whole run), so a document the reader refuses leaves no
    partial output behind."""
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    rc, _, err = _run([str(FIXTURES / "order_to_cash.json"), str(bad), "-o", str(tmp_path / "out")])
    assert rc == 2 and "bad.json" in err
    assert not (tmp_path / "out").exists()


def test_diagnose_draws_the_refused_process_and_points_at_it(tmp_path):
    src = tmp_path / "u.json"
    src.write_text(json.dumps(UNSTRUCTURED), encoding="utf-8")
    rc, out, err = _run([str(src), "-o", str(tmp_path / "out")])
    assert rc == 2 and not (tmp_path / "out").exists()          # without the flag: nothing extra
    rc, out, err = _run([str(src), "-o", str(tmp_path / "out"), "--diagnose"])
    drawing = tmp_path / "out" / "unstructured.refused.puml"
    assert rc == 2 and out == "" and drawing.exists()
    assert err.endswith(f"(see {drawing.as_posix()})\n")
    text = drawing.read_text(encoding="utf-8")
    assert text.startswith("@startuml unstructured-refused\n") and "#red" in text
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["unstructured.refused.puml"]


def test_diagnose_with_a_report_records_the_drawing(tmp_path):
    src = tmp_path / "u.json"
    src.write_text(json.dumps(UNSTRUCTURED), encoding="utf-8")
    side = tmp_path / "s.json"
    rc, _, _ = _run([str(src), str(FIXTURES / "order_to_cash.json"), "-o", str(tmp_path / "out"),
                     "--diagnose", "--report", str(side)])
    doc = json.loads(side.read_text(encoding="utf-8"))
    refused, converted = doc["processes"]
    assert rc == 2 and refused["diagnostic"].endswith("/unstructured.refused.puml")
    assert "diagnostic" not in converted and "\\" not in refused["diagnostic"]


def test_diagnose_needs_files():
    rc, _, err = _run([str(FIXTURES / "order_to_cash.json"), "-o", "-", "--diagnose"])
    assert rc == 2 and "--diagnose needs files" in err


def test_without_notes_the_sidecar_says_what_the_flag_would_add(tmp_path):
    src = FIXTURES / "corpus" / "project-financing-to-be.json"
    side = tmp_path / "s.json"
    rc, _, err = _run([str(src), "-o", str(tmp_path / "out"), "--report", str(side)])
    assert rc == 0 and err == ""                       # sidecar only, not stderr
    (rec,) = json.loads(side.read_text(encoding="utf-8"))["processes"]
    assert [d["code"] for d in rec["dropped"]] == ["data-omitted"] * 3
    assert "not drawn without --notes" in rec["dropped"][0]["detail"]
    rc, _, _ = _run([str(src), "-o", str(tmp_path / "notes"), "--notes", "--report", str(side)])
    (rec,) = json.loads(side.read_text(encoding="utf-8"))["processes"]
    assert rc == 0 and rec["dropped"] == []


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
                              "converted_percent": 50.0, "approximated": 0, "dropped": 0, "flagged": 0}


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
