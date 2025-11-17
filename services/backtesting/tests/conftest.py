"""
Pytest configuration and fixtures for Backtesting Service tests.
"""

import sys
import os
import pytest
import uuid
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4
from sqlalchemy import create_engine, TypeDecorator, CHAR
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from shared.utils.database import Base
from services.backtesting.app.core.database import get_db
from services.backtesting.app.main import app
from services.backtesting.app.models.backtest_run import BacktestRun
from services.backtesting.app.models.backtest_trade import BacktestTrade
from services.backtesting.app.models.backtest_metrics import BacktestMetrics


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


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

# Create test session factory
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database session for each test.

    Creates all tables before the test and drops them after.
    Includes UUID type adapter for SQLite compatibility.
    """
    # Store original column types
    original_types = {}

    # Replace PostgreSQL-specific types with SQLite-compatible types
    # Process ALL tables in Base.metadata (includes tables from other services)
    for table_name, table in Base.metadata.tables.items():
        for column in table.columns:
            if hasattr(column.type, '__class__') and column.type.__class__.__name__ == 'UUID':
                original_types[f"{table_name}.{column.name}"] = column.type
                column.type = GUID()
            elif hasattr(column.type, '__class__') and column.type.__class__.__name__ == 'JSONB':
                original_types[f"{table_name}.{column.name}"] = column.type
                column.type = JSON()

    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    # Create session
    session = TestSessionLocal()

    yield session

    # Cleanup
    session.close()
    Base.metadata.drop_all(bind=test_engine)

    # Restore original types
    for table_name, table in Base.metadata.tables.items():
        for column in table.columns:
            key = f"{table_name}.{column.name}"
            if key in original_types:
                column.type = original_types[key]


@pytest.fixture(scope="function")
def client(db_session):
    """
    Create a test client with database session override.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_backtest_run(db_session):
    """
    Create a sample backtest run for testing.
    """
    backtest_run = BacktestRun(
        id=uuid4(),
        strategy_name="Rules Only",
        market="BTC/USDT",
        interval="1h",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        initial_balance=Decimal("100000.00"),
        final_balance=Decimal("120000.00"),
        status="COMPLETED",
        progress=1.0,
        created_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    
    db_session.add(backtest_run)
    db_session.commit()
    db_session.refresh(backtest_run)
    
    return backtest_run


@pytest.fixture
def sample_backtest_trades(db_session, sample_backtest_run):
    """
    Create sample backtest trades for testing.
    """
    trades = []
    
    # Entry trade
    entry_trade = BacktestTrade(
        id=uuid4(),
        backtest_run_id=sample_backtest_run.id,
        market="BTC/USDT",
        trade_type="ENTRY",
        quantity=Decimal("0.5"),
        price=Decimal("50000.00"),
        timestamp=datetime(2024, 6, 1, 12, 0, 0),
        commission=Decimal("25.00"),
        slippage=Decimal("12.50"),
        realized_pnl=None
    )
    trades.append(entry_trade)
    
    # Exit trade
    exit_trade = BacktestTrade(
        id=uuid4(),
        backtest_run_id=sample_backtest_run.id,
        market="BTC/USDT",
        trade_type="EXIT",
        quantity=Decimal("0.5"),
        price=Decimal("52000.00"),
        timestamp=datetime(2024, 6, 2, 12, 0, 0),
        commission=Decimal("26.00"),
        slippage=Decimal("0.00"),
        realized_pnl=Decimal("937.50")
    )
    trades.append(exit_trade)
    
    for trade in trades:
        db_session.add(trade)
    
    db_session.commit()
    
    for trade in trades:
        db_session.refresh(trade)
    
    return trades


@pytest.fixture
def sample_backtest_metrics(db_session, sample_backtest_run):
    """
    Create sample backtest metrics for testing.
    """
    metrics = BacktestMetrics(
        id=uuid4(),
        backtest_run_id=sample_backtest_run.id,
        total_trades=10,
        winning_trades=6,
        losing_trades=4,
        win_rate=0.6,
        avg_win=Decimal("1500.00"),
        avg_loss=Decimal("-800.00"),
        profit_factor=1.875,
        max_drawdown=0.15,
        sharpe_ratio=1.5,
        calmar_ratio=1.2,
        sortino_ratio=2.0,
        omega_ratio=1.8,
        total_commission=Decimal("500.00"),
        total_slippage=Decimal("250.00"),
        roi=0.20
    )
    
    db_session.add(metrics)
    db_session.commit()
    db_session.refresh(metrics)
    
    return metrics

