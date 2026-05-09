"""CLI entry point for running producers."""
import argparse
import os
import sys
from datetime import datetime, timedelta

import structlog

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def run_gdelt(bootstrap_servers: str) -> int:
    """Run GDELT producer."""
    from .gdelt_producer import GDELTProducer
    
    logger.info("starting_gdelt_producer")
    
    producer = GDELTProducer(bootstrap_servers=bootstrap_servers)
    
    # Fetch last 1 hour
    count = producer.fetch_and_publish(hours_back=1)
    
    logger.info("gdelt_producer_complete", published_count=count)
    return count


def run_acled(bootstrap_servers: str, days: int = 7) -> int:
    """Run ACLED producer."""
    from .acled_producer import ACLEDProducer
    
    api_key = os.getenv("ACLED_API_KEY")
    email = os.getenv("ACLED_EMAIL")
    
    if not api_key or not email:
        logger.error(
            "acled_credentials_missing",
            set_key=bool(api_key),
            set_email=bool(email)
        )
        print("Error: ACLED_API_KEY and ACLED_EMAIL environment variables required")
        return 0
    
    logger.info("starting_acled_producer", days_back=days)
    
    producer = ACLEDProducer(
        api_key=api_key,
        email=email,
        bootstrap_servers=bootstrap_servers
    )
    
    count = producer.fetch_and_publish(days_back=days)
    
    logger.info("acled_producer_complete", published_count=count)
    return count


def run_ais(bootstrap_servers: str) -> int:
    """Run AIS producer."""
    from .ais_producer import AISProducer
    
    username = os.getenv("AISHUB_USERNAME")
    password = os.getenv("AISHUB_PASSWORD")
    
    if not username:
        logger.warning("aishub_username_missing")
        print("Warning: AISHUB_USERNAME not set - will try public data only")
    
    logger.info("starting_ais_producer")
    
    producer = AISProducer(
        username=username,
        password=password,
        bootstrap_servers=bootstrap_servers
    )
    
    # Fetch chokepoint vessels
    count = producer.fetch_and_publish(filter_chokepoints=True)
    
    logger.info("ais_producer_complete", published_count=count)
    return count


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Meridian Data Producers"
    )
    parser.add_argument(
        "source",
        choices=["gdelt", "acled", "ais", "all"],
        help="Data source to ingest"
    )
    parser.add_argument(
        "--bootstrap-servers",
        default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        help="Kafka bootstrap servers"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Days of history (for ACLED)"
    )
    
    args = parser.parse_args()
    
    logger.info(
        "producer_cli_started",
        source=args.source,
        bootstrap_servers=args.bootstrap_servers
    )
    
    try:
        if args.source == "gdelt":
            count = run_gdelt(args.bootstrap_servers)
        elif args.source == "acled":
            count = run_acled(args.bootstrap_servers, args.days)
        elif args.source == "ais":
            count = run_ais(args.bootstrap_servers)
        elif args.source == "all":
            gdelt_count = run_gdelt(args.bootstrap_servers)
            acled_count = run_acled(args.bootstrap_servers, args.days)
            ais_count = run_ais(args.bootstrap_servers)
            count = gdelt_count + acled_count + ais_count
        
        logger.info("producer_cli_complete", total_published=count)
        print(f"Published {count} events to Kafka")
        return 0
        
    except Exception as e:
        logger.error("producer_cli_error", error=str(e))
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
