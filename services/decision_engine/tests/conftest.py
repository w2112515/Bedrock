"""
Pytest configuration and fixtures for DecisionEngine Service tests.
"""

import sys
import os
import pytest
import uuid
from unittest.mock import Mock, AsyncMock, MagicMock
from sqlalchemy import create_engine, event, TypeDecorator, CHAR
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import UUID

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from services.decision_engine.app.core.database import Base, get_db
from services.decision_engine.app.models.signal import Signal
from services.decision_engine.app.models.arbitration_config import ArbitrationConfig


# ============================================
# SQLite UUID Type Adapter
# ============================================

class GUID(TypeDecorator):
    """
    Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            else:
                return value


# ============================================
# Database Fixtures
# ============================================

@pytest.fixture(scope="function")
def test_db():
    """
    Create an in-memory SQLite database for testing.
    Includes UUID and JSONB type adapters for SQLite compatibility.
    """
    from sqlalchemy import JSON
    from services.decision_engine.app.models.signal import Signal
    from services.decision_engine.app.models.arbitration_config import ArbitrationConfig

    # Store original column types
    original_signal_id_type = Signal.__table__.c.id.type
    original_onchain_signals_type = Signal.__table__.c.onchain_signals.type
    original_arbitration_id_type = ArbitrationConfig.__table__.c.id.type

    # Create in-memory database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    # Replace PostgreSQL-specific types with SQLite-compatible types
    Signal.__table__.c.id.type = GUID()  # UUID → GUID (CHAR(36))
    Signal.__table__.c.onchain_signals.type = JSON()  # JSONB → JSON
    ArbitrationConfig.__table__.c.id.type = GUID()  # UUID → GUID (CHAR(36))

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    # Insert default ArbitrationConfig for tests
    from decimal import Decimal
    default_config = ArbitrationConfig(
        id=uuid.uuid4(),
        version=1,
        rule_weight=Decimal("0.4"),
        ml_weight=Decimal("0.3"),
        llm_weight=Decimal("0.3"),
        min_approval_score=Decimal("70.0"),
        adaptive_threshold_enabled=False,
        is_active=True
    )
    db.add(default_config)
    db.commit()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        # Restore original column types
        Signal.__table__.c.id.type = original_signal_id_type
        Signal.__table__.c.onchain_signals.type = original_onchain_signals_type
        ArbitrationConfig.__table__.c.id.type = original_arbitration_id_type


# ============================================
# Mock Fixtures
# ============================================

@pytest.fixture
def mock_httpx_client():
    """
    Mock httpx.AsyncClient for testing HTTP requests.
    """
    mock_client = AsyncMock()
    
    # Mock K-line data response
    mock_kline_response = Mock()
    mock_kline_response.status_code = 200
    mock_kline_response.json.return_value = {
        "klines": [
            {
                "open_time": "2024-11-08T00:00:00Z",
                "open_price": "64000.00",
                "high_price": "65000.00",
                "low_price": "63500.00",
                "close_price": "64800.00",
                "volume": "1000.50"
            }
            for i in range(100)  # 100 K-lines
        ]
    }
    
    # Mock onchain data response
    mock_onchain_response = Mock()
    mock_onchain_response.status_code = 200
    mock_onchain_response.json.return_value = {
        "large_transfers_count": 8,
        "exchange_netflow": -1500.5,
        "smart_money_flow": 250.3,
        "active_addresses_growth": 0.25
    }
    
    # Configure mock client
    async def mock_get(url, **kwargs):
        if "/klines/" in url:
            return mock_kline_response
        elif "/onchain/" in url:
            return mock_onchain_response
        else:
            mock_response = Mock()
            mock_response.status_code = 404
            return mock_response
    
    mock_client.get = mock_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    return mock_client


@pytest.fixture
def mock_redis():
    """
    Mock Redis client for testing.
    """
    mock_redis_client = Mock()
    mock_redis_client.ping.return_value = True
    mock_redis_client.publish.return_value = 1
    
    return mock_redis_client


@pytest.fixture
def sample_kline_data():
    """
    Sample K-line data for testing.
    """
    return [
        {
            "open_time": f"2024-11-08T{i:02d}:00:00Z",
            "open_price": f"{64000 + i * 10}.00",
            "high_price": f"{65000 + i * 10}.00",
            "low_price": f"{63500 + i * 10}.00",
            "close_price": f"{64800 + i * 10}.00",
            "volume": f"{1000 + i * 5}.50"
        }
        for i in range(100)
    ]


@pytest.fixture
def sample_market_data(sample_kline_data):
    """
    Sample market data from MarketFilter.
    """
    return {
        "symbol": "BTCUSDT",
        "kline_data": sample_kline_data,
        "onchain_data": {
            "large_transfers": 8,
            "exchange_netflow": -1500.5,
            "smart_money_flow": 250.3,
            "active_addresses_growth": 0.25
        },
        "trend_score": 75.0,
        "onchain_score": 20.0,
        "total_score": 95.0
    }


@pytest.fixture
def sample_signal(test_db):
    """
    Create a sample Signal object in the test database.
    """
    signal = Signal(
        market="BTCUSDT",
        signal_type="PULLBACK_BUY",
        entry_price=65000.00,
        stop_loss_price=63500.00,
        profit_target_price=68000.00,
        risk_unit_r=1500.00,
        suggested_position_weight=0.85,
        reward_risk_ratio=2.00,
        onchain_signals={
            "large_transfers": 8,
            "exchange_netflow": -1500.5
        },
        rule_engine_score=87.5
    )
    
    test_db.add(signal)
    test_db.commit()
    test_db.refresh(signal)
    
    return signal


# ============================================
# Pytest Configuration
# ============================================

@pytest.fixture(autouse=True)
def reset_environment():
    """
    Reset environment variables before each test.
    """
    # Store original environment
    original_env = os.environ.copy()
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)

