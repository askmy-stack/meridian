"""Kafka consumers module for Meridian."""

__all__ = ["EntityResolutionConsumer", "GraphLoaderConsumer"]


def __getattr__(name: str):  # PEP 562 lazy exports
    if name == "EntityResolutionConsumer":
        from .entity_resolution import EntityResolutionConsumer

        return EntityResolutionConsumer
    if name == "GraphLoaderConsumer":
        from .graph_loader import GraphLoaderConsumer

        return GraphLoaderConsumer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
