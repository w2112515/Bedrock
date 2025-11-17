"""
Arbitration API Endpoints

Provides endpoints for:
- Arbitration configuration management
- Configuration history and rollback
- Arbitration statistics

Phase 2 - Task 2.3.8: Implement Arbitration API
"""

import sys
import os
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import uuid

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from shared.utils.database import get_db
from services.decision_engine.app.models.arbitration_config import ArbitrationConfig
from services.decision_engine.app.models.signal import Signal

logger = setup_logging("arbitration_api")

router = APIRouter(prefix="/v1/arbitration", tags=["Arbitration"])


# ============================================
# Pydantic Models
# ============================================

class ArbitrationConfigResponse(BaseModel):
    """Response model for arbitration configuration."""
    id: str
    version: int
    rule_weight: float
    ml_weight: float
    llm_weight: float
    min_approval_score: float
    adaptive_threshold_enabled: bool
    is_active: bool
    created_at: datetime

    @classmethod
    def from_orm(cls, obj):
        """Convert ORM object to Pydantic model."""
        return cls(
            id=str(obj.id),
            version=obj.version,
            rule_weight=float(obj.rule_weight),
            ml_weight=float(obj.ml_weight),
            llm_weight=float(obj.llm_weight),
            min_approval_score=float(obj.min_approval_score),
            adaptive_threshold_enabled=obj.adaptive_threshold_enabled,
            is_active=obj.is_active,
            created_at=obj.created_at
        )

    class Config:
        from_attributes = True


class ArbitrationConfigUpdate(BaseModel):
    """Request model for updating arbitration configuration."""
    rule_weight: float = Field(..., ge=0.0, le=1.0, description="Rule engine weight (0-1)")
    ml_weight: float = Field(..., ge=0.0, le=1.0, description="ML model weight (0-1)")
    llm_weight: float = Field(..., ge=0.0, le=1.0, description="LLM weight (0-1)")
    min_approval_score: float = Field(..., ge=0.0, le=100.0, description="Minimum approval score (0-100)")
    adaptive_threshold_enabled: bool = Field(default=False, description="Enable adaptive threshold (Phase 3)")
    
    @validator('rule_weight', 'ml_weight', 'llm_weight')
    def validate_weights_sum(cls, v, values):
        """Validate that weights sum to 1.0."""
        if 'rule_weight' in values and 'ml_weight' in values:
            total = values['rule_weight'] + values['ml_weight'] + v
            if abs(total - 1.0) > 0.0001:
                raise ValueError(f"Weights must sum to 1.0, got {total:.4f}")
        return v


class ArbitrationStatsResponse(BaseModel):
    """Response model for arbitration statistics."""
    total_signals: int
    approved_signals: int
    rejected_signals: int
    approval_rate: float
    
    # Engine agreement statistics
    ml_llm_agreement_rate: Optional[float] = None
    rule_ml_agreement_rate: Optional[float] = None
    rule_llm_agreement_rate: Optional[float] = None
    
    # Score distributions
    avg_rule_score: float
    avg_ml_score: Optional[float] = None
    avg_llm_score: Optional[float] = None
    avg_final_score: float
    
    # Top rejection reasons
    top_rejection_reasons: List[dict]


# ============================================
# API Endpoints
# ============================================

@router.get("/config", response_model=ArbitrationConfigResponse)
async def get_active_config(db: Session = Depends(get_db)):
    """
    Get current active arbitration configuration.

    Returns:
        Active ArbitrationConfig object

    Raises:
        HTTPException 404: If no active config found
    """
    config = db.query(ArbitrationConfig).filter_by(is_active=True).first()

    if not config:
        logger.error("No active arbitration config found")
        raise HTTPException(status_code=404, detail="No active configuration found")

    logger.info(f"Retrieved active config version {config.version}")
    return ArbitrationConfigResponse.from_orm(config)


@router.put("/config", response_model=ArbitrationConfigResponse)
async def update_config(
    update: ArbitrationConfigUpdate,
    db: Session = Depends(get_db)
):
    """
    Update arbitration configuration (creates new version).
    
    This endpoint:
    1. Deactivates current active config
    2. Creates new config version with updated values
    3. Sets new config as active
    
    Args:
        update: New configuration values
        
    Returns:
        Newly created ArbitrationConfig object
    """
    try:
        # 1. Get current active config
        current_config = db.query(ArbitrationConfig).filter_by(is_active=True).first()
        
        if current_config:
            # Deactivate current config
            current_config.is_active = False
            logger.info(f"Deactivated config version {current_config.version}")
        
        # 2. Calculate next version number
        max_version = db.query(func.max(ArbitrationConfig.version)).scalar() or 0
        next_version = max_version + 1
        
        # 3. Create new config
        new_config = ArbitrationConfig(
            id=uuid.uuid4(),
            version=next_version,
            rule_weight=Decimal(str(update.rule_weight)),
            ml_weight=Decimal(str(update.ml_weight)),
            llm_weight=Decimal(str(update.llm_weight)),
            min_approval_score=Decimal(str(update.min_approval_score)),
            adaptive_threshold_enabled=update.adaptive_threshold_enabled,
            is_active=True
        )
        
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        
        logger.info(
            f"Created new config version {next_version}: "
            f"rule={update.rule_weight}, ml={update.ml_weight}, llm={update.llm_weight}, "
            f"threshold={update.min_approval_score}"
        )

        return ArbitrationConfigResponse.from_orm(new_config)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")


@router.get("/config/history", response_model=List[ArbitrationConfigResponse])
async def get_config_history(
    limit: int = Query(default=10, ge=1, le=100, description="Number of versions to return"),
    db: Session = Depends(get_db)
):
    """
    Get arbitration configuration history.
    
    Args:
        limit: Maximum number of versions to return (default: 10)
        
    Returns:
        List of ArbitrationConfig objects ordered by version (descending)
    """
    configs = (
        db.query(ArbitrationConfig)
        .order_by(desc(ArbitrationConfig.version))
        .limit(limit)
        .all()
    )

    logger.info(f"Retrieved {len(configs)} config versions")
    return [ArbitrationConfigResponse.from_orm(c) for c in configs]


@router.post("/config/rollback/{version}", response_model=ArbitrationConfigResponse)
async def rollback_config(
    version: int,
    db: Session = Depends(get_db)
):
    """
    Rollback to a specific configuration version.
    
    This endpoint:
    1. Finds the specified version
    2. Deactivates current active config
    3. Creates a new config with same values as specified version
    4. Sets new config as active
    
    Args:
        version: Version number to rollback to
        
    Returns:
        Newly created ArbitrationConfig object
        
    Raises:
        HTTPException 404: If specified version not found
    """
    try:
        # 1. Find target version
        target_config = db.query(ArbitrationConfig).filter_by(version=version).first()
        
        if not target_config:
            raise HTTPException(status_code=404, detail=f"Version {version} not found")
        
        # 2. Deactivate current active config
        current_config = db.query(ArbitrationConfig).filter_by(is_active=True).first()
        if current_config:
            current_config.is_active = False
        
        # 3. Calculate next version number
        max_version = db.query(func.max(ArbitrationConfig.version)).scalar() or 0
        next_version = max_version + 1
        
        # 4. Create new config with target values
        new_config = ArbitrationConfig(
            id=uuid.uuid4(),
            version=next_version,
            rule_weight=target_config.rule_weight,
            ml_weight=target_config.ml_weight,
            llm_weight=target_config.llm_weight,
            min_approval_score=target_config.min_approval_score,
            adaptive_threshold_enabled=target_config.adaptive_threshold_enabled,
            is_active=True
        )
        
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        
        logger.info(
            f"Rolled back to version {version}, created new version {next_version}"
        )

        return ArbitrationConfigResponse.from_orm(new_config)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to rollback config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to rollback configuration: {str(e)}")


def _parse_final_score_from_explanation(explanation: str) -> Optional[float]:
    """
    从 explanation 文本中解析 final_score。

    支持的格式：
    - "✅ APPROVED: Strong consensus. Rule=75.5, ML=87.0, LLM=82.0 → Final=78.2"
    - "❌ REJECTED: Weak consensus (ML unavailable). Rule=65.0, LLM=70.0 → Final=66.5"

    Args:
        explanation: 决策解释文本

    Returns:
        解析出的 final_score，如果解析失败返回 None
    """
    if not explanation:
        return None

    import re
    # 匹配 "Final=XX.XX" 或 "Final=XX.X" 或 "Final=XX"
    match = re.search(r'Final=(\d+\.?\d*)', explanation)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


@router.get("/stats", response_model=ArbitrationStatsResponse)
async def get_arbitration_stats(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get arbitration statistics.
    
    Args:
        days: Number of days to analyze (default: 7)
        
    Returns:
        ArbitrationStatsResponse with comprehensive statistics
    """
    try:
        # Calculate date threshold
        from datetime import timedelta
        threshold_date = datetime.utcnow() - timedelta(days=days)
        
        # Query signals
        signals = db.query(Signal).filter(Signal.created_at >= threshold_date).all()
        
        if not signals:
            return ArbitrationStatsResponse(
                total_signals=0,
                approved_signals=0,
                rejected_signals=0,
                approval_rate=0.0,
                avg_rule_score=0.0,
                avg_final_score=0.0,
                top_rejection_reasons=[]
            )
        
        # Calculate basic stats
        total = len(signals)
        approved = sum(1 for s in signals if s.final_decision == "APPROVED")
        rejected = sum(1 for s in signals if s.final_decision == "REJECTED")
        approval_rate = (approved / total * 100) if total > 0 else 0.0
        
        # Calculate average scores
        avg_rule_score = sum(s.rule_engine_score for s in signals) / total
        
        ml_scores = [s.ml_confidence_score for s in signals if s.ml_confidence_score is not None]
        avg_ml_score = sum(ml_scores) / len(ml_scores) if ml_scores else None

        # Calculate avg_llm_score
        # Note: After backfill, all signals with llm_sentiment should have llm_sentiment_score
        llm_scores = [s.llm_sentiment_score for s in signals if s.llm_sentiment_score is not None]
        avg_llm_score = sum(llm_scores) / len(llm_scores) if llm_scores else None

        # Log statistics for monitoring
        llm_score_str = f"{avg_llm_score:.2f}" if avg_llm_score is not None else "N/A"
        logger.info(
            f"Calculated avg_llm_score from {len(llm_scores)}/{total} signals: {llm_score_str}"
        )

        # Calculate avg_final_score from explanation field
        final_scores = []
        for s in signals:
            if s.explanation:
                parsed_score = _parse_final_score_from_explanation(s.explanation)
                if parsed_score is not None:
                    final_scores.append(parsed_score)

        # Use parsed scores if available, otherwise fallback to rule_engine_score
        if final_scores:
            avg_final_score = sum(final_scores) / len(final_scores)
            logger.info(
                f"Calculated avg_final_score from {len(final_scores)}/{total} signals' explanations: {avg_final_score:.2f}"
            )
        else:
            # Fallback: use rule_engine_score as proxy
            avg_final_score = avg_rule_score
            logger.warning(
                f"Could not parse final_score from explanations, using avg_rule_score as fallback: {avg_final_score:.2f}"
            )

        # Top rejection reasons
        rejection_reasons = {}
        for s in signals:
            if s.rejection_reason:
                reason = s.rejection_reason
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
        
        top_rejection_reasons = [
            {"reason": reason, "count": count}
            for reason, count in sorted(
                rejection_reasons.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        ]
        
        logger.info(
            f"Generated stats for {days} days: "
            f"{total} signals, {approved} approved ({approval_rate:.1f}%)"
        )
        
        return ArbitrationStatsResponse(
            total_signals=total,
            approved_signals=approved,
            rejected_signals=rejected,
            approval_rate=approval_rate,
            avg_rule_score=avg_rule_score,
            avg_ml_score=avg_ml_score,
            avg_llm_score=avg_llm_score,
            avg_final_score=avg_final_score,
            top_rejection_reasons=top_rejection_reasons
        )
        
    except Exception as e:
        logger.error(f"Failed to generate stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate statistics: {str(e)}")

