"""
LLM Adapter Factory

Factory class for creating LLM adapter instances based on configuration.
Supports multiple LLM providers (Qwen, DeepSeek, OpenAI, Claude).

Design Pattern: Factory Pattern
Design Principle: Open/Closed Principle (OCP) - Easy to add new providers

Phase 2 - Architecture Enhancement: LLM provider selection
"""

from typing import Optional

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from services.decision_engine.app.adapters.llm_interface import LLMInterface
from services.decision_engine.app.adapters.qwen_adapter import QwenAdapter
from services.decision_engine.app.core.config import settings
from shared.utils.logger import setup_logging

logger = setup_logging("llm_factory")


class LLMAdapterFactory:
    """
    LLM adapter factory class.
    
    Dynamically creates LLM adapter instances based on LLM_PROVIDER configuration.
    
    Supported Providers:
    - qwen: Alibaba Cloud Qwen (通义千问)
    - deepseek: DeepSeek (未来扩展)
    - openai: OpenAI GPT-4 (未来扩展)
    - claude: Anthropic Claude (未来扩展)
    
    Usage:
        # In scheduler.py or signals.py
        from services.decision_engine.app.adapters.llm_factory import LLMAdapterFactory
        
        llm_adapter = LLMAdapterFactory.create_adapter()
        rule_engine = RuleEngine(ml_adapter=ml_adapter, llm_adapter=llm_adapter)
    
    Future Extension Example:
        # To add DeepSeek support:
        # 1. Implement DeepSeekAdapter(LLMInterface)
        # 2. Add elif branch in create_adapter():
        #    elif provider == "deepseek":
        #        return DeepSeekAdapter(...)
        # 3. Set LLM_PROVIDER=deepseek in .env
    """
    
    @staticmethod
    def create_adapter() -> Optional[LLMInterface]:
        """
        Create LLM adapter based on LLM_PROVIDER configuration.
        
        Returns:
            LLMInterface instance or None if LLM is disabled
            
        Example:
            adapter = LLMAdapterFactory.create_adapter()
            if adapter:
                result = await adapter.analyze_sentiment(...)
        """
        # Check if LLM is enabled
        if not settings.LLM_ENABLED:
            logger.info("LLM is disabled in configuration")
            return None
        
        provider = settings.LLM_PROVIDER.lower()
        logger.info(f"Creating LLM adapter for provider: {provider}")
        
        # Qwen (Alibaba Cloud)
        if provider == "qwen":
            return LLMAdapterFactory._create_qwen_adapter()
        
        # Future extension points:
        # elif provider == "deepseek":
        #     return LLMAdapterFactory._create_deepseek_adapter()
        # 
        # elif provider == "openai":
        #     return LLMAdapterFactory._create_openai_adapter()
        # 
        # elif provider == "claude":
        #     return LLMAdapterFactory._create_claude_adapter()
        
        else:
            logger.error(f"Unknown LLM provider: {provider}")
            return None
    
    @staticmethod
    def _create_qwen_adapter() -> Optional[QwenAdapter]:
        """
        Create Qwen adapter instance.
        
        Returns:
            QwenAdapter or None if API key is not configured
        """
        if not settings.QWEN_API_KEY:
            logger.warning("QWEN_API_KEY not configured, LLM disabled")
            return None
        
        try:
            adapter = QwenAdapter(
                api_key=settings.QWEN_API_KEY,
                api_url=settings.QWEN_API_URL,
                model=settings.QWEN_MODEL,
                timeout=settings.QWEN_TIMEOUT,
                temperature=settings.QWEN_TEMPERATURE,
                cache_ttl=settings.LLM_CACHE_TTL,
                enable_cache=settings.LLM_ENABLE_CACHE
            )
            logger.info("QwenAdapter created successfully")
            return adapter
        except Exception as e:
            logger.error(f"Failed to create QwenAdapter: {e}")
            return None
    
    # Future extension methods:
    # 
    # @staticmethod
    # def _create_deepseek_adapter() -> Optional[DeepSeekAdapter]:
    #     """Create DeepSeek adapter instance."""
    #     if not settings.DEEPSEEK_API_KEY:
    #         logger.warning("DEEPSEEK_API_KEY not configured")
    #         return None
    #     
    #     return DeepSeekAdapter(
    #         api_key=settings.DEEPSEEK_API_KEY,
    #         api_url=settings.DEEPSEEK_API_URL,
    #         ...
    #     )
    # 
    # @staticmethod
    # def _create_openai_adapter() -> Optional[OpenAIAdapter]:
    #     """Create OpenAI adapter instance."""
    #     if not settings.OPENAI_API_KEY:
    #         logger.warning("OPENAI_API_KEY not configured")
    #         return None
    #     
    #     return OpenAIAdapter(
    #         api_key=settings.OPENAI_API_KEY,
    #         model=settings.OPENAI_MODEL,
    #         ...
    #     )
    # 
    # @staticmethod
    # def _create_claude_adapter() -> Optional[ClaudeAdapter]:
    #     """Create Claude adapter instance."""
    #     if not settings.CLAUDE_API_KEY:
    #         logger.warning("CLAUDE_API_KEY not configured")
    #         return None
    #     
    #     return ClaudeAdapter(
    #         api_key=settings.CLAUDE_API_KEY,
    #         model=settings.CLAUDE_MODEL,
    #         ...
    #     )

