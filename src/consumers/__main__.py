"""CLI for Meridian Kafka consumers."""

from __future__ import annotations

import argparse
import os
import sys

import structlog

from .pipeline_topics import ENTITY_RESOLUTION_TOPICS

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


def run_graph_loader(bootstrap_servers: str, max_messages: int) -> int:
    from .graph_loader import GraphLoaderConsumer

    consumer = GraphLoaderConsumer(bootstrap_servers=bootstrap_servers)
    stats = consumer.run(max_messages=max_messages)
    logger.info("graph_loader_complete", **stats)
    print(
        f"Graph loader: loaded={stats['loaded']} skipped={stats['skipped']} errors={stats['errors']}"
    )
    return 0 if stats["errors"] == 0 else 1


def run_vessel_loader(bootstrap_servers: str, max_messages: int) -> int:
    from .vessel_loader import VesselLoaderConsumer

    consumer = VesselLoaderConsumer(bootstrap_servers=bootstrap_servers)
    stats = consumer.run(max_messages=max_messages)
    logger.info("vessel_loader_complete", **stats)
    print(
        f"Vessel loader: loaded={stats['loaded']} linked={stats['linked']} "
        f"errors={stats['errors']}"
    )
    return 0 if stats["errors"] == 0 else 1


def run_rag_indexer(bootstrap_servers: str, max_messages: int) -> int:
    from .rag_indexer import RagIndexerConsumer

    consumer = RagIndexerConsumer(bootstrap_servers=bootstrap_servers)
    stats = consumer.run(max_messages=max_messages)
    logger.info("rag_indexer_complete", **stats)
    print(
        f"RAG indexer: indexed={stats['indexed']} skipped={stats['skipped']} "
        f"errors={stats['errors']}"
    )
    return 0 if stats["errors"] == 0 else 1


def run_entity_resolution(bootstrap_servers: str, max_messages: int) -> int:
    from .entity_resolution import EntityResolutionConsumer

    consumer = EntityResolutionConsumer(bootstrap_servers=bootstrap_servers)
    consumer.subscribe(ENTITY_RESOLUTION_TOPICS)
    consumer.run(max_messages=max_messages or None)
    print(f"Entity resolution stats: {consumer.get_stats()}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Meridian Kafka consumers")
    parser.add_argument(
        "consumer",
        choices=["graph-loader", "vessel-loader", "entity-resolution", "rag-indexer"],
        help="Consumer to run",
    )
    parser.add_argument(
        "--bootstrap-servers",
        default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=int(os.getenv("PIPELINE_MAX_MESSAGES", "500")),
        help="Stop after N Kafka messages (0 = until idle)",
    )
    args = parser.parse_args()

    max_messages = args.max_messages if args.max_messages > 0 else None

    if args.consumer == "graph-loader":
        return run_graph_loader(args.bootstrap_servers, max_messages or 500)
    if args.consumer == "vessel-loader":
        return run_vessel_loader(args.bootstrap_servers, max_messages or 500)
    if args.consumer == "rag-indexer":
        return run_rag_indexer(args.bootstrap_servers, max_messages or 500)
    return run_entity_resolution(args.bootstrap_servers, max_messages or 500)


if __name__ == "__main__":
    sys.exit(main())
