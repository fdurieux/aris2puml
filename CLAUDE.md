# Working on aris2puml

## Working in this repository (agent pickup point)

Read, in this order, before touching anything:

1. `README.md` — what goes in (the version-1 JSON), what comes out (the
   mapping table), what is refused and why.
2. `ROADMAP.md` — the status baseline at the top, the arcs with their
   gates, the **Never** list, and the version plan at the bottom. Work is
   organised by roadmap item; find the item your task belongs to and read
   its dated log entries, which record what was measured and decided.
3. `tests/fixtures/corpus/README.md` — the nine real EPCs, what each one
   does today, and the census figures every number in the docs comes from.

Then, when the task touches the structuring pass or a reader, look at how
the fixtures exercise it before reading the code: `tests/test_structure.py`,
`tests/test_loops.py`, `tests/test_entry.py`.

Conventions for recording work:

- A roadmap item is closed by ticking it and adding a dated, italicised
  log entry under it saying what shipped and what was measured. Older
  entries are history: append, do not rewrite, unless one states a fact
  that was wrong when written — then correct it and say so in the commit.
- A corpus figure (a percentage, a count of models) is written down only
  after running `tools/corpus/census.py` or `--report` over the set it
  describes. Never extrapolate one from an older figure.
- A finding about the tools that lives in prose (a mapping-table row, a
  refusal reason in the corpus table) is checked against the current CLI
  before it is repeated anywhere.

Iron rules — these are not judgement calls:

- **No invented structure.** An EPC that does not reduce to nested
  single-entry, single-exit blocks is refused, with the node named. Do
  not add a "repair" path, a heuristic, or a best-effort layout, however
  small the gap.
- **Defects are preserved, never repaired.** A missing end event, an
  unnamed XOR outcome, a noun-named function all pass through so pumllint
  can report them. The converter makes the EPC checkable; it does not
  make it pass.
- **No linting and no EPC semantic checks in this repo.** Rules live in
  pumllint. If a check is needed, it goes there, and the mapping table is
  updated in both repositories.
- **No EPC shape built from imagination.** A new accepted shape needs a
  fixture from the corpus (or a real ARIS export) showing that modellers
  draw it, and the census figure showing how often.
- **Real-ARIS work is adopter-gated.** Items marked as gated on an
  adopter with ARIS (A1b, the report script at runtime, C1) cannot be
  closed by synthesising an export. Do not fake the fixture.
- **The JSON contract is version 1 and extends additively only.** A new
  optional field or array keeps version 1; anything else is the 1.0.0
  decision in the version plan and belongs to the maintainer.
- **Re-litigating a "Never" is the maintainer's decision**, taken on the
  clause recorded next to it. An agent may point at the clause; it may
  not act on it.

## Environment & commands

Python 3.11 or 3.12, no runtime dependencies. Two optional extras:
`test` (pytest) and `check` (the pinned pumllint floor, used by `--check`
and by the three tests that lint the converter's output).

```bash
pip install -e ".[test,check]"            # both extras; CI installs exactly this
python -m pytest -q                       # 108 tests; 3 skip when pumllint is absent
aris2puml in.json -o out/                 # one .puml per process
aris2puml --from epml SAPModels.epml -o out/
aris2puml in.json -o out/ --check -c tests/fixtures/conventions.toml   # then lint
aris2puml in.json -o out/ --report sidecar.json --strict --diagnose    # fidelity gate
python tools/corpus/fetch_sap.py          # the five SAP EPCs, into tests/fixtures/corpus/sap/ (gitignored)
python tools/corpus/census.py DIR         # convert-or-refuse tally over a directory of JSON
```

`out/`, `sidecar.json` and anything else you write are not gitignored:
write scratch output outside the repository or delete it before
committing. `tests/fixtures/corpus/sap/` is gitignored on purpose (licence).

CI is `.github/workflows/tests.yml`: the pytest matrix on ubuntu and
windows for 3.11 and 3.12, then the console-script smoke step. Windows is
in the matrix because the CLI writes diagrams with `newline="\n"` and
prints forward-slash paths; keep both when touching `cli.py`.

pumllint's floor is set in `pyproject.toml` (`check = ["pumllint>=0.33"]`)
with a comment saying which rule needed the bump. Raise it only when the
suite needs a newer rule, and say which in the comment. To test against
pumllint `main` instead of the pinned release, install it from its
checkout: `pip install -e ../pumllint` when the two repositories sit side
by side.

## Context that saves you an investigation

- **Refusals stop at the first defect.** `structure()` raises on the first
  `StructureError` it meets walking from the start, so a model can carry
  several defects and `--diagnose` shows only the first. Both mortgage
  corpus models refuse on an unstructured XOR join in the credit
  decision; the AND-split-joined-at-OR behind it is real and unreached.
- **The interface `ref` goes nowhere yet.** The emitter writes it as
  `' aris: interface <ref>`, a comment; pumllint's parser drops every
  comment line, so neither its rules nor `pumllint trace` ever see it.
  `--diagnose` draws it. Cross-process resolution is roadmap item B4
  (`--manifest`), not a pumllint rule.
- **The version-1 JSON edges are `from`/`to`**, not `src`/`dst` (the
  in-memory `Edge` uses `src`/`dst`). A quick script over the fixtures
  needs the former.
- **The process carries one attribute: `owner`.** Product, segment,
  channel or any other facet would be an additive contract change plus
  the report script, not an emitter tweak.
- **The README's corpus figures are dated.** "32 % of BPMAI" is the
  pre-A2 census; the current columns (74.0 % SAP, 46.0 % BPMAI, 40.5 %
  under `--strict`) are in `tests/fixtures/corpus/README.md`. Quote that
  file, not the README paragraph.
- **The nine-model corpus is four files in git plus five fetched.** Tests
  that need the SAP five skip when `sap/` is absent; run `fetch_sap.py`
  before measuring anything SAP-related.
- **No public ARIS AML export exists.** ROADMAP item A1b records the
  search (ARIS Community, Zenodo, figshare, 4TU, the two DTD-only
  projects). Do not repeat it; the gate is an adopter with Architect.
- **The "no entry" refusal is empty on SAP.** The three cases turned out
  to be a loop-header misclassification, fixed under B1. Do not build an
  argument on that bucket.
- **The sidecar and the census count the same thing by different routes**
  and must agree on `converted`; a change to one is checked against the
  other over the corpus.
- **The golden diagram is pumllint's demo with comments stripped.** A
  mapping change starts in pumllint's `docs/business-processes.md` §2 and
  `docs/process-demo/`, then lands here as a regenerated
  `tests/expected/order-to-cash.puml`.

## Model & effort selection (advise before starting a task)

State, in the first message of a task, which model tier and effort the
task needs and whether the current session fits. If the session is
under-sized for the work, say so before starting rather than after.

| Task | Model tier | Effort | Why |
|---|---|---|---|
| Docs sync, corpus-table or log-entry correction, README wording | Haiku or Sonnet | low | The facts come from running the CLI; the writing is short |
| Emitter or reader change with a golden fixture to match | Sonnet | medium | Byte-for-byte expected output gives a tight feedback loop |
| Corpus census or measurement runs (SAP, BPMAI) | Sonnet | medium | Wall clock and bookkeeping, not reasoning; record the numbers, then stop |
| Structuring pass: `structure.py`, entry regions, loops, post-dominators | Opus or above | high | Graph algorithms with refusal semantics; the failure mode is silently inventing structure |
| Anything that changes the JSON contract, the sidecar shape, or the mapping table | Opus or above | high | Cross-repo contract; must be reasoned through against pumllint's parser and docs |
| A new reader (Arc C) | Opus or above | high | Gated on an adopter first; if the gate has fired, it is contract work |
| Roadmap decisions, "Never" re-litigation, version bumps | — | — | Not an agent task; put the case to the maintainer |

Effort means the reasoning budget the harness is set to, not how long to
spend. A low-effort session on a structuring change will pass the tests
and still be wrong on the next corpus; a high-effort session on a docs fix
is money spent on nothing.

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
- **The version-1 JSON contract** (`README.md` "The intermediate JSON (version 1)"). Extend it
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

## Working on pumllint (the companion repository)

A mapping change, a new construct the parser must model, or a rule the
converter's output needs usually touches pumllint too. Its own `CLAUDE.md`
governs there; the essentials, so a session spanning both repositories
does not have to open it first:

**Tests.** Both must pass:

```bash
python tests/run_tests.py     # zero-dependency runner (stdlib only) — the promise the project makes
python -m pytest              # the above plus the executable RULES.md spec (pytest-bdd)
```

Tests are plain assert functions, no fixtures, no third-party imports.
After changing `RULES.md`, run `python tools/extract_features.py` or CI
fails. After a deliberate scoring or reporter change, regenerate the
published pilot artefacts (`docs/example-maturity-report.html`,
`docs/example-badge.json`) with `pumllint score examples/`; a test
compares them byte for byte.

**Pull requests.** The same standing authorisation: open a PR, wait for CI
to pass, then merge — no need to ask. Wait for the whole matrix including
the `windows` job, the only one that exercises PowerShell argument
handling and the Windows console codec. Never merge on red or pending.

**Contracts, not details.** Exit codes `0` / `1` / `2` (the composite
action and both pre-commit hooks depend on them; a new "nothing was
checked" condition warns on stderr and keeps the exit code). Report
shapes for `-f json` (lint, score, trace), pinned by the shipped JSON
Schemas in `pumllint/schemas/`. Rule IDs, their kebab-case names and
config keys. Reported file paths use forward slashes on every platform
(compare against `Path.as_posix()`, never `str(path)`). All CLI output
goes through `_out`/`_err` in `pumllint/cli.py`; a bare `print()`
reintroduces the Windows crash those helpers exist to prevent.

When a change lands in both repositories, merge pumllint's first and
release it, then raise this repository's floor if the change needs it.
