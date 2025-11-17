"""
Backtest trade schemas.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel


class BacktestTradeResponse(BaseModel):
    """Response schema for backtest trade."""
    
    id: UUID
    backtest_run_id: UUID
    market: str
    signal_id: Optional[UUID] = None
    trade_type: str
    quantity: Decimal
    price: Decimal
    timestamp: datetime
    commission: Decimal
    slippage: Decimal
    realized_pnl: Optional[Decimal] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

