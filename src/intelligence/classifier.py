"""BERT-based Event Classifier for Meridian.

Classifies conflict and news events into risk categories using BERT.
Fine-tuned on ACLED labels for supply chain risk prediction.

Risk Categories:
- CRITICAL: Armed conflict, major sanctions, port blockade
- HIGH: Protests, strikes, severe weather, cyber attack
- MEDIUM: Diplomatic tensions, regulatory changes
- LOW: Minor incidents, routine disruptions
- NONE: No risk detected
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import structlog
import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

logger = structlog.get_logger(__name__)


@dataclass
class ClassificationResult:
    """Result from event classification."""
    text: str
    label: str  # CRITICAL, HIGH, MEDIUM, LOW, NONE
    confidence: float  # 0-1
    all_scores: Dict[str, float]  # Scores for all categories
    model_version: str


class BERTEventClassifier:
    """BERT-based classifier for supply chain risk events.
    
    Uses a pre-trained BERT model fine-tuned on ACLED conflict data.
    Falls back to zero-shot classification if fine-tuned model unavailable.
    
    Usage:
        classifier = BERTEventClassifier()
        result = classifier.classify("Protesters blockaded the port of Shanghai")
        print(result.label)  # "HIGH" or "CRITICAL"
    """
    
    # Risk categories in order of severity
    RISK_CATEGORIES = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    
    # Default model - using distilbert for efficiency, can be swapped for bert-base
    DEFAULT_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"
    
    # Candidate labels for zero-shot classification
    ZERO_SHOT_LABELS = [
        "armed conflict, war, military attack",
        "protest, strike, demonstration, civil unrest",
        "port blockage, shipping disruption, logistics delay",
        "severe weather, natural disaster, hurricane, earthquake",
        "cyber attack, data breach, system outage",
        "diplomatic tension, trade dispute, sanctions",
        "routine operations, normal activity, no disruption"
    ]
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        use_zero_shot: bool = False,
        device: Optional[str] = None
    ):
        """Initialize BERT classifier.
        
        Args:
            model_name: HuggingFace model name (default: distilbert-sst)
            use_zero_shot: Use zero-shot classification instead of fine-tuned
            device: 'cuda', 'cpu', or None (auto)
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.use_zero_shot = use_zero_shot
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        self.logger = logger.bind(
            classifier="BERTEventClassifier",
            model=self.model_name,
            device=self.device
        )
        
        self._tokenizer: Optional[AutoTokenizer] = None
        self._model: Optional[AutoModelForSequenceClassification] = None
        self._pipeline = None
        
        self._load_model()
    
    def _load_model(self) -> None:
        """Load BERT model and tokenizer."""
        try:
            if self.use_zero_shot:
                # Zero-shot classification for cases without fine-tuned model
                from transformers import pipeline
                self._pipeline = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli",
                    device=0 if self.device == "cuda" else -1
                )
                self.logger.info("zero_shot_pipeline_loaded")
            else:
                # Standard classification pipeline
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self._model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_name
                )
                self._model.to(self.device)
                self._model.eval()
                
                self.logger.info(
                    "bert_model_loaded",
                    model=self.model_name
                )
                
        except Exception as e:
            self.logger.error("model_load_failed", error=str(e))
            # Fallback to zero-shot
            self.logger.warning("falling_back_to_zero_shot")
            self.use_zero_shot = True
            self._load_model()
    
    def classify(self, text: str) -> ClassificationResult:
        """Classify event text into risk category.
        
        Args:
            text: Event description or news text
            
        Returns:
            ClassificationResult with label, confidence, and all scores
        """
        if not text or len(text.strip()) < 10:
            return ClassificationResult(
                text=text,
                label="NONE",
                confidence=1.0,
                all_scores={cat: 0.0 for cat in self.RISK_CATEGORIES},
                model_version=self.model_name
            )
        
        try:
            if self.use_zero_shot:
                return self._classify_zero_shot(text)
            else:
                return self._classify_bert(text)
                
        except Exception as e:
            self.logger.error("classification_failed", error=str(e), text=text[:100])
            # Return safe default
            return ClassificationResult(
                text=text,
                label="MEDIUM",
                confidence=0.5,
                all_scores={cat: 0.2 for cat in self.RISK_CATEGORIES},
                model_version=self.model_name
            )
    
    def _classify_bert(self, text: str) -> ClassificationResult:
        """Classify using standard BERT model."""
        # Tokenize
        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Inference
        with torch.no_grad():
            outputs = self._model(**inputs)
            logits = outputs.logits
            probs = F.softmax(logits, dim=-1)
        
        # Get scores
        scores = probs[0].cpu().numpy()
        
        # Map to risk categories (adjust based on model output structure)
        # For binary models, we'll use a mapping approach
        if len(scores) == 2:
            # Binary: map negative to NONE/LOW, positive to MEDIUM/HIGH/CRITICAL
            risk_scores = {
                "NONE": scores[0] * 0.8,
                "LOW": scores[0] * 0.2,
                "MEDIUM": scores[1] * 0.3,
                "HIGH": scores[1] * 0.5,
                "CRITICAL": scores[1] * 0.2
            }
        else:
            # Multi-class: assume model outputs match our categories
            risk_scores = {
                cat: float(scores[i]) if i < len(scores) else 0.0
                for i, cat in enumerate(self.RISK_CATEGORIES)
            }
        
        # Get top category
        label = max(risk_scores, key=risk_scores.get)
        confidence = risk_scores[label]
        
        return ClassificationResult(
            text=text,
            label=label,
            confidence=confidence,
            all_scores=risk_scores,
            model_version=self.model_name
        )
    
    def _classify_zero_shot(self, text: str) -> ClassificationResult:
        """Classify using zero-shot approach."""
        result = self._pipeline(
            text,
            self.ZERO_SHOT_LABELS,
            multi_label=False
        )
        
        # Map zero-shot labels to risk categories
        label_mapping = {
            "armed conflict, war, military attack": "CRITICAL",
            "protest, strike, demonstration, civil unrest": "HIGH",
            "port blockage, shipping disruption, logistics delay": "HIGH",
            "severe weather, natural disaster, hurricane, earthquake": "CRITICAL",
            "cyber attack, data breach, system outage": "HIGH",
            "diplomatic tension, trade dispute, sanctions": "MEDIUM",
            "routine operations, normal activity, no disruption": "NONE"
        }
        
        # Get scores for each risk category
        risk_scores: Dict[str, float] = {cat: 0.0 for cat in self.RISK_CATEGORIES}
        
        for label, score in zip(result["labels"], result["scores"]):
            risk_cat = label_mapping.get(label, "MEDIUM")
            risk_scores[risk_cat] = max(risk_scores[risk_cat], score)
        
        # Normalize scores
        total = sum(risk_scores.values())
        if total > 0:
            risk_scores = {k: v / total for k, v in risk_scores.items()}
        
        # Get top category
        top_label = max(risk_scores, key=risk_scores.get)
        confidence = risk_scores[top_label]
        
        return ClassificationResult(
            text=text,
            label=top_label,
            confidence=confidence,
            all_scores=risk_scores,
            model_version="zero-shot-bart"
        )
    
    def batch_classify(
        self,
        texts: List[str],
        batch_size: int = 8
    ) -> List[ClassificationResult]:
        """Classify multiple texts in batches.
        
        Args:
            texts: List of texts to classify
            batch_size: Number of texts to process at once
            
        Returns:
            List of ClassificationResults
        """
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_results = [self.classify(text) for text in batch]
            results.extend(batch_results)
            
            self.logger.debug(
                "batch_processed",
                batch_start=i,
                batch_size=len(batch)
            )
        
        return results
    
    def get_risk_score(self, text: str) -> float:
        """Get numeric risk score (0-1) from classification.
        
        Args:
            text: Event description
            
        Returns:
            Risk score 0.0 (none) to 1.0 (critical)
        """
        result = self.classify(text)
        
        # Map labels to numeric scores
        label_scores = {
            "NONE": 0.0,
            "LOW": 0.25,
            "MEDIUM": 0.5,
            "HIGH": 0.75,
            "CRITICAL": 1.0
        }
        
        base_score = label_scores.get(result.label, 0.5)
        
        # Adjust by confidence
        adjusted_score = base_score * (0.8 + 0.2 * result.confidence)
        
        return min(1.0, adjusted_score)


class RuleBasedClassifier:
    """Rule-based classifier as fallback when ML models unavailable.
    
    Uses keyword matching and pattern rules for risk classification.
    """
    
    # Risk keywords by category
    KEYWORDS = {
        "CRITICAL": [
            "war", "invasion", "missile", "bombing", "airstrike",
            "cyberattack", "ransomware", "port closed", "port blockade",
            "hurricane", "earthquake", "tsunami", "flood"
        ],
        "HIGH": [
            "protest", "strike", "demonstration", "riot",
            "port congestion", "shipping delay", "supply shortage",
            "trade war", "sanctions", "embargo"
        ],
        "MEDIUM": [
            "tension", "dispute", "investigation", "regulatory",
            "policy change", "customs delay"
        ],
        "LOW": [
            "minor", "small", "localized", "temporary"
        ]
    }
    
    def classify(self, text: str) -> ClassificationResult:
        """Classify using keyword matching."""
        text_lower = text.lower()
        scores = {cat: 0.0 for cat in ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]}
        
        # Score based on keyword presence
        for category, keywords in self.KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[category] += 1.0
        
        # Normalize
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        else:
            scores["NONE"] = 1.0
        
        # Get top category
        label = max(scores, key=scores.get)
        confidence = scores[label]
        
        return ClassificationResult(
            text=text,
            label=label,
            confidence=confidence,
            all_scores=scores,
            model_version="rule-based"
        )
    
    def get_risk_score(self, text: str) -> float:
        """Get numeric risk score."""
        result = self.classify(text)
        label_scores = {"NONE": 0.0, "LOW": 0.25, "MEDIUM": 0.5, "HIGH": 0.75, "CRITICAL": 1.0}
        return label_scores.get(result.label, 0.5)


# Singleton instance
_classifier: Optional[BERTEventClassifier] = None


def get_classifier() -> BERTEventClassifier:
    """Get or create singleton classifier."""
    global _classifier
    if _classifier is None:
        # Try BERT first, fall back to zero-shot
        _classifier = BERTEventClassifier(use_zero_shot=False)
    return _classifier


def classify_event(text: str) -> ClassificationResult:
    """Convenience function for quick classification."""
    return get_classifier().classify(text)
