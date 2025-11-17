"""
Pydantic schemas for Account API.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
from uuid import UUID


class AccountResponse(BaseModel):
    """Account response schema."""
    
    id: UUID
    balance: Decimal
    available_balance: Decimal
    frozen_balance: Decimal
    updated_at: datetime
    
    class Config:
        from_attributes = True

