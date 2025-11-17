"""
Portfolio Service - Main application entry point.

Responsibilities:
1. Initialize FastAPI application
2. Configure middleware (CORS, logging)
3. Register API routes
4. Manage application lifecycle (startup/shutdown)
5. Start EventSubscriber
"""

import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from shared.utils.logger import setup_logging
from services.portfolio.app.core.config import settings
from services.portfolio.app.core.database import SessionLocal
from services.portfolio.app.api import api_router
from services.portfolio.app.events.subscriber import event_subscriber
from services.portfolio.app.services.account_service import AccountService

logger = setup_logging("portfolio_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Portfolio Service starting up...")
    
    # Initialize default account
    try:
        db = SessionLocal()
        account_service = AccountService(db)
        account = account_service.get_account()
        logger.info(
            f"Account initialized: id={account.id}, "
            f"balance={account.balance}"
        )
        db.close()
    except Exception as e:
        logger.error(f"Failed to initialize account: {e}")
    
    # Start event subscriber
    try:
        event_subscriber.start()
        logger.info("EventSubscriber started")
    except Exception as e:
        logger.error(f"Failed to start EventSubscriber: {e}")
    
    logger.info("Portfolio Service startup complete")
    
    yield
    
    # Shutdown
    logger.info("Portfolio Service shutting down...")
    
    # Stop event subscriber
    try:
        event_subscriber.stop()
        logger.info("EventSubscriber stopped")
    except Exception as e:
        logger.error(f"Failed to stop EventSubscriber: {e}")
    
    logger.info("Portfolio Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Portfolio Service",
    description="Portfolio management service for cryptocurrency trading platform",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure allowed origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(api_router)

logger.info(
    f"Portfolio Service initialized on port {settings.SERVICE_PORT}"
)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "services.portfolio.app.main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=True
    )

