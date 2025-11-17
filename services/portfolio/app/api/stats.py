"""
Stats API endpoints.
"""

import sys
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.portfolio.app.core.database import get_db
from services.portfolio.app.services.stats_service import StatsService
from services.portfolio.app.schemas.stats import StatsResponse

logger = setup_logging("api.stats")

router = APIRouter()


@router.get("", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """
    Get portfolio statistics.
    
    Returns:
    - total_pnl: Total realized profit/loss
    - win_rate: Win rate (0.0-1.0)
    - total_trades: Total number of trades (closed positions)
    - winning_trades: Number of winning trades
    - losing_trades: Number of losing trades
    - avg_win: Average profit per winning trade
    - avg_loss: Average loss per losing trade
    - profit_factor: Profit factor (total wins / total losses)
    - open_positions: Number of currently open positions
    - total_commission: Total commission paid
    """
    try:
        stats_service = StatsService(db)
        stats = stats_service.get_stats()
        
        return StatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

