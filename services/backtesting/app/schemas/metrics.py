"""
Backtest metrics schemas.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel


class BacktestMetricsResponse(BaseModel):
    """Response schema for backtest metrics."""
    
    id: UUID
    backtest_run_id: UUID
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: Decimal
    avg_loss: Decimal
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    omega_ratio: Optional[float] = None
    total_commission: Decimal
    total_slippage: Decimal
    roi: float
    created_at: datetime
    
    class Config:
        from_attributes = True

