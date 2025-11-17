"""
Generate Test Signals for Frontend Verification

This script generates high-quality test signals that meet the original strategy standards:
- rule_engine_score >= 60.0
- Realistic market data
- Proper risk/reward ratios

Usage:
    docker-compose exec decision_engine python scripts/generate_test_signals.py
"""

import sys
import os
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from sqlalchemy.orm import Session
from services.decision_engine.app.core.database import SessionLocal, engine
from services.decision_engine.app.models.signal import Signal
from services.decision_engine.app.events.publisher import EventPublisher
from shared.utils.logger import setup_logging

logger = setup_logging("test_data_generator")


async def generate_test_signals():
    """
    Generate 3 high-quality test signals for frontend verification.

    All signals meet original strategy standards:
    - rule_engine_score >= 60.0 (original MIN_RULE_ENGINE_SCORE)
    - Realistic entry/stop/target prices
    - Proper risk/reward ratios
    """
    logger.info("Starting test signal generation...")

    db = SessionLocal()
    publisher = EventPublisher()
    
    try:
        # Test signals with high quality scores (符合原始策略标准)
        test_signals = [
            {
                "market": "BTCUSDT",
                "signal_type": "PULLBACK_BUY",
                "entry_price": Decimal("102447.47"),
                "stop_loss_price": Decimal("96827.68"),
                "profit_target_price": Decimal("108067.26"),
                "risk_unit_r": Decimal("5619.79"),
                "suggested_position_weight": Decimal("0.7500"),  # Medium-high confidence
                "reward_risk_ratio": Decimal("1.00"),
                "rule_engine_score": 75.0,  # 符合原始标准 (>= 60.0)
                "onchain_signals": None,
                "ml_confidence_score": None,
                "llm_sentiment": None,
                "final_decision": None,
                "explanation": None
            },
            {
                "market": "ETHUSDT",
                "signal_type": "PULLBACK_BUY",
                "entry_price": Decimal("3366.78"),
                "stop_loss_price": Decimal("3187.89"),
                "profit_target_price": Decimal("3724.56"),
                "risk_unit_r": Decimal("178.89"),
                "suggested_position_weight": Decimal("0.8500"),  # High confidence
                "reward_risk_ratio": Decimal("2.00"),
                "rule_engine_score": 87.5,  # 高置信度 (>= 85.0)
                "onchain_signals": None,
                "ml_confidence_score": None,
                "llm_sentiment": None,
                "final_decision": None,
                "explanation": None
            },
            {
                "market": "BNBUSDT",
                "signal_type": "PULLBACK_BUY",
                "entry_price": Decimal("968.75"),
                "stop_loss_price": Decimal("917.03"),
                "profit_target_price": Decimal("1072.19"),
                "risk_unit_r": Decimal("51.72"),
                "suggested_position_weight": Decimal("0.6500"),  # Medium confidence
                "reward_risk_ratio": Decimal("2.00"),
                "rule_engine_score": 72.0,  # 中置信度 (70-85)
                "onchain_signals": None,
                "ml_confidence_score": None,
                "llm_sentiment": None,
                "final_decision": None,
                "explanation": None
            }
        ]
        
        created_signals = []
        
        for signal_data in test_signals:
            # Create signal in database
            signal = Signal(**signal_data)
            db.add(signal)
            db.commit()
            db.refresh(signal)
            
            created_signals.append(signal)
            
            logger.info(
                f"✅ Created test signal: {signal.market} "
                f"(ID: {signal.id}, Score: {signal.rule_engine_score}, "
                f"Weight: {signal.suggested_position_weight})"
            )
            
            # Publish signal.created event to Redis
            try:
                await publisher.publish_signal_created(signal)
                logger.info(f"✅ Published signal.created event for {signal.market}")
            except Exception as e:
                logger.error(f"❌ Failed to publish event for {signal.market}: {e}")
        
        logger.info(f"\n🎉 Successfully generated {len(created_signals)} test signals!")
        logger.info("\nNext steps:")
        logger.info("1. Check signals API: curl http://localhost:8002/v1/signals")
        logger.info("2. Check Portfolio Service logs for position creation")
        logger.info("3. Check positions API: curl http://localhost:8003/v1/positions")
        logger.info("4. Refresh browser at http://localhost:3000 to verify frontend")
        
        return created_signals
        
    except Exception as e:
        logger.error(f"❌ Error generating test signals: {e}")
        db.rollback()
        raise
    finally:
        db.close()


async def cleanup_test_signals():
    """
    Clean up test signals (optional).
    Use this to remove test data after verification.
    """
    logger.info("Cleaning up test signals...")
    
    db = SessionLocal()
    
    try:
        # Delete all signals (use with caution!)
        deleted_count = db.query(Signal).delete()
        db.commit()
        
        logger.info(f"✅ Deleted {deleted_count} signals")
        
    except Exception as e:
        logger.error(f"❌ Error cleaning up signals: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate test signals for frontend verification")
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up all test signals (use with caution!)"
    )
    
    args = parser.parse_args()
    
    if args.cleanup:
        asyncio.run(cleanup_test_signals())
    else:
        asyncio.run(generate_test_signals())

