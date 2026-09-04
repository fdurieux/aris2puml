#!/usr/bin/env python3
"""Fetch the five SAP reference EPCs of the corpus, which this repository
does not redistribute.

The 604 EPCs of the SAP R/3 reference model are published as one EPML
document under Creative Commons Attribution-NonCommercial-ShareAlike 3.0.
The NonCommercial clause is an added restriction that GPL-3.0-or-later
software may not carry, and it would follow any file derived from them,
so the models are fetched from upstream on demand instead of being kept
in git. What is in git is this script and the digests below: enough to
reproduce the same five files, byte for byte, and to notice if upstream
changes.

    python tools/corpus/fetch_sap.py                 # download and build
    python tools/corpus/fetch_sap.py --zip local.zip # from a local copy
    python tools/corpus/fetch_sap.py --verify        # check what is there

Output lands in ``tests/fixtures/corpus/sap/``, which is git-ignored. The
files are yours to use under the upstream licence, not this repository's.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from epml_to_json import convert  # noqa: E402

SOURCE_PAGE = "http://fundamentals-of-bpm.org/process-model-collections/"
ZIP_URL = ("https://www.dropbox.com/s/amotpexykz63rbr/"
           "EPC-EPML-Reference-Model.zip?dl=1")
MEMBER = "SAPModels.epml"
EPML_SHA256 = "d344dd98306bda06091fa8a2afda9edaf1a73ae6c2198f0869fdd3cbc7648bea"

# epcId in SAPModels.epml → the name the corpus README uses for it
MODELS = {
    "440": "sap-loan-origination",
    "439": "sap-loans-lifecycle",
    "441": "sap-loan-rollover",
    "459": "sap-currency-option-lifecycle",
    "171": "sap-outgoing-payments",
}

# What a correct run produces. A mismatch means upstream moved, not that
# your copy is broken — say so in the corpus README before repinning.
DIGESTS = {
    "source/sap-loan-origination.epml":
        "f0e76129fdff7c1d21ddaa31b4737c28d27cb2946439ad835ae021afc8b867bd",
    "source/sap-loans-lifecycle.epml":
        "e5a858ef7df15cee417e74d3b2a8b55d8381720e84c6ea2ce9bc4d6824672a2e",
    "source/sap-loan-rollover.epml":
        "16747fb26a1f5db5949be269aaf876ecaf0b2775f1f991e6cf2d537d4a18c38d",
    "source/sap-currency-option-lifecycle.epml":
        "5c696df2b2dc73fdd5cc3a4fdb72f369dda55ecb48798930863ab42d39fb34f6",
    "source/sap-outgoing-payments.epml":
        "2374d64dfa60bdb42e834acdd43bdb520938ffb80f65c0ea69953e4962d3133a",
    "sap-loan-origination.json":
        "d83044df639ca494c9fe170fc343cef1eb2c908078d07b9aaeb547343fb27fdb",
    "sap-loans-lifecycle.json":
        "658ef8ca8719da7f4fc15d814bb4c3f5856e0a87a22a093f270692d43efecb40",
    "sap-loan-rollover.json":
        "de8861065250e8d2533f1565861029551f7cfbd83c8c5a6aec7443e9348e21c2",
    "sap-currency-option-lifecycle.json":
        "5702e5c6270f36c21fde61ae4620751066582081b3bf7648eff022ec5da98563",
    "sap-outgoing-payments.json":
        "a78a322b188b65ee6900fd4c23527971576518ec1e7b00b830e692df14ed486c",
}

OUT = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "corpus" / "sap"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_epml(zip_path: Path | None) -> bytes:
    if zip_path is not None:
        blob = zip_path.read_bytes()
    else:
        print(f"downloading {ZIP_URL}", file=sys.stderr)
        with urllib.request.urlopen(ZIP_URL, timeout=120) as response:
            blob = response.read()
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        name = next(n for n in archive.namelist() if n.endswith(MEMBER))
        return archive.read(name)


def build(epml: bytes) -> dict[str, bytes]:
    """The five models, as {relative path: bytes}."""
    import json

    root = ET.fromstring(epml)
    files: dict[str, bytes] = {}
    for epc in root.iter("epc"):
        base = MODELS.get(epc.get("epcId"))
        if base is None:
            continue
        doc = ET.Element("epml")
        doc.append(epc)
        ET.indent(doc, space=" ")
        buffer = io.BytesIO()
        ET.ElementTree(doc).write(buffer, encoding="utf-8", xml_declaration=True)
        files[f"source/{base}.epml"] = buffer.getvalue()
        files[f"{base}.json"] = (
            json.dumps(convert(epc), indent=1) + "\n").encode("utf-8")
    missing = set(MODELS.values()) - {p.rsplit("/", 1)[-1][:-5] for p in files}
    if missing:
        raise SystemExit(f"not found in {MEMBER}: {', '.join(sorted(missing))}")
    return files


def report(files: dict[str, bytes]) -> int:
    drift = 0
    for path, data in sorted(files.items()):
        want = DIGESTS.get(path)
        got = digest(data)
        if want is None:
            print(f"  ?  {path}  (unpinned)")
        elif want == got:
            print(f"  ok {path}")
        else:
            drift += 1
            print(f"  DRIFT {path}\n       expected {want}\n       got      {got}")
    return drift


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--zip", type=Path, metavar="PATH",
                        help=f"a local copy of the archive from {SOURCE_PAGE}")
    parser.add_argument("--verify", action="store_true",
                        help="check the files already in place, fetch nothing")
    args = parser.parse_args(argv[1:])

    if args.verify:
        if not OUT.is_dir():
            print(f"{OUT} is not there; run without --verify to build it",
                  file=sys.stderr)
            return 1
        present = {str(p.relative_to(OUT)).replace("\\", "/"): p.read_bytes()
                   for p in sorted(OUT.rglob("*")) if p.is_file()}
        missing = sorted(set(DIGESTS) - set(present))
        drift = report(present)
        for path in missing:
            print(f"  MISSING {path}")
        return 1 if drift or missing else 0

    epml = load_epml(args.zip)
    if digest(epml) != EPML_SHA256:
        print(f"warning: {MEMBER} is not the pinned revision "
              f"({digest(epml)}); upstream may have republished it",
              file=sys.stderr)
    files = build(epml)
    (OUT / "source").mkdir(parents=True, exist_ok=True)
    for path, data in files.items():
        (OUT / path).write_bytes(data)
    print(f"wrote {len(files)} files to {OUT}")
    drift = report(files)
    print("\nThese files are Creative Commons Attribution-NonCommercial-"
          "ShareAlike 3.0,\nnot GPL: SAP R/3 reference model EPCs from\n"
          f"{SOURCE_PAGE}")
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
