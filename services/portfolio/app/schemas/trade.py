"""
Pydantic schemas for Trade API.
"""

from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, field_serializer
from uuid import UUID


class TradeResponse(BaseModel):
    """Trade response schema."""

    id: UUID
    position_id: UUID
    trade_type: str
    market: str
    quantity: Decimal
    price: Decimal
    timestamp: datetime
    commission: Decimal
    realized_pnl: Optional[Decimal] = None

    # Serialize Decimal fields as float for frontend compatibility
    @field_serializer('quantity', 'price', 'commission', 'realized_pnl')
    def serialize_decimal(self, value: Optional[Decimal]) -> Optional[float]:
        """Convert Decimal to float for JSON serialization."""
        return float(value) if value is not None else None

    class Config:
        from_attributes = True


class TradeListResponse(BaseModel):
    """Trade list response schema with pagination."""
    
    trades: List[TradeResponse]
    total: int
    limit: int
    offset: int

