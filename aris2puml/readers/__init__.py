"""Input formats → :class:`aris2puml.model.Process`."""

from aris2puml.readers.epml import read_epml
from aris2puml.readers.json_ import read_json

READERS = {"json": read_json, "epml": read_epml}

__all__ = ["READERS", "read_epml", "read_json"]
