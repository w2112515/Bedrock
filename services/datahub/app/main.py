"""
DataHub Service - Main Application Entry Point
"""

import os
import sys
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from shared.utils.logger import setup_logging
from shared.utils.database import engine, Base
from services.datahub.app.api import health, klines, onchain
from services.datahub.app.middleware import RequestLoggingMiddleware, PrometheusMetricsMiddleware, get_metrics
from services.datahub.app.exceptions import (
    DataHubException,
    ExternalAPIException,
    ValidationException,
    RateLimitException,
    CircuitBreakerOpenException
)
from services.datahub.app.error_handlers import (
    datahub_exception_handler,
    external_api_exception_handler,
    validation_exception_handler,
    rate_limit_exception_handler,
    circuit_breaker_exception_handler,
    http_exception_handler,
    generic_exception_handler
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Setup logging
logger = setup_logging("datahub", log_level=os.getenv("LOG_LEVEL", "INFO"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting DataHub Service...")
    
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down DataHub Service...")


# Create FastAPI application
app = FastAPI(
    title="DataHub Service",
    description="Market data collection and management service",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Add Prometheus metrics middleware
app.add_middleware(PrometheusMetricsMiddleware)

# Register exception handlers
app.add_exception_handler(DataHubException, datahub_exception_handler)
app.add_exception_handler(ExternalAPIException, external_api_exception_handler)
app.add_exception_handler(ValidationException, validation_exception_handler)
app.add_exception_handler(RateLimitException, rate_limit_exception_handler)
app.add_exception_handler(CircuitBreakerOpenException, circuit_breaker_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(klines.router, prefix="/v1/klines", tags=["K-Lines"])
app.include_router(onchain.router, prefix="/v1/onchain", tags=["On-Chain Data"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "DataHub",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "klines": "/v1/klines",
            "onchain": "/v1/onchain",
            "metrics": "/metrics",
            "docs": "/docs"
        }
    }


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Exposes application metrics in Prometheus format for monitoring.
    """
    return get_metrics()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("DATAHUB_PORT", 8001))
    uvicorn.run(
        "services.datahub.app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
    )

