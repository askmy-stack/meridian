"""Alerting module for Meridian.

Provides notification and alerting services:
- Slack alerting with deduplication
- Multi-tier alert system (INFO, WARNING, CRITICAL)
- Rate limiting and spam prevention
"""

from .slack import (
    Alert,
    AlertTier,
    SlackAlertingService,
    get_alerting_service,
    send_critical_alert,
    send_warning_alert,
)

__all__ = [
    "Alert",
    "AlertTier",
    "SlackAlertingService",
    "get_alerting_service",
    "send_critical_alert",
    "send_warning_alert",
]
