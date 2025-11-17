"""
Health check endpoints

Provides health and readiness checks for the service.
"""

import sys
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from shared.utils.redis_client import get_redis_client
from services.decision_engine.app.core.database import engine
from services.decision_engine.app.core.config import settings

logger = setup_logging("health_api")

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str


class ReadinessResponse(BaseModel):
    """Readiness check response."""
    status: str
    checks: dict


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Basic health check.
    
    Returns 200 if service is running.
    """
    return HealthResponse(
        status="healthy",
        service="DecisionEngine",
        version="1.0.0"
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check():
    """
    Readiness check.
    
    Checks:
    1. PostgreSQL database connection
    2. Redis connection
    3. DataHub Service availability
    
    Returns 200 if all checks pass, 503 otherwise.
    """
    checks = {
        "database": "unknown",
        "redis": "unknown",
        "datahub": "unknown"
    }
    
    all_healthy = True

    # 1. Check PostgreSQL
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "healthy"
        logger.debug("Database check: healthy")
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)}"
        all_healthy = False
        logger.error(f"Database check failed: {e}")
    
    # 2. Check Redis
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        checks["redis"] = "healthy"
        logger.debug("Redis check: healthy")
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"
        all_healthy = False
        logger.error(f"Redis check failed: {e}")
    
    # 3. Check DataHub Service
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.get(f"{settings.DATAHUB_BASE_URL}/health")
            if response.status_code == 200:
                checks["datahub"] = "healthy"
                logger.debug("DataHub check: healthy")
            else:
                checks["datahub"] = f"unhealthy: status {response.status_code}"
                all_healthy = False
    except Exception as e:
        checks["datahub"] = f"unhealthy: {str(e)}"
        all_healthy = False
        logger.error(f"DataHub check failed: {e}")
    
    # Return response
    if all_healthy:
        return ReadinessResponse(
            status="ready",
            checks=checks
        )
    else:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "checks": checks
            }
        )

