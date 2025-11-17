"""
Pydantic schemas for Stats API.
"""

from decimal import Decimal
from pydantic import BaseModel, Field


class StatsResponse(BaseModel):
    """Account statistics response schema."""
    
    total_pnl: Decimal = Field(description="Total realized profit/loss")
    win_rate: Decimal = Field(description="Win rate (0.0-1.0)")
    total_trades: int = Field(description="Total number of trades (closed positions)")
    winning_trades: int = Field(description="Number of winning trades")
    losing_trades: int = Field(description="Number of losing trades")
    avg_win: Decimal = Field(description="Average profit per winning trade")
    avg_loss: Decimal = Field(description="Average loss per losing trade")
    profit_factor: Decimal = Field(description="Profit factor (total wins / total losses)")
    open_positions: int = Field(description="Number of currently open positions")
    total_commission: Decimal = Field(description="Total commission paid")

