"""
Pullback Entry Strategy

Detects pullback buy signals when price retraces to support level (MA20).
Calculates entry price, stop loss, profit target, and suggested position weight.
"""

import sys
import os
from typing import Dict, Any, Optional
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.decision_engine.app.core.config import settings

logger = setup_logging("pullback_entry")


class PullbackEntryStrategy:
    """
    Pullback entry strategy.
    
    Responsibilities:
    1. Detect price pullback to support level (MA20)
    2. Calculate entry price, stop loss, profit target
    3. Calculate reward/risk ratio
    4. Calculate suggested position weight based on rule_engine_score
    """
    
    def __init__(self):
        self.ma_period = settings.PULLBACK_MA_PERIOD
        self.tolerance = settings.PULLBACK_TOLERANCE
        self.atr_multiplier_stop = settings.ATR_MULTIPLIER_STOP
        self.atr_multiplier_target = settings.ATR_MULTIPLIER_TARGET
        
    def analyze(
        self, 
        market_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze pullback buy signal.
        
        Args:
            market_data: Market data from MarketFilter
            {
                "symbol": "BTCUSDT",
                "kline_data": [...],
                "trend_score": 75.0,
                "onchain_score": 20.0,
                "total_score": 95.0
            }
            
        Returns:
            Signal data or None if no signal:
            {
                "signal_type": "PULLBACK_BUY",
                "entry_price": 65000.50,
                "stop_loss_price": 63500.00,
                "profit_target_price": 68000.00,
                "risk_unit_r": 1500.00,
                "reward_risk_ratio": 2.00,
                "suggested_position_weight": 0.85,
                "rule_engine_score": 87.5
            }
        """
        try:
            kline_data = market_data["kline_data"]
            if len(kline_data) < self.ma_period:
                logger.warning(f"Insufficient K-line data for {market_data['symbol']}")
                return None
            
            # 1. Check pullback condition
            pullback_detected = self._detect_pullback(kline_data)
            if not pullback_detected:
                logger.debug(f"No pullback detected for {market_data['symbol']}")
                return None
            
            # 2. Calculate prices
            latest_kline = kline_data[-1]
            entry_price = float(latest_kline["close_price"])
            
            # Calculate ATR for stop loss and target
            atr = self._calculate_atr(kline_data)
            
            # Calculate support level (MA20)
            support_level = self._calculate_ma(kline_data, self.ma_period)
            
            # Stop loss: below support or entry - ATR*multiplier
            stop_loss_price = min(
                support_level * (1 - self.tolerance),
                entry_price - (atr * self.atr_multiplier_stop)
            )
            
            # Profit target: entry + ATR*multiplier
            profit_target_price = entry_price + (atr * self.atr_multiplier_target)
            
            # Risk unit (R)
            risk_unit_r = entry_price - stop_loss_price
            
            # 3. Calculate reward/risk ratio
            reward = profit_target_price - entry_price
            risk = entry_price - stop_loss_price
            reward_risk_ratio = reward / risk if risk > 0 else 0.0
            
            # 4. Calculate rule engine score
            rule_engine_score = market_data["total_score"]
            
            # 5. Calculate suggested position weight
            suggested_position_weight = self.calculate_position_weight(rule_engine_score)
            
            signal_data = {
                "signal_type": "PULLBACK_BUY",
                "entry_price": entry_price,
                "stop_loss_price": stop_loss_price,
                "profit_target_price": profit_target_price,
                "risk_unit_r": risk_unit_r,
                "reward_risk_ratio": round(reward_risk_ratio, 2),
                "suggested_position_weight": round(suggested_position_weight, 4),
                "rule_engine_score": round(rule_engine_score, 2)
            }
            
            logger.info(
                f"Pullback signal for {market_data['symbol']}: "
                f"entry={entry_price:.2f}, stop={stop_loss_price:.2f}, "
                f"target={profit_target_price:.2f}, R/R={reward_risk_ratio:.2f}, "
                f"weight={suggested_position_weight:.4f}"
            )
            
            return signal_data
            
        except Exception as e:
            logger.error(f"Error analyzing pullback for {market_data['symbol']}: {e}")
            return None
    
    def _detect_pullback(self, kline_data: list) -> bool:
        """
        Detect pullback to MA20.

        Conditions (RELAXED FOR TESTING):
        1. Price is above MA20 (uptrend confirmed)
        2. Price is within reasonable range of MA20 (not too far away)

        Original strict conditions:
        - Price was above MA20
        - Price pulled back to MA20 (within tolerance)
        - Recent volume confirms the move
        """
        try:
            recent_klines = kline_data[-self.ma_period:]
            latest_kline = recent_klines[-1]

            # Calculate MA20
            ma20 = self._calculate_ma(kline_data, self.ma_period)

            # Current price
            current_price = float(latest_kline["close_price"])

            # RELAXED CONDITION: Just check if price is above MA20 (uptrend)
            # This allows signal generation for testing purposes
            price_to_ma_ratio = current_price / ma20

            # Price should be above MA20 but not too far (within 10%)
            if price_to_ma_ratio >= 1.0 and price_to_ma_ratio <= 1.10:
                logger.info(f"Pullback detected: price={current_price:.2f}, MA20={ma20:.2f}, ratio={price_to_ma_ratio:.4f}")
                return True

            logger.debug(f"No pullback: price={current_price:.2f}, MA20={ma20:.2f}, ratio={price_to_ma_ratio:.4f}")
            return False

        except Exception as e:
            logger.error(f"Error detecting pullback: {e}")
            return False
    
    def _calculate_ma(self, kline_data: list, period: int) -> float:
        """Calculate moving average."""
        recent_klines = kline_data[-period:]
        close_prices = [float(k["close_price"]) for k in recent_klines]
        return sum(close_prices) / len(close_prices)
    
    def _calculate_atr(self, kline_data: list, period: int = 14) -> float:
        """
        Calculate Average True Range (ATR).
        
        ATR = average of True Range over period
        True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
        """
        try:
            if len(kline_data) < period + 1:
                # Fallback: use simple range
                latest = kline_data[-1]
                return float(latest["high_price"]) - float(latest["low_price"])
            
            true_ranges = []
            for i in range(-period, 0):
                current = kline_data[i]
                previous = kline_data[i - 1]
                
                high = float(current["high_price"])
                low = float(current["low_price"])
                prev_close = float(previous["close_price"])
                
                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close)
                )
                true_ranges.append(tr)
            
            return sum(true_ranges) / len(true_ranges)
            
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            # Fallback
            latest = kline_data[-1]
            return float(latest["high_price"]) - float(latest["low_price"])
    
    def calculate_position_weight(self, rule_engine_score: float) -> float:
        """
        Calculate suggested position weight based on rule_engine_score.
        
        Rules:
        - score >= 85: 0.8-1.0 (high confidence)
        - score 70-85: 0.5-0.7 (medium confidence)
        - score < 70: 0.3-0.5 (low confidence)
        
        Uses linear interpolation within each range.
        """
        if rule_engine_score >= settings.HIGH_CONFIDENCE_THRESHOLD:
            # High confidence: map 85-100 to 0.8-1.0
            ratio = (rule_engine_score - settings.HIGH_CONFIDENCE_THRESHOLD) / (100 - settings.HIGH_CONFIDENCE_THRESHOLD)
            ratio = min(1.0, max(0.0, ratio))  # Clamp to [0, 1]
            weight = settings.HIGH_CONFIDENCE_WEIGHT_MIN + ratio * (
                settings.HIGH_CONFIDENCE_WEIGHT_MAX - settings.HIGH_CONFIDENCE_WEIGHT_MIN
            )
            
        elif rule_engine_score >= settings.MEDIUM_CONFIDENCE_THRESHOLD:
            # Medium confidence: map 70-85 to 0.5-0.7
            ratio = (rule_engine_score - settings.MEDIUM_CONFIDENCE_THRESHOLD) / (
                settings.HIGH_CONFIDENCE_THRESHOLD - settings.MEDIUM_CONFIDENCE_THRESHOLD
            )
            ratio = min(1.0, max(0.0, ratio))
            weight = settings.MEDIUM_CONFIDENCE_WEIGHT_MIN + ratio * (
                settings.MEDIUM_CONFIDENCE_WEIGHT_MAX - settings.MEDIUM_CONFIDENCE_WEIGHT_MIN
            )
            
        else:
            # Low confidence: map 0-70 to 0.3-0.5
            ratio = rule_engine_score / settings.MEDIUM_CONFIDENCE_THRESHOLD
            ratio = min(1.0, max(0.0, ratio))
            weight = settings.LOW_CONFIDENCE_WEIGHT_MIN + ratio * (
                settings.LOW_CONFIDENCE_WEIGHT_MAX - settings.LOW_CONFIDENCE_WEIGHT_MIN
            )
        
        return weight

