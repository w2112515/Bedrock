"""
API routers for Backtesting Service.
"""

from fastapi import APIRouter
from services.backtesting.app.api import backtests, health, metrics

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(backtests.router, prefix="/v1/backtests", tags=["Backtests"])
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(metrics.router, tags=["Metrics"])

__all__ = ["api_router"]

