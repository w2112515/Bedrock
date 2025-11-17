"""
Event Publisher - Publishes portfolio.updated and position.closed events.
"""

import sys
import os
import json
import time
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from shared.utils.redis_client import get_redis_client
from services.portfolio.app.core.config import settings
from services.portfolio.app.models.position import Position

logger = setup_logging("event_publisher")


class EventPublisher:
    """
    Event publisher for portfolio events.
    
    Publishes:
    1. portfolio.updated - When position is opened or updated
    2. position.closed - When position is closed
    """
    
    def __init__(self):
        """Initialize EventPublisher."""
        self.portfolio_updated_channel = settings.PORTFOLIO_UPDATED_CHANNEL
        self.position_closed_channel = settings.POSITION_CLOSED_CHANNEL
        self.max_retries = settings.EVENT_PUBLISH_MAX_RETRIES
        self.retry_delay = settings.EVENT_PUBLISH_RETRY_DELAY
        
        logger.info(
            f"EventPublisher initialized: "
            f"portfolio_updated={self.portfolio_updated_channel}, "
            f"position_closed={self.position_closed_channel}"
        )
    
    def publish_portfolio_updated(self, position: Position, action: str):
        """
        Publish portfolio.updated event.
        
        Args:
            position: Position object
            action: Action type (e.g., POSITION_OPENED, POSITION_UPDATED)
        """
        try:
            event_payload = {
                "position_id": str(position.id),
                "market": position.market,
                "action": action,
                "position_size": float(position.position_size),
                "entry_price": float(position.entry_price),
                "current_price": float(position.current_price),
                "unrealized_pnl": float(position.unrealized_pnl) if position.unrealized_pnl else 0.0,
                "position_weight_used": float(position.position_weight_used),
                "status": position.status,
                "timestamp": position.created_at.isoformat() if position.created_at else None
            }
            
            self._publish_event(self.portfolio_updated_channel, event_payload)
            
            logger.info(
                f"Published portfolio.updated event: "
                f"position_id={position.id}, action={action}"
            )
            
        except Exception as e:
            logger.error(f"Error publishing portfolio.updated event: {e}")
            raise
    
    def publish_position_closed(
        self,
        position: Position,
        exit_price: float,
        exit_reason: str,
        realized_pnl: float
    ):
        """
        Publish position.closed event.
        
        Args:
            position: Position object
            exit_price: Exit price
            exit_reason: Exit reason
            realized_pnl: Realized profit/loss
        """
        try:
            event_payload = {
                "position_id": str(position.id),
                "market": position.market,
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "realized_pnl": realized_pnl,
                "roi": (realized_pnl / float(position.position_size * position.entry_price)) * 100 if position.position_size and position.entry_price else 0.0,
                "timestamp": position.closed_at.isoformat() if position.closed_at else None
            }
            
            self._publish_event(self.position_closed_channel, event_payload)
            
            logger.info(
                f"Published position.closed event: "
                f"position_id={position.id}, realized_pnl={realized_pnl}"
            )
            
        except Exception as e:
            logger.error(f"Error publishing position.closed event: {e}")
            raise
    
    def _publish_event(self, channel: str, event_payload: Dict[str, Any]):
        """
        Publish event to Redis channel with retry mechanism.
        
        Args:
            channel: Redis channel name
            event_payload: Event payload dictionary
        """
        message = json.dumps(event_payload)
        
        for attempt in range(self.max_retries):
            try:
                redis_client = get_redis_client()
                redis_client.publish(channel, message)
                
                logger.debug(
                    f"Event published to channel '{channel}': "
                    f"{message[:100]}..."
                )
                
                return
                
            except Exception as e:
                logger.warning(
                    f"Failed to publish event (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(
                        f"Failed to publish event after {self.max_retries} attempts"
                    )
                    raise


# Global event publisher instance
event_publisher = EventPublisher()

