"""
LLM Adapter Interface

Defines the abstract interface for LLM adapters.
Supports multiple LLM implementations (Qwen, DeepSeek, GPT-4, Claude).

Phase 2 - Task 2.2.1: Define LLMInterface abstract interface
"""

from abc import ABC, abstractmethod
from typing import Optional, TypedDict


class SentimentResult(TypedDict):
    """
    LLM sentiment analysis result.
    
    Attributes:
        sentiment: Market sentiment (BULLISH/BEARISH/NEUTRAL)
        confidence: Confidence score (0-100)
        explanation: Brief explanation of the analysis
    """
    sentiment: str          # BULLISH/BEARISH/NEUTRAL
    confidence: float       # 0-100
    explanation: str        # Analysis explanation


class LLMInterface(ABC):
    """
    Abstract interface for LLM adapters.
    
    This interface defines the standard contract for sentiment analysis
    using various LLM providers (Qwen, DeepSeek, GPT-4, Claude).
    
    Design Principles:
    - Interface Segregation Principle (ISP): Only defines necessary methods
    - Open/Closed Principle (OCP): Easy to extend with new LLM providers
    - Dependency Inversion Principle (DIP): High-level modules depend on this abstraction
    
    Usage:
        class QwenAdapter(LLMInterface):
            async def analyze_sentiment(self, **kwargs) -> Optional[SentimentResult]:
                # Implementation
                pass
    """
    
    @abstractmethod
    async def analyze_sentiment(
        self,
        market: str,
        current_price: float,
        price_change_24h: float,
        volume_24h: float,
        technical_indicators: dict,
        signal_type: str,
        entry_price: float,
        stop_loss_price: float,
        profit_target_price: float,
        rule_engine_score: float,
        ml_confidence_score: Optional[float]
    ) -> Optional[SentimentResult]:
        """
        Analyze market sentiment using LLM.
        
        This method takes market data, technical indicators, and signal details
        as input, and returns a sentiment analysis result.
        
        Args:
            market: Trading pair (e.g., BTCUSDT)
            current_price: Current market price
            price_change_24h: 24-hour price change percentage
            volume_24h: 24-hour trading volume
            technical_indicators: Technical indicators dict (RSI, MACD, MA, etc.)
            signal_type: Signal type (e.g., PULLBACK_BUY)
            entry_price: Entry price
            stop_loss_price: Stop loss price
            profit_target_price: Profit target price
            rule_engine_score: Rule engine score (0-100)
            ml_confidence_score: ML confidence score (0-100, optional)
            
        Returns:
            SentimentResult or None if analysis fails
            
        Example:
            result = await adapter.analyze_sentiment(
                market="BTCUSDT",
                current_price=50000.0,
                price_change_24h=5.2,
                volume_24h=1000000.0,
                technical_indicators={"rsi_14": 45.0, "macd": 120.5, ...},
                signal_type="PULLBACK_BUY",
                entry_price=49500.0,
                stop_loss_price=48000.0,
                profit_target_price=52000.0,
                rule_engine_score=85.0,
                ml_confidence_score=90.0
            )
            
            if result:
                print(f"Sentiment: {result['sentiment']}")
                print(f"Confidence: {result['confidence']}")
                print(f"Explanation: {result['explanation']}")
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if LLM service is available.
        
        Returns:
            True if the LLM service is properly configured and available,
            False otherwise
            
        Example:
            if adapter.is_available():
                result = await adapter.analyze_sentiment(...)
            else:
                logger.warning("LLM service not available")
        """
        pass

