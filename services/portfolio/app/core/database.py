"""
Database configuration for Portfolio Service.

Uses shared database utilities from shared/utils/database.py.
Configures SQLAlchemy engine with connection pooling.
"""

import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from shared.utils.database import Base
from services.portfolio.app.core.config import settings

# ============================================
# Database Engine Configuration
# ============================================

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,              # Number of connections to keep in pool
    max_overflow=20,           # Maximum number of connections to create beyond pool_size
    pool_pre_ping=True,        # Verify connections before using them
    pool_recycle=3600,         # Recycle connections after 1 hour
    echo=False                 # Set to True for SQL query logging
)

# ============================================
# Session Factory
# ============================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# ============================================
# Database Dependency
# ============================================

def get_db():
    """
    Database session dependency for FastAPI.
    
    Yields a database session and ensures it's closed after use.
    
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

