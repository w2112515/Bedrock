"""
Pydantic schemas for Position API.
"""

from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_serializer
from uuid import UUID


class PositionResponse(BaseModel):
    """Position response schema."""

    id: UUID
    market: str
    signal_id: UUID
    position_size: Decimal
    entry_price: Decimal
    current_price: Decimal
    stop_loss_price: Decimal
    profit_target_price: Decimal
    position_weight_used: Decimal = Field(description="Actual position weight used (0.0000-1.0000)")
    status: str
    unrealized_pnl: Optional[Decimal] = None
    created_at: datetime
    closed_at: Optional[datetime] = None
    exit_reason: Optional[str] = None

    # Serialize Decimal fields as float for frontend compatibility
    @field_serializer('position_size', 'entry_price', 'current_price',
                      'stop_loss_price', 'profit_target_price',
                      'position_weight_used', 'unrealized_pnl')
    def serialize_decimal(self, value: Optional[Decimal]) -> Optional[float]:
        """Convert Decimal to float for JSON serialization."""
        return float(value) if value is not None else None

    class Config:
        from_attributes = True


class PositionListResponse(BaseModel):
    """Position list response schema with pagination."""
    
    positions: List[PositionResponse]
    total: int
    limit: int
    offset: int


class PositionEstimateResponse(BaseModel):
    """Position estimate response schema (方案A核心端点)."""

    signal_id: Optional[UUID] = None
    market: str
    estimated_position_size: Decimal = Field(description="Estimated position size (quantity)")
    estimated_cost: Decimal = Field(description="Estimated total cost (including commission and slippage)")
    position_weight_used: Decimal = Field(description="Position weight that will be used")
    commission: Decimal = Field(description="Estimated commission")
    slippage: Decimal = Field(description="Estimated slippage cost")
    risk_percentage: Decimal = Field(description="Risk as percentage of account balance")
    entry_price: Decimal
    stop_loss_price: Decimal
    profit_target_price: Decimal

    # Serialize Decimal fields as float for frontend compatibility
    @field_serializer('estimated_position_size', 'estimated_cost',
                      'position_weight_used', 'commission', 'slippage',
                      'risk_percentage', 'entry_price', 'stop_loss_price',
                      'profit_target_price')
    def serialize_decimal(self, value: Decimal) -> float:
        """Convert Decimal to float for JSON serialization."""
        return float(value)

