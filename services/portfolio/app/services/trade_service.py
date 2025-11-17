"""
Trade Service - Business logic for trade management.
"""

import sys
import os
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.portfolio.app.models.trade import Trade

logger = setup_logging("trade_service")


class TradeService:
    """
    Trade management service.
    
    Provides business logic for querying trades.
    """
    
    def __init__(self, db: Session):
        """
        Initialize TradeService.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_trades(
        self,
        position_id: Optional[UUID] = None,
        trade_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[List[Trade], int]:
        """
        Get trades with optional filters and pagination.
        
        Args:
            position_id: Filter by position ID (optional)
            trade_type: Filter by trade type (optional)
            limit: Maximum number of results
            offset: Number of results to skip
        
        Returns:
            Tuple of (trades list, total count)
        """
        try:
            query = self.db.query(Trade)
            
            # Apply filters
            if position_id:
                query = query.filter(Trade.position_id == position_id)
            if trade_type:
                query = query.filter(Trade.trade_type == trade_type)
            
            # Get total count
            total = query.count()
            
            # Apply pagination and ordering
            trades = query.order_by(desc(Trade.timestamp)).limit(limit).offset(offset).all()
            
            logger.info(
                f"Retrieved {len(trades)} trades "
                f"(total={total}, position_id={position_id}, trade_type={trade_type})"
            )
            
            return trades, total
            
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            raise
    
    def get_trade_by_id(self, trade_id: UUID) -> Optional[Trade]:
        """
        Get trade by ID.
        
        Args:
            trade_id: Trade ID
        
        Returns:
            Trade object or None if not found
        """
        try:
            trade = self.db.query(Trade).filter(Trade.id == trade_id).first()
            
            if trade:
                logger.info(f"Retrieved trade: id={trade_id}")
            else:
                logger.warning(f"Trade not found: id={trade_id}")
            
            return trade
            
        except Exception as e:
            logger.error(f"Error getting trade by ID: {e}")
            raise

