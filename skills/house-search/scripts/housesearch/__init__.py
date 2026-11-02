"""Deterministic helpers for the /house-search skill.

The agent does the reading, searching and judging. These modules do the parts
that must be exact and repeatable: vocabulary normalisation, geocoding,
nearby-place lookup, traffic maths, waterlogging matching, scoring and report
rendering. Everything is standard library only.
"""

__version__ = "0.1.0"
