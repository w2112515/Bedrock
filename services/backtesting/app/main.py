"""
Backtesting Service - FastAPI Application

Provides backtesting functionality for trading strategies.
"""

import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from shared.utils.logger import setup_logging
from services.backtesting.app.core.config import settings
from services.backtesting.app.core.database import engine
from services.backtesting.app.api import api_router

logger = setup_logging("backtesting_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Backtesting Service...")
    logger.info(f"Service version: {settings.SERVICE_VERSION}")
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    logger.info(f"Celery Broker: {settings.CELERY_BROKER_URL}")
    logger.info(f"DataHub URL: {settings.DATAHUB_URL}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Backtesting Service...")
    engine.dispose()


# Create FastAPI application
app = FastAPI(
    title="Backtesting Service",
    description="Backtesting service for trading strategies",
    version=settings.SERVICE_VERSION,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "backtesting",
        "version": settings.SERVICE_VERSION,
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "services.backtesting.app.main:app",
        host="0.0.0.0",
        port=settings.BACKTESTING_PORT,
        reload=True
    )

