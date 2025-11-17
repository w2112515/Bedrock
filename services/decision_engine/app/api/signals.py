"""
Signals API endpoints

Provides endpoints for signal generation and querying.
"""

import sys
import os
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.decision_engine.app.core.database import get_db
from services.decision_engine.app.core.config import settings
from services.decision_engine.app.models.signal import Signal
from services.decision_engine.app.engines.rule_engine import RuleEngine
from services.decision_engine.app.events.publisher import event_publisher

logger = setup_logging("signals_api")

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class GenerateSignalRequest(BaseModel):
    """Request model for signal generation."""
    market: Optional[str] = Field(None, description="Specific market to analyze (e.g., BTCUSDT). If not provided, analyzes all configured markets.")
    force_analysis: bool = Field(False, description="Force analysis even if recent signal exists")
    strategy_type: str = Field(
        default="auto",
        description="Strategy type: 'rules_only' (Rules Engine only), 'rules_ml' (Rules + ML/LLM), or 'auto' (use settings)"
    )

    @validator("strategy_type")
    def validate_strategy_type(cls, v):
        """Validate strategy_type parameter."""
        allowed_types = ["rules_only", "rules_ml", "auto"]
        if v not in allowed_types:
            raise ValueError(f"strategy_type must be one of {allowed_types}, got: {v}")
        return v


class SignalResponse(BaseModel):
    """Response model for a single signal."""
    id: str
    market: str
    signal_type: str
    entry_price: float
    stop_loss_price: float
    profit_target_price: float
    risk_unit_r: float
    suggested_position_weight: float
    reward_risk_ratio: Optional[float]
    onchain_signals: Optional[dict]
    rule_engine_score: float
    ml_confidence_score: Optional[float]
    llm_sentiment: Optional[str]
    final_decision: Optional[str]
    explanation: Optional[str]
    created_at: str


class SignalListResponse(BaseModel):
    """Response model for signal list."""
    signals: List[SignalResponse]
    total_count: int
    limit: int
    offset: int


# ============================================
# API Endpoints
# ============================================

@router.post("/generate", response_model=SignalResponse)
async def generate_signal(
    request: GenerateSignalRequest,
    db: Session = Depends(get_db)
):
    """
    Generate trading signal(s).
    
    If market is specified, analyzes that market only.
    Otherwise, analyzes all configured markets.
    
    Returns the first generated signal (if any).
    """
    try:
        logger.info(
            f"Signal generation requested: market={request.market}, "
            f"strategy_type={request.strategy_type}"
        )

        # Determine ML/LLM enablement based on strategy_type
        if request.strategy_type == "rules_only":
            ml_enabled = False
            llm_enabled = False
        elif request.strategy_type == "rules_ml":
            ml_enabled = True
            llm_enabled = True
        else:  # "auto"
            ml_enabled = settings.ML_ENABLED
            llm_enabled = settings.LLM_ENABLED

        # Initialize ML adapter (Phase 2)
        ml_adapter = None
        if ml_enabled and settings.ML_ENABLED:
            from services.decision_engine.app.adapters.xgboost_adapter import XGBoostAdapter
            try:
                ml_adapter = XGBoostAdapter(
                    model_path=settings.ML_MODEL_PATH,
                    fallback_score=settings.ML_FALLBACK_SCORE,
                    feature_names_path=settings.ML_FEATURE_NAMES_PATH
                )
                logger.info("ML adapter initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize ML adapter: {e}")

        # Initialize LLM adapter (Phase 2)
        llm_adapter = None
        if llm_enabled and settings.LLM_ENABLED:
            from services.decision_engine.app.adapters.llm_factory import LLMAdapterFactory
            try:
                llm_adapter = LLMAdapterFactory.create_adapter()
                logger.info("LLM adapter initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM adapter: {e}")

        # Initialize rule engine with ML, LLM adapters, and event publisher
        rule_engine = RuleEngine(
            ml_adapter=ml_adapter,
            llm_adapter=llm_adapter,
            event_publisher=event_publisher
        )
        
        # Determine symbols to analyze
        if request.market:
            symbols = [request.market]
        else:
            symbols = settings.TRADING_SYMBOLS
        
        # Generate signals (events are published inside RuleEngine)
        signals = await rule_engine.analyze(
            symbols=symbols,
            db=db,
            interval="1h"
        )

        # Filter only APPROVED signals for API response
        # (REJECTED signals are already saved to DB and published to signal.rejected channel)
        approved_signals = [s for s in signals if s.final_decision == "APPROVED"]

        if not approved_signals:
            raise HTTPException(
                status_code=404,
                detail=f"No approved signals generated for {request.market or 'configured markets'}"
            )

        # Return first approved signal
        first_signal = approved_signals[0]
        
        return SignalResponse(
            id=str(first_signal.id),
            market=first_signal.market,
            signal_type=first_signal.signal_type,
            entry_price=float(first_signal.entry_price),
            stop_loss_price=float(first_signal.stop_loss_price),
            profit_target_price=float(first_signal.profit_target_price),
            risk_unit_r=float(first_signal.risk_unit_r),
            suggested_position_weight=float(first_signal.suggested_position_weight),
            reward_risk_ratio=float(first_signal.reward_risk_ratio) if first_signal.reward_risk_ratio else None,
            onchain_signals=first_signal.onchain_signals,
            rule_engine_score=first_signal.rule_engine_score,
            ml_confidence_score=first_signal.ml_confidence_score,
            llm_sentiment=first_signal.llm_sentiment,
            final_decision=first_signal.final_decision,
            explanation=first_signal.explanation,
            created_at=first_signal.created_at.isoformat() if first_signal.created_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating signal: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/list", response_model=SignalListResponse)
async def list_signals(
    market: Optional[str] = Query(None, description="Filter by market"),
    limit: int = Query(10, ge=1, le=100, description="Number of signals to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    List historical signals with pagination.
    
    Supports filtering by market and pagination.
    Results are sorted by created_at descending (newest first).
    """
    try:
        # Build query
        query = db.query(Signal)
        
        # Apply market filter
        if market:
            query = query.filter(Signal.market == market)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination and sorting
        signals = query.order_by(desc(Signal.created_at)).limit(limit).offset(offset).all()
        
        # Convert to response models
        signal_responses = [
            SignalResponse(
                id=str(signal.id),
                market=signal.market,
                signal_type=signal.signal_type,
                entry_price=float(signal.entry_price),
                stop_loss_price=float(signal.stop_loss_price),
                profit_target_price=float(signal.profit_target_price),
                risk_unit_r=float(signal.risk_unit_r),
                suggested_position_weight=float(signal.suggested_position_weight),
                reward_risk_ratio=float(signal.reward_risk_ratio) if signal.reward_risk_ratio else None,
                onchain_signals=signal.onchain_signals,
                rule_engine_score=signal.rule_engine_score,
                ml_confidence_score=signal.ml_confidence_score,
                llm_sentiment=signal.llm_sentiment,
                final_decision=signal.final_decision,
                explanation=signal.explanation,
                created_at=signal.created_at.isoformat() if signal.created_at else None
            )
            for signal in signals
        ]
        
        return SignalListResponse(
            signals=signal_responses,
            total_count=total_count,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Error listing signals: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class TimeRangeInfo(BaseModel):
    """Time range information"""
    start_date: Optional[str] = Field(None, description="Start date (ISO 8601)")
    end_date: Optional[str] = Field(None, description="End date (ISO 8601)")


class ArbiterStatsResponse(BaseModel):
    """Arbiter statistics response model"""
    approved_count: int = Field(..., description="Number of APPROVED signals")
    rejected_count: int = Field(..., description="Number of REJECTED signals")
    total_count: int = Field(..., description="Total number of signals")
    approval_rate: float = Field(..., description="Approval rate (0.0-1.0)")
    rejection_reasons: Dict[str, int] = Field(..., description="Rejection reasons distribution")
    time_range: TimeRangeInfo = Field(..., description="Query time range")


@router.get("/arbiter-stats", response_model=ArbiterStatsResponse)
async def get_arbiter_stats(
    start_date: Optional[str] = Query(None, description="Start date (ISO 8601, e.g., 2024-11-01T00:00:00Z)"),
    end_date: Optional[str] = Query(None, description="End date (ISO 8601, e.g., 2024-11-16T23:59:59Z)"),
    db: Session = Depends(get_db)
):
    """
    Get arbitration statistics.

    Returns statistics about APPROVED/REJECTED signals, including:
    - Count statistics
    - Approval rate
    - Rejection reason distribution

    Supports optional time range filtering.
    """
    try:
        query = db.query(Signal)

        parsed_start_date = None
        parsed_end_date = None

        if start_date:
            try:
                parsed_start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(Signal.created_at >= parsed_start_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid start_date format: {start_date}. Use ISO 8601 format (e.g., 2024-11-01T00:00:00Z)"
                )

        if end_date:
            try:
                parsed_end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(Signal.created_at <= parsed_end_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid end_date format: {end_date}. Use ISO 8601 format (e.g., 2024-11-16T23:59:59Z)"
                )

        approved_count = query.filter(Signal.final_decision == "APPROVED").count()
        rejected_count = query.filter(Signal.final_decision == "REJECTED").count()
        total_count = approved_count + rejected_count

        approval_rate = approved_count / total_count if total_count > 0 else 0.0

        rejection_reasons_query = (
            db.query(Signal.rejection_reason, func.count(Signal.id).label('count'))
            .filter(Signal.final_decision == "REJECTED")
        )

        if parsed_start_date:
            rejection_reasons_query = rejection_reasons_query.filter(Signal.created_at >= parsed_start_date)
        if parsed_end_date:
            rejection_reasons_query = rejection_reasons_query.filter(Signal.created_at <= parsed_end_date)

        rejection_reasons_results = rejection_reasons_query.group_by(Signal.rejection_reason).all()
        rejection_reasons = {reason or "Unknown": count for reason, count in rejection_reasons_results}

        logger.info(f"Arbiter stats: approved={approved_count}, rejected={rejected_count}, total={total_count}, rate={approval_rate:.2%}")

        return ArbiterStatsResponse(
            approved_count=approved_count,
            rejected_count=rejected_count,
            total_count=total_count,
            approval_rate=approval_rate,
            rejection_reasons=rejection_reasons,
            time_range=TimeRangeInfo(start_date=start_date, end_date=end_date)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get arbiter stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(
    signal_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a single signal by ID.
    """
    try:
        signal = db.query(Signal).filter(Signal.id == signal_id).first()
        
        if not signal:
            raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")
        
        return SignalResponse(
            id=str(signal.id),
            market=signal.market,
            signal_type=signal.signal_type,
            entry_price=float(signal.entry_price),
            stop_loss_price=float(signal.stop_loss_price),
            profit_target_price=float(signal.profit_target_price),
            risk_unit_r=float(signal.risk_unit_r),
            suggested_position_weight=float(signal.suggested_position_weight),
            reward_risk_ratio=float(signal.reward_risk_ratio) if signal.reward_risk_ratio else None,
            onchain_signals=signal.onchain_signals,
            rule_engine_score=signal.rule_engine_score,
            ml_confidence_score=signal.ml_confidence_score,
            llm_sentiment=signal.llm_sentiment,
            final_decision=signal.final_decision,
            explanation=signal.explanation,
            created_at=signal.created_at.isoformat() if signal.created_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting signal {signal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

