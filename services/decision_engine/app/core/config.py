"""
Configuration management for DecisionEngine Service.
Uses pydantic-settings to load configuration from environment variables.
"""

import os
from typing import List
from enum import Enum
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

from shared.utils.logger import setup_logging

logger = setup_logging("config")


# ============================================================================
# ML模型版本枚举 (ML Model Version Enum)
# 用途：显式定义支持的模型版本，启动时进行严格校验
# ============================================================================

class MLModelVersion(str, Enum):
    """
    ML模型版本枚举

    支持的版本：
    - V1: 13个基础技术指标特征
    - V2_6: 19个多频特征（multifreq-full baseline）
    - V2_7: 30个特征（19个多频 + 11个跨币种特征）
    """
    V1 = "v1"
    V2_6 = "v2_6"
    V2_7 = "v2_7"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ============================================
    # Service Configuration
    # ============================================
    SERVICE_NAME: str = "decision_engine"
    SERVICE_PORT: int = Field(default=8002, env="DECISION_ENGINE_PORT")
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
    # DataHub Service Configuration
    # ============================================
    DATAHUB_BASE_URL: str = Field(
        default="http://localhost:8001",
        env="DATAHUB_BASE_URL"
    )
    DATAHUB_TIMEOUT: int = Field(default=30, env="DATAHUB_TIMEOUT")
    
    # ============================================
    # Scheduler Configuration
    # ============================================
    SIGNAL_GENERATION_INTERVAL_MINUTES: int = Field(
        default=60,
        env="SIGNAL_GENERATION_INTERVAL_MINUTES"
    )
    ENABLE_SCHEDULER: bool = Field(default=True, env="ENABLE_SCHEDULER")
    
    # ============================================
    # Strategy Parameters
    # ============================================
    # Rule Engine
    MIN_RULE_ENGINE_SCORE: float = Field(default=60.0, env="MIN_RULE_ENGINE_SCORE")
    HIGH_CONFIDENCE_THRESHOLD: float = Field(default=85.0, env="HIGH_CONFIDENCE_THRESHOLD")
    MEDIUM_CONFIDENCE_THRESHOLD: float = Field(default=70.0, env="MEDIUM_CONFIDENCE_THRESHOLD")
    
    # Position Weight Ranges
    HIGH_CONFIDENCE_WEIGHT_MIN: float = Field(default=0.8, env="HIGH_CONFIDENCE_WEIGHT_MIN")
    HIGH_CONFIDENCE_WEIGHT_MAX: float = Field(default=1.0, env="HIGH_CONFIDENCE_WEIGHT_MAX")
    MEDIUM_CONFIDENCE_WEIGHT_MIN: float = Field(default=0.5, env="MEDIUM_CONFIDENCE_WEIGHT_MIN")
    MEDIUM_CONFIDENCE_WEIGHT_MAX: float = Field(default=0.7, env="MEDIUM_CONFIDENCE_WEIGHT_MAX")
    LOW_CONFIDENCE_WEIGHT_MIN: float = Field(default=0.3, env="LOW_CONFIDENCE_WEIGHT_MIN")
    LOW_CONFIDENCE_WEIGHT_MAX: float = Field(default=0.5, env="LOW_CONFIDENCE_WEIGHT_MAX")
    
    # Market Filter
    MIN_VOLUME_INCREASE_RATIO: float = Field(default=1.5, env="MIN_VOLUME_INCREASE_RATIO")
    MIN_TREND_SCORE: float = Field(default=60.0, env="MIN_TREND_SCORE")
    
    # OnChain Scoring
    ONCHAIN_LARGE_TRANSFERS_THRESHOLD: int = Field(default=5, env="ONCHAIN_LARGE_TRANSFERS_THRESHOLD")
    ONCHAIN_LARGE_TRANSFERS_SCORE: float = Field(default=10.0, env="ONCHAIN_LARGE_TRANSFERS_SCORE")
    ONCHAIN_NETFLOW_THRESHOLD: float = Field(default=1000.0, env="ONCHAIN_NETFLOW_THRESHOLD")
    ONCHAIN_NETFLOW_SCORE: float = Field(default=15.0, env="ONCHAIN_NETFLOW_SCORE")
    ONCHAIN_SMART_MONEY_THRESHOLD: float = Field(default=0.0, env="ONCHAIN_SMART_MONEY_THRESHOLD")
    ONCHAIN_SMART_MONEY_SCORE: float = Field(default=20.0, env="ONCHAIN_SMART_MONEY_SCORE")
    ONCHAIN_ACTIVE_ADDRESSES_THRESHOLD: float = Field(default=0.2, env="ONCHAIN_ACTIVE_ADDRESSES_THRESHOLD")
    ONCHAIN_ACTIVE_ADDRESSES_SCORE: float = Field(default=5.0, env="ONCHAIN_ACTIVE_ADDRESSES_SCORE")
    
    # Pullback Entry Strategy
    PULLBACK_MA_PERIOD: int = Field(default=20, env="PULLBACK_MA_PERIOD")
    PULLBACK_TOLERANCE: float = Field(default=0.02, env="PULLBACK_TOLERANCE")  # 2%
    ATR_MULTIPLIER_STOP: float = Field(default=2.0, env="ATR_MULTIPLIER_STOP")
    ATR_MULTIPLIER_TARGET: float = Field(default=3.0, env="ATR_MULTIPLIER_TARGET")
    
    # ============================================
    # Trading Symbols
    # ============================================
    TRADING_SYMBOLS: List[str] = Field(
        default=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
        env="TRADING_SYMBOLS"
    )
    
    # ============================================
    # Event Publishing
    # ============================================
    EVENT_PUBLISH_MAX_RETRIES: int = Field(default=3, env="EVENT_PUBLISH_MAX_RETRIES")
    EVENT_PUBLISH_RETRY_DELAY: float = Field(default=1.0, env="EVENT_PUBLISH_RETRY_DELAY")

    # ============================================
    # ML Model Configuration (Phase 2)
    # ============================================
    ML_ENABLED: bool = Field(default=True, env="ML_ENABLED")

    # 模型版本配置（支持v1/v2_6/v2_7多版本切换）
    ML_MODEL_VERSION: str = Field(
        default="v1",
        env="ML_MODEL_VERSION",
        description="ML模型版本 (v1/v2_6/v2_7)"
    )

    # 模型文件路径
    ML_MODEL_PATH: str = Field(
        default="services/decision_engine/models/xgboost_signal_confidence_v1.pkl",
        env="ML_MODEL_PATH",
        description="ML模型文件路径"
    )

    # 特征名称文件路径（支持动态指定）
    ML_FEATURE_NAMES_PATH: str = Field(
        default="services/decision_engine/models/feature_names.json",
        env="ML_FEATURE_NAMES_PATH",
        description="特征名称文件路径"
    )

    ML_FALLBACK_SCORE: float = Field(default=50.0, env="ML_FALLBACK_SCORE")

    @field_validator("ML_MODEL_VERSION")
    @classmethod
    def validate_model_version(cls, v: str) -> str:
        """
        验证ML模型版本是否合法

        为什么需要这个验证：
        - 防止配置错误导致运行时异常
        - 在服务启动时就发现配置问题，而不是在运行时
        - 提供清晰的错误信息，便于快速定位问题

        Args:
            v: 模型版本字符串

        Returns:
            验证通过的模型版本字符串

        Raises:
            ValueError: 如果模型版本非法
        """
        v_lower = v.lower()
        valid_versions = [e.value for e in MLModelVersion]

        if v_lower not in valid_versions:
            raise ValueError(
                f"Invalid ML_MODEL_VERSION: '{v}'. "
                f"Must be one of: {', '.join(valid_versions)}"
            )

        return v_lower

    # ============================================
    # LLM Configuration (Phase 2)
    # ============================================
    LLM_ENABLED: bool = Field(default=True, env="LLM_ENABLED")
    LLM_PROVIDER: str = Field(default="qwen", env="LLM_PROVIDER")  # qwen/deepseek/openai/claude

    # Qwen API Configuration
    QWEN_API_KEY: str = Field(default="", env="QWEN_API_KEY")
    QWEN_API_URL: str = Field(
        default="https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        env="QWEN_API_URL"
    )
    QWEN_MODEL: str = Field(default="qwen-turbo", env="QWEN_MODEL")
    QWEN_TIMEOUT: float = Field(default=30.0, env="QWEN_TIMEOUT")
    QWEN_TEMPERATURE: float = Field(default=0.2, env="QWEN_TEMPERATURE")

    # LLM Cache Configuration
    LLM_CACHE_TTL: int = Field(default=900, env="LLM_CACHE_TTL")  # 15 minutes
    LLM_ENABLE_CACHE: bool = Field(default=True, env="LLM_ENABLE_CACHE")

    # ============================================
    # Arbiter Configuration (Phase 2)
    # ⚠️ ML权重已降低：TD-002实验已冻结，当前权重为临时参数
    # 理由：v2.7模型AUC=0.5939，投入产出比低，优先投入Phase 2-3核心功能
    # 待Phase 3 Level 2完成后，重新评估是否启动ML v3.x项目
    # ============================================
    ARBITER_RULE_WEIGHT: float = Field(
        default=0.55,
        env="ARBITER_RULE_WEIGHT",
        description="Rule engine weight in decision arbiter (increased from 0.4)"
    )
    ARBITER_ML_WEIGHT: float = Field(
        default=0.15,
        env="ARBITER_ML_WEIGHT",
        description="ML model weight in decision arbiter (FROZEN, temporary parameter)"
    )
    ARBITER_LLM_WEIGHT: float = Field(
        default=0.3,
        env="ARBITER_LLM_WEIGHT",
        description="LLM weight in decision arbiter"
    )
    ARBITER_MIN_APPROVAL_SCORE: float = Field(
        default=70.0,
        env="ARBITER_MIN_APPROVAL_SCORE",
        description="Minimum weighted score for APPROVED decision (0-100)"
    )

    # LLM Sentiment to Score Mapping (Phase 2)
    LLM_SENTIMENT_BULLISH_BASE: float = Field(default=90.0, env="LLM_SENTIMENT_BULLISH_BASE")
    LLM_SENTIMENT_NEUTRAL_BASE: float = Field(default=50.0, env="LLM_SENTIMENT_NEUTRAL_BASE")
    LLM_SENTIMENT_BEARISH_BASE: float = Field(default=10.0, env="LLM_SENTIMENT_BEARISH_BASE")
    LLM_SENTIMENT_CONFIDENCE_MULTIPLIER: float = Field(default=0.2, env="LLM_SENTIMENT_CONFIDENCE_MULTIPLIER")

    # ============================================
    # Funding Rate Strategy Configuration (Phase 2)
    # ============================================
    FUNDING_RATE_ENABLED: bool = Field(
        default=False,
        env="FUNDING_RATE_ENABLED",
        description="Enable funding rate strategy (default: disabled)"
    )
    FUNDING_RATE_HIGH_THRESHOLD: float = Field(
        default=0.001,
        env="FUNDING_RATE_HIGH_THRESHOLD",
        description="High funding rate threshold (0.1%, triggers SHORT signal)"
    )
    FUNDING_RATE_LOW_THRESHOLD: float = Field(
        default=-0.001,
        env="FUNDING_RATE_LOW_THRESHOLD",
        description="Low funding rate threshold (-0.1%, triggers LONG signal)"
    )
    FUNDING_RATE_CACHE_TTL: int = Field(
        default=28800,
        env="FUNDING_RATE_CACHE_TTL",
        description="Funding rate cache TTL in seconds (default: 8 hours)"
    )

    def __init__(self, **kwargs):
        """
        初始化配置并记录关键信息

        为什么在这里记录日志：
        - 服务启动时立即显示当前使用的模型版本
        - 便于排查配置问题和版本切换问题
        - 提供清晰的审计日志
        """
        super().__init__(**kwargs)
        logger.info(f"=" * 60)
        logger.info(f"ML Model Configuration:")
        logger.info(f"  - Version: {self.ML_MODEL_VERSION}")
        logger.info(f"  - Model Path: {self.ML_MODEL_PATH}")
        logger.info(f"  - Feature Names Path: {self.ML_FEATURE_NAMES_PATH}")
        logger.info(f"  - Enabled: {self.ML_ENABLED}")
        logger.info(f"=" * 60)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
settings = Settings()

