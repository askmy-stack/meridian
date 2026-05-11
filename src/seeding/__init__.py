"""Seeding module for Meridian.

Scripts to seed the knowledge graph with canonical data.
"""

from .ports_chokepoints import PortChokepointSeeder, CHOKEPOINTS, MAJOR_PORTS

__all__ = [
    "PortChokepointSeeder",
    "CHOKEPOINTS",
    "MAJOR_PORTS",
]
