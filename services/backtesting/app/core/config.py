"""
Backtesting Service Configuration.

Manages all configuration settings using Pydantic Settings.
"""

import os
from decimal import Decimal
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Backtesting Service configuration settings.
    
    All settings can be overridden via environment variables.
    """
    
    # ============================================
    # Service Configuration
    # ============================================
    SERVICE_NAME: str = "backtesting"
    SERVICE_VERSION: str = "1.0.0"
    BACKTESTING_PORT: int = Field(default=8004, env="BACKTESTING_PORT")
    
    # ============================================
    # Database Configuration
    # ============================================
    DATABASE_URL: str = Field(
        default="postgresql://bedrock:bedrock_password@localhost:5432/bedrock_db",
        env="DATABASE_URL"
    )
    DB_POOL_SIZE: int = Field(default=10, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=20, env="DB_MAX_OVERFLOW")
    DB_POOL_PRE_PING: bool = Field(default=True, env="DB_POOL_PRE_PING")
    DB_POOL_RECYCLE: int = Field(default=3600, env="DB_POOL_RECYCLE")
    DB_ECHO: bool = Field(default=False, env="DB_ECHO")
    
    # ============================================
    # Redis Configuration
    # ============================================
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_MAX_CONNECTIONS: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    REDIS_DECODE_RESPONSES: bool = Field(default=True, env="REDIS_DECODE_RESPONSES")
    
    # ============================================
    # Celery Configuration
    # ============================================
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        env="CELERY_BROKER_URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/1",
        env="CELERY_RESULT_BACKEND"
    )
    CELERY_TASK_TIME_LIMIT: int = Field(default=3600, env="CELERY_TASK_TIME_LIMIT")
    
    # ============================================
    # External Services
    # ============================================
    DATAHUB_URL: str = Field(
        default="http://localhost:8001",
        env="DATAHUB_URL"
    )
    DECISION_ENGINE_URL: str = Field(
        default="http://localhost:8002",
        env="DECISION_ENGINE_URL"
    )
    
    # ============================================
    # Backtesting Configuration
    # ============================================
    DEFAULT_COMMISSION_RATE: Decimal = Field(
        default=Decimal("0.001"),
        env="DEFAULT_COMMISSION_RATE",
        description="Default commission rate (0.1%)"
    )
    DEFAULT_SLIPPAGE_RATE: Decimal = Field(
        default=Decimal("0.0005"),
        env="DEFAULT_SLIPPAGE_RATE",
        description="Default slippage rate (0.05%)"
    )
    DEFAULT_INITIAL_BALANCE: Decimal = Field(
        default=Decimal("100000.00"),
        env="DEFAULT_INITIAL_BALANCE",
        description="Default initial balance for backtesting"
    )
    MAX_KLINES_PER_REQUEST: int = Field(
        default=1000,
        env="MAX_KLINES_PER_REQUEST",
        description="Maximum K-lines to fetch per request from DataHub"
    )
    
    # ============================================
    # Monitoring Configuration
    # ============================================
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    METRICS_PORT: int = Field(default=9004, env="METRICS_PORT")
    
    # ============================================
    # Logging Configuration
    # ============================================
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()

