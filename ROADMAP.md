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
  *2026-09-06: an adopter's governance brief (two documents — a SAFe-CDP ×
  APQC taxonomy design with an artefact ledger, and a toolchain assessment
  placing this chain as "Loop A, commit-time" against process-mining
  conformance as "Loop B") was read against this roadmap and pumllint's;
  the reconciliation, twenty-one claim checks with file and line, is
  published beside the documents (https://claude.ai/code/artifact/c3e39034-e727-430b-8170-8ca152ea9b80).
  Its "sequence, not scope" is this item: build the export script first,
  then run advisory over the credit L3 set and read the sidecar before the
  findings — A1b, then the 0.3.0 criterion measured by A3. Nothing on the
  gate moves. One question for the maintainer, raised by the brief and not
  settled here: this item's deliverable is an anonymised real export
  committed under `tests/fixtures/real/`, and a bank's credit process may
  not be committable at all; the corpus README's fetched-not-committed
  shape (the SAP five) is the precedent if not. On such a corpus expect the
  first refusal to be the credit-decision join both mortgage models carry
  — two XOR outcomes converging on the approve/reject action — a modelling
  defect per B1's 2026-09-06 entry, so `--diagnose` is the answer, not a
  converter change.*
  *2026-09-06, decided by the maintainer: the adopter's credit processes
  cannot be committed, in any form. A1's deliverable therefore changes
  shape, not substance. What the item still delivers: the script fixed to
  the adopter's ARIS version and method filter, and one real EPC that
  round-trips — export → JSON → activity diagram → `--check` clean under
  the guide's conventions, the 0.2.0 criterion as written. What it no
  longer delivers: an export or a golden diagram in git. The fixture is
  private, in the shape the SAP five already have — `tests/fixtures/real/`
  git-ignored, populated by the adopter, every test that reads it skipping
  when it is absent — and what reaches the repository is what the corpus
  README already carries for the SAP set: a census row, refusal buckets,
  the sidecar's counts, no names and no diagram. The 1.0.0 criterion,
  "three real processes in the golden corpus", cannot be met by this
  adopter's processes as written; whether a private fixture counts toward
  it, or the golden corpus stays public and the criterion is re-read, is
  the maintainer's call and is not taken here.*
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
  *2026-09-06: a third bucket, `flagged` — a model defect the diagram
  shows as it is, neither dropped nor bent — added with the no-lane lane.
  Rendering checked for the first time over the whole BPMAI set: once a
  diagram uses swimlanes PlantUML wants one before `start` and rejects
  `||`, so 126 of the 1 994 converted diagrams (first function unowned,
  a later one owned) plus the empty-org-unit-name cases did not render;
  and a function with no org unit after an owned one silently inherited
  its lane — 322 of the 441 laned processes. Now, in a process that uses
  lanes, every action is drawn in its own and "no org unit" is a lane of
  its own: blank by default (ACT005 flags it, the honest signal), labelled
  by `--no-lane` on request, counted as `no-lane` either way. An org unit
  with no name is drawn as a blank lane and counted as `unnamed-lane`.
  Decision, by the maintainer, from a SWOT of blank / readable /
  lint-clean placeholders: blank, configurable, counted regardless — the
  count is what keeps a lint-clean label from hiding the gap. 1 670 of the
  1 994 diagrams are byte-identical; the 324 others differ only in lane
  lines.*
  *2026-09-05: the name collision is fixed. Measured first on BPMAI: 1 994
  processes converted into 1 833 files — 73 names shared by 234 processes,
  161 diagrams overwritten (`new-process` ×22, `neuer-prozess` ×17 …).
  Now a name shared within one run gets the process id appended for every
  holder, in the file name and the diagram's own `@startuml` name, so no
  file is overwritten and none depends on input order for keeping the
  bare name; every input is read before the first file is written, which
  the naming needs and which also means a document the reader refuses
  leaves no partial output behind.*
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
  *2026-09-06: the loop tail is written half by half. `repeat while (…)`
  took ` is (back) not (exit)` whenever either label existed, which left a
  bare `not` when the exit outcome has no event (PlantUML rejects it) and
  `is not (X)` when the back edge has none (PlantUML accepts and
  mis-parses it: the condition swallows the text). Seven loops in six of
  the 1 994 converted BPMAI diagrams; all render now, and the missing
  event stays missing, as it should. pumllint's `repeat while` regex read
  only the condition, so an eventless loop outcome was not an ACT003
  finding; closed upstream the same day (pumllint#137, released as 0.33.0):
  ACT003 now reads `is`/`not`/`endwhile` labels, and over the BPMAI set it
  reports exactly the 41 loops with neither label and the 10 with one
  missing. The floor is `pumllint>=0.33`.*
  *The SAP census moves 445 → 447 of 604. Neither mortgage model converts
  even now: both refuse on the XOR join before their approve/reject
  action, fed by outcomes of two different XOR splits — an unstructured
  join, and a real defect, not a loop shape. Behind it, the AND split
  after approval joins at an OR, a second defect the walk never reaches.*
- [x] **B2. `--strict`** *(2026-09-05)* — refuse OR connectors and any
  other approximation instead of warning, for teams gating on conversion
  fidelity. Small. *2026-09-04: folded mid-flow triggers (A2) are the
  second approximation this must refuse.*
  *Shipped on top of A3's notes: strict is a set membership, not a string
  match. Scope, chosen by the maintainer: everything the structuring pass
  records — the three approximations (OR connector, OR-joined start
  events, mid-flow trigger) and the two `backward` drops (return-path
  events, return-path org unit). Reader drops stay out: they are the
  contract, and B3 is their answer. Re-litigate the scope when B3 gives
  information objects a place in the diagram. Over the nine-model corpus
  `--strict --report` reads 3 of 9 (the three SAP OR approximations become
  refusals); over BPMAI 1 756 of 4 332 (40.5 %) convert faithfully, from
  46.0 % with approximations allowed.*
- [x] **B3. `--notes`** *(2026-09-05)* — information objects, documents and
  IT systems as `note right` on their function; opt-in because pumllint's
  GEN008 counts notes. Extends the JSON contract additively (a `"data"`
  array; version stays 1). Small emitter change; the report script grows a
  pass.
  *Shipped as designed: `"data"` items are `{id, kind, name, node, role?}`
  with `kind` ∈ information/document/system; one note per function, not
  per object, so GEN008 (≥ 4 notes and > 0.5 per element) stays quiet on
  any real process; a note follows a `backward` action too. The EPML reader
  carries `<dataField>`/`<application>` tied to a function by a
  `<relation>`; the BPMAI corpus tool carries `Data`/`System` shapes tied by
  a `Relation`; the report script gained its pass (information carriers,
  clusters, technical terms, application system types; still unrun).
  Demand, measured first: the SAP reference EPML carries no data element at
  all (only arc/event/function/connectors — not even roles), so nothing
  moves there; of the four kept BPMAI models one,
  `project-financing-to-be.json`, has three ERP-system objects, now in its
  fixture; the real source is ARIS, adopter-gated like the script. Without
  `--notes` every data object is a `data-omitted` record in the sidecar, so
  `--report` now measures what the flag would add.*
- [x] **B4. Process hierarchy** *(2026-09-06)* — a `--manifest` that writes the set of
  converted processes and their interface references, so pumllint lints
  them as one batch (XD004 across processes) and a missing referenced
  process is reported. Medium.
  *Shipped in its cheapest form, pulled forward on the 2026-09-06 review
  of the two repositories against a process-architecture brief: the
  interface's target id was written only as the `' aris: interface`
  comment, which pumllint's parser drops, so nothing downstream could
  ever resolve it. Now the footer also carries `— interfaces: <ref>, …`
  (node order, deduplicated; pumllint's §2 mapping row moved with it,
  pumllint#139), each converted sidecar record lists the same ids, and
  `--manifest PATH` writes the converted processes as the JSON array
  `pumllint trace --requirements` reads. No rule and no new pumllint code:
  `trace --fail-on-unknown-ref` over the manifest is the hierarchy check,
  a refused process is left out of the manifest so a link to it is
  reported, and the ARIS landscape passed as the inventory turns
  `--fail-on-uncovered` into landscape conformance. `--check` was already
  one pumllint invocation per run, so the XD004 half needed nothing. A
  variant-of relation between processes, when the JSON contract grows one,
  would ride the same manifest. The golden moves by its footer line only;
  the corpus figures do not move (no kept model carries an interface).*
  *2026-09-06, later: the adopter brief (see A1's entry of this date) puts
  two things on the process that the contract does not carry — a design
  lifecycle state (Draft … Published … Retired) and a capability-variant
  type — and asks whether either must cross into the projection. Neither
  does, today. "Cite Published processes only" is the inventory's shape,
  not the diagram's: export the Published set as the `--requirements`
  list and `trace --fail-on-unknown-ref` refuses every other reference,
  with no attribute in the JSON. The variant relation stays where this
  entry left it — it rides the manifest when the contract grows one — and
  the brief itself records the construct as not yet in the published
  method, so there is no demand to gate on; pumllint's typed
  diagram→diagram links item (Arc C, `ref over` / declared links) is the
  other half when there is. The contract stays at `owner`.*
- [x] **B5. Structure diagnostics** *(2026-09-05)* — on `StructureError`,
  write the partial diagram with the offending connector as a `#red` note
  so the modeller sees *where* to restructure, instead of an id on stderr.
  Medium, UX-only; do after B1 shows which errors real users hit.
  *Shipped as `--diagnose`, opt-in, and not as a partial activity diagram:
  there is no such thing — the refusal is the finding that the graph has
  no block structure, and the walk raises from inside a recursion whose
  half-built blocks live in stack frames, so anything drawn as an activity
  diagram would be invented structure. What can be drawn is the EPC
  itself: `<name>.refused.puml` is the process as a graph in PlantUML's
  component dialect, the node(s) the refusal names in red, the reason as a
  note, `!pragma layout smetana` pinned so it renders without Graphviz.
  `StructureError` now carries the ids it names, so nothing is parsed out
  of prose. The gate was met by the census: unstructured join is the first
  refusal in both collections (14.2 % of SAP, 19.6 % of BPMAI), and the
  drawing of `mortgage-application.json` shows its join fed by outcomes of
  two different XOR splits at a glance.*

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
  *2026-09-06: the adopter brief (A1's entry of this date) tags
  "pre-commit hook, GitHub Action, ratchet" as a fact of the chain; it is
  a fact of pumllint's half only — this item is the converter's, and the
  brief's pipeline is the CI adopter the gate names, once it exists. Gate
  unchanged.*
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

| Version | Contents | Exit criterion | Status (2026-09-06) |
|---|---|---|---|
| 0.1.0 (shipped 2026-09-04) | JSON contract v1, structure, emit, CLI, untested script | — | shipped |
| 0.2.0 | A1, A2, A3, A4 | one real EPC converts and lints clean under the guide's conventions | A2, A3 shipped; A1 adopter-gated (A1a served by the public corpus, A1b the script at runtime) and A4 waits on it — **open on the gate alone** |
| 0.3.0 | B1–B3, D1 | ≥ 90 % of the adopter's process corpus converts without refusal (measured by A3) | B2, B3 shipped, C0 shipped unplanned; B1 at its residual (the remaining loop shapes have no faithful activity-diagram form); D1 open; the criterion is measured on the adopter's corpus, so it cannot close before 0.2.0 |
| 0.4.0 | B4, B5, and C1 if its gate fired | — | B4, B5 shipped ahead of 0.2.0; C1 gated |
| 1.0.0 | JSON contract v1 frozen | three real processes in the golden corpus; D1 green for a month | open, on 0.2.0's gate and D1 |

*Read 2026-09-06: the contents column no longer orders the releases.
Everything in the 0.3.0 and 0.4.0 rows that was not adopter-gated shipped
before 0.2.0's gate fired, so the next cut — whatever its number — carries
A2–A3, B2–B5 and C0 on top of 0.1.0 and waits on A1 and A4 alone. Whether
that ships as 0.2.0 under the criterion as written, or the rows are
renumbered, is the maintainer's decision; this table records the state,
not the cut.*
