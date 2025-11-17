"""
Account API endpoints.
"""

import sys
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.portfolio.app.core.database import get_db
from services.portfolio.app.services.account_service import AccountService
from services.portfolio.app.schemas.account import AccountResponse

logger = setup_logging("api.account")

router = APIRouter()


@router.get("", response_model=AccountResponse)
async def get_account(db: Session = Depends(get_db)):
    """
    Get account information.
    
    Returns:
    - id: Account UUID
    - balance: Total account balance
    - available_balance: Available balance for new positions
    - frozen_balance: Frozen balance (locked in open positions)
    - updated_at: Last update timestamp
    """
    try:
        account_service = AccountService(db)
        account = account_service.get_account()
        
        return AccountResponse.from_orm(account)
        
    except Exception as e:
        logger.error(f"Error getting account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

