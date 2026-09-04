# Real-EPC corpus

Nine EPCs from two public model collections — four kept here, five
fetched on demand — so that the structuring pass is developed against
shapes real modellers drew rather than shapes the textbook suggests. The
roadmap's rule — *no EPC shape is built from imagination* — needs a
corpus; this is the first one.

**This is not Arc A1.** A1 wants an export from an adopter's own ARIS,
round-tripped through `aris/export_epc.js`, which is still the unverified
link in the chain. Nothing here went through that script: these models
come from public research collections in their own formats. What the
corpus does buy is the *shapes*, and a measurement of how many of them the
converter accepts (below).

## Which of these came from ARIS

This tool converts ARIS exports, so it matters that most of this corpus
did not come from ARIS:

| Models | Drawn in | ARIS artefact |
|---|---|---|
| the five `sap/` models | ARIS — the *ARIS for mySAP* database, IDS Scheer | yes |
| the four kept models | Oryx / Signavio, a browser editor | no |

The SAP models keep their ARIS identity in the data: each `<epc>` carries
an ARIS internal model id in its `name` attribute — `1Tr_fyhp`,
`1Ex_egln`, `1Im_lcbm` — under the German ARIS module prefixes (`1Tr`
Treasury, `1Ex` externes Rechnungswesen, `1Im` Immobilien). That is
first-hand evidence, readable in the fetched files. The onward step, ARIS
→ AML → EPML, is what the literature reports; it is not visible in the
data and is not verified here.

The BPMAI four are EPCs by notation only. They earn their place because
the shapes a modeller draws are what `structure.py` has to survive, and
because they are the corpus's only mortgage process — but they say
nothing about what an ARIS export looks like.

## Why there is no AML file here

AML — ARIS's own XML export, defined by `ARIS-Export.dtd` — is the format
`aris/export_epc.js` sidesteps and the one Arc C2 would read. No EPC in
it is public. Searched 2026-09-04, all empty:

- **ARIS Community** — the DTD ships on the ARIS DVD (`%ARISHOME%\aml\`)
  and in the ARIS Download Center; no sample export is attached to the
  posts that discuss it.
- **`stavnstrup/nisp2aris`** — carries the DTD and an XSL that *writes*
  AML, but its input is a NATO standards taxonomy: no EPC, and no AML
  output committed.
- **`koppor/oryx-editor`** — carries the DTD and Mendling's
  `AML2EPML_2.xslt` / `EPML2AML_2.xslt`, but grepping the whole tree for
  `<!DOCTYPE AML` and `<AML` returns nothing, and its `TestAMLSupport`
  is an empty stub.
- **Zenodo, figshare, 4TU** — nothing. Germany's *Nationale
  Prozessbibliothek* was restricted to public-sector staff and closed in
  2015.
- **ARIS Express `.adf`** — genuinely ARIS, and downloadable from ARIS
  Community, but the `model` and `data` members inside the ZIP are
  encrypted: high-entropy bytes, matching neither zlib, raw deflate,
  gzip, bzip2 nor LZMA. Only `metainfo.xml` and a `preview.js`
  drawing-command stream are readable, and rebuilding a graph from a
  render stream would be exactly the invented structure this project
  refuses.

AML export needs a licensed ARIS Architect or Designer. That is not a gap
a better search closes; it is A1b's adopter gate, stated in terms of what
can be downloaded.

Two things *are* public and will help C2 when it starts: the full AML
grammar (`ARIS-Export.dtd`, 431 lines, in `nisp2aris`; the Oryx copy is a
45-line subset) and the AML↔EPML stylesheets in Oryx. Neither carries the
numbers a reader needs — `TypeNum`, `SymbolNum` and `Model.Type` are all
declared `NMTOKEN`, so which integer means "function" or "XOR connector"
lives in ARIS's method tables and in no published document. That is the
same gap `aris/export_epc.js` warns adopters about in its header.

## Layout

    source/     the four kept files as published, in their upstream format
    *.json      the same models in the version-1 intermediate contract
    sap/        the five SAP models — fetched, git-ignored, not GPL

Four of the nine models are in the repository. The five SAP ones are not:
they carry a NonCommercial clause this repository cannot, so a script
rebuilds them from upstream instead (see *Sources* below):

    python tools/corpus/fetch_sap.py            # into sap/, git-ignored
    python tools/corpus/fetch_sap.py --verify   # check what is there

The `*.json` files — in both places — are what `aris2puml` reads.
Regenerate the four kept ones from `source/` with the converters in
`tools/corpus/`:

    python tools/corpus/bpmai_to_json.py source/ out/ 504129192

`bpmai_to_json.py` names its output by the model's own id; the four kept
files are renamed to say what they model. `fetch_sap.py` does the
renaming itself, over `epml_to_json.py`. All three drop what the contract
has no place for (information objects, IT systems, annotations) and pass
names through untouched — typos, line breaks and duplicate labels
included, because pumllint's job is to report them. `epml_to_json.py` no
longer owns its mapping: it writes what `aris2puml.readers.epml` produces,
so the fixtures and the CLI's `--from epml` cannot drift apart. Oryx JSON
has no reader and is not an accepted input format; adding one would be a
roadmap decision (Arc C), not something this corpus presumes.

## The models

| File | Models | Size | Today |
|------|--------|------|-------|
| `mortgage-application.json` | mortgage origination: application check, credit history, approval, property inspection, deed, mortgage insurance, disbursement | 11 f / 17 e / 7 xor / 1 and / 1 or, 41 edges | its rework loop is now a `backward`; still refused, on an AND split that joins at an OR |
| `mortgage-application-variant.json` | the same process modelled by a second author, with a rework loop and a disconnected fragment | 13 f / 18 e / 6 xor / 1 and / 1 or, 42 edges | its rework loop is now a `while`; still refused, on an AND split that joins at an OR |
| `project-financing-to-be.json` | customer-financing to-be process across two org units, escalating to the bank for release of funds | 15 f / 16 e / 6 xor / 3 and, 39 edges, 2 lanes | **converts** (A2: two entry events become the opening `if`) |
| `credit-application-de.json` | credit application over two intake channels: record customer data, check collateral, set conditions or reject | 5 f / 7 e / 2 xor / 2 and, 16 edges | **converts** (A2) |
| `sap/sap-loan-origination.json` † | SAP TR-LO loan origination: inquiry, application, credit standing, approval, offer, contract, disbursement | 7 f / 12 e / 4 xor, 22 edges | **converts**, with a mid-flow trigger warning (A2) |
| `sap/sap-loans-lifecycle.json` † | SAP TR-LO loans lifecycle: new transactions, rollover, accounting, expiring conditions | 3 f / 11 e / 5 xor / 1 or, 20 edges | **converts**, with the OR-split warning (A2) |
| `sap/sap-loan-rollover.json` † | SAP TR-LO rollover: select position, determine conditions, generate offer | 3 f / 7 e / 1 xor / 3 and, 14 edges | **converts** (A2) |
| `sap/sap-currency-option-lifecycle.json` † | SAP treasury: exercise, knock-in/out, expiry, termination, netting, settlement | 8 f / 17 e / 5 xor / 3 or, 33 edges | refused — a join reached without passing through its split; genuinely unstructured |
| `sap/sap-outgoing-payments.json` † | SAP FI-AP outgoing payments: release, automatic and manual runs, payment media | 4 f / 17 e / 2 xor / 3 and / 1 or, 27 edges | **converts**, with the OR-split warning |

† fetched by `tools/corpus/fetch_sap.py`, not in the repository.

`mortgage-application.json` is the complex credit process the corpus was
assembled around. It carries, in one diagram, most of what the roadmap is
short of: a rework loop back over the application check, a three-outcome
XOR on the loan amount, a conditional credit-history check, an AND fork
whose branches are a property inspection and a deed with a nested
insurance XOR, and an OR join before disbursement. Its variant is the
same process drawn by a different author — useful because the two
disagree on where the loop closes and on how the outcomes are named,
which is the kind of drift a conventions gate exists to catch.

No mortgage *lifecycle* model (servicing, arrears, redemption) is in
either collection; the loan lifecycle is represented by the SAP TR-LO
pair, at overview altitude.

## What the corpus measures

Run over every model in each upstream collection, not just the nine kept
here (`tools/corpus/census.py`):

| | SAP reference model (604 EPCs) | BPMAI (4332 EPCs) |
|---|---|---|
| converts | 26.3 % | 32.0 % |
| multiple start events (A2) | 69.5 % | 23.5 % |
| loop shapes (B1) | 0.7 % | 19.8 % |
| unstructured join or split/join mismatch | 1.0 % | 15.8 % |
| reader refused (unnamed or malformed element) | 2.5 % | 5.6 % |
| smaller refusals | — | 3.3 % |

*Those are the numbers before A2 shipped (2026-09-04, later the same
day). After it, re-run over the SAP set with the same command:*

| SAP reference model, after A2 | |
|---|---|
| converts | **73.7 %** (445 of 604; 68 of them with a mid-flow trigger warning) |
| unstructured join or split/join mismatch | 17.4 % |
| loop shapes (B1) | 4.1 % |
| reader refused (unnamed element) | 2.5 % |
| A2 residual: no entry at all (every start is a mid-flow trigger) | 0.5 % |
| unstructured cycle, connector-less splits, entry branches missing their join | 1.8 % |

*The BPMAI column is not re-run: its 388 MB archive is not cached here.
Its A2 share was 23.5 %, most of it the two-entry shape the four kept
models have, so the same order of gain is expected but not measured.*

Two collections, two very different populations — the SAP models are
generated overview diagrams with many entry points, the BPMAI models are
hand-drawn by students — and both put the same two items at the top:
**A2 first, B1 second**. Together they would move BPMAI from 32 % to
75 % and the SAP set from 26 % to 97 %. The unstructured-join share
is the floor: those models have no block structure to find, and refusing
them is the correct answer.

The 2.5 %–5.6 % of models the *reader* rejects are mostly elements with
an empty label. That is a contract question, not a structuring one: the
version-1 JSON requires a name on every function and event, and real
exports do not always have one.

The census and the CLI's `--report` sidecar count the same things by
different routes — the census over a directory of intermediate JSON, the
sidecar over one run's inputs — and must agree on `converted`. Reproduce
either column by downloading the collection (below), converting it whole,
and running the census:

    python tools/corpus/bpmai_to_json.py bpmai/models /tmp/all
    python tools/corpus/census.py /tmp/all

## Sources, licences and attribution

**BPM Academic Initiative model collection** (`mortgage-application`,
`mortgage-application-variant`, `project-financing-to-be`,
`credit-application-de`) — 29 810 models, 4332 of them EPCs, collected
from the academic BPM modelling platform. Version BPMAI-29-10-2019,
<https://doi.org/10.5281/zenodo.3758705>, published under **Creative
Commons Attribution 3.0**. Kept files are unmodified, under their upstream
model ids: 504129192, 1525267023, 1030995632, 278909031.

**EPC models of the ERP reference model** (the five `sap/` files) — 604
EPCs of the SAP R/3 reference model, distributed as one EPML document
with *Fundamentals of Business Process Management*,
<http://fundamentals-of-bpm.org/process-model-collections/>, under
**Creative Commons Attribution-NonCommercial-ShareAlike 3.0**.

That NonCommercial clause is an added restriction, and GPL-3.0-or-later
software may not carry one. It would also follow anything derived from
the models, the version-1 translations included. So this repository does
not redistribute them: `tools/corpus/fetch_sap.py` downloads the upstream
archive and rebuilds the five files into `sap/`, which `.gitignore`
excludes. What is in git is the script and a SHA-256 for each file it
produces, which is enough to reproduce the corpus byte for byte and to
notice if upstream republishes. Whoever runs it holds the result under
the upstream licence, not this repository's.

Each fetched file is one `<epc>` element lifted out of `SAPModels.epml`
unchanged; the `name` attribute is the ARIS model id the collection ships
(`1Tr_fyhp` and so on — the collection carries no model titles, so the
descriptions in the table above were read off the element labels and are
not in the data).

Note that a public repository has no private part: had the five files
been committed, they would have been published. Storing them instead of
fetching them means a second, private repository — a submodule or a
manual copy — and buys nothing this script does not already give, since
the models are a public download either way.

Nothing in this directory is packaged: `pyproject.toml` ships
`aris2puml*` only. The census columns above are reproducible from the
upstream downloads without keeping either collection in the repository.
