# Working on aris2puml

## Tests

```bash
pip install -e ".[test,check]"
python -m pytest -q
aris2puml tests/fixtures/order_to_cash.json -o out --check -c tests/fixtures/conventions.toml
```

The second line is the suite; the third is the end-to-end smoke CI runs
after it. `check` pulls the pinned pumllint floor (`pumllint>=0.33`), which
the suite lints the converter's output with — the two repositories share
one mapping table, and `tests/test_golden.py` pins it byte for byte against
pumllint's `docs/process-demo/order_to_cash.puml` with its comment lines
stripped. If a golden diagram changes on purpose, regenerate the expected
file and say so in the commit; never edit the expected file by hand.

After a change to the structuring pass or a reader, re-run the corpus
figures if they move, and update `tests/fixtures/corpus/README.md` and the
matching ROADMAP entry together — the census (`tools/corpus/census.py`)
and the `--report` sidecar must agree on `converted`.

## Pull requests

Standing authorisation from the maintainer: **open a PR, wait for CI to pass,
then merge it — no need to ask.** Wait for the whole matrix: ubuntu and
windows, Python 3.11 and 3.12, plus the console-script smoke step. Do not
merge on a red or pending run.

## Things that are contracts, not details

- **Exit codes** `0` / `1` / `2`: converted; `--check` found issues; an
  input could not be read or structured, or usage error. A refusal is
  always `2`, `--strict` included.
- **The version-1 JSON contract** (`README.md` "What goes in"). Extend it
  additively only — a new optional array or field, version stays 1. A
  breaking change is the 1.0.0 decision in ROADMAP.md, not a patch.
- **The sidecar shape** (`--report`, `aris2puml/report.py` docstring):
  versioned, and its `converted` count must equal the census's.
- **The mapping table** in README.md "What comes out" mirrors pumllint's
  `docs/business-processes.md` §2. Change them together, never one alone.
- **Refusal messages name the node id** and the reason verbatim; the
  sidecar and `--diagnose` read the ids from `StructureError`, never from
  the prose. Do not reword a refusal without checking both consumers.
- **Defects are preserved, never repaired**, and **no invented structure**:
  an unstructured EPC is refused, not bent into blocks. Both are in
  ROADMAP.md's "Never" list with their re-litigation clauses.
- **Output file names are deterministic** and independent of input order:
  a duplicate slug gets the process id appended.
