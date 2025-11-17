"""
Trade API endpoints.
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
from services.portfolio.app.services.trade_service import TradeService
from services.portfolio.app.schemas.trade import TradeResponse, TradeListResponse

logger = setup_logging("api.trades")

router = APIRouter()


@router.get("", response_model=TradeListResponse)
async def get_trades(
    position_id: Optional[UUID] = Query(None, description="Filter by position ID"),
    trade_type: Optional[str] = Query(None, description="Filter by trade type (ENTRY, EXIT)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """
    Get trades with optional filters and pagination.
    
    Query Parameters:
    - position_id: Filter by position ID
    - trade_type: Filter by trade type (ENTRY, EXIT)
    - limit: Maximum number of results (1-100, default: 20)
    - offset: Number of results to skip (default: 0)
    """
    try:
        trade_service = TradeService(db)
        trades, total = trade_service.get_trades(
            position_id=position_id,
            trade_type=trade_type,
            limit=limit,
            offset=offset
        )
        
        return TradeListResponse(
            trades=[TradeResponse.from_orm(t) for t in trades],
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get trade by ID.
    
    Path Parameters:
    - trade_id: Trade UUID
    """
    try:
        trade_service = TradeService(db)
        trade = trade_service.get_trade_by_id(trade_id)
        
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        return TradeResponse.from_orm(trade)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

