# The private fixture

Your own ARIS exports go here, and nothing you put here is ever committed:
the directory is git-ignored except for this file. It exists because a
real process from a real ARIS repository usually cannot be published, and
the converter still has to be proven against one (ROADMAP A1).

## What to put here

The JSON files the report script `aris/export_epc.js` writes -- one file
per export, any number of processes per file, in the version-1 contract
the top-level README describes. Nothing else is read: `.puml` output,
sidecars and diagnostics belong in a directory outside the repository.

## What happens then

`python -m pytest -q tests/test_real.py` runs two checks over every file:

1. it reads as version-1 JSON, and every process in it is well formed;
2. every process converts without a refusal and lints clean under the
   guide's conventions (`tests/fixtures/conventions.toml`) -- the same
   command an adopter runs, `aris2puml FILE -o OUT --check -c CONVENTIONS`.

With this directory empty the module skips as a whole, so the suite is
green either way; the round trip is only ever claimed when a file is here.
One process passing both checks is the 0.2.0 exit criterion on the
roadmap; three are the 1.0.0 one. The suite runs only where the files are,
so that claim is yours to make, not CI's.

## When a check fails

A refusal (exit 2) names the node; run the same file with `--diagnose` to
see the EPC as a graph with that node in red, and restructure the model in
ARIS. The converter will not invent the structure. A finding (exit 1) is
pumllint's, and the guide explains each rule. Both are results, not
defects of the fixture: the point of this directory is to find out.

## What can be published

Figures, never files. Once the exports are here:

    python tools/corpus/private_set.py

prints the row for `tests/fixtures/corpus/README.md` -- the converted
count and percentage, the refusal buckets in that file's own names, and
the sidecar's approximated / dropped / flagged counts -- from the census
and the `--report` sidecar together, and refuses to print if the two
disagree. Paste it under *The private set* with the date it was measured;
it carries no process names and no diagram. A wider corpus you only want
measured, not proven, does not need to be here at all: the tool takes any
directory as its argument.
