"""Slack Alerting Service for Meridian.

Sends alerts to Slack channels based on risk thresholds.
Supports multiple alert tiers: INFO, WARNING, CRITICAL.

Features:
- Rich message formatting with attachments
- Alert deduplication (per P-004 decision)
- Rate limiting to avoid spam
- Thread-based updates for ongoing events
"""

import os
import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

import structlog

# Try to import requests for HTTP calls
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = structlog.get_logger(__name__)


class AlertTier(Enum):
    """Alert severity tiers."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert message."""
    tier: AlertTier
    title: str
    message: str
    
    # Context
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    event_id: Optional[str] = None
    
    # Risk data
    risk_score: Optional[float] = None
    risk_category: Optional[str] = None
    impact_summary: Optional[str] = None
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    # Causal inference metadata (D-005)
    causal_claim_allowed: Optional[bool] = None
    causal_method: Optional[str] = None
    causal_effect_size: Optional[float] = None
    causal_disclaimer: Optional[str] = None
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tier": self.tier.value,
            "title": self.title,
            "message": self.message,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "event_id": self.event_id,
            "risk_score": self.risk_score,
            "risk_category": self.risk_category,
            "impact_summary": self.impact_summary,
            "recommendations": self.recommendations,
            "causal_claim_allowed": self.causal_claim_allowed,
            "causal_method": self.causal_method,
            "causal_effect_size": self.causal_effect_size,
            "causal_disclaimer": self.causal_disclaimer,
            "timestamp": self.timestamp
        }
    
    @property
    def dedup_key(self) -> str:
        """Generate deduplication key."""
        # Key based on entity + tier + truncated title
        key_parts = [
            self.entity_id or "global",
            self.tier.value,
            self.title[:50]  # First 50 chars of title
        ]
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()


class SlackAlertingService:
    """Slack alerting service with deduplication and rate limiting.
    
    Usage:
        # Initialize with webhook URL
        service = SlackAlertingService(
            webhook_url="https://hooks.slack.com/services/..."
        )
        
        # Send CRITICAL alert
        alert = Alert(
            tier=AlertTier.CRITICAL,
            title="Supplier Disruption Detected",
            message="Foxconn factory in Zhengzhou experiencing production halt",
            entity_id="supplier-foxconn-001",
            entity_type="supplier",
            risk_score=0.85,
            risk_category="CRITICAL",
            recommendations=[
                "Activate alternative supplier",
                "Review inventory buffer",
                "Notify affected customers"
            ]
        )
        
        service.send_alert(alert)
    """
    
    # Tier configuration
    TIER_CONFIG = {
        AlertTier.INFO: {
            "color": "#36a64f",  # Green
            "emoji": ":information_source:",
            "threshold": 0.0,  # Always send
            "rate_limit_minutes": 60
        },
        AlertTier.WARNING: {
            "color": "#ff9900",  # Orange
            "emoji": ":warning:",
            "threshold": 0.5,
            "rate_limit_minutes": 30
        },
        AlertTier.CRITICAL: {
            "color": "#ff0000",  # Red
            "emoji": ":rotating_light:",
            "threshold": 0.8,
            "rate_limit_minutes": 5  # Can send more frequently
        }
    }
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        default_channel: str = "#supply-chain-alerts",
        enable_dedup: bool = True,
        dedup_window_minutes: int = 60
    ):
        """Initialize Slack alerting service.
        
        Args:
            webhook_url: Slack webhook URL (or from SLACK_WEBHOOK_URL env var)
            default_channel: Default channel to post to
            enable_dedup: Enable alert deduplication
            dedup_window_minutes: Window for deduplication
        """
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.default_channel = default_channel
        self.enable_dedup = enable_dedup
        self.dedup_window = timedelta(minutes=dedup_window_minutes)
        
        self.logger = logger.bind(service="SlackAlertingService")

        # Deduplication cache: dedup_key -> last_sent_timestamp
        self._dedup_cache: Dict[str, datetime] = {}

        # Rate limiting cache: tier -> last_sent_timestamp
        self._rate_limit_cache: Dict[AlertTier, datetime] = {}

        # In-memory alert history (ring buffer) for /alerts API endpoint.
        # NOTE: cleared on process restart — swap for Redis/Postgres in prod (see B-13).
        from collections import deque
        self._history: "deque[Alert]" = deque(maxlen=int(os.getenv("ALERT_HISTORY_SIZE", "500")))
        
        if not self.webhook_url:
            self.logger.warning("no_webhook_configured", message="Alerts will be logged only")
    
    def send_alert(self, alert: Alert, channel: Optional[str] = None) -> bool:
        """Send alert to Slack.
        
        Args:
            alert: Alert to send
            channel: Optional channel override
            
        Returns:
            True if sent successfully, False otherwise
        """
        # Check deduplication
        if self.enable_dedup and not self._should_send(alert):
            self.logger.debug(
                "alert_deduplicated",
                tier=alert.tier.value,
                title=alert.title
            )
            return False
        
        # Check rate limiting
        if not self._check_rate_limit(alert.tier):
            self.logger.debug(
                "alert_rate_limited",
                tier=alert.tier.value,
                title=alert.title
            )
            return False
        
        # Build message
        payload = self._build_payload(alert, channel)
        
        # Send or log
        if self.webhook_url and REQUESTS_AVAILABLE:
            success = self._send_to_slack(payload)
        else:
            # Log instead of sending
            self._log_alert(alert)
            success = True
        
        if success:
            # Update caches
            self._update_dedup_cache(alert)
            self._update_rate_limit_cache(alert.tier)
            # Record in history for API consumption
            self._history.append(alert)
            try:
                from .persistence import get_alert_store
                get_alert_store().append(alert)
            except Exception as exc:
                logger.warning("alert_persist_failed", error=str(exc))
        
        return success
    
    def _should_send(self, alert: Alert) -> bool:
        """Check if alert should be sent (deduplication)."""
        dedup_key = alert.dedup_key
        now = datetime.now()
        
        if dedup_key in self._dedup_cache:
            last_sent = self._dedup_cache[dedup_key]
            if now - last_sent < self.dedup_window:
                return False
        
        return True
    
    def _check_rate_limit(self, tier: AlertTier) -> bool:
        """Check rate limit for tier."""
        if tier not in self._rate_limit_cache:
            return True
        
        last_sent = self._rate_limit_cache[tier]
        now = datetime.now()
        
        config = self.TIER_CONFIG[tier]
        min_interval = timedelta(minutes=config["rate_limit_minutes"])
        
        return now - last_sent >= min_interval
    
    def _update_dedup_cache(self, alert: Alert) -> None:
        """Update deduplication cache."""
        self._dedup_cache[alert.dedup_key] = datetime.now()
        
        # Clean old entries periodically
        if len(self._dedup_cache) > 1000:
            self._cleanup_cache()
    
    def _update_rate_limit_cache(self, tier: AlertTier) -> None:
        """Update rate limit cache."""
        self._rate_limit_cache[tier] = datetime.now()
    
    def _cleanup_cache(self) -> None:
        """Remove old entries from dedup cache."""
        now = datetime.now()
        old_keys = [
            k for k, v in self._dedup_cache.items()
            if now - v > self.dedup_window
        ]
        for k in old_keys:
            del self._dedup_cache[k]
    
    def _build_payload(self, alert: Alert, channel: Optional[str]) -> Dict[str, Any]:
        """Build Slack webhook payload."""
        config = self.TIER_CONFIG[alert.tier]
        
        # Build attachment fields
        fields = []
        
        if alert.entity_id:
            fields.append({
                "title": "Entity",
                "value": f"{alert.entity_type or 'Unknown'}: {alert.entity_id}",
                "short": True
            })
        
        if alert.risk_score is not None:
            fields.append({
                "title": "Risk Score",
                "value": f"{alert.risk_score:.1%} ({alert.risk_category or 'N/A'})",
                "short": True
            })
        
        if alert.event_id:
            fields.append({
                "title": "Event ID",
                "value": alert.event_id,
                "short": True
            })
        
        # Build recommendations section
        actions = []
        for i, rec in enumerate(alert.recommendations[:3]):
            actions.append({
                "type": "button",
                "text": rec[:30],  # Truncate if too long
                "style": "primary" if i == 0 else "default"
            })
        
        attachment = {
            "fallback": f"{alert.title}: {alert.message}",
            "color": config["color"],
            "title": f"{config['emoji']} {alert.title}",
            "text": alert.message,
            "fields": fields,
            "footer": "Meridian Supply Chain Risk Intelligence",
            "ts": int(time.time()),
            "actions": actions if actions else None
        }
        
        payload = {
            "channel": channel or self.default_channel,
            "username": "Meridian Alerts",
            "icon_emoji": config["emoji"],
            "attachments": [attachment]
        }
        
        return payload
    
    def _send_to_slack(self, payload: Dict[str, Any]) -> bool:
        """Send payload to Slack webhook."""
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                self.logger.info("alert_sent_to_slack", channel=payload["channel"])
                return True
            else:
                self.logger.error(
                    "slack_send_failed",
                    status_code=response.status_code,
                    response=response.text
                )
                return False
                
        except Exception as e:
            self.logger.error("slack_send_exception", error=str(e))
            return False
    
    def _log_alert(self, alert: Alert) -> None:
        """Log alert when Slack not configured."""
        self.logger.info(
            "alert_logged",
            tier=alert.tier.value,
            title=alert.title,
            entity_id=alert.entity_id,
            risk_score=alert.risk_score
        )
    
    def send_batch(self, alerts: List[Alert]) -> Dict[str, int]:
        """Send multiple alerts.
        
        Returns:
            Dict with sent/skipped/failed counts
        """
        stats = {"sent": 0, "skipped": 0, "failed": 0}
        
        for alert in alerts:
            success = self.send_alert(alert)
            
            if success:
                stats["sent"] += 1
            else:
                # Could be skipped (dedup/rate limit) or failed
                stats["skipped"] += 1
        
        return stats
    
    def send_risk_alert(
        self,
        entity_id: str,
        entity_type: str,
        risk_score: float,
        risk_category: str,
        event_description: str,
        recommendations: Optional[List[str]] = None
    ) -> bool:
        """Convenience method for sending risk alerts."""
        # Determine tier based on risk category
        if risk_category == "CRITICAL":
            tier = AlertTier.CRITICAL
        elif risk_category == "HIGH":
            tier = AlertTier.WARNING
        else:
            tier = AlertTier.INFO
        
        alert = Alert(
            tier=tier,
            title=f"Risk Alert: {entity_type.title()} {entity_id[:8]}...",
            message=event_description,
            entity_id=entity_id,
            entity_type=entity_type,
            risk_score=risk_score,
            risk_category=risk_category,
            recommendations=recommendations or ["Review supplier status", "Check inventory levels"]
        )
        
        return self.send_alert(alert)
    
    def send_simulation_result(
        self,
        scenario_name: str,
        disruption_probability: float,
        affected_suppliers: int,
        revenue_at_risk: float
    ) -> bool:
        """Send simulation completion alert."""
        # Determine tier based on disruption probability
        if disruption_probability > 0.7:
            tier = AlertTier.CRITICAL
        elif disruption_probability > 0.4:
            tier = AlertTier.WARNING
        else:
            tier = AlertTier.INFO
        
        alert = Alert(
            tier=tier,
            title=f"Simulation Complete: {scenario_name}",
            message=(
                f"Disruption probability: {disruption_probability:.1%}\n"
                f"Suppliers affected: {affected_suppliers}\n"
                f"Revenue at risk: ${revenue_at_risk:,.0f}"
            ),
            recommendations=[
                "Review simulation details",
                "Update contingency plans"
            ]
        )
        
        return self.send_alert(alert)
    
    def get_recent_alerts(
        self,
        limit: int = 100,
        tier: Optional[AlertTier] = None,
    ) -> List[Alert]:
        """Return most recent alerts (newest first), optionally filtered by tier."""
        try:
            from .persistence import get_alert_store
            stored = get_alert_store().list_recent(limit=limit, tier=tier)
            if stored:
                result: List[Alert] = []
                for row in stored:
                    try:
                        result.append(
                            Alert(
                                tier=AlertTier(row["tier"]),
                                title=row["title"],
                                message=row["message"],
                                entity_id=row.get("entity_id"),
                                entity_type=row.get("entity_type"),
                                risk_score=row.get("risk_score"),
                                recommendations=row.get("recommendations") or [],
                                timestamp=row.get("timestamp", datetime.now().isoformat()),
                            )
                        )
                    except (KeyError, ValueError):
                        continue
                if result:
                    return result
        except Exception as exc:
            logger.warning("alert_store_read_failed", error=str(exc))

        alerts = list(self._history)
        alerts.reverse()  # newest first
        if tier is not None:
            alerts = [a for a in alerts if a.tier == tier]
        return alerts[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        by_tier = {tier.value: 0 for tier in AlertTier}
        for alert in self._history:
            by_tier[alert.tier.value] = by_tier.get(alert.tier.value, 0) + 1

        return {
            "total": len(self._history),
            "by_tier": by_tier,
            "history_size": len(self._history),
            "dedup_cache_size": len(self._dedup_cache),
            "webhook_configured": bool(self.webhook_url),
            "last_alerts_by_tier": {
                tier.value: self._rate_limit_cache.get(tier, "never").__str__()
                for tier in AlertTier
            },
        }


# Singleton instance
_service: Optional[SlackAlertingService] = None


def get_alerting_service() -> SlackAlertingService:
    """Get or create singleton alerting service."""
    global _service
    if _service is None:
        _service = SlackAlertingService()
    return _service


def send_critical_alert(
    title: str,
    message: str,
    entity_id: Optional[str] = None
) -> bool:
    """Convenience function for critical alerts."""
    service = get_alerting_service()
    
    alert = Alert(
        tier=AlertTier.CRITICAL,
        title=title,
        message=message,
        entity_id=entity_id
    )
    
    return service.send_alert(alert)


def send_warning_alert(
    title: str,
    message: str,
    entity_id: Optional[str] = None
) -> bool:
    """Convenience function for warning alerts."""
    service = get_alerting_service()
    
    alert = Alert(
        tier=AlertTier.WARNING,
        title=title,
        message=message,
        entity_id=entity_id
    )
    
    return service.send_alert(alert)
