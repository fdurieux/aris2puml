"""Input formats → :class:`aris2puml.model.Process`."""

from aris2puml.readers.json_ import read_json

READERS = {"json": read_json}

__all__ = ["READERS", "read_json"]
