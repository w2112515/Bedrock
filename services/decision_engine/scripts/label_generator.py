"""
Label Generator - Generate training labels based on future price movements.

This module implements an asymmetric three-class labeling strategy optimized
for cryptocurrency bull market conditions (2024-2025).

Labeling Strategy:
- Bullish (label=1): Future 24h max high >= current close + 2.0%
- Bearish (label=0): Future 24h min low <= current close - 1.5%
- Neutral (discard): Price movement within [-1.5%, +2.0%] range

Design Principles:
- Asymmetric thresholds: Reflect bull market bias
- Noise reduction: Discard neutral samples to improve model precision
- Class balance: Ensure bullish/bearish ratio between 0.4-0.6
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from typing import List, Dict, Optional, Tuple
import structlog

logger = structlog.get_logger()


class LabelGenerator:
    """
    Asymmetric three-class label generator.
    
    Generates training labels based on future price movements with
    asymmetric thresholds optimized for bull market conditions.
    
    Example:
        generator = LabelGenerator(
            future_window_hours=24,
            bullish_threshold_pct=2.0,
            bearish_threshold_pct=-1.5
        )
        
        label = generator.generate_label(
            current_close=50000.0,
            future_klines=[...]
        )
        
        if label is not None:
            # Valid label (bullish=1 or bearish=0)
            pass
        else:
            # Neutral sample (discard)
            pass
    """
    
    def __init__(
        self,
        future_window_hours: int = 24,
        bullish_threshold_pct: float = 1.0,  # EXPERIMENT 1: Lowered to +1.0%
        bearish_threshold_pct: float = -1.0  # EXPERIMENT 1: Lowered to -1.0%
    ):
        """
        Initialize label generator.

        Args:
            future_window_hours: Future prediction window (hours)
            bullish_threshold_pct: Bullish threshold (positive percentage)
            bearish_threshold_pct: Bearish threshold (negative percentage)
        """
        self.future_window_hours = future_window_hours
        self.bullish_threshold_pct = bullish_threshold_pct
        self.bearish_threshold_pct = bearish_threshold_pct

        # Statistics
        self.stats = {
            "total_samples": 0,
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
            "conflict_count": 0,
            "insufficient_data_count": 0
        }
        
        logger.info(
            "label_generator_initialized",
            future_window_hours=future_window_hours,
            bullish_threshold_pct=bullish_threshold_pct,
            bearish_threshold_pct=bearish_threshold_pct
        )
    
    def generate_label(
        self,
        current_close: float,
        future_klines: List[Dict]
    ) -> Optional[int]:
        """
        Generate label based on future price movements with conflict detection.

        Args:
            current_close: Current closing price
            future_klines: List of future K-line dicts (should contain at least
                          future_window_hours K-lines)

        Returns:
            - 1: Bullish (only bullish threshold hit)
            - 0: Bearish (only bearish threshold hit)
            - None: Neutral, conflict, or insufficient data (discard sample)

        Label Logic (FALLBACK: First-Hit Wins Strategy):
            1. Calculate threshold prices
            2. Iterate through future K-lines in chronological order
            3. Return label of whichever threshold is hit first:
               - If bullish threshold hit first → Bullish (1)
               - If bearish threshold hit first → Bearish (0)
               - If neither hit within window → Neutral, discard (None)

            Note: This strategy eliminates conflict samples by using temporal priority
        """
        self.stats["total_samples"] += 1

        # Check if we have enough future data
        if len(future_klines) < self.future_window_hours:
            self.stats["insufficient_data_count"] += 1
            return None

        # Use only the required window
        window = future_klines[:self.future_window_hours]

        # Calculate threshold prices
        bullish_threshold_price = current_close * (1 + self.bullish_threshold_pct / 100)
        bearish_threshold_price = current_close * (1 + self.bearish_threshold_pct / 100)

        # FALLBACK STRATEGY: First-Hit Wins
        # Iterate through K-lines in chronological order and return first hit
        for kline in window:
            # Check bullish threshold first (high price)
            if kline['high'] >= bullish_threshold_price:
                self.stats["bullish_count"] += 1
                return 1  # Bullish hit first

            # Check bearish threshold (low price)
            if kline['low'] <= bearish_threshold_price:
                self.stats["bearish_count"] += 1
                return 0  # Bearish hit first

        # Neither threshold hit within window (neutral sample, discard)
        self.stats["neutral_count"] += 1
        return None
    
    def get_statistics(self) -> Dict:
        """
        Get label generation statistics.

        Returns:
            Dictionary with statistics including:
            - total_samples: Total samples processed
            - bullish_count: Number of bullish labels
            - bearish_count: Number of bearish labels
            - neutral_count: Number of neutral samples (discarded)
            - conflict_count: Number of conflict samples (always 0 in first-hit strategy)
            - insufficient_data_count: Samples with insufficient future data
            - bullish_ratio: Bullish / (Bullish + Bearish)
            - valid_samples: Bullish + Bearish
        """
        valid_samples = self.stats["bullish_count"] + self.stats["bearish_count"]
        bullish_ratio = (
            self.stats["bullish_count"] / valid_samples
            if valid_samples > 0
            else 0.0
        )

        return {
            **self.stats,
            "valid_samples": valid_samples,
            "bullish_ratio": bullish_ratio,
            "discard_ratio": (
                (self.stats["neutral_count"] + self.stats["conflict_count"] + self.stats["insufficient_data_count"])
                / self.stats["total_samples"]
                if self.stats["total_samples"] > 0
                else 0.0
            )
        }
    
    def print_statistics(self):
        """Print label generation statistics."""
        stats = self.get_statistics()

        logger.info("=" * 60)
        logger.info("Label Generation Statistics")
        logger.info("=" * 60)
        logger.info(f"Total samples processed: {stats['total_samples']}")
        logger.info(f"Valid samples (used for training): {stats['valid_samples']}")
        logger.info(f"  - Bullish (label=1): {stats['bullish_count']} ({stats['bullish_ratio']:.1%})")
        logger.info(f"  - Bearish (label=0): {stats['bearish_count']} ({1-stats['bullish_ratio']:.1%})")
        logger.info(f"Discarded samples: {stats['neutral_count'] + stats['conflict_count'] + stats['insufficient_data_count']}")
        logger.info(f"  - Neutral (neither threshold hit): {stats['neutral_count']}")
        logger.info(f"  - Conflict (both thresholds hit): {stats['conflict_count']}")
        logger.info(f"  - Insufficient future data: {stats['insufficient_data_count']}")
        logger.info(f"Discard ratio: {stats['discard_ratio']:.1%}")
        logger.info(f"Conflict ratio: {stats['conflict_count']/stats['total_samples']:.1%}" if stats['total_samples'] > 0 else "Conflict ratio: 0.0%")
        logger.info("=" * 60)


def main():
    """Test label generator."""
    generator = LabelGenerator(
        future_window_hours=24,
        bullish_threshold_pct=2.0,
        bearish_threshold_pct=-1.5
    )
    
    # Test case 1: Bullish (price goes up 3%)
    future_klines_bullish = [
        {'high': 51500, 'low': 50000} for _ in range(24)
    ]
    label = generator.generate_label(50000.0, future_klines_bullish)
    print(f"Test 1 (Bullish): label={label}, expected=1")
    
    # Test case 2: Bearish (price goes down 2%)
    future_klines_bearish = [
        {'high': 50000, 'low': 49000} for _ in range(24)
    ]
    label = generator.generate_label(50000.0, future_klines_bearish)
    print(f"Test 2 (Bearish): label={label}, expected=0")
    
    # Test case 3: Neutral (price moves within [-1.5%, +2.0%])
    future_klines_neutral = [
        {'high': 50500, 'low': 49500} for _ in range(24)
    ]
    label = generator.generate_label(50000.0, future_klines_neutral)
    print(f"Test 3 (Neutral): label={label}, expected=None")
    
    generator.print_statistics()


if __name__ == "__main__":
    main()

