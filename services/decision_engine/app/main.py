"""
DecisionEngine Service - Main Application

FastAPI application for trading signal generation.
"""

import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from shared.utils.logger import setup_logging
from services.decision_engine.app.core.config import settings
from services.decision_engine.app.core.database import engine, Base
from services.decision_engine.app.core.scheduler import signal_scheduler
from services.decision_engine.app.api import v1_router
from services.decision_engine.app.api.health import router as health_router
from services.decision_engine.app.api.metrics import router as metrics_router, record_api_request
from services.decision_engine.app.api.arbitration import router as arbitration_router

logger = setup_logging("decision_engine")


# ============================================
# Lifespan Context Manager
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting DecisionEngine Service...")
    
    try:
        # Create database tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
        
        # Start scheduler
        signal_scheduler.start()
        logger.info("Signal scheduler started")
        
        logger.info("DecisionEngine Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start DecisionEngine Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down DecisionEngine Service...")
    
    try:
        # Stop scheduler
        signal_scheduler.stop()
        logger.info("Signal scheduler stopped")
        
        logger.info("DecisionEngine Service shut down successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# ============================================
# FastAPI Application
# ============================================

app = FastAPI(
    title="DecisionEngine Service",
    description="Trading signal generation service with rule-based decision engine",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================
# Middleware
# ============================================

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging and metrics middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all requests and record metrics.
    """
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    # Process request
    try:
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"status={response.status_code} duration={duration:.3f}s"
        )
        
        # Record metrics
        record_api_request(
            endpoint=request.url.path,
            method=request.method,
            status=response.status_code
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Request failed: {request.method} {request.url.path} error={e}")
        
        # Record error metric
        record_api_request(
            endpoint=request.url.path,
            method=request.method,
            status=500
        )
        
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


# ============================================
# Routes
# ============================================

@app.get("/")
async def root():
    """
    Root endpoint with service information.
    """
    return {
        "service": "DecisionEngine",
        "version": "1.0.0",
        "description": "Trading signal generation service",
        "endpoints": {
            "signals": "/v1/signals",
            "health": "/health",
            "ready": "/ready",
            "metrics": "/metrics"
        }
    }


# Include routers
app.include_router(v1_router)
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(arbitration_router)

# Debug: Log all registered routes
logger.info("=== All Registered Routes ===")
for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        logger.info(f"  {route.path} - {route.methods}")
logger.info("==============================")



# ============================================
# Error Handlers
# ============================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# ============================================
# Entry Point
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "services.decision_engine.app.main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG,
        log_level="info"
    )

