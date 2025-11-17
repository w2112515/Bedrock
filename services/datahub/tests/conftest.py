"""
Pytest Fixtures for DataHub Service Tests

Provides reusable test fixtures for mocking dependencies.

IMPORTANT: Mock Configuration Best Practices
--------------------------------------------
1. All external API calls (Binance, Bitquery) are automatically mocked in unit tests
2. Network access is blocked by pytest-socket plugin for unit tests
3. Integration tests must be explicitly marked with @pytest.mark.integration
4. Always use fixtures from this file to ensure consistent mocking

Network Isolation:
- Unit tests (@pytest.mark.unit): Network access BLOCKED
- Integration tests (@pytest.mark.integration): Network access ALLOWED
- Use --allow-hosts flag to whitelist specific hosts if needed
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from shared.models.base import Base
from services.datahub.app.main import app
from services.datahub.app.models.kline import KLine
from services.datahub.app.models.onchain import OnChainMetrics
from services.datahub.app.adapters.binance_adapter import BinanceAdapter
from services.datahub.app.adapters.bitquery_adapter import BitqueryAdapter


# ============================================================================
# Pytest Configuration Hooks
# ============================================================================

def pytest_runtest_setup(item):
    """
    Hook to enforce network isolation for unit tests.

    This ensures that unit tests cannot accidentally make real API calls.
    """
    # Check if test is marked as unit test
    if "unit" in [mark.name for mark in item.iter_markers()]:
        # Enable socket blocking for unit tests
        if hasattr(item.config, "_socket_allow_hosts"):
            # Block all network access for unit tests
            item.config._socket_allow_hosts = []


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mock_db():
    """
    Create a mock database session.
    
    Returns:
        Mock database session
    """
    db = Mock(spec=Session)
    db.query = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.rollback = MagicMock()
    db.refresh = MagicMock()
    db.close = MagicMock()
    return db


@pytest.fixture(scope="function")
def in_memory_db():
    """
    Create an in-memory SQLite database for integration tests.
    
    Returns:
        SQLAlchemy session
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(engine)


# ============================================================================
# Redis Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mock_redis():
    """
    Create a mock Redis client.
    
    Returns:
        Mock Redis client
    """
    redis_client = Mock()
    redis_client.get = MagicMock(return_value=None)
    redis_client.set = MagicMock(return_value=True)
    redis_client.delete = MagicMock(return_value=1)
    redis_client.publish = MagicMock(return_value=1)
    return redis_client


# ============================================================================
# Adapter Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mock_binance_adapter():
    """
    Create a mock Binance adapter.
    
    Returns:
        Mock Binance adapter
    """
    adapter = Mock(spec=BinanceAdapter)
    adapter.get_klines = MagicMock()
    adapter.test_connection = MagicMock(return_value=True)
    return adapter


@pytest.fixture(scope="function")
def mock_httpx_client():
    """
    Create a mock httpx.Client to prevent real network calls.

    This fixture automatically mocks httpx.Client for all tests.
    Tests can override the return value by patching the mock.

    Returns:
        Mock httpx.Client
    """
    with patch('httpx.Client') as mock_client_class:
        # Create mock client instance using MagicMock to support context manager
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        mock_client.post.return_value = mock_response
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None

        # Make Client() return our mock
        mock_client_class.return_value = mock_client

        yield mock_client


@pytest.fixture(scope="function")
def mock_bitquery_adapter():
    """
    Create a mock Bitquery adapter.

    Returns:
        Mock Bitquery adapter
    """
    adapter = Mock(spec=BitqueryAdapter)
    adapter.get_large_transfers = MagicMock()
    adapter.get_smart_money_activity = MagicMock()
    adapter.get_exchange_netflow = MagicMock()
    adapter.get_active_addresses = MagicMock()
    adapter.get_dex_trades = MagicMock()
    adapter.get_token_transfers = MagicMock()
    adapter.test_connection = MagicMock(return_value=True)
    return adapter


# ============================================================================
# Model Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def sample_kline():
    """
    Create a sample K-line model instance.

    Returns:
        KLine model instance
    """
    return KLine(
        id=1,
        symbol="BTCUSDT",
        interval="1h",
        open_time=1699531200000,  # FIXED: Use Unix timestamp in milliseconds
        close_time=1699534799999,
        open_price=35000.00,
        high_price=35500.00,
        low_price=34800.00,
        close_price=35200.00,
        volume=1000.50,
        quote_volume=35100000.00,
        trade_count=5000,  # FIXED: Changed from 'trades' to 'trade_count'
        taker_buy_base_volume=500.25,  # FIXED: Changed from 'taker_buy_volume' to 'taker_buy_base_volume'
        taker_buy_quote_volume=17550000.00,
        source="binance"  # FIXED: Added required source field
    )


@pytest.fixture(scope="function")
def sample_kline_data():
    """
    Create sample K-line data (dict format from Binance API).
    
    Returns:
        List of K-line data dictionaries
    """
    return [
        {
            "open_time": 1699488000000,
            "open": "35000.00",
            "high": "35500.00",
            "low": "34800.00",
            "close": "35200.00",
            "volume": "1000.50",
            "close_time": 1699491599999,
            "quote_volume": "35100000.00",
            "trades": 5000,
            "taker_buy_volume": "500.25",
            "taker_buy_quote_volume": "17550000.00"
        },
        {
            "open_time": 1699491600000,
            "open": "35200.00",
            "high": "35800.00",
            "low": "35100.00",
            "close": "35600.00",
            "volume": "1200.75",
            "close_time": 1699495199999,
            "quote_volume": "42600000.00",
            "trades": 6000,
            "taker_buy_volume": "600.50",
            "taker_buy_quote_volume": "21300000.00"
        }
    ]


@pytest.fixture(scope="function")
def sample_onchain_metrics():
    """
    Create a sample on-chain metrics model instance.

    Returns:
        OnChainMetrics model instance
    """
    return OnChainMetrics(
        id=1,
        symbol="BTC",
        network="eth",
        contract_address="0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",
        timestamp=1699531200,  # FIXED: Use Unix timestamp in seconds (not datetime)
        transaction_count=1500,
        transaction_volume=15000.50,  # FIXED: Changed from 'total_transfer_volume'
        transaction_volume_usd=750000.00,  # FIXED: Added USD value
        active_addresses=600,  # FIXED: Removed 'unique_addresses', kept 'active_addresses'
        new_addresses=200,  # FIXED: Added new_addresses field
        dex_volume_usd=5000000.00,  # FIXED: Added DEX metrics
        dex_trade_count=250,
        price_usd=50000.00,  # FIXED: Added price field
        source="bitquery"  # FIXED: Added source field (required)
    )


@pytest.fixture(scope="function")
def sample_large_transfers_data():
    """
    Create sample large transfers data (dict format from Bitquery API).
    
    Returns:
        List of large transfer data dictionaries
    """
    return [
        {
            "timestamp": 1699531200,  # FIXED: Use Unix timestamp in seconds
            "from_address": "0xabc123...",
            "to_address": "0xdef456...",
            "amount": 150.5,
            "transaction_hash": "0x123abc...",
            "block_number": 18500000
        },
        {
            "timestamp": 1699532100,  # FIXED: Use Unix timestamp in seconds
            "from_address": "0xghi789...",
            "to_address": "0xjkl012...",
            "amount": 200.75,
            "transaction_hash": "0x456def...",
            "block_number": 18500050
        }
    ]


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mock_app(mock_db, mock_redis):
    """
    Create FastAPI app with mocked dependencies.

    This fixture overrides the app's dependencies to use mocked
    database and Redis clients, preventing real network connections
    during testing.

    Args:
        mock_db: Mocked database session
        mock_redis: Mocked Redis client

    Yields:
        FastAPI app instance with overridden dependencies
    """
    from services.datahub.app.main import app
    from shared.utils.database import get_db
    from shared.utils.redis_client import get_redis_client

    # Store original dependency overrides
    original_overrides = app.dependency_overrides.copy()

    # Override dependencies with mocks
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    yield app

    # Restore original dependency overrides
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)


@pytest.fixture(scope="function")
def test_client(mock_app):
    """
    Create a FastAPI test client with mocked dependencies.

    This fixture creates a TestClient using the mock_app fixture,
    which has all external dependencies (database, Redis) mocked.

    Args:
        mock_app: FastAPI app with mocked dependencies

    Returns:
        TestClient instance
    """
    return TestClient(mock_app)


@pytest.fixture(scope="function")
def mock_get_db(mock_db):
    """
    Mock the get_db dependency.
    
    Args:
        mock_db: Mock database session
    
    Returns:
        Mock get_db function
    """
    def _mock_get_db():
        yield mock_db
    
    return _mock_get_db


# ============================================================================
# Environment Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mock_env_vars():
    """
    Mock environment variables.
    
    Returns:
        Dictionary of environment variables
    """
    return {
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",
        "REDIS_URL": "redis://localhost:6379/0",
        "BINANCE_API_KEY": "test_binance_key",
        "BINANCE_API_SECRET": "test_binance_secret",
        "BITQUERY_API_KEY": "test_bitquery_key",
        "BITQUERY_API_URL": "https://streaming.bitquery.io/graphql",
        "LOG_LEVEL": "DEBUG"
    }


@pytest.fixture(autouse=True)
def reset_circuit_breakers():
    """
    Reset circuit breakers before each test.
    
    This ensures tests don't interfere with each other.
    """
    from services.datahub.app.utils import reset_all_circuit_breakers
    reset_all_circuit_breakers()
    yield
    reset_all_circuit_breakers()

