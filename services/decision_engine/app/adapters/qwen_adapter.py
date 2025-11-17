"""
Qwen Adapter

Implements LLMInterface for Qwen API (Alibaba Cloud DashScope).

Features:
1. Async HTTP calls to Qwen API
2. Redis caching (TTL=15 minutes)
3. Retry mechanism (3 attempts, exponential backoff)
4. Timeout handling (30 seconds)
5. Graceful degradation (returns NEUTRAL on failure)
6. Statistics tracking (cache hit rate, failure rate)

Phase 2 - Task 2.2.5: Implement QwenAdapter
Phase 2 - Task 2.2.6: Implement retry mechanism
Phase 2 - Task 2.2.7: Implement response caching
Phase 2 - Task 2.2.8: Implement failure degradation
"""

import httpx
import hashlib
from typing import Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from services.decision_engine.app.adapters.llm_interface import (
    LLMInterface, 
    SentimentResult
)
from services.decision_engine.app.utils.sentiment_parser import SentimentParser
from shared.utils.redis_client import cache_get, cache_set
from shared.utils.logger import setup_logging

logger = setup_logging("qwen_adapter")


class QwenAdapter(LLMInterface):
    """
    Qwen API adapter implementation.
    
    This adapter integrates Alibaba Cloud's Qwen LLM for sentiment analysis.
    
    Design Principles:
    - Single Responsibility Principle (SRP): Only responsible for Qwen API integration
    - Dependency Inversion Principle (DIP): Depends on LLMInterface abstraction
    - Robustness: Comprehensive error handling and degradation
    
    Usage:
        adapter = QwenAdapter(
            api_key="your_api_key",
            api_url="https://dashscope.aliyuncs.com/...",
            model="qwen-turbo",
            timeout=30.0,
            cache_ttl=900,
            temperature=0.2
        )
        
        result = await adapter.analyze_sentiment(
            market="BTCUSDT",
            current_price=50000.0,
            ...
        )
    """
    
    def __init__(
        self,
        api_key: str,
        api_url: str,
        model: str = "qwen-turbo",
        timeout: float = 30.0,
        cache_ttl: int = 900,  # 15 minutes
        temperature: float = 0.2,  # Low temperature for consistency
        enable_cache: bool = True
    ):
        """
        Initialize QwenAdapter.
        
        Args:
            api_key: Qwen API key
            api_url: Qwen API endpoint URL
            model: Model name (qwen-turbo/qwen-plus/qwen-max)
            timeout: Request timeout in seconds
            cache_ttl: Cache TTL in seconds
            temperature: Temperature parameter (0.0-1.0, lower = more deterministic)
            enable_cache: Whether to enable Redis caching
        """
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self.temperature = temperature
        self.enable_cache = enable_cache
        self.parser = SentimentParser()
        
        # Load prompt template
        self.prompt_template = self._load_prompt_template()
        
        # Statistics
        self.stats = {
            "total_calls": 0,
            "cache_hits": 0,
            "api_calls": 0,
            "failures": 0,
            "timeouts": 0
        }
        
        logger.info(
            f"QwenAdapter initialized: model={model}, "
            f"timeout={timeout}s, cache_ttl={cache_ttl}s, "
            f"temperature={temperature}"
        )
    
    def _load_prompt_template(self) -> str:
        """Load prompt template from file."""
        try:
            template_path = "services/decision_engine/app/prompts/signal_analysis.txt"
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load prompt template: {e}")
            # Return inline fallback template
            return self._get_fallback_prompt_template()
    
    def _get_fallback_prompt_template(self) -> str:
        """Fallback prompt template (inline)."""
        return """你是一个专业的加密货币市场分析师。请根据以下市场数据和技术指标，分析市场情绪。

市场数据:
- 交易对: {market}
- 当前价格: {current_price}
- 24h涨跌幅: {price_change_24h}%
- 24h成交量: {volume_24h}

技术指标:
- RSI(14): {rsi}
- MACD: {macd}
- MA(20): {ma_20}
- MA(50): {ma_50}

信号详情:
- 信号类型: {signal_type}
- 入场价: {entry_price}
- 止损价: {stop_loss_price}
- 目标价: {profit_target_price}
- 规则引擎评分: {rule_engine_score}
- ML置信度: {ml_confidence_score}

请以JSON格式输出你的分析结果（不要包含任何其他文字）:
{{
  "sentiment": "BULLISH/BEARISH/NEUTRAL",
  "confidence": 0-100,
  "explanation": "简要说明你的分析理由（50字以内）"
}}"""
    
    def _build_cache_key(self, **kwargs) -> str:
        """
        Build cache key.
        
        Uses market and key parameters to generate a hash.
        """
        market = kwargs.get("market", "")
        # Use key parameters to generate hash
        key_data = f"{market}:{kwargs.get('current_price')}:{kwargs.get('signal_type')}"
        signal_hash = hashlib.md5(key_data.encode()).hexdigest()[:8]
        return f"llm:sentiment:{market}:{signal_hash}"
    
    def _build_prompt(self, **kwargs) -> str:
        """Build prompt from template."""
        return self.prompt_template.format(
            market=kwargs.get("market", ""),
            current_price=kwargs.get("current_price", 0),
            price_change_24h=kwargs.get("price_change_24h", 0),
            volume_24h=kwargs.get("volume_24h", 0),
            rsi=kwargs.get("technical_indicators", {}).get("rsi_14", "N/A"),
            macd=kwargs.get("technical_indicators", {}).get("macd", "N/A"),
            ma_20=kwargs.get("technical_indicators", {}).get("ma_20", "N/A"),
            ma_50=kwargs.get("technical_indicators", {}).get("ma_50", "N/A"),
            signal_type=kwargs.get("signal_type", ""),
            entry_price=kwargs.get("entry_price", 0),
            stop_loss_price=kwargs.get("stop_loss_price", 0),
            profit_target_price=kwargs.get("profit_target_price", 0),
            rule_engine_score=kwargs.get("rule_engine_score", 0),
            ml_confidence_score=kwargs.get("ml_confidence_score", "N/A")
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError))
    )
    async def _call_qwen_api(self, prompt: str) -> dict:
        """
        Call Qwen API with retry mechanism.
        
        Retries 3 times with exponential backoff on timeout/network errors.
        
        Raises:
            httpx.TimeoutException: Request timeout
            httpx.HTTPStatusError: HTTP error (4xx, 5xx)
            Exception: Other errors
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            "parameters": {
                "temperature": self.temperature,
                "result_format": "message"
            }
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.api_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    async def analyze_sentiment(self, **kwargs) -> Optional[SentimentResult]:
        """
        Analyze market sentiment (implements LLMInterface).
        
        Workflow:
        1. Check cache
        2. Build prompt
        3. Call Qwen API (with retry)
        4. Parse response
        5. Cache result
        6. Degrade to NEUTRAL on failure
        
        Returns:
            SentimentResult or None if all attempts fail
        """
        self.stats["total_calls"] += 1
        
        try:
            # 1. Check cache
            if self.enable_cache:
                cache_key = self._build_cache_key(**kwargs)
                cached_result = cache_get(cache_key)
                if cached_result:
                    self.stats["cache_hits"] += 1
                    logger.info(f"Cache hit for {kwargs.get('market')}")
                    return cached_result
            
            # 2. Build prompt
            prompt = self._build_prompt(**kwargs)
            
            # 3. Call API
            logger.info(f"Calling Qwen API for {kwargs.get('market')}")
            self.stats["api_calls"] += 1
            api_response = await self._call_qwen_api(prompt)
            
            # 4. Parse response
            result = self.parser.parse(api_response)
            
            # 5. Cache result
            if self.enable_cache and result:
                cache_set(cache_key, result, expire=self.cache_ttl)
                logger.info(f"Cached result for {kwargs.get('market')}")
            
            return result
            
        except httpx.TimeoutException as e:
            self.stats["timeouts"] += 1
            self.stats["failures"] += 1
            logger.warning(
                f"Qwen API timeout for {kwargs.get('market')}: {e}"
            )
            return self._get_neutral_fallback("API超时")
            
        except httpx.HTTPStatusError as e:
            self.stats["failures"] += 1
            if e.response.status_code == 429:
                logger.error(f"Qwen API quota exceeded: {e}")
                return self._get_neutral_fallback("API配额耗尽")
            else:
                logger.error(f"Qwen API HTTP error: {e}")
                return self._get_neutral_fallback(f"HTTP错误{e.response.status_code}")
                
        except Exception as e:
            self.stats["failures"] += 1
            logger.error(f"Unexpected error in analyze_sentiment: {e}")
            return self._get_neutral_fallback("未知错误")
    
    def _get_neutral_fallback(self, reason: str) -> SentimentResult:
        """
        Degrade to NEUTRAL sentiment.
        
        Args:
            reason: Failure reason
            
        Returns:
            NEUTRAL sentiment result
        """
        return {
            "sentiment": "NEUTRAL",
            "confidence": 50.0,
            "explanation": f"LLM API调用失败（{reason}），降级为中性情绪"
        }
    
    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return bool(self.api_key and self.api_url)
    
    def get_stats(self) -> dict:
        """Get statistics."""
        return {
            **self.stats,
            "cache_hit_rate": (
                self.stats["cache_hits"] / self.stats["total_calls"] * 100
                if self.stats["total_calls"] > 0 else 0
            ),
            "failure_rate": (
                self.stats["failures"] / self.stats["total_calls"] * 100
                if self.stats["total_calls"] > 0 else 0
            )
        }

