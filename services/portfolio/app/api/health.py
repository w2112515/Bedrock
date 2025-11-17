"""
Health check API endpoints.
"""

import sys
import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from shared.utils.redis_client import get_redis_client
from services.portfolio.app.core.database import get_db
from services.portfolio.app.core.config import settings

logger = setup_logging("api.health")

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
    - status: Service status
    - service: Service name
    """
    return {
        "status": "healthy",
        "service": "portfolio"
    }


@router.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check endpoint.
    
    Checks:
    - Database connection
    - Redis connection
    
    Returns:
    - status: Service readiness status
    - checks: Individual check results
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
    
    # Overall status
    all_ready = all(checks.values())
    
    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks
    }


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns basic service metrics.
    """
    # TODO: Implement Prometheus metrics collection
    return {
        "service": "portfolio",
        "version": "1.0.0"
    }

