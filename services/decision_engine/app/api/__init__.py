"""
API endpoints for DecisionEngine Service
"""

from fastapi import APIRouter

# Create main v1 router
v1_router = APIRouter(prefix="/v1")

# Import and include sub-routers
from .signals import router as signals_router
from .health import router as health_router
from .metrics import router as metrics_router

v1_router.include_router(signals_router, prefix="/signals", tags=["Signals"])

__all__ = ["v1_router", "health_router", "metrics_router"]

