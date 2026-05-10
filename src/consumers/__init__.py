"""Kafka consumers module for Meridian.

Consumers that process events and update the knowledge graph.
"""

from .entity_resolution import EntityResolutionConsumer

__all__ = ["EntityResolutionConsumer"]
