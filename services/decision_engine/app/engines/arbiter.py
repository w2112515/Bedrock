"""
Decision Arbiter for DecisionEngine Service.

Arbitrates final trading decisions by combining scores from:
- Rule Engine
- ML Model
- LLM Sentiment Analysis

Phase 2 - Task 2.3.4: Implement Decision Arbiter
"""

import sys
import os
from typing import Tuple, Dict, Any, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from decimal import Decimal
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.decision_engine.app.core.config import settings
from services.decision_engine.app.models.signal import Signal
from services.decision_engine.app.models.arbitration_config import ArbitrationConfig

logger = setup_logging("arbiter")


class ArbitrationConfigError(Exception):
    """Configuration-related error in arbitration logic."""


@dataclass(frozen=True)
class ArbitrationConfigValues:
    """Immutable value object for arbitration configuration.

    This decouples cached configuration from SQLAlchemy session state.
    """

    version: int
    rule_weight: Decimal
    ml_weight: Decimal
    llm_weight: Decimal
    min_approval_score: Decimal
    adaptive_threshold_enabled: bool


class DecisionArbiter:
    """
    Decision Arbiter for combining multiple decision engines.
    
    This class implements the arbitration logic that combines scores from:
    1. Rule Engine (technical analysis)
    2. ML Model (machine learning predictions)
    3. LLM (sentiment analysis)
    
    Design Principles:
    - Single Responsibility: Only responsible for arbitration logic
    - Open/Closed: Extensible for Phase 3 dynamic weights
    - Dependency Inversion: Depends on configuration abstraction
    
    Phase 2 Implementation:
    - Fixed weights from database configuration
    - LLM sentiment to score conversion with confidence adjustment
    - Weighted scoring algorithm
    - Approval threshold comparison
    
    Phase 3 Extensions (Reserved):
    - Dynamic weight adjustment based on backtest performance
    - Adaptive threshold based on market volatility
    - Reinforcement learning optimization
    
    Usage:
        arbiter = DecisionArbiter()
        decision, explanation, rejection_reason = await arbiter.arbitrate(signal, db)
        signal.final_decision = decision
        signal.explanation = explanation
        signal.rejection_reason = rejection_reason
    """
    
    def __init__(self):
        """Initialize Decision Arbiter."""
        # Cache immutable value object to avoid cross-session ORM issues
        self._cached_config: Optional[ArbitrationConfigValues] = None

    def get_active_config(self, db: Session) -> ArbitrationConfigValues:
        """Get active arbitration configuration as a value object.

        Uses caching to avoid repeated database queries while keeping the
        cached configuration detached from SQLAlchemy session state.

        Args:
            db: Database session

        Returns:
            Active ArbitrationConfigValues instance
        """
        if self._cached_config is not None:
            logger.info(
                f"Using cached arbitration config (version={self._cached_config.version})"
            )
            return self._cached_config

        orm_config = db.query(ArbitrationConfig).filter_by(is_active=True).first()

        if orm_config:
            logger.info(
                f"Loaded active arbitration config from DB (version={orm_config.version})"
            )
            config_values = ArbitrationConfigValues(
                version=orm_config.version,
                rule_weight=orm_config.rule_weight,
                ml_weight=orm_config.ml_weight,
                llm_weight=orm_config.llm_weight,
                min_approval_score=orm_config.min_approval_score,
                adaptive_threshold_enabled=orm_config.adaptive_threshold_enabled,
            )
        else:
            logger.error(
                "No active arbitration config found, using default values from settings"
            )
            # Fallback to environment variables (value object only, no ORM instance)
            config_values = ArbitrationConfigValues(
                version=0,
                rule_weight=Decimal(str(settings.ARBITER_RULE_WEIGHT)),
                ml_weight=Decimal(str(settings.ARBITER_ML_WEIGHT)),
                llm_weight=Decimal(str(settings.ARBITER_LLM_WEIGHT)),
                min_approval_score=Decimal(str(settings.ARBITER_MIN_APPROVAL_SCORE)),
                adaptive_threshold_enabled=False,
            )

        self._cached_config = config_values
        return config_values

    def convert_sentiment_to_score(
        self, 
        sentiment: str, 
        confidence: float
    ) -> float:
        """
        Convert LLM sentiment to numerical score (0-100).
        
        Formula: final_score = base_score + (confidence - 50) * multiplier
        
        Base scores (Phase 2 - Aggressive mapping):
        - BULLISH: 90
        - NEUTRAL: 50
        - BEARISH: 10
        
        Confidence adjustment:
        - Multiplier: 0.2 (configurable)
        - Example: BULLISH + confidence=85 → 90 + (85-50)*0.2 = 97
        
        Args:
            sentiment: BULLISH/NEUTRAL/BEARISH
            confidence: 0-100
            
        Returns:
            Score in range [0, 100]
        """
        base_scores = {
            "BULLISH": settings.LLM_SENTIMENT_BULLISH_BASE,
            "NEUTRAL": settings.LLM_SENTIMENT_NEUTRAL_BASE,
            "BEARISH": settings.LLM_SENTIMENT_BEARISH_BASE
        }
        
        # Get base score (default to NEUTRAL if unknown sentiment)
        base_score = base_scores.get(sentiment.upper(), settings.LLM_SENTIMENT_NEUTRAL_BASE)
        
        # Apply confidence adjustment
        adjustment = (confidence - 50) * settings.LLM_SENTIMENT_CONFIDENCE_MULTIPLIER
        final_score = base_score + adjustment
        
        # Clamp to [0, 100]
        clamped_score = max(0.0, min(100.0, final_score))
        
        logger.debug(
            f"Sentiment conversion: {sentiment} (confidence={confidence:.1f}) → "
            f"base={base_score}, adjustment={adjustment:.2f}, final={clamped_score:.2f}"
        )
        
        return clamped_score
    
    def calculate_weighted_score(
        self,
        rule_score: float,
        ml_score: Optional[float],
        llm_score: float,
        config: ArbitrationConfigValues
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate weighted final score.
        
        If ML score is unavailable (None), redistributes ML weight to other engines:
        - 60% to Rule Engine
        - 40% to LLM
        
        Args:
            rule_score: Rule engine score (0-100)
            ml_score: ML confidence score (0-100) or None
            llm_score: LLM sentiment score (0-100)
            config: Arbitration configuration
            
        Returns:
            Tuple of (final_score, breakdown_dict)
            
        Example breakdown_dict:
            {
                "rule_score": 85.0,
                "rule_weight": 0.4,
                "ml_score": 78.0,
                "ml_weight": 0.3,
                "llm_score": 82.0,
                "llm_weight": 0.3,
                "final_score": 81.5
            }
        """
        # Handle missing ML score
        if ml_score is None:
            # Redistribute ML weight
            ml_weight_value = float(config.ml_weight)
            adjusted_rule_weight = float(config.rule_weight) + ml_weight_value * 0.6
            adjusted_llm_weight = float(config.llm_weight) + ml_weight_value * 0.4
            
            final_score = (
                rule_score * adjusted_rule_weight +
                llm_score * adjusted_llm_weight
            )
            
            breakdown = {
                "rule_score": rule_score,
                "rule_weight": adjusted_rule_weight,
                "ml_score": None,
                "ml_weight": 0.0,
                "llm_score": llm_score,
                "llm_weight": adjusted_llm_weight,
                "final_score": final_score,
                "ml_unavailable": True
            }
            
            logger.info(
                f"Weighted score (ML unavailable): "
                f"Rule={rule_score:.1f}*{adjusted_rule_weight:.2f} + "
                f"LLM={llm_score:.1f}*{adjusted_llm_weight:.2f} = {final_score:.2f}"
            )
        else:
            # All engines available
            final_score = (
                rule_score * float(config.rule_weight) +
                ml_score * float(config.ml_weight) +
                llm_score * float(config.llm_weight)
            )
            
            breakdown = {
                "rule_score": rule_score,
                "rule_weight": float(config.rule_weight),
                "ml_score": ml_score,
                "ml_weight": float(config.ml_weight),
                "llm_score": llm_score,
                "llm_weight": float(config.llm_weight),
                "final_score": final_score,
                "ml_unavailable": False
            }
            
            logger.info(
                f"Weighted score: "
                f"Rule={rule_score:.1f}*{config.rule_weight} + "
                f"ML={ml_score:.1f}*{config.ml_weight} + "
                f"LLM={llm_score:.1f}*{config.llm_weight} = {final_score:.2f}"
            )
        
        return final_score, breakdown
    
    def _generate_approval_explanation(self, breakdown: Dict[str, Any]) -> str:
        """
        Generate human-readable explanation for APPROVED decision.
        
        Args:
            breakdown: Score breakdown dictionary
            
        Returns:
            Explanation string
        """
        if breakdown.get("ml_unavailable"):
            return (
                f"✅ APPROVED: Strong consensus (ML unavailable). "
                f"Rule={breakdown['rule_score']:.1f}, "
                f"LLM={breakdown['llm_score']:.1f} → "
                f"Final={breakdown['final_score']:.2f}"
            )
        else:
            return (
                f"✅ APPROVED: Strong consensus. "
                f"Rule={breakdown['rule_score']:.1f}, "
                f"ML={breakdown['ml_score']:.1f}, "
                f"LLM={breakdown['llm_score']:.1f} → "
                f"Final={breakdown['final_score']:.2f}"
            )
    
    def _generate_rejection_explanation(self, breakdown: Dict[str, Any]) -> str:
        """
        Generate human-readable explanation for REJECTED decision.
        
        Args:
            breakdown: Score breakdown dictionary
            
        Returns:
            Explanation string
        """
        if breakdown.get("ml_unavailable"):
            return (
                f"❌ REJECTED: Weak consensus (ML unavailable). "
                f"Rule={breakdown['rule_score']:.1f}, "
                f"LLM={breakdown['llm_score']:.1f} → "
                f"Final={breakdown['final_score']:.2f}"
            )
        else:
            return (
                f"❌ REJECTED: Weak consensus. "
                f"Rule={breakdown['rule_score']:.1f}, "
                f"ML={breakdown['ml_score']:.1f}, "
                f"LLM={breakdown['llm_score']:.1f} → "
                f"Final={breakdown['final_score']:.2f}"
            )
    
    async def arbitrate(
        self,
        signal: Signal,
        db: Session
    ) -> Tuple[str, str, Optional[str]]:
        """
        Arbitrate final decision for a trading signal.
        
        Process:
        1. Load active configuration
        2. Extract LLM confidence from explanation JSON
        3. Convert LLM sentiment to score
        4. Calculate weighted final score
        5. Compare against approval threshold
        6. Generate explanation and rejection reason
        
        Args:
            signal: Signal object with scores populated
            db: Database session
            
        Returns:
            Tuple of (final_decision, explanation, rejection_reason)
            - final_decision: "APPROVED" or "REJECTED"
            - explanation: Human-readable explanation
            - rejection_reason: Reason for rejection (None if approved)
        """
        # 1. Load config
        config = self.get_active_config(db)
        
        # 2. Extract LLM confidence from explanation
        llm_confidence = 50.0  # Default
        if signal.explanation:
            try:
                # Try to parse explanation as JSON
                explanation_data = json.loads(signal.explanation)
                llm_confidence = explanation_data.get("confidence", 50.0)
            except (json.JSONDecodeError, AttributeError):
                # If not JSON, use default confidence
                logger.debug(f"Could not parse LLM confidence from explanation, using default {llm_confidence}")
        
        # 3. Convert LLM sentiment to score
        llm_score = self.convert_sentiment_to_score(
            sentiment=signal.llm_sentiment or "NEUTRAL",
            confidence=llm_confidence
        )

        # Save LLM sentiment score to Signal
        signal.llm_sentiment_score = llm_score

        logger.debug(
            f"LLM sentiment conversion: {signal.llm_sentiment} (confidence={llm_confidence:.1f}) → score={llm_score:.2f}"
        )

        # 4. Calculate weighted score
        final_score, breakdown = self.calculate_weighted_score(
            rule_score=signal.rule_engine_score,
            ml_score=signal.ml_confidence_score,
            llm_score=llm_score,
            config=config
        )
        
        # 5. Make decision
        threshold = float(config.min_approval_score)
        if final_score >= threshold:
            decision = "APPROVED"
            explanation = self._generate_approval_explanation(breakdown)
            rejection_reason = None
            
            logger.info(
                f"Signal {signal.id} APPROVED: "
                f"final_score={final_score:.2f} >= threshold={threshold}"
            )
        else:
            decision = "REJECTED"
            explanation = self._generate_rejection_explanation(breakdown)
            rejection_reason = (
                f"Weighted score {final_score:.2f} below threshold {threshold}"
            )
            
            logger.info(
                f"Signal {signal.id} REJECTED: "
                f"final_score={final_score:.2f} < threshold={threshold}"
            )
        
        return decision, explanation, rejection_reason
    
    # ============================================
    # Phase 3 Reserved Interfaces
    # ============================================
    
    def get_dynamic_weights(
        self,
        market_volatility: float,
        recent_performance: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate dynamic weights based on market conditions and performance.
        
        **Phase 3 Extension**: This method is reserved for future implementation.
        
        Args:
            market_volatility: Current market volatility (ATR-based)
            recent_performance: Recent performance metrics for each engine
            
        Returns:
            Dictionary of dynamic weights
            
        Example:
            {
                "rule_weight": 0.45,
                "ml_weight": 0.35,
                "llm_weight": 0.20
            }
        """
        raise NotImplementedError(
            "Dynamic weight adjustment is a Phase 3 feature. "
            "Use fixed weights from database configuration in Phase 2."
        )

