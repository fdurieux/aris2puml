# aris2puml roadmap

Status baseline: **v0.1.0** (2026-09-04) shipped the version-1 JSON
contract, the structuring pass, the emitter, the CLI with `--check`, a test
suite pinned to pumllint's `docs/process-demo/` corpus, and an **untested**
ARIS report-script template. This file holds what remains, in priority
order, and the reasoning that closed what is not on it.

**How this file is laid out**: the *working agreements* — the
prioritisation method — come first, because every item below is ranked by
them; the **arcs** hold every open item as a `- [ ]` checkbox with its tier
and its gate; the **never** list is the decision log, each entry with the
condition that would reopen it. Annotate dated records in place rather
than rewriting them.

## Working agreements (read before picking anything up)

**Demand-driven, not missing pieces.** The tool exists for one path: a real
ARIS EPC → a PlantUML activity diagram → pumllint's conventions gate. Every
item is ranked on three questions, in this order:

1. **Does it unblock that path?** Anything on the path outranks everything
   off it.
2. **Is it a refusal a real EPC will hit?** Breadth of accepted shapes
   beats new front-ends: a refused process yields nothing.
3. **Cost, and who can pay it.** Items only an ARIS-holding adopter can
   validate are gated on that adopter, not on effort.

Tiers: **P0** now, blocking real use · **P1** next, breadth · **P2** later,
gated on a named trigger · **Never**, settled with a re-litigation clause.

Two rules that follow from the pin to pumllint:

- **Defects are preserved, never repaired.** A dangling flow gets no
  `stop`, an eventless XOR outcome a bare `else`, names pass through
  untouched. Any item that would make the converter "helpfully" fix a
  process is off the roadmap: repairing hides exactly what the linter
  exists to show.
- **No EPC shape is built from imagination.** Every new structuring shape
  needs a fixture from a real export first (Arc A1 creates that corpus).
  The v0.1.0 shapes were built from the textbook; the next ones come from
  the field.

## Arc A — Make the one path real (P0)

- [ ] **A1. Validate `aris/export_epc.js` against a real ARIS** — the
  unverified link. Everything downstream is speculative until one real EPC
  round-trips. Deliverable: the script fixed to the adopter's ARIS version
  and method filter, plus an anonymised real export committed under
  `tests/fixtures/real/` with its golden diagram. *Gate: an adopter with
  ARIS Architect. Owner: the adopter, with the maintainer pairing.* The
  cheapest item on this list and the highest-value one.
  *2026-09-04: still open. A public corpus now stands in for the shapes
  (`tests/fixtures/corpus/`, nine EPCs from the SAP reference model and
  the BPM Academic Initiative — the SAP five fetched, not redistributed,
  their licence being incompatible with ours) but not for the report
  script, which remains unrun.*
  *2026-09-04, later: the script's API calls were checked statically
  against the ARIS Report Scripting Best Practices guide and ARIS
  Community report code — confirmed and unconfirmed names are listed in
  the script's header; the one call found nowhere (`ObjOccGUID`) was
  replaced by a definition-GUID-plus-index id. Still unrun. A1 therefore
  reads as two halves: A1a, real-world shapes — served by the corpus and
  the census; A1b, the script at runtime — adopter-gated, unchanged.*
  *2026-09-04, later still: A1b's gate is confirmed unavoidable. A search
  for a public ARIS export in AML found none — not on ARIS Community, not
  in the two open-source projects that carry `ARIS-Export.dtd`
  (`nisp2aris`, `oryx-editor`, both DTD-and-stylesheet only), not on
  Zenodo, figshare or 4TU. ARIS Express `.adf` files are downloadable and
  genuinely ARIS, but their payload is encrypted. AML export needs a
  licensed Architect or Designer, so no amount of searching substitutes
  for the adopter. Recorded in `tests/fixtures/corpus/README.md`.*
- [x] **A2. Multiple start events** *(2026-09-04)* — shipped as *entry
  regions* plus *mid-flow triggers*. Entry region: start events grouped by
  the join each reaches, following the post-dominator tree, into nested
  `if`/`switch` (XOR join) or `fork` (AND/OR join) blocks right after
  `start`, the events as branch labels; chains of XOR joins flatten into
  one `switch`; a nested group's label is its event names joined by its
  join's word. Mid-flow trigger: a start event whose path meets a join fed
  from inside the flow (after a split) is folded into the arrow label at
  that join — merged with the preceding event's label — with an
  `' epc: external trigger` marker and a stderr warning; only pure
  event/join trees are folded, a trigger path carrying a function stays
  refused. Measured on the SAP set: **26.3 % → 73.7 %** converting (445 of
  604; 68 carry a trigger warning); every converted diagram passes
  PlantUML `-checkonly`. The flat "one virtual split" design was measured
  first and rejected at 47.6 %: SAP joins its entries in trees.
  *Decision record — rendering of mid-flow triggers, chosen by the
  maintainer 2026-09-04 from three options: fold into the arrow label and
  warn (chosen; 73.7 %), refuse with a precise message (63.1 %), or a
  `note` (counts against pumllint's GEN008). Re-litigate only with an
  adopter whose gate needs the refusal: B2's `--strict` is the planned
  form.* Residual: 0.5 % of the SAP set has no entry at all (every start
  is a trigger), recorded, not queued.
  *2026-09-04: measured. 69.5 % of the 604 SAP reference EPCs and 23.5 %
  of the 4332 BPMAI EPCs are refused for this and nothing else — the
  largest single refusal in both collections, and the one that blocks
  every credit process in the corpus.*
- [x] **A3. Fidelity sidecar** *(2026-09-04)* — shipped as
  `--report sidecar.json`: a versioned JSON document with a summary block
  (`converted_percent` is the number a process owner reads) and one record
  per process — *approximated* (OR → `fork`, a mid-flow trigger folded into
  an arrow label), *dropped* (a `backward` return path's events and org
  unit; reading EPML, the information objects and IT systems the contract
  never carried), *refused* (the connector and reason, verbatim). The
  structuring pass now records `Note(code, node, text)` rather than prose,
  and readers take an optional per-process notes channel, so the sidecar
  never re-parses a warning; the stderr wording is unchanged. With the
  flag a refusal is recorded and the run continues to the next process,
  which is what makes a corpus measurable; the exit code is still 2 when
  anything was refused, and without the flag behaviour is exactly as
  before. Over the nine-model corpus it agrees with `tools/corpus/census.py`
  to the process (6 of 9, 66.7 %). One thing it exposes rather than fixes:
  outputs are named from the process *name*, so two processes sharing a
  name overwrite one file — the sidecar shows both records pointing at it.
  The 0.3.0 criterion, "≥ 90 % converts, measured by A3", is now measurable.
  *2026-09-05: the first corpus-wide run exposed a hang. Seven BPMAI
  models — all tiny — contain a cycle that never reaches an end event (a
  connector whose only successor is itself, or a ring of connectors
  nothing leaves); the post-dominator fixed point degenerates on such
  nodes, its immediate-post-dominator links form a cycle instead of a
  tree, and the entry region's walk up that tree never ended. Fixed as a
  refusal, not a repair: a node that never reaches a sink is reported by
  id, the mirror of the "unreachable nodes" check at the other end. None
  of the seventeen models with the shape had converted, so no diagram
  changes. The BPMAI census now completes — **46.0 %** of 4332 convert
  after A2 and B1, from 32.0 % before — and `--report` over the whole
  collection agrees with it to the process.*
- [ ] **A4. PyPI release 0.2.0** once A1 has one real fixture. Until then
  the README says "install from git".

## Arc B — Breadth of accepted EPCs (P1, ordered by expected hit rate)

- [ ] **B1. Loop shapes** — today: one back edge from an XOR split (or its
  outcome event) to an XOR join. Add, each against a fixture from A1's
  corpus: test-at-top loops (`while`), loops whose body contains a
  split/join, two loops sharing a header.
  *2026-09-04: second-largest refusal, at 19.8 % of BPMAI (0.7 % of the
  SAP set, which barely models loops). `mortgage-application.json` and
  its variant are both refused here: the back edge leaves from an event
  that follows a function, not from an XOR outcome.*
  *2026-09-04, later: the back edges themselves were counted rather than
  the refusals — 2566 of them across the 1433 BPMAI models that have one,
  by the shape they make:*

  | Shape | BPMAI | SAP | Status |
  |---|---|---|---|
  | back edge from an XOR outcome event | 1041 | 8 | accepted since v0.1.0 |
  | activities on the return path (`backward`) | 695 | 8 | **refused** |
  | header not an XOR join — OR, AND or an activity | 426 | 17 | refused; no structured form |
  | XOR both merges the retry and decides (`while`) | 220 | 1 | **accepted now** |
  | back edge from the XOR split itself | 184 | 5 | accepted since v0.1.0 |

  *The `while` shape is done: one XOR that both merges and decides becomes
  `while … endwhile`, drawn from `mortgage-application-variant.json`
  (`tests/test_loops.py`).*
  *2026-09-04, later: the `backward` shape is done too. pumllint#135 added
  the mapping-table row and taught its parser to model the construct, so
  the action on a return path is checked by ACT006 like any other; this
  repo now emits `repeat … backward :Function; … repeat while (…)` when a
  loop's return path runs through exactly one function. Events and the org
  unit on that path are dropped — `backward` takes one action, no arrow and
  no swimlane — each with a warning, in the same spirit as the OR
  approximation. The 201 back edges with no function or several stay
  refused: there is no faithful form for them.*
  *Fixed in the same pass, because it blocked the shape entirely: a start
  event feeding a loop header was classified as a mid-process trigger (its
  header looks "fed from inside" by its own back edge), which left the
  canonical rework loop with no entry at all. That was an A2 residual, not
  a loop-shape problem — it accounted for all three "no entry" refusals in
  the SAP set, which now resolve to their real state.*
  *The SAP census moves 445 → 447 of 604. Neither mortgage model converts
  even now: both refuse on an AND split that joins at an OR, which is a
  real defect and not a loop shape.*
- [ ] **B2. `--strict`** — refuse OR connectors and any other
  approximation instead of warning, for teams gating on conversion
  fidelity. Small. *2026-09-04: folded mid-flow triggers (A2) are the
  second approximation this must refuse.*
- [ ] **B3. `--notes`** — information objects, documents and IT systems as
  `note right` on their function; opt-in because pumllint's GEN008 counts
  notes. Extends the JSON contract additively (a `"data"` array; version
  stays 1). Small emitter change; the report script grows a pass.
- [ ] **B4. Process hierarchy** — a `--manifest` that writes the set of
  converted processes and their interface references, so pumllint lints
  them as one batch (XD004 across processes) and a missing referenced
  process is reported. Medium.
- [ ] **B5. Structure diagnostics** — on `StructureError`, write the
  partial diagram with the offending connector as a `#red` note so the
  modeller sees *where* to restructure, instead of an id on stderr.
  Medium, UX-only; do after B1 shows which errors real users hit.

## Arc C — Second front-end (P2, gated)

- [x] **C0. EPML reader (`--from epml`)** *(2026-09-04)* — shipped ahead of
  C1 on evidence rather than demand: EPML is the one open EPC interchange
  format, and the only one with a real corpus behind it (the 604-process
  SAP reference model, `tests/fixtures/corpus/`). The mapping lives in
  `aris2puml/readers/epml.py`; `tools/corpus/epml_to_json.py` delegates
  to it so fixtures and reader cannot drift. Roles tied to functions
  become lanes; `processInterface` becomes an interface. Not a reader for
  Oryx/Signavio JSON — that stays corpus tooling (`bpmai_to_json.py`).

- [ ] **C1. BPMN 2.0 XML reader (`--from bpmn`)** — tasks → function,
  lanes → lane, exclusive/parallel/inclusive gateways → xor/and/or,
  start/end events → event, call activity → interface, one `Process` per
  participant. Covers ARIS-modelled BPMN and, incidentally, Camunda and
  Signavio exports. *Gate: an adopter with BPMN-in-ARIS who cannot use
  `bpmnlint` directly — the tool built for BPMN.* Medium-large; the
  `Process` model needs no change.
- [ ] **C2. AML reader** — read ARIS's native XML export, removing the
  report-script step. *Gate: sample AML files from at least two ARIS
  versions, because the schema is proprietary and version-dependent.*
  Large. Stays behind C1 unless A1 shows the report script is unworkable
  in the adopter's environment.
  *2026-09-04: the gate is firmer than it reads. No public AML EPC exists
  to sample from at all (see A1b's note), so both versions must come from
  adopters. What is public is the grammar — `ARIS-Export.dtd`, 431 lines,
  in `stavnstrup/nisp2aris` — and Mendling's AML↔EPML stylesheets in
  `koppor/oryx-editor`. Those settle the element structure but not the
  constants: `TypeNum`, `SymbolNum` and `Model.Type` are `NMTOKEN` in the
  DTD, so the integers for function, event and connector live in ARIS's
  method tables. A reader built on the DTD alone would parse the file and
  still not know what it read — the same gap `aris/export_epc.js` carries
  in its header.*

## Arc D — Operations (P2, wait for pull)

- [ ] **D1. Cross-repo drift job** — a scheduled CI job that runs the test
  suite against pumllint `main` (not the pinned release), so a change to
  pumllint's parser or rules that breaks the mapping is caught within a
  day. Small, high leverage; do it as soon as A4 exists.
- [ ] **D2. Composite GitHub Action and pre-commit hook** — mirror
  pumllint's; the CLI already has the exit codes. Wait for one CI adopter.
- [ ] **D3. `--from csv`** — a flat table export for teams whose ARIS
  administrators will not run scripts. Only if A1 reveals that is the
  blocker.

## Never (settled; each with its re-litigation clause)

- **No linting in aris2puml.** Rules live in pumllint; this tool only makes
  the EPC checkable. *Re-litigate if pumllint declines a process-specific
  rule an adopter needs and the check is only expressible on the graph.*
- **No EPC semantic checks** — event/function alternation, connector
  pairing, start/end-on-event. That is ARIS's own conventions checker.
  *Same clause as above.*
- **No BPMN output, no round-trip to ARIS.** One direction, one target.
  *Re-litigate only if a consumer other than pumllint appears that needs
  the intermediate model as its input — then the JSON, not a new emitter,
  is the product.*
- **No GUI, no ARIS plugin.** The report script is the integration
  surface. *Re-litigate if A1 shows report scripts are administratively
  blocked at typical adopters; D3 is the first fallback, not a plugin.*
- **No invented structure.** Unstructured EPCs are refused, never
  "repaired". *No clause: this is the tool's reason to exist.*

## Version plan

| Version | Contents | Exit criterion |
|---|---|---|
| 0.1.0 (shipped 2026-09-04) | JSON contract v1, structure, emit, CLI, untested script | — |
| 0.2.0 | A1, A2, A3, A4 | one real EPC converts and lints clean under the guide's conventions |
| 0.3.0 | B1–B3, D1 | ≥ 90 % of the adopter's process corpus converts without refusal (measured by A3) |
| 0.4.0 | B4, B5, and C1 if its gate fired | — |
| 1.0.0 | JSON contract v1 frozen | three real processes in the golden corpus; D1 green for a month |
