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
pip install aris2puml            # + pumllint for --check: pip install "aris2puml[check]"

aris2puml order_to_cash.json -o processes/
aris2puml order_to_cash.json -o processes/ --check -c conventions.toml --fail-on major
aris2puml order_to_cash.json -o -            # print the diagram
```

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
  "edges":   [{"from": "e1", "to": "f1"}, {"from": "f1", "to": "x1"}]
}
```

`kind` is one of `function`, `event`, `xor`, `and`, `or`, `interface`.
`lane` (functions and interfaces) is a lane id; `ref` (interfaces) is the
linked process id. A file may hold several documents under `"processes"`.
Information objects, documents and IT systems are not part of the
contract: the activity diagram has no place for them and the linter
nothing to check on them.

The contract is notation-neutral. A BPMN 2.0 XML reader targeting the
same `Process` model is the intended second front-end; none ships yet.

## What comes out

| EPC element | PlantUML | pumllint checks |
|-------------|----------|-----------------|
| function | `:Verb object;` on one line | ACT006 (verb-first), ACT004 |
| org unit on a function | `\|Org unit\|` swimlane, re-declared whenever the lane changes | ACT005, XD004 |
| start event | `start` then `-> Event;` | ACT001 |
| end event | `-> Event;` then `stop` | ACT002 |
| XOR with two outcomes | `if (First outcome?) then (Event A) … else (Event B) … endif` | ACT003 |
| XOR with more outcomes | `switch (Function outcome?)` / `case (Event)` … `endswitch` | ACT003 |
| AND split/join | `fork` / `fork again` / `end fork` | ACT004 |
| OR split/join | `fork` preceded by `' epc: OR-split <id>`, plus a warning on stderr | — |
| loop (back edge to an XOR join) | `repeat … repeat while (Back event?) is (Back event) not (Exit event)` | ACT004 |
| process interface | `' aris: interface <ref>` then `:Name;` | ACT006 |
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

- more than one start node (v1 supports exactly one start event);
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

## Development

```bash
pip install -e ".[test,check]"
python -m pytest
```

What comes next, and in what order: [ROADMAP.md](ROADMAP.md).
