"""
Event Subscriber - Subscribes to signal.created events from DecisionEngine.

Implements error recovery mechanism with failed_signal_events table.
"""

import sys
import os
import json
import time
import threading
from uuid import UUID
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from shared.utils.redis_client import get_redis_client
from services.portfolio.app.core.config import settings
from services.portfolio.app.core.database import SessionLocal
from services.portfolio.app.models.failed_signal_event import FailedSignalEvent
from services.portfolio.app.services.trade_executor import TradeExecutor
from services.portfolio.app.events.publisher import event_publisher

logger = setup_logging("event_subscriber")


class EventSubscriber:
    """
    Event subscriber for signal.created events.
    
    Responsibilities:
    1. Subscribe to signal.created channel
    2. Process incoming events (create positions)
    3. Handle errors and save failed events
    4. Publish portfolio.updated events
    """
    
    def __init__(self):
        """Initialize EventSubscriber."""
        self.channel = settings.SIGNAL_CREATED_CHANNEL
        self.running = False
        self.subscriber_thread = None
        self.max_retries = settings.EVENT_SUBSCRIBE_MAX_RETRIES
        self.retry_delay = settings.EVENT_SUBSCRIBE_RETRY_DELAY
        
        logger.info(f"EventSubscriber initialized for channel: {self.channel}")
    
    def start(self):
        """
        Start the event subscriber.
        
        Runs in a background thread to avoid blocking the main application.
        """
        if self.running:
            logger.warning("EventSubscriber is already running")
            return
        
        self.running = True
        self.subscriber_thread = threading.Thread(
            target=self._run_subscriber,
            daemon=True,
            name="EventSubscriber"
        )
        self.subscriber_thread.start()
        
        logger.info(f"EventSubscriber started, listening on channel: {self.channel}")
    
    def stop(self):
        """Stop the event subscriber."""
        if not self.running:
            logger.warning("EventSubscriber is not running")
            return
        
        self.running = False
        
        if self.subscriber_thread:
            self.subscriber_thread.join(timeout=5)
        
        logger.info("EventSubscriber stopped")
    
    def _run_subscriber(self):
        """
        Main subscriber loop.
        
        Continuously listens for messages on the subscribed channel.
        Implements automatic reconnection on errors.
        """
        while self.running:
            try:
                redis_client = get_redis_client()
                pubsub = redis_client.pubsub()
                pubsub.subscribe(self.channel)
                
                logger.info(f"Subscribed to channel: {self.channel}")
                
                for message in pubsub.listen():
                    if not self.running:
                        break
                    
                    if message['type'] == 'message':
                        self._handle_message(message['data'])
                
                pubsub.unsubscribe()
                pubsub.close()
                
            except Exception as e:
                logger.error(f"Error in subscriber loop: {e}")
                if self.running:
                    logger.info(f"Reconnecting in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
    
    def _handle_message(self, message_data):
        """
        Handle incoming message.

        Args:
            message_data: Message data from Redis (str or bytes)
        """
        try:
            # Parse event payload
            # Handle both str (decode_responses=True) and bytes
            if isinstance(message_data, bytes):
                event_payload = json.loads(message_data.decode('utf-8'))
            else:
                event_payload = json.loads(message_data)
            
            signal_id = event_payload.get('signal_id')
            market = event_payload.get('market')
            
            logger.info(
                f"Received signal.created event: "
                f"signal_id={signal_id}, market={market}"
            )
            
            # Process event
            self._process_signal_created(event_payload)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            # Save failed event for retry
            self._save_failed_event(message_data, str(e))
    
    def _process_signal_created(self, event_payload: dict):
        """
        Process signal.created event.
        
        Workflow:
        1. Create position using TradeExecutor
        2. Publish portfolio.updated event
        
        Args:
            event_payload: Signal event payload
        """
        db = SessionLocal()
        try:
            # Create position
            trade_executor = TradeExecutor(db)
            position = trade_executor.open_position(event_payload)
            
            logger.info(
                f"Position created from signal: "
                f"position_id={position.id}, signal_id={event_payload.get('signal_id')}"
            )
            
            # Publish portfolio.updated event
            event_publisher.publish_portfolio_updated(position, action='POSITION_OPENED')
            
        except Exception as e:
            logger.error(f"Error processing signal.created event: {e}")
            raise
        finally:
            db.close()
    
    def _save_failed_event(self, message_data: bytes, error_message: str):
        """
        Save failed event to database for retry.
        
        Args:
            message_data: Raw message data
            error_message: Error message
        """
        db = SessionLocal()
        try:
            event_payload = json.loads(message_data.decode('utf-8'))
            signal_id = event_payload.get('signal_id')
            
            failed_event = FailedSignalEvent(
                signal_id=UUID(signal_id) if signal_id else UUID('00000000-0000-0000-0000-000000000000'),
                event_payload=event_payload,
                error_message=error_message,
                status='PENDING',
                retry_count=0
            )
            
            db.add(failed_event)
            db.commit()
            
            logger.info(
                f"Saved failed event: "
                f"signal_id={signal_id}, error={error_message[:100]}"
            )
            
        except Exception as e:
            logger.error(f"Error saving failed event: {e}")
            db.rollback()
        finally:
            db.close()


# Global event subscriber instance
event_subscriber = EventSubscriber()

