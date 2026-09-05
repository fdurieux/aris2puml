from pathlib import Path

import pytest

from aris2puml.model import Edge, Lane, Node, Process

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
EXPECTED = ROOT / "expected"


def build(nodes, edges, lanes=(), pid="P-1", name="Test process", owner="QA") -> Process:
    """Compact process builder: nodes as (id, kind[, name[, lane[, ref]]])
    tuples, edges as 'a>b' strings, lanes as (id, name)."""
    ns = []
    for spec in nodes:
        nid, kind, *rest = spec
        nm = rest[0] if rest else ""
        lane = rest[1] if len(rest) > 1 else None
        ref = rest[2] if len(rest) > 2 else None
        ns.append(Node(nid, kind, nm, lane, ref))
    es = [Edge(*e.split(">")) for e in edges]
    proc = Process(pid, name, owner, [Lane(*l) for l in lanes], ns, es)
    assert proc.validate() == []
    return proc


@pytest.fixture
def build_process():
    return build
