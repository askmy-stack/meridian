"""Structured event classifier — JSON output only, no risk scoring (D-006)."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class EventClassification:
    """Structured classification for raw news / GDELT text."""

    event_type: str
    severity_proxy: float  # 0–1 intensity proxy, NOT SCRI
    locations: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    classifier: str = "rule-based"
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "severity_proxy": round(self.severity_proxy, 3),
            "locations": self.locations,
            "entities": self.entities,
            "classifier": self.classifier,
        }


# Event type rules — maps keywords → (event_type, base severity proxy)
EVENT_RULES: List[tuple[str, tuple[str, float]]] = [
    (r"\b(war|invasion|airstrike|missile|bombing|armed conflict)\b", ("armed_conflict", 0.9)),
    (r"\b(blockade|port closed|canal blocked|shipping halted)\b", ("port_disruption", 0.85)),
    (r"\b(sanction|embargo|export ban|trade restriction)\b", ("sanctions", 0.75)),
    (r"\b(protest|strike|riot|demonstration|unrest)\b", ("civil_unrest", 0.6)),
    (r"\b(hurricane|earthquake|flood|wildfire|typhoon|cyclone)\b", ("natural_disaster", 0.8)),
    (r"\b(cyber|ransomware|hack|data breach)\b", ("cyber_incident", 0.7)),
    (r"\b(tariff|trade war|export control|diplomatic)\b", ("trade_tension", 0.55)),
    (r"\b(congestion|delay|backlog|shortage)\b", ("logistics_delay", 0.5)),
]

LOCATION_PATTERN = re.compile(
    r"\b(?:in|at|near|around)\s+([A-Z][a-zA-Z\s\-]{2,40})(?:[,\.]|\s+(?:port|canal|strait|region))",
    re.IGNORECASE,
)
ENTITY_PATTERN = re.compile(
    r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})\b",
)


class RuleBasedEventClassifier:
    """Keyword + pattern classifier — no ML dependencies."""

    def classify(self, text: str) -> EventClassification:
        text = (text or "").strip()
        if len(text) < 5:
            return EventClassification(
                event_type="unknown",
                severity_proxy=0.3,
                classifier="rule-based",
                raw_text=text,
            )

        text_lower = text.lower()
        event_type = "general_signal"
        severity = 0.4

        for pattern, (etype, base_sev) in EVENT_RULES:
            if re.search(pattern, text_lower):
                event_type = etype
                severity = base_sev
                break

        locations = list(
            dict.fromkeys(m.group(1).strip() for m in LOCATION_PATTERN.finditer(text))
        )[:5]

        # Simple entity extraction — capitalized phrases, filter common words
        stop = {"The", "A", "An", "In", "At", "On", "For", "And", "Or", "Red", "Sea"}
        entities = [
            m.group(1)
            for m in ENTITY_PATTERN.finditer(text)
            if m.group(1) not in stop and len(m.group(1)) > 2
        ][:8]

        return EventClassification(
            event_type=event_type,
            severity_proxy=severity,
            locations=locations,
            entities=entities,
            classifier="rule-based",
            raw_text=text,
        )


class LLMStubEventClassifier:
    """Optional LLM interface — returns structured JSON, never risk_score."""

    def classify(self, text: str) -> EventClassification:
        provider = os.getenv("LLM_PROVIDER", "stub").lower()
        if provider == "stub":
            return RuleBasedEventClassifier().classify(text)

        prompt = (
            "Classify this news text. Return JSON only with keys: "
            "event_type, severity_proxy (0-1, NOT a supplier risk score), "
            "locations (array), entities (array). No risk_score field.\n\n"
            f"Text: {text[:800]}"
        )
        raw = self._call_llm(prompt)
        if raw:
            try:
                data = json.loads(raw)
                return EventClassification(
                    event_type=str(data.get("event_type", "general_signal")),
                    severity_proxy=min(1.0, max(0.0, float(data.get("severity_proxy", 0.5)))),
                    locations=list(data.get("locations") or [])[:5],
                    entities=list(data.get("entities") or [])[:8],
                    classifier=f"llm-{provider}",
                    raw_text=text,
                )
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                logger.info("llm_classifier_parse_failed", error=str(exc))

        return RuleBasedEventClassifier().classify(text)

    def _call_llm(self, prompt: str) -> Optional[str]:
        provider = os.getenv("LLM_PROVIDER", "stub").lower()
        if provider == "ollama":
            return self._ollama(prompt)
        if provider == "openai":
            return self._openai(prompt)
        return None

    def _ollama(self, prompt: str) -> Optional[str]:
        try:
            import requests

            resp = requests.post(
                f"{os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}/api/generate",
                json={
                    "model": os.getenv("OLLAMA_MODEL", "gemma2:2b"),
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("response")
        except Exception as exc:
            logger.info("ollama_classifier_skipped", error=str(exc))
            return None

    def _openai(self, prompt: str) -> Optional[str]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        try:
            import requests

            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "max_tokens": 300,
                },
                timeout=30,
            )
            resp.raise_for_status()
            choices = resp.json().get("choices") or []
            if choices:
                return choices[0]["message"]["content"]
        except Exception as exc:
            logger.info("openai_classifier_skipped", error=str(exc))
        return None


_classifier: Optional[RuleBasedEventClassifier] = None


def classify_news_event(text: str) -> EventClassification:
    """Classify raw news text — respects ENABLE_LLM_CLASSIFIER flag."""
    use_llm = os.getenv("ENABLE_LLM_CLASSIFIER", "false").lower() in ("1", "true", "yes")
    if use_llm:
        return LLMStubEventClassifier().classify(text)
    global _classifier
    if _classifier is None:
        _classifier = RuleBasedEventClassifier()
    return _classifier.classify(text)
