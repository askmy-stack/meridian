"""Shared Kafka topic lists for Meridian ingestion pipeline."""

from __future__ import annotations

from typing import List

# GDELT conflict-related topics (see GDELTProducer)
GDELT_CONFLICT_TOPICS: List[str] = [
    "meridian.gdelt.conflict",
    "meridian.gdelt.protest",
    "meridian.gdelt.fight",
    "meridian.gdelt.assault",
    "meridian.gdelt.mass_violence",
]

# ACLED mapped event types (see ACLEDProducer.EVENT_TYPE_MAP values)
ACLED_TOPICS: List[str] = [
    "meridian.acled.conflict",
    "meridian.acled.violence",
    "meridian.acled.protest",
    "meridian.acled.riot",
    "meridian.acled.strategic",
    "meridian.acled.explosions",
]

# AISHub vessel topics (see AISProducer source_name="aishub")
AISHUB_TOPICS: List[str] = [
    "meridian.aishub.position",
    "meridian.aishub.port_call",
    "meridian.aishub.chokepoint_transit",
]

GRAPH_LOADER_TOPICS: List[str] = GDELT_CONFLICT_TOPICS + ACLED_TOPICS

ENTITY_RESOLUTION_TOPICS: List[str] = GDELT_CONFLICT_TOPICS + ACLED_TOPICS

VESSEL_LOADER_TOPICS: List[str] = AISHUB_TOPICS
