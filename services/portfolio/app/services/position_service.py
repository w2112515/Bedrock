"""
Position Service - Business logic for position management.
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
from services.portfolio.app.models.position import Position

logger = setup_logging("position_service")


class PositionService:
    """
    Position management service.
    
    Provides business logic for querying positions.
    """
    
    def __init__(self, db: Session):
        """
        Initialize PositionService.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_positions(
        self,
        market: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> tuple[List[Position], int]:
        """
        Get positions with optional filters and pagination.
        
        Args:
            market: Filter by market (optional)
            status: Filter by status (optional)
            limit: Maximum number of results
            offset: Number of results to skip
        
        Returns:
            Tuple of (positions list, total count)
        """
        try:
            query = self.db.query(Position)
            
            # Apply filters
            if market:
                query = query.filter(Position.market == market)
            if status:
                query = query.filter(Position.status == status)
            
            # Get total count
            total = query.count()
            
            # Apply pagination and ordering
            positions = query.order_by(desc(Position.created_at)).limit(limit).offset(offset).all()
            
            logger.info(
                f"Retrieved {len(positions)} positions "
                f"(total={total}, market={market}, status={status})"
            )
            
            return positions, total
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            raise
    
    def get_position_by_id(self, position_id: UUID) -> Optional[Position]:
        """
        Get position by ID.
        
        Args:
            position_id: Position ID
        
        Returns:
            Position object or None if not found
        """
        try:
            position = self.db.query(Position).filter(Position.id == position_id).first()
            
            if position:
                logger.info(f"Retrieved position: id={position_id}")
            else:
                logger.warning(f"Position not found: id={position_id}")
            
            return position
            
        except Exception as e:
            logger.error(f"Error getting position by ID: {e}")
            raise
    
    def get_open_positions(self) -> List[Position]:
        """
        Get all open positions.
        
        Returns:
            List of open positions
        """
        try:
            positions = self.db.query(Position).filter(Position.status == 'OPEN').all()
            
            logger.info(f"Retrieved {len(positions)} open positions")
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting open positions: {e}")
            raise

