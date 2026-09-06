# Working in this repository (agent pickup point)

Converter: ARIS EPC exports (a small notation-neutral JSON, or EPML) →
one PlantUML activity diagram per process → pumllint's conventions gate.
The core discipline: **the converter makes the EPC checkable, it never
makes it pass.** Defects pass through for pumllint to report, and an EPC
that does not reduce to nested single-entry, single-exit blocks is refused
with the node named. Every accepted shape is backed by a fixture from a
real model collection and a census figure, never by imagination.

## Read in this order when resuming

1. `ROADMAP.md` — status baseline at the top, the arcs with their gates,
   the **Never** list, the version plan at the bottom. Work is organised
   by roadmap item: find the item your task belongs to and read its dated,
   italicised log entries, which record what was measured and decided.
2. `README.md` — what goes in (the version-1 JSON), what comes out (the
   mapping table, one row per EPC element, with the pumllint rule that
   checks it), what is refused and why, the sidecar, `--strict`,
   `--diagnose`.
3. `tests/fixtures/corpus/README.md` — the nine real EPCs, what each does
   today, the census columns every figure in the docs comes from, and the
   licence reasons five of them are fetched rather than committed.
4. When the task touches the structuring pass or a reader: the fixtures
   before the code — `tests/test_structure.py`, `tests/test_loops.py`,
   `tests/test_entry.py`, then `aris2puml/structure.py`.
5. pumllint's `docs/business-processes.md` §2 — the mapping table this
   repository implements line for line; a mapping change starts there.

## Audiences and register

Every document here is written for one of two readers, and the register
follows the reader, not the topic:

- **Adopter-facing** — `README.md`, and anything an adopter meets first:
  assume no prior knowledge of ARIS, PlantUML or pumllint. Name a concept
  before using it, say what a flag does and what the reader gets back, and
  keep a plain-English walkthrough beside any command sequence the README
  recommends (the model is README §"The two commands, in plain English").
- **Maintainer-facing** — `ROADMAP.md`, the corpus README, this file,
  commit messages, PR bodies and chat replies: assume all of it. Terse,
  dense, symbols cited by name.

"Explain in plain English" is therefore the adopter register, not a
verbosity setting: apply it when the reader is an adopter, or when asked.
A prose walkthrough has no golden behind it, so `tests/test_docs_flags.py`
is its gate: every `--<name>` option that `README.md` or this file mentions must be
an option of aris2puml's CLI or, for the pumllint commands the README
recommends beside it, of pumllint's. Rename or drop an option and the
suite is red until the prose moves with it.

## Iron rules

- **No invented structure.** An EPC whose connectors do not reduce to
  nested single-entry, single-exit blocks is refused, with the node named.
  No "repair" path, no heuristic, no best-effort layout, however small the
  gap. This is the tool's reason to exist and carries no re-litigation
  clause.
- **Defects are preserved, never repaired.** A missing end event, an
  unnamed XOR outcome, a noun-named function all pass through so pumllint
  can report them.
- **No linting and no EPC semantic checks in this repository.** Rules
  live in pumllint; event/function alternation and connector pairing are
  ARIS's own checker's. A needed check goes to pumllint, and the mapping
  table moves in both repositories in the same change.
- **No EPC shape built from imagination.** A new accepted shape needs a
  fixture from the corpus (or a real ARIS export) showing modellers draw
  it, and the census figure saying how often.
- **Real-ARIS work is adopter-gated.** Items gated on an adopter with ARIS
  Architect (A1b, the report script at runtime; C1) cannot be closed by
  synthesising an export. Do not fake the fixture.
- **The JSON contract is version 1 and extends additively only.** A new
  optional field or array keeps version 1 (the `data` array under B3 is
  the precedent). Anything else is the 1.0.0 decision in the version plan
  and belongs to the maintainer.
- **A corpus figure is written down only after it was measured** by
  `tools/corpus/census.py` or `--report` over the set it describes. Never
  extrapolate one from an older figure or from a subset.
- **Roadmap log entries are appended, not rewritten.** Close an item by
  ticking it and adding a dated entry saying what shipped and what was
  measured. Correct an older entry only when it states a fact that was
  wrong when written, and say so in the commit.
- **Documentation moves with the work.** A change to what converts, what
  is refused, or what the sidecar counts updates `README.md`, the corpus
  README table, and the ROADMAP entry in the same commit.
- **Re-litigating a "Never" is the maintainer's decision**, taken on the
  clause recorded beside it. An agent may point at the clause; it may not
  act on it.

## Model & effort selection (advise before starting a task)

Every session picks a **model** and a **reasoning effort**. State the pair
a task wants before starting it, and again when the work changes shape
mid-session — the owner switches with `/model` (model), `/config`
(effort) and `/fast` (fast mode). The pair is a recommendation, never a
silent downgrade: cost/latency trades are the owner's call.

Effort is `low | medium | high | xhigh | max`. `xhigh` is Claude Code's
default and the best setting for most coding and agentic work on the
5-family; `high` is the quality/token sweet spot; `max` is for
"correctness matters more than cost"; `low` is for subagents and simple
mechanical steps. Haiku 4.5 has no effort knob. Context: 1M on Fable 5.1
/ Opus 5 / Sonnet 5, 200K on Haiku 4.5. API list price per 1M in/out —
Fable 5.1 $10/$50, Opus 5 $5/$25, Sonnet 5 $2/$10, Haiku 4.5 $1/$5 — so
an Opus 5 escalation costs ~2.5x a Sonnet 5 run and far less than one
invented structure shipped to a corpus of 4 332 models.

| Task | Model @ effort | Why |
| --- | --- | --- |
| The structuring pass — `structure.py`, entry regions, loop shapes, post-dominators, a new refusal | Opus 5 @ `xhigh` | Graph algorithms with refusal semantics; the failure mode is silently inventing structure, which no test catches until the next census. |
| A contract change — the JSON, the sidecar shape, the mapping table, a refusal message's wording | Opus 5 @ `xhigh`–`max` | Cross-repository contract; reason it through against pumllint's parser and docs before the first edit. |
| A new reader (Arc C) or the report script (A1) once its gate has fired | Opus 5 @ `xhigh` | Contract work under adopter evidence you cannot regenerate. |
| Long-horizon design where being wrong costs days — process hierarchy (B4), variant handling, the 1.0.0 freeze | Fable 5.1 @ `high`–`xhigh` | Give the whole spec up front and keep the prompt un-prescriptive. |
| Emitter or reader change with a golden fixture to match | Sonnet 5 @ `high` | Byte-for-byte expected output gives a tight loop; escalate if the golden must move. |
| Corpus census or measurement runs (SAP, BPMAI), corpus README columns | Sonnet 5 @ `medium`–`high` | Wall clock and bookkeeping; record the numbers, then stop. |
| Docs sync, log-entry correction, README wording, PR-to-green babysitting | Sonnet 5 @ `medium` | The facts come from running the CLI; the writing is short. |
| Read-only lookups: where a refusal is raised, what a fixture contains | Sonnet 5 @ `high`, Haiku 4.5 for a one-shot | Haiku's 200K context will not hold a corpus run's output. |
| Roadmap decisions, "Never" re-litigation, version bumps | — | Not an agent task; put the case to the maintainer. |

Standing rules:

- **Never downgrade for cost on structure-touching work.** Anything that
  can change what converts, what is refused, or a golden diagram runs at
  Opus 5 `xhigh` or above. Say when a task has crossed into that
  territory mid-session instead of pressing on.
- **Escalate on the second miss, don't grind.** A step that failed twice
  at Sonnet 5 is a signal to re-run at Opus 5 `xhigh` with the full task
  spec restated, not to try a third variation.
- **Heavy output eats context.** A BPMAI-wide census, a 4 332-file
  conversion log or a `--report` sidecar over the whole set belongs on a
  1M-context model, or behind a subagent that reads it and reports the
  conclusion.

## Environment & commands

Python 3.11 or 3.12, no runtime dependencies. Two optional extras: `test`
(pytest) and `check` (the pinned pumllint floor, used by `--check` and by
the three tests that lint the converter's output).

```bash
pip install -e ".[test,check]"            # both extras; CI installs exactly this
python -m pytest -q                       # "136 passed, 1 skipped" with pumllint
                                          # installed: the skip is test_real.py, the
                                          # private-fixture module, whole, until
                                          # tests/fixtures/real/ holds an export.
                                          # Without pumllint: "111 passed, 5 skipped" -
                                          # and each skip is a WHOLE MODULE (test_cli,
                                          # test_lanes, test_notes, test_docs_flags,
                                          # test_real: 25 tests never collected, the
                                          # cross-repo pin and the docs gate among
                                          # them), so a green run with 5 skips has
                                          # linted nothing; install [check] before
                                          # trusting a full-suite claim

aris2puml in.json -o out/                 # one .puml per process
aris2puml --from epml SAPModels.epml -o out/          # every EPC in an EPML document
aris2puml in.json -o out/ --check -c tests/fixtures/conventions.toml
                                          # then lint with the guide's config
aris2puml in.json -o out/ --report sidecar.json       # fidelity sidecar: what was
                                          # dropped, approximated, refused
aris2puml in.json -o out/ --strict        # approximations become refusals
aris2puml in.json -o out/ --diagnose      # <name>.refused.puml: the EPC as a
                                          # graph, offending node in red
aris2puml in.json -o out/ --notes         # data objects as `note right`
                                          # (off by default: GEN008 counts notes)
aris2puml in.json -o out/ --manifest m.json          # converted processes + interface
                                          # targets, the inventory for
                                          # `pumllint trace --requirements m.json`
aris2puml in.json -o -                    # stdout; refuses with --check/--diagnose

python tools/corpus/fetch_sap.py          # the five SAP EPCs into
                                          # tests/fixtures/corpus/sap/ (gitignored;
                                          # CC BY-NC-SA, never committed)
python tools/corpus/epml_to_json.py SAP.epml DIR      # whole collection to JSON
python tools/corpus/bpmai_to_json.py bpmai/models DIR # same for the BPMAI set
python tools/corpus/census.py DIR         # convert-or-refuse tally, refusals
                                          # bucketed by reason; the source of
                                          # every corpus figure in the docs
python tools/corpus/private_set.py [DIR]  # the corpus README's row for the
                                          # private set (tests/fixtures/real/ by
                                          # default): census + sidecar, printed
                                          # in the README's bucket names, refused
                                          # when the two disagree on `converted`
```

Scratch output (`out/`, `sidecar.json`) is not gitignored: write it outside
the repository or delete it before committing.

CI is `.github/workflows/tests.yml`: the pytest matrix on ubuntu and
windows for 3.11 and 3.12, then the console-script smoke step
(`aris2puml tests/fixtures/order_to_cash.json -o out --check -c
tests/fixtures/conventions.toml`). Windows is in the matrix because the
CLI writes diagrams with `newline="\n"` and prints forward-slash paths;
keep both when touching `cli.py`.

pumllint's floor is `check = ["pumllint>=0.33"]` in `pyproject.toml`, with
a comment naming the rule that needed the bump. Raise it only when the
suite needs a newer rule, and say which. To test against pumllint `main`
rather than the pinned release: `pip install -e ../pumllint` when the two
repositories sit side by side (roadmap item D1 automates this).

## Context that saves you an investigation

- **Refusals stop at the first defect.** `structure()` raises on the
  first `StructureError` it meets walking from the start, so a model can
  carry several and `--diagnose` shows only the first. Both mortgage
  corpus models refuse on an unstructured XOR join inside the credit
  decision (two XOR outcomes converging on one reject/approve action);
  the AND-split-joined-at-OR behind it is real and unreached.
- **The interface `ref` is carried twice, and only one copy is checkable.**
  The `' aris: interface <ref>` comment is for readers and `--diagnose`;
  pumllint's parser drops every comment line. The footer's
  `— interfaces: <ref>, …` suffix is what GEN007 and `pumllint trace` read,
  and `--manifest` plus `trace --fail-on-unknown-ref` is the hierarchy
  check (B4, shipped 2026-09-06). There is no rule behind it, and a
  variant-of relation would ride the same manifest when the contract
  grows one.
- **The version-1 JSON edges are `from`/`to`**, not `src`/`dst` (the
  in-memory `Edge` uses `src`/`dst`). A quick script over the fixtures
  needs the former.
- **The process carries one attribute: `owner`.** Product, segment,
  channel or any other facet is an additive contract change plus the
  report script, not an emitter tweak.
- **Corpus figures live in one place.** The README's paragraph quotes
  the headline columns (74.0 % SAP, 46.0 % BPMAI, 40.5 % under
  `--strict`); the full table and the earlier columns are in
  `tests/fixtures/corpus/README.md`. When the census moves, update both
  in the same commit, and quote the corpus README anywhere else.
- **The "no entry" refusal bucket is empty on SAP.** The three cases
  turned out to be a loop-header misclassification, fixed under B1. Do
  not build an argument on that bucket.
- **The private fixture is `tests/fixtures/real/`**, git-ignored except for
  its README, never committed (A1, 2026-09-06: the adopter's processes
  cannot be committed; a private fixture counts toward 1.0.0).
  `tests/test_real.py` proves every export there round-trips and lints
  clean, and skips as a whole module while the directory is empty. What
  reaches the repository is a census row in the corpus README, measured
  first. Do not put a synthetic export there to make the module run.
- **The nine-model corpus is four files in git plus five fetched.** Tests
  needing the SAP five skip when `sap/` is absent; run `fetch_sap.py`
  before measuring anything SAP-related. The four in git are BPMAI models
  drawn in Signavio — EPCs by notation only, not ARIS artefacts.
- **No public ARIS AML export exists.** ROADMAP item A1b records the
  search (ARIS Community, Zenodo, figshare, 4TU, the two DTD-only
  projects). Do not repeat it; the gate is an adopter with Architect.
- **The sidecar and the census count the same thing by different routes**
  and must agree on `converted`; a change to one is checked against the
  other over the corpus.
- **The golden diagram is pumllint's demo with comments stripped.** A
  mapping change starts in pumllint's `docs/business-processes.md` §2 and
  `docs/process-demo/`, then lands here as a regenerated
  `tests/expected/order-to-cash.puml`.
- **`--strict` is a set membership, not a string match**: it refuses the
  notes the structuring pass records (`APPROXIMATED` in `model.py` plus
  the two `backward` drops). Reader-level drops are the contract and stay
  out; adding a note code is what widens `--strict`.
- **Hosted sessions push through a branch-scoped git proxy, and cannot
  delete a branch.** Pushes to the designated branch work and the GitHub
  MCP tools open and merge PRs, but a branch-deleting push
  (`git push origin :refs/heads/<branch>`) is refused by the proxy with
  `HTTP 403` — and then prints `Everything up-to-date`, so read the whole
  output, never the last line. No MCP tool deletes a ref or changes a
  repository setting, and a direct API write to the settings endpoint is
  denied by the session's permission gate — reading it works
  (`delete_branch_on_merge` in the repository object). Delete-branch-on-
  merge was off until the 2026-09-06 hygiene pass (six stale branches
  here, twelve in pumllint, all deleted by the owner that day); it is an
  owner setting — `gh repo edit` with its delete-branch-on-merge option,
  or Settings → General → "Automatically delete head branches" — and a
  merged PR's branch vanishing is the sign it is on. Verify a ref with
  `git ls-remote origin 'refs/heads/*'`; deleting one is the owner's, via
  `gh api -X DELETE repos/fdurieux/aris2puml/git/refs/heads/<branch>` or
  the Branches page.

## Tests

```bash
pip install -e ".[test,check]"
python -m pytest -q
aris2puml tests/fixtures/order_to_cash.json -o out --check -c tests/fixtures/conventions.toml
```

The second line is the suite; the third is the end-to-end smoke CI runs
after it. `tests/test_golden.py` pins the emitter byte for byte against
pumllint's `docs/process-demo/order_to_cash.puml` with its comment lines
stripped. If a golden diagram changes on purpose, regenerate the expected
file and say so in the commit; never edit the expected file by hand.

After a change to the structuring pass or a reader, re-run the corpus
figures if they move, and update `tests/fixtures/corpus/README.md` and the
matching ROADMAP entry together.

## Pull requests

Standing authorisation from the maintainer: **open a PR, wait for CI to pass,
then merge it — no need to ask.** Wait for the whole matrix: ubuntu and
windows, Python 3.11 and 3.12, plus the console-script smoke step. Do not
merge on a red or pending run.

## Things that are contracts, not details

- **Exit codes** `0` / `1` / `2`: converted; `--check` found issues; an
  input could not be read or structured, or usage error. A refusal is
  always `2`, `--strict` included.
- **The version-1 JSON contract** (`README.md` "The intermediate JSON
  (version 1)"). Additive extensions only; a break is the 1.0.0 decision.
- **The sidecar shape** (`--report`, `aris2puml/report.py` docstring):
  versioned, and its `converted` count must equal the census's.
- **The mapping table** in README.md "What comes out" mirrors pumllint's
  `docs/business-processes.md` §2. Change them together, never one alone.
- **Refusal messages name the node id** and the reason verbatim; the
  sidecar and `--diagnose` read the ids from `StructureError`, never from
  the prose. Do not reword a refusal without checking both consumers.
- **Output file names are deterministic** and independent of input order:
  a duplicate slug gets the process id appended.

## Changes that span pumllint

pumllint's own `CLAUDE.md` governs there, with the same standing merge
authorisation; read it before touching that repository. The cross-repo
order: land and release the pumllint side first, then raise this
repository's floor if the change needs it, then land the aris2puml side
with the regenerated golden. Never leave the mapping table different in
the two repositories at a merge.
