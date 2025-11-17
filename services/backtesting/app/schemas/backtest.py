"""
Backtest request/response schemas.
"""

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, validator


class CreateBacktestRequest(BaseModel):
    """Request schema for creating a backtest."""

    strategy_name: str = Field(..., description="Strategy name (e.g., 'Rules Only', 'Rules + ML')")
    strategy_type: str = Field(
        default="rules_only",
        description="Strategy type: 'rules_only' (Rules Engine only) or 'rules_ml' (Rules + ML/LLM)"
    )
    market: str = Field(..., description="Trading pair (e.g., 'BTC/USDT')")
    interval: str = Field(default="1h", description="K-line interval (e.g., '1h', '4h', '1d')")
    start_date: date = Field(..., description="Backtest start date")
    end_date: date = Field(..., description="Backtest end date")
    initial_balance: Decimal = Field(default=Decimal("100000.00"), description="Initial balance")

    @validator("strategy_type")
    def validate_strategy_type(cls, v):
        """Validate strategy_type parameter."""
        allowed_types = ["rules_only", "rules_ml"]
        if v not in allowed_types:
            raise ValueError(f"strategy_type must be one of {allowed_types}, got: {v}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "strategy_name": "Rules Only",
                "strategy_type": "rules_only",
                "market": "BTC/USDT",
                "interval": "1h",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "initial_balance": 100000.00
            }
        }


class BacktestRunResponse(BaseModel):
    """Response schema for backtest run."""

    id: UUID
    strategy_name: str
    strategy_type: str
    market: str
    interval: str
    start_date: date
    end_date: date
    initial_balance: Decimal
    final_balance: Optional[Decimal] = None
    status: str
    progress: float
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BacktestListResponse(BaseModel):
    """Response schema for backtest list."""
    
    backtests: List[BacktestRunResponse]
    total: int
    page: int
    page_size: int

