"""
Market Data Generator - Generate synthetic K-line data for ML training.

This module generates realistic synthetic market data with different
trend patterns (bullish, bearish, sideways) for training ML models.

Design Philosophy:
- Reproducible: Fixed seed for consistent results
- Realistic: Simulates actual market dynamics
- Labeled: Each sample has a clear trend label
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Any
import structlog

logger = structlog.get_logger()


class MarketDataGenerator:
    """
    Synthetic market data generator for ML training.
    
    Generates K-line sequences with labeled trend patterns:
    - Bullish: Upward trending market
    - Bearish: Downward trending market
    - Sideways: Range-bound market
    
    Example:
        generator = MarketDataGenerator(seed=42)
        samples = generator.generate_klines(num_samples=1000)
        
        for klines, label in samples:
            # klines: List of 100 K-line dicts
            # label: 0 (bearish/sideways) or 1 (bullish)
            pass
    """
    
    def __init__(self, seed: int = 42, base_price: float = 50000.0):
        """
        Initialize data generator.
        
        Args:
            seed: Random seed for reproducibility
            base_price: Base price for BTC (default: 50000 USDT)
        """
        random.seed(seed)
        self.base_price = base_price
        logger.info(
            "data_generator_initialized",
            seed=seed,
            base_price=base_price
        )
    
    def generate_klines(
        self,
        num_samples: int = 1000,
        lookback_periods: int = 100
    ) -> List[Tuple[List[Dict[str, Any]], int]]:
        """
        Generate synthetic K-line samples with labels.
        
        Args:
            num_samples: Number of samples to generate
            lookback_periods: Number of K-lines per sample
        
        Returns:
            List of (klines, label) tuples where:
            - klines: List of K-line dictionaries
            - label: 0 (bearish/sideways) or 1 (bullish)
        """
        samples = []
        
        logger.info(
            "generating_samples",
            num_samples=num_samples,
            lookback_periods=lookback_periods
        )
        
        for i in range(num_samples):
            # Randomly select trend type
            trend_type = random.choice(['bullish', 'bearish', 'sideways'])
            
            # Generate K-line sequence
            klines = self._generate_trend_klines(lookback_periods, trend_type)
            
            # Generate label (binary classification)
            # 1 = bullish (buy signal)
            # 0 = bearish or sideways (no buy signal)
            label = 1 if trend_type == 'bullish' else 0
            
            samples.append((klines, label))
            
            if (i + 1) % 100 == 0:
                logger.debug(f"Generated {i + 1}/{num_samples} samples")
        
        logger.info(
            "sample_generation_complete",
            total_samples=len(samples),
            bullish_count=sum(1 for _, label in samples if label == 1),
            bearish_sideways_count=sum(1 for _, label in samples if label == 0)
        )
        
        return samples
    
    def _generate_trend_klines(
        self,
        periods: int,
        trend_type: str
    ) -> List[Dict[str, Any]]:
        """
        Generate K-line sequence with specific trend pattern.
        
        Args:
            periods: Number of K-lines to generate
            trend_type: 'bullish', 'bearish', or 'sideways'
        
        Returns:
            List of K-line dictionaries with OHLCV data
        """
        klines = []
        
        # Start from base price with some randomness
        current_price = self.base_price * random.uniform(0.9, 1.1)
        
        # Set trend parameters
        if trend_type == 'bullish':
            drift = 0.002  # +0.2% per period on average
            volatility = 0.01  # 1% volatility
        elif trend_type == 'bearish':
            drift = -0.002  # -0.2% per period on average
            volatility = 0.01  # 1% volatility
        else:  # sideways
            drift = 0.0  # No trend
            volatility = 0.005  # Lower volatility
        
        # Generate K-lines
        for i in range(periods):
            # Calculate price change
            change = drift + random.gauss(0, volatility)
            current_price *= (1 + change)
            
            # Ensure price stays positive
            current_price = max(current_price, 1.0)
            
            # Generate OHLC
            open_price = current_price
            
            # High and low with intraday volatility
            intraday_volatility = abs(random.gauss(0, 0.005))
            high_price = open_price * (1 + intraday_volatility)
            low_price = open_price * (1 - intraday_volatility)
            
            # Close price between high and low
            close_price = random.uniform(low_price, high_price)
            
            # Volume with some randomness
            base_volume = 5000
            volume = base_volume * random.uniform(0.5, 2.0)
            
            # Create K-line dictionary
            kline = {
                'open': float(open_price),
                'high': float(high_price),
                'low': float(low_price),
                'close': float(close_price),
                'volume': float(volume),
                'timestamp': datetime.utcnow() - timedelta(hours=periods - i)
            }
            
            klines.append(kline)
            
            # Update current price for next iteration
            current_price = close_price
        
        return klines


def main():
    """Test data generator."""
    generator = MarketDataGenerator(seed=42)
    samples = generator.generate_klines(num_samples=10, lookback_periods=100)
    
    print(f"Generated {len(samples)} samples")
    print(f"First sample: {len(samples[0][0])} K-lines, label={samples[0][1]}")
    print(f"First K-line: {samples[0][0][0]}")


if __name__ == "__main__":
    main()

