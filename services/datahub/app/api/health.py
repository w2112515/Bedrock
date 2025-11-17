"""
Health Check API Endpoints
"""

import os
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.utils.database import get_db
from shared.utils.redis_client import get_redis_client
from shared.models.schemas import HealthCheckResponse

# Load environment variables
load_dotenv()

router = APIRouter()


@router.get("/", response_model=HealthCheckResponse)
async def health_check(db: Session = Depends(get_db)) -> HealthCheckResponse:
    """
    Health check endpoint.
    
    Checks:
    - Service is running
    - Database connection
    - Redis connection
    """
    dependencies: Dict[str, Any] = {}
    
    # Check database
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        dependencies["database"] = "healthy"
    except Exception as e:
        dependencies["database"] = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        dependencies["redis"] = "healthy"
    except Exception as e:
        dependencies["redis"] = f"unhealthy: {str(e)}"
    
    # Check external APIs (basic check)
    binance_api_key = os.getenv("BINANCE_API_KEY")
    bitquery_api_key = os.getenv("BITQUERY_API_KEY")
    
    dependencies["binance_api"] = "configured" if binance_api_key else "not configured"
    dependencies["bitquery_api"] = "configured" if bitquery_api_key else "not configured"
    
    # Determine overall status
    status = "healthy"
    if dependencies["database"] != "healthy" or dependencies["redis"] != "healthy":
        status = "degraded"
    
    return HealthCheckResponse(
        status=status,
        service="DataHub",
        version="0.1.0",
        timestamp=datetime.utcnow(),
        dependencies=dependencies,
    )


@router.get("/ready")
async def readiness_check(db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Readiness check endpoint for Kubernetes.
    """
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not ready", "error": str(e)}


@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check endpoint for Kubernetes.
    """
    return {"status": "alive"}

