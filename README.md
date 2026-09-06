# aris2puml

Convert ARIS EPC exports into PlantUML **activity diagrams** that
[pumllint](https://github.com/fdurieux/pumllint) can gate on your naming
conventions. Zero runtime dependencies, Python ≥ 3.11, GPL-3.0-or-later.

This is the converter half of pumllint's
[Linting business processes](https://github.com/fdurieux/pumllint/blob/main/docs/business-processes.md)
guide. The guide owns the mapping table; this tool mechanises it. The
output is **activity diagrams, not BPMN** — if you have BPMN in hand, run
[`bpmnlint`](https://github.com/bpmn-io/bpmnlint) on it instead.

```bash
# Not on PyPI yet (roadmap A4) — install from git:
pip install git+https://github.com/fdurieux/aris2puml
pip install "aris2puml[check] @ git+https://github.com/fdurieux/aris2puml"   # + pumllint, for --check

aris2puml order_to_cash.json -o processes/
aris2puml order_to_cash.json -o processes/ --check -c conventions.toml --fail-on major
aris2puml order_to_cash.json -o -            # print the diagram
aris2puml --from epml SAPModels.epml -o out/  # every EPC in an EPML document
aris2puml corpus/*.json -o out/ --report sidecar.json  # + what each process dropped, approximated or refused
aris2puml corpus/*.json -o out/ --strict                # refuse what would be approximated or dropped
aris2puml corpus/*.json -o out/ --diagnose              # + <name>.refused.puml for each refusal: where, drawn
aris2puml corpus/*.json -o out/ --notes                 # + each function's documents and systems as a note
aris2puml corpus/*.json -o out/ --no-lane "Owner TBD"   # label the lane of functions that have no org unit
aris2puml corpus/*.json -o out/ --manifest manifest.json  # + the converted processes and their interface targets,
                                                          #   the inventory `pumllint trace` reads
```

Each process becomes `<process-name-slug>.puml`; when two processes in one
run share a name, every one of them gets its process id appended
(`new-process-proc-1.puml`), so no diagram overwrites another and none
depends on input order for keeping the bare name.

Exit codes: `0` converted (and, with `--check`, nothing at or above
`--fail-on`); `1` `--check` found issues; `2` an input could not be read
or structured, or usage error.

## Pipeline

```
ARIS report script  ──►  intermediate JSON  ──►  aris2puml  ──►  .puml  ──►  pumllint
(aris/export_epc.js)     (the contract below)    structure+emit             conventions gate
```

- **`aris/export_epc.js`** is an ARIS report-script template that walks a
  selected EPC and writes the JSON. **It is untested** — written against
  the documented ARIS Script API without an ARIS installation to run it
  on. Expect to adjust the object-type constants and attribute lookups to
  your ARIS version and method filter. The JSON contract is the stable
  part; keep that and everything downstream works.
- **`aris2puml/structure.py`** finds the block structure in the EPC graph
  and refuses, naming the connector, when there is none.
- **`aris2puml/emit.py`** writes PlantUML following the guide's mapping
  table line for line.

### Your own exports

You do not have to commit a real process to prove the converter on one.
Put the JSON the report script writes under `tests/fixtures/real/` -- the
directory is git-ignored, and its README says what goes there -- and
`python -m pytest -q tests/test_real.py` checks that every process in it
reads as version-1 JSON, converts without a refusal, and lints clean under
`tests/fixtures/conventions.toml`. With the directory empty the module
skips. One process passing is the roadmap's 0.2.0 exit criterion; three
are 1.0.0's. What reaches the repository afterwards is a census row in
the corpus README, never the export -- `python tools/corpus/private_set.py`
prints that row ready to paste.

## The intermediate JSON (version 1)

```json
{
  "version": 1,
  "process": {"id": "PROC-0042", "name": "Order to cash", "owner": "Sales Operations"},
  "lanes":   [{"id": "ou1", "name": "Sales"}],
  "nodes":   [{"id": "f1", "kind": "function",  "name": "Receive order", "lane": "ou1"},
              {"id": "e1", "kind": "event",     "name": "Order received"},
              {"id": "x1", "kind": "xor"},
              {"id": "p1", "kind": "interface", "name": "Handle complaint", "ref": "PROC-0051"}],
  "edges":   [{"from": "e1", "to": "f1"}, {"from": "f1", "to": "x1"}],
  "data":    [{"id": "d1", "kind": "document", "name": "Order form", "node": "f1", "role": "input"}]
}
```

`kind` is one of `function`, `event`, `xor`, `and`, `or`, `interface`.
`lane` (functions and interfaces) is a lane id; `ref` (interfaces) is the
linked process id. A file may hold several documents under `"processes"`.
`"data"` (optional) carries the information objects, documents and IT
systems hung on a function: `kind` is `information`, `document` or
`system`, `node` the function or interface, `role` (`input`/`output`)
optional. They are not control flow: the diagram shows them only with
`--notes`, and the linter has nothing to check on them.

The contract is notation-neutral, and it is not the only input:
`--from epml` reads EPML, the open EPC interchange format that ProM, EPC
Tools, bflow* and the academic model collections speak (same mapping,
`aris2puml/readers/epml.py`; roles tied to functions become lanes,
process interfaces become interfaces). A BPMN 2.0 XML reader targeting
the same `Process` model would be a third front-end; none ships, and the
roadmap says when one would.

## What comes out

| EPC element | PlantUML | pumllint checks |
|-------------|----------|-----------------|
| function | `:Verb object;` on one line | ACT006 (verb-first), ACT004 |
| org unit on a function | `\|Org unit\|` swimlane, re-declared whenever the lane changes | ACT005, XD004 |
| function with no org unit, in a process that has them | the *no-lane lane*: `\| \|`, blank, so ACT005 flags the missing owner — or the label `--no-lane` gives it; counted in the sidecar as `no-lane` either way. An org unit with no name is a blank lane too (`unnamed-lane`) | ACT005 |
| start event | `start` then `-> Event;` | ACT001 |
| several start events, joined before the first function | an *entry region*: `if`/`switch` (XOR join) or `fork` (AND/OR join) right after `start`, the events as branch labels, nested as the joins nest; a chain of XOR joins is one `switch`; a nested group's label is its event names joined by its join's word (`A or B`, `A and B`) | ACT003 |
| start event entering the flow at a join fed from inside the process (a *mid-flow trigger*) | folded into the arrow label at that join (merged with the preceding event's label: `-> Procured and Budget to be updated;`), preceded by `' epc: external trigger at <join> (<kind>)`, plus a warning on stderr | — |
| end event | `-> Event;` then `stop` | ACT002 |
| XOR with two outcomes | `if (First outcome?) then (Event A) … else (Event B) … endif` | ACT003 |
| XOR with more outcomes | `switch (Function outcome?)` / `case (Event)` … `endswitch` | ACT003 |
| AND split/join | `fork` / `fork again` / `end fork` | ACT004 |
| OR split/join | `fork` preceded by `' epc: OR-split <id>`, plus a warning on stderr | — |
| loop (back edge to an XOR join below the header) | `repeat … repeat while (Back event?) is (Back event) not (Exit event)` — each label only when the loop has that event | ACT003, ACT004 |
| loop whose XOR both merges the retry and decides | `while (Back event?) is (Back event) … endwhile (Exit event)` | ACT003, ACT004 |
| loop with one function on the return path | `repeat` … `backward :Function;` … `repeat while (…)`; events and the org unit there are dropped, with a warning | ACT006, ACT003, ACT004 |
| process interface | `' aris: interface <ref>` then `:Name;`, and `<ref>` in the footer (`— interfaces: <ref>, …`): the comment is for readers, the footer is what pumllint sees | ACT006; GEN007, `pumllint trace` |
| information object, document, IT system on a function | nothing, by default; with `--notes`, one `note right` per function listing them (`document: Order form`, `system: ERP`, `input: …`) | GEN008 |
| process name, id, owner | `@startuml <slug>`, `title`, `footer owner: … — ARIS process <id>` (then `— interfaces: …` when the process has any) | GEN001/002/006/007 |

**Defects are preserved, not repaired.** A flow that ends on a function
instead of an end event gets no `stop`, so pumllint's ACT002 reports the
missing end event; an XOR outcome with no event gets a bare `else`, so
ACT003 reports it; lane and function names are passed through untouched
for ACT005/ACT006. The converter's job is to make the EPC checkable, not
to make it pass.

`tests/expected/order-to-cash.puml` is pumllint's
`docs/process-demo/order_to_cash.puml` with its comment lines stripped,
and `tests/fixtures/conventions.toml` is that guide's configuration —
the test suite lints the converter's output with it, so the two
repositories cannot drift apart on the mapping without a test saying so.

## What is refused

`StructureError`, exit 2, nothing written for that process, the
offending node named:

- no entry at all: every start event is a mid-flow trigger, or a group of
  start events that share no join below their region;
- a start event entering mid-flow through a path that carries a function
  (only pure event trees are folded);
- a split whose branches do not all reach one join, or that jump into
  another split's region;
- an XOR split joined by an AND (or any kind mismatch);
- a loop that does not leave from an XOR split and re-enter at an XOR
  join, or a loop split with more than two outcomes;
- a function or event with more than one successor (a split without a
  connector);
- nodes unreachable from the start.

Structure the EPC first. The converter will not invent structure the
model does not have.

## Where it refused: `--diagnose`

A refusal names a connector id on stderr. `--diagnose` also draws it: for
each process the structuring pass refuses, `<name>.refused.puml` is written
beside the outputs — the EPC as the graph it is, events as ellipses,
functions as boxes, connectors as labelled circles, the node(s) the refusal
names in **red** and the reason as a note on the first of them. It is not
an activity diagram and is not meant to lint: the refusal *is* the finding
that the graph has no block structure, so any activity diagram of it would
be invented structure. It carries `!pragma layout smetana`, so it renders
wherever the activity diagrams do, with or without Graphviz. With
`--report`, the refused record carries the drawing's path as `diagnostic`.

## What was lost: the fidelity sidecar

`--report sidecar.json` writes, per run, the account the diagram itself
cannot carry — for every process, what was:

- **approximated** — the shape survives with its meaning bent: an OR split
  emitted as `fork`, a mid-flow trigger folded into an arrow label;
- **dropped** — an element with no place in the diagram: the events and the
  org unit on a `backward` return path; a data object tied to no function;
  and, without `--notes`, every data object the diagram would have shown
  with it (`data-omitted` — the sidecar measures what the flag would add);
- **refused** — the process, with the connector and the reason, verbatim;
- **flagged** — a defect the diagram shows as it is, neither dropped nor
  bent: a function with no org unit in a process that has them (drawn in
  the no-lane lane), an org unit with no name (drawn as a blank lane).
  Counted whatever `--no-lane` says, so a label that lints clean cannot
  hide a missing owner from the number.

A summary block gives the number a process owner reads
(`converted_percent`); the per-process records are the evidence the
roadmap is prioritised on. With `--report` a refusal is recorded and the
run **continues** to the next process instead of stopping at the first;
the exit code is still `2` when anything was refused. Reader-level drops
go into the sidecar only — they are the contract working as documented,
not a per-run surprise — while the structuring pass's approximations and
drops are also warned on stderr, as before.

## Process hierarchy: `--manifest`

A process interface is the one piece of cross-process structure an EPC
carries. Its target's id rides in the footer, so `pumllint trace` can
resolve it — and `--manifest manifest.json` writes the other half, the
inventory: a JSON array of the converted processes, each with the ids its
interfaces link to, in the form `trace --requirements` reads (objects with
an `id`; the rest rides along):

```json
[{"id": "PROC-0042", "name": "Order to cash", "output": "out/order-to-cash.puml",
  "interfaces": ["PROC-0051"]}]
```

```bash
aris2puml exports/*.json -o out/ --manifest manifest.json
pumllint trace out/ --requirements manifest.json -c conventions.toml --fail-on-unknown-ref
```

Every diagram cites its own id and its interfaces' targets, and the
inventory is the set of diagrams, so the matrix reads as: an **unknown
reference** is an interface whose target process has no diagram in the
batch — missing from the export, or refused (a refused process is left
out of the manifest on purpose, so a link to it is reported, not hidden);
coverage is complete by construction. Pass the ARIS process landscape as
the inventory instead of the manifest and `--fail-on-uncovered` names the
landscape entries no diagram realises. `--check` already lints the run's
diagrams as one batch, so pumllint's XD004 catches an org unit spelled
two ways across processes without any of this.

The same ids sit on each converted record of the sidecar (`interfaces`).

### The two commands, in plain English

For a reader who has never used either tool.

**The situation.** An organisation keeps its business processes as
diagrams in a modelling tool called ARIS. Each diagram is an event-driven
process chain, or EPC: a chain of events ("credit application received"),
functions ("check credit history"), and connectors that split and rejoin
the flow. Some functions are special. A *process interface* is a box that
says "at this point, another process takes over", and it carries the
identifier of that other process. It is how one process points at
another. Two small tools work on these diagrams. `aris2puml`, this one,
translates an EPC out of ARIS into a plain-text notation called PlantUML,
so the diagram can live in a code repository and be checked mechanically.
`pumllint` is a checker for PlantUML files, in the way a spell checker
checks prose: it reads diagrams, applies rules about how a well-formed
diagram should look, and reports what it finds. Together the two commands
answer one question: does every process that one of your diagrams points
at actually exist as a diagram? A process interface pointing at a process
nobody has drawn, or that was exported but could not be converted, is a
broken link in the process landscape.

**The first command, piece by piece.**

- `aris2puml` starts the converter.
- `exports/*.json` names the input. ARIS does not hand its diagrams to the
  converter directly; a small report script run inside ARIS exports each
  process as a JSON file — a plain-text file holding the process name, its
  identifier, its owner, its lanes for the organisational units involved,
  its nodes, and the arrows between them. The star is a wildcard, so this
  reads every such file in the folder `exports`. Each file is one process.
- `-o out/` says where the results go: one PlantUML text file per
  converted process, into the folder `out`, named after the process
  ("Order to cash" becomes `order-to-cash.puml`). Converting is not
  guaranteed. The converter refuses any process whose flow cannot be
  expressed as properly nested blocks — a branch that jumps into the middle
  of another branch, say — and refuses rather than guessing, because it
  must never invent structure the modeller did not draw. A refused process
  gets no output file and a message naming the exact connector at fault.
  Inside each converted file the converter writes a footer line carrying
  the process owner, the process's own identifier and the identifiers of
  every process its interfaces point at. That footer is where the second
  tool looks.
- `--manifest manifest.json` asks for one extra file: a list, in JSON, of
  every process that converted in this run — its identifier, its name,
  where its diagram was written, and which other processes it points at.
  Refused processes are deliberately left out, because they have no
  diagram. The manifest is the inventory of diagrams that now exist.

**The second command, piece by piece.**

- `pumllint trace` starts the checker in its tracing mode. Most of the
  time pumllint checks individual diagrams for style and completeness.
  Tracing mode builds a cross-reference table between an inventory of
  identifiers and the diagrams that mention them, then reports three kinds
  of mismatch. It was built for requirement identifiers, so a team could
  see which requirements a diagram realises; here the identifiers are
  process identifiers, and the machinery works unchanged.
- `out/` tells it which diagrams to read: every PlantUML file in the
  folder the first command filled. In each file it looks at the diagram's
  name and its title, header, footer, caption and notes, and collects every
  string that looks like an identifier. It does not read comment lines,
  which is exactly why the converter puts the identifiers in the footer
  rather than only in a comment.
- `--requirements manifest.json` supplies the inventory. The option's name
  comes from the tool's original purpose, but it accepts any list of
  identifiers, and the manifest is in the accepted shape. So the inventory
  is the set of processes that have a diagram.
- `-c conventions.toml` points at a configuration file. Among other things
  it tells pumllint what a process identifier looks like, as a pattern
  such as "`PROC-` followed by four digits". Without it the tool could not
  tell which words in a footer are identifiers. The same file configures
  the style checks, so the pattern is defined once.
- With the diagrams read and the inventory loaded, every identifier lands
  in one of three groups. An inventory entry no diagram mentions is
  *uncovered*. A diagram that mentions no identifier is *unlinked*. An
  identifier a diagram mentions that is absent from the inventory is an
  *unknown reference*. Here every diagram mentions its own identifier in
  its footer, so every entry is covered by at least its own diagram and no
  diagram is unlinked; the interesting group is the third. An unknown
  reference means a footer names a process its interfaces point at, and
  that process has no diagram in the batch — never exported, or exported
  and refused. That is the broken link.
- `--fail-on-unknown-ref` turns the report into a verdict. Without it the
  tool prints the table and exits normally. With it, the tool still prints
  the table but exits with a failure code if the third group is not empty.
  The exit code is the number a command hands back to whoever ran it, and
  automated pipelines read it: a failure makes a build go red, which is
  what turns the check into a gate a team can enforce on every change.

**What you get.** If everything is consistent, the second command prints
a summary saying all processes are covered with no unknown references,
and exits successfully. If not, it prints each missing identifier with
the diagram and line that points at it — "`PROC-0051` is referenced by
`order-to-cash.puml` at line 3 but is not in the inventory" — so the
process owner sees exactly which link is broken and where. One variation:
hand the second command the full list of processes from the ARIS process
landscape instead of the manifest, and the first group becomes meaningful
too — an *uncovered* entry is a process the landscape says exists but
nobody has a checkable diagram for, and `--fail-on-uncovered` gates on it
the same way.

## Gating on fidelity: `--strict`

`--strict` turns every approximation and drop the structuring pass would
otherwise record into a refusal: an OR connector, OR-joined start events,
a mid-flow trigger, a `backward` return path that loses its events or its
org unit. The message is the warning's first half plus
`(refused under --strict)`; the exit code is `2`, like any other refusal.
Reader-level drops are not in scope — they are the contract, not a choice
the converter made. `--strict --report` is the pair for a team gating on
fidelity: the sidecar's `converted_percent` is then the share of the corpus
that converts *faithfully*, and each refusal says what would have bent.

How often that bites, measured over two public EPC collections: 74.0 %
of the 604 SAP reference models convert today (26.3 % before several
start events were supported) and 46.0 % of the 4332 BPM Academic
Initiative models (32.0 % before; 40.5 % under `--strict`). The first
refusal in both is an unstructured join (14.2 % and 19.6 %); loop shapes
with no faithful form are the second on BPMAI (18.6 %). The nine EPCs
the shapes were developed against — a mortgage origination process among
them — are in [`tests/fixtures/corpus/`](tests/fixtures/corpus/README.md)
with the full census columns and their method. Five of the nine are fetched rather than
redistributed, their licence being incompatible with this one; one
command builds them.

## Development

```bash
pip install -e ".[test,check]"
python -m pytest
```

What comes next, and in what order: [ROADMAP.md](ROADMAP.md).
