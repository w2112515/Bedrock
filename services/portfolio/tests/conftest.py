"""
Pytest configuration and fixtures for Portfolio Service tests.
"""

import sys
import os
import pytest
import uuid
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import create_engine, TypeDecorator, CHAR, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import UUID
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from shared.utils.database import Base
from services.portfolio.app.core.database import get_db
from services.portfolio.app.main import app
from services.portfolio.app.models.account import Account
from services.portfolio.app.models.position import Position
from services.portfolio.app.models.trade import Trade
from services.portfolio.app.models.failed_signal_event import FailedSignalEvent


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
    Includes UUID and JSONB type adapters for SQLite compatibility.
    """
    # Store original column types
    original_types = {}

    # Replace PostgreSQL-specific types with SQLite-compatible types
    for table_name, table in Base.metadata.tables.items():
        if table_name in ['account', 'positions', 'trades', 'failed_signal_events']:
            for column in table.columns:
                if hasattr(column.type, '__class__') and column.type.__class__.__name__ == 'UUID':
                    original_types[f"{table_name}.{column.name}"] = column.type
                    column.type = GUID()
                elif hasattr(column.type, '__class__') and column.type.__class__.__name__ == 'JSONB':
                    original_types[f"{table_name}.{column.name}"] = column.type
                    column.type = JSON()

    # Create tables
    Base.metadata.create_all(bind=test_engine)

    # Create session
    session = TestSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop tables
        Base.metadata.drop_all(bind=test_engine)

        # Restore original column types
        for key, original_type in original_types.items():
            table_name, column_name = key.split('.')
            Base.metadata.tables[table_name].columns[column_name].type = original_type


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
def sample_account(db_session):
    """
    Create a sample account for testing.
    """
    account = Account(
        id=uuid4(),
        balance=Decimal("100000.00"),
        available_balance=Decimal("100000.00"),
        frozen_balance=Decimal("0.00")
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    
    return account


@pytest.fixture
def sample_position(db_session, sample_account):
    """
    Create a sample position for testing.
    """
    position = Position(
        market="BTC/USDT",
        signal_id=uuid4(),
        position_size=Decimal("0.5"),
        entry_price=Decimal("50000.00"),
        current_price=Decimal("50000.00"),
        stop_loss_price=Decimal("49000.00"),
        profit_target_price=Decimal("52000.00"),
        position_weight_used=Decimal("0.25"),
        status="OPEN",
        unrealized_pnl=Decimal("0.00")
    )
    db_session.add(position)
    db_session.commit()
    db_session.refresh(position)
    
    return position


@pytest.fixture
def sample_trade(db_session, sample_position):
    """
    Create a sample trade for testing.
    """
    trade = Trade(
        position_id=sample_position.id,
        trade_type="ENTRY",
        market="BTC/USDT",
        quantity=Decimal("0.5"),
        price=Decimal("50000.00"),
        commission=Decimal("25.00")
    )
    db_session.add(trade)
    db_session.commit()
    db_session.refresh(trade)
    
    return trade


@pytest.fixture
def sample_signal_data():
    """
    Create sample signal data for testing.
    """
    return {
        "signal_id": str(uuid4()),
        "market": "BTC/USDT",
        "entry_price": "50000.00",
        "stop_loss_price": "49000.00",
        "profit_target_price": "52000.00",
        "risk_unit_r": "1000.00",
        "suggested_position_weight": "0.25"
    }

