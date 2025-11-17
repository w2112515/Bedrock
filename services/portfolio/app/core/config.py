"""
Configuration settings for Portfolio Service.

Loads configuration from environment variables using Pydantic Settings.
"""

import sys
import os
from decimal import Decimal
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ============================================
    # Service Configuration
    # ============================================
    SERVICE_NAME: str = "portfolio"
    SERVICE_PORT: int = Field(default=8003, env="PORTFOLIO_PORT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # ============================================
    # Database Configuration
    # ============================================
    DATABASE_URL: str = Field(
        default="postgresql://bedrock:bedrock_password@localhost:5432/bedrock_db",
        env="DATABASE_URL"
    )
    
    # ============================================
    # Redis Configuration
    # ============================================
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_PASSWORD: str = Field(default="", env="REDIS_PASSWORD")
    
    @property
    def REDIS_URL(self) -> str:
        """Construct Redis URL from components."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # ============================================
    # Account Configuration
    # ============================================
    DEFAULT_ACCOUNT_ID: str = Field(
        default="00000000-0000-0000-0000-000000000001",
        env="DEFAULT_ACCOUNT_ID"
    )
    INITIAL_BALANCE: Decimal = Field(default=Decimal("100000.00"), env="INITIAL_BALANCE")
    
    # ============================================
    # Position Sizing Configuration
    # ============================================
    DEFAULT_RISK_PER_TRADE: Decimal = Field(
        default=Decimal("0.02"),
        env="DEFAULT_RISK_PER_TRADE",
        description="Default risk per trade as percentage of account balance (e.g., 0.02 = 2%)"
    )
    MAX_POSITION_WEIGHT: Decimal = Field(
        default=Decimal("1.0"),
        env="MAX_POSITION_WEIGHT",
        description="Maximum position weight allowed (e.g., 1.0 = 100% of account)"
    )
    
    # ============================================
    # Trading Costs
    # ============================================
    COMMISSION_RATE: Decimal = Field(
        default=Decimal("0.001"),
        env="COMMISSION_RATE",
        description="Commission rate (e.g., 0.001 = 0.1%)"
    )
    SLIPPAGE_RATE: Decimal = Field(
        default=Decimal("0.0005"),
        env="SLIPPAGE_RATE",
        description="Slippage rate (e.g., 0.0005 = 0.05%)"
    )
    
    # ============================================
    # Event Configuration
    # ============================================
    EVENT_PUBLISH_MAX_RETRIES: int = Field(default=3, env="EVENT_PUBLISH_MAX_RETRIES")
    EVENT_PUBLISH_RETRY_DELAY: float = Field(default=1.0, env="EVENT_PUBLISH_RETRY_DELAY")
    EVENT_SUBSCRIBE_MAX_RETRIES: int = Field(default=3, env="EVENT_SUBSCRIBE_MAX_RETRIES")
    EVENT_SUBSCRIBE_RETRY_DELAY: float = Field(default=5.0, env="EVENT_SUBSCRIBE_RETRY_DELAY")
    
    # Event channels
    SIGNAL_CREATED_CHANNEL: str = Field(default="signal.created", env="SIGNAL_CREATED_CHANNEL")
    PORTFOLIO_UPDATED_CHANNEL: str = Field(default="portfolio.updated", env="PORTFOLIO_UPDATED_CHANNEL")
    POSITION_CLOSED_CHANNEL: str = Field(default="position.closed", env="POSITION_CLOSED_CHANNEL")
    
    # ============================================
    # Auto Close Position Configuration
    # ============================================
    ENABLE_AUTO_CLOSE: bool = Field(
        default=False,
        env="ENABLE_AUTO_CLOSE",
        description="Enable automatic position closing when price hits stop loss or profit target (MVP: disabled)"
    )
    AUTO_CLOSE_CHECK_INTERVAL_SECONDS: int = Field(
        default=60,
        env="AUTO_CLOSE_CHECK_INTERVAL_SECONDS",
        description="Interval for checking positions for auto-close (seconds)"
    )
    
    # ============================================
    # DataHub Service Configuration (for price updates)
    # ============================================
    DATAHUB_BASE_URL: str = Field(
        default="http://localhost:8001",
        env="DATAHUB_BASE_URL"
    )
    DATAHUB_TIMEOUT: int = Field(default=30, env="DATAHUB_TIMEOUT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
settings = Settings()

