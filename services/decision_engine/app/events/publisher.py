"""
Event Publisher

Publishes SignalCreated events to Redis Pub/Sub.
Implements retry mechanism and failure handling.
"""

import sys
import os
import json
import asyncio
from typing import Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from shared.utils.redis_client import get_redis_client
from services.decision_engine.app.core.config import settings
from services.decision_engine.app.models.signal import Signal

logger = setup_logging("event_publisher")


class EventPublisher:
    """
    Event publisher for SignalCreated events.
    
    Responsibilities:
    1. Publish SignalCreated events to Redis Pub/Sub
    2. Implement retry mechanism with exponential backoff
    3. Handle failures gracefully (log and continue)
    
    Event format follows project specification (4.2.1):
    {
        "event_type": "signal.created",
        "schema_version": "2.0",
        "timestamp": "2024-11-08T14:30:00Z",
        "signal_id": "...",
        "market": "BTC/USDT",
        ...
    }
    """
    
    def __init__(self):
        self.channel = "signal.created"
        self.max_retries = settings.EVENT_PUBLISH_MAX_RETRIES
        self.retry_delay = settings.EVENT_PUBLISH_RETRY_DELAY
        
    async def publish_signal_created(
        self,
        signal: Signal
    ) -> bool:
        """
        Publish SignalCreated event to Redis (Phase 2 - Task 2.3.7).

        Phase 2 Behavior:
        - APPROVED signals: Published to 'signal.created' channel
        - REJECTED signals: Published to 'signal.rejected' channel

        Args:
            signal: Signal object to publish

        Returns:
            True if published successfully, False otherwise
        """
        try:
            # 1. Build event payload
            event_payload = self._build_event_payload(signal)
            event_json = json.dumps(event_payload)

            # 2. Determine channel based on final_decision
            if signal.final_decision == "APPROVED":
                channel = self.channel
                event_type = "signal.created"
            elif signal.final_decision == "REJECTED":
                channel = "signal.rejected"
                event_type = "signal.rejected"
            else:
                # Fallback for signals without final_decision (backward compatibility)
                channel = self.channel
                event_type = "signal.created"
                logger.warning(
                    f"Signal {signal.id} has no final_decision, "
                    f"publishing to default channel"
                )

            # Update event_type in payload
            event_payload["event_type"] = event_type
            event_json = json.dumps(event_payload)

            # 3. Publish with retry
            success = await self._publish_with_retry(event_json, channel=channel)

            if success:
                logger.info(
                    f"Published {event_type} event for signal {signal.id} "
                    f"({signal.market}) to channel '{channel}'"
                )
            else:
                logger.error(
                    f"Failed to publish {event_type} event for signal {signal.id} "
                    f"after {self.max_retries} retries"
                )

            return success

        except Exception as e:
            logger.error(f"Error publishing event for signal {signal.id}: {e}")
            return False
    
    def _build_event_payload(self, signal: Signal) -> dict:
        """
        Build event payload according to specification.

        Schema version 2.1 includes Phase 2 fields:
        - final_decision
        - explanation
        - rejection_reason
        """
        payload = {
            "event_type": "signal.created",
            "schema_version": "2.1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "signal_id": str(signal.id),
            "market": signal.market,
            "signal_type": signal.signal_type,
            "entry_price": float(signal.entry_price),
            "stop_loss_price": float(signal.stop_loss_price),
            "profit_target_price": float(signal.profit_target_price),
            "risk_unit_r": float(signal.risk_unit_r),
            # Phase 1 new fields
            "suggested_position_weight": float(signal.suggested_position_weight),
            "reward_risk_ratio": float(signal.reward_risk_ratio) if signal.reward_risk_ratio else None,
            "onchain_signals": signal.onchain_signals,
            # Scoring
            "rule_engine_score": signal.rule_engine_score,
            "ml_confidence_score": signal.ml_confidence_score,
            "llm_sentiment": signal.llm_sentiment,
            # Decision (Phase 2)
            "final_decision": signal.final_decision,
            "explanation": signal.explanation,
            "rejection_reason": signal.rejection_reason
        }

        return payload
    
    async def _publish_with_retry(
        self,
        event_json: str,
        channel: Optional[str] = None
    ) -> bool:
        """
        Publish event with retry mechanism.

        Retry strategy:
        - Max retries: 3 (configurable)
        - Exponential backoff: 1s, 2s, 4s
        - If all retries fail, log error and return False

        Args:
            event_json: JSON string to publish
            channel: Optional channel override (defaults to self.channel)
        """
        redis_client = get_redis_client()
        target_channel = channel or self.channel

        for attempt in range(self.max_retries):
            try:
                # Publish to Redis channel
                redis_client.publish(target_channel, event_json)
                
                logger.debug(f"Event published successfully on attempt {attempt + 1}")
                return True
                
            except Exception as e:
                logger.warning(
                    f"Failed to publish event (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    logger.debug(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed
                    logger.error(f"All {self.max_retries} publish attempts failed")
                    return False
        
        return False
    
    async def publish_batch(self, signals: list) -> dict:
        """
        Publish multiple signals in batch.
        
        Args:
            signals: List of Signal objects
            
        Returns:
            {
                "total": 10,
                "success": 8,
                "failed": 2
            }
        """
        results = {
            "total": len(signals),
            "success": 0,
            "failed": 0
        }
        
        for signal in signals:
            success = await self.publish_signal_created(signal)
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
        
        logger.info(
            f"Batch publish completed: {results['success']}/{results['total']} successful"
        )
        
        return results


# Global instance
event_publisher = EventPublisher()

