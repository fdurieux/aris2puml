"""Fixture JSON → expected .puml, byte for byte. `tests/expected/order-to-cash.puml`
is pumllint's docs/process-demo/order_to_cash.puml with its comment lines
stripped — the pin that keeps the two repositories on one mapping table."""

import pytest

from aris2puml.emit import emit
from aris2puml.readers.json_ import read_json
from aris2puml.structure import structure
from tests.conftest import EXPECTED, FIXTURES


@pytest.mark.parametrize("fixture, expected", [
    ("order_to_cash.json", "order-to-cash.puml"),
    ("order_to_cash_draft.json", "order-to-cash-first-draft.puml"),
])
def test_fixture_emits_the_golden_diagram(fixture, expected):
    (proc,) = read_json(FIXTURES / fixture)
    text = emit(proc, structure(proc))
    assert text == (EXPECTED / expected).read_text(encoding="utf-8")
