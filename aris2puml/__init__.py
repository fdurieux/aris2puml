"""aris2puml — ARIS EPC export → PlantUML activity diagram.

The pipeline is three steps, each a module:

    readers  : an input format → :mod:`aris2puml.model` (a plain graph)
    structure: the graph → nested single-entry/single-exit blocks
    emit     : the blocks → PlantUML text, one diagram per process

The output follows the mapping table in pumllint's
docs/business-processes.md line for line, so a converted process lints
clean under that guide's conventions.toml when the EPC follows the
conventions, and reports the same findings when it does not.
"""

__version__ = "0.1.0"
