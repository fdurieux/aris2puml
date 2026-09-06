"""The prose gate: every ``--flag`` README.md and CLAUDE.md mention exists.

A plain-English walkthrough has no golden behind it, so this is what keeps
it from lying after an option is renamed: each documented flag must be an
option of aris2puml's parser or, for the pumllint commands the README
recommends beside it, of one of pumllint's. Needs pumllint, like the other
cross-repository pins.
"""

import re
from pathlib import Path

import pytest

from aris2puml.cli import _parser

pumllint_cli = pytest.importorskip("pumllint.cli")

ROOT = Path(__file__).resolve().parents[1]
DOCS = ("README.md", "CLAUDE.md")
FLAG = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]*")


def _options(parser) -> set[str]:
    return {o for o in parser._option_string_actions if o.startswith("--")}


def _pumllint_options() -> set[str]:
    flags: set[str] = set()
    for name, build in vars(pumllint_cli).items():
        if name.startswith("build_") and name.endswith("parser") and callable(build):
            flags |= _options(build())
    return flags


def test_every_documented_flag_is_an_option_of_one_of_the_two_tools():
    ours, theirs = _options(_parser()), _pumllint_options()
    assert "--manifest" in ours and "--fail-on-unknown-ref" in theirs  # the probe works
    for doc in DOCS:
        text = (ROOT / doc).read_text(encoding="utf-8")
        for flag in sorted({m.group() for m in FLAG.finditer(text)}):
            assert flag in ours or flag in theirs, f"{doc} mentions {flag}, which neither tool accepts"
