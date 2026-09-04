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
- [ ] **A2. Multiple start events** — the most common refusal a real EPC
  will hit ("Order received" / "Order changed" joined by an XOR). Design:
  an XOR join of start events → `start` then an immediate `if`/`switch`
  with each event as a branch label and empty bodies that merge; an AND
  join → `start` then `fork` with `-> Event;` per branch. Structural change
  in `structure.py` (`_Walker.__init__` start handling); emitter unchanged.
  *2026-09-04: measured. 69.5 % of the 604 SAP reference EPCs and 23.5 %
  of the 4332 BPMAI EPCs are refused for this and nothing else — the
  largest single refusal in both collections, and the one that blocks
  every credit process in the corpus.*
- [ ] **A3. Fidelity sidecar** — per conversion, a JSON sidecar listing
  what was dropped (information objects, systems), approximated (OR →
  fork), refused (process, connector, reason). Turns "it converted" into a
  number a process owner can read, and is the evidence base for every
  later priority call. `--report sidecar.json` in `cli.py`.
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
- [ ] **B2. `--strict`** — refuse OR connectors and any other
  approximation instead of warning, for teams gating on conversion
  fidelity. Small.
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
