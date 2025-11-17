"""
Position API endpoints.
"""

import sys
import os
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.portfolio.app.core.database import get_db
from services.portfolio.app.services.position_service import PositionService
from services.portfolio.app.services.position_sizer import PositionSizer
from services.portfolio.app.services.account_service import AccountService
from services.portfolio.app.schemas.position import (
    PositionResponse,
    PositionListResponse,
    PositionEstimateResponse
)

logger = setup_logging("api.positions")

router = APIRouter()


@router.get("", response_model=PositionListResponse)
async def get_positions(
    market: Optional[str] = Query(None, description="Filter by market"),
    status: Optional[str] = Query(None, description="Filter by status (OPEN, CLOSED)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """
    Get positions with optional filters and pagination.
    
    Query Parameters:
    - market: Filter by market (e.g., BTC/USDT)
    - status: Filter by status (OPEN, CLOSED)
    - limit: Maximum number of results (1-100, default: 20)
    - offset: Number of results to skip (default: 0)
    """
    try:
        position_service = PositionService(db)
        positions, total = position_service.get_positions(
            market=market,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return PositionListResponse(
            positions=[PositionResponse.from_orm(p) for p in positions],
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{position_id}", response_model=PositionResponse)
async def get_position(
    position_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get position by ID.
    
    Path Parameters:
    - position_id: Position UUID
    """
    try:
        position_service = PositionService(db)
        position = position_service.get_position_by_id(position_id)
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        return PositionResponse.from_orm(position)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/estimate", response_model=PositionEstimateResponse)
async def estimate_position(
    signal_data: dict,
    db: Session = Depends(get_db)
):
    """
    Estimate position size and costs for a signal (方案A核心端点).
    
    Request Body:
    - signal_id: Signal UUID
    - market: Trading pair (e.g., BTC/USDT)
    - entry_price: Entry price
    - stop_loss_price: Stop loss price
    - profit_target_price: Profit target price
    - risk_unit_r: Risk unit (R) in quote currency
    - suggested_position_weight: Optional suggested position weight (0.0-1.0)
    
    Returns:
    - estimated_position_size: Estimated position size (quantity)
    - estimated_cost: Estimated total cost (including commission and slippage)
    - position_weight_used: Position weight that will be used
    - commission: Estimated commission
    - slippage: Estimated slippage cost
    - risk_percentage: Risk as percentage of account balance
    """
    try:
        # Get account
        account_service = AccountService(db)
        account = account_service.get_account()
        
        # Estimate position
        position_sizer = PositionSizer()
        estimation = position_sizer.estimate_position(
            signal_data=signal_data,
            account_balance=account.available_balance
        )
        
        return PositionEstimateResponse(**estimation)
        
    except Exception as e:
        logger.error(f"Error estimating position: {e}")
        raise HTTPException(status_code=500, detail=str(e))

