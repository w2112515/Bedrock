"""
Create test signal with ML and LLM data for UI verification.
"""

import sys
import os
from decimal import Decimal
from datetime import datetime
import uuid

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from services.decision_engine.app.models.signal import Signal

# Database connection
DATABASE_URL = "postgresql://bedrock_user:bedrock_password@localhost:5432/bedrock_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def create_test_signal():
    """Create a test signal with ML and LLM data."""
    db = SessionLocal()
    
    try:
        # Create test signal
        signal = Signal(
            id=uuid.uuid4(),
            market="BTCUSDT",
            signal_type="PULLBACK_BUY",
            entry_price=Decimal("95000.00"),
            stop_loss_price=Decimal("94000.00"),
            profit_target_price=Decimal("97000.00"),
            risk_unit_r=Decimal("1000.00"),
            suggested_position_weight=Decimal("0.65"),
            reward_risk_ratio=Decimal("2.0"),
            onchain_signals=None,
            rule_engine_score=75.5,
            ml_confidence_score=0.87,  # 87% confidence
            llm_sentiment="BULLISH",
            final_decision="APPROVED",
            explanation="✅ APPROVED: Strong consensus. Rule=75.5, ML=87.0, LLM=BULLISH → Final=78.2",
            created_at=datetime.utcnow()
        )
        
        db.add(signal)
        db.commit()
        db.refresh(signal)
        
        print(f"✅ Test signal created successfully!")
        print(f"   ID: {signal.id}")
        print(f"   Market: {signal.market}")
        print(f"   ML Confidence: {signal.ml_confidence_score}")
        print(f"   LLM Sentiment: {signal.llm_sentiment}")
        print(f"   Final Decision: {signal.final_decision}")
        
        return signal
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating test signal: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_test_signal()

