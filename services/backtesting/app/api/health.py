"""
Health check endpoints.
"""

import sys
import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.backtesting.app.core.database import get_db
from services.backtesting.app.core.redis import get_redis_client

logger = setup_logging("health_api")

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "backtesting"
    }


@router.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check endpoint.
    
    Checks database and Redis connectivity.
    
    Returns:
        Readiness status with dependency checks
    """
    checks = {
        "database": False,
        "redis": False
    }
    
    # Check database
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        logger.error(f"Database check failed: {e}")
    
    # Check Redis
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        checks["redis"] = True
    except Exception as e:
        logger.error(f"Redis check failed: {e}")
    
    all_ready = all(checks.values())
    
    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks
    }

