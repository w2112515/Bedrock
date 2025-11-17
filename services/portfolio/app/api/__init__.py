"""
API routes for Portfolio Service.
"""

from fastapi import APIRouter
from services.portfolio.app.api import positions, trades, account, stats, health

api_router = APIRouter()

# Include all route modules
api_router.include_router(positions.router, prefix="/v1/positions", tags=["positions"])
api_router.include_router(trades.router, prefix="/v1/trades", tags=["trades"])
api_router.include_router(account.router, prefix="/v1/account", tags=["account"])
api_router.include_router(stats.router, prefix="/v1/stats", tags=["stats"])
api_router.include_router(health.router, tags=["health"])

__all__ = ['api_router']

