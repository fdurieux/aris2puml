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
| process interface | `' aris: interface <ref>` then `:Name;` | ACT006 |
| information object, document, IT system on a function | nothing, by default; with `--notes`, one `note right` per function listing them (`document: Order form`, `system: ERP`, `input: …`) | GEN008 |
| process name, id, owner | `@startuml <slug>`, `title`, `footer owner: … — ARIS process <id>` | GEN001/002/006/007 |

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

How often that bites, measured over two public EPC collections: 74 % of
the 604 SAP reference models convert today (26 % before several start
events were supported), and 32 % of the 4332 BPM Academic Initiative
models did at that earlier point, multiple start events accounting for
24 % of its refusals. The nine EPCs those numbers were read off — a mortgage
origination process among them — are in
[`tests/fixtures/corpus/`](tests/fixtures/corpus/README.md) with the
census and its method. Five of the nine are fetched rather than
redistributed, their licence being incompatible with this one; one
command builds them.

## Development

```bash
pip install -e ".[test,check]"
python -m pytest
```

What comes next, and in what order: [ROADMAP.md](ROADMAP.md).
