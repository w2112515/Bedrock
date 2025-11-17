"""
Exit Strategy

Implements three-in-one exit mechanism:
1. Initial stop loss
2. Trailing stop loss
3. Profit target
"""

import sys
import os
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.decision_engine.app.core.config import settings

logger = setup_logging("exit_strategy")


class ExitStrategy:
    """
    Three-in-one exit strategy.
    
    Responsibilities:
    1. Calculate initial stop loss price
    2. Calculate trailing stop distance
    3. Calculate profit target price
    
    Note: This is a calculation-only class for Phase 1.
    Actual exit execution will be handled by PortfolioService.
    """
    
    def __init__(self):
        self.atr_multiplier_stop = settings.ATR_MULTIPLIER_STOP
        self.atr_multiplier_target = settings.ATR_MULTIPLIER_TARGET
        
    def calculate_exits(
        self, 
        entry_price: float,
        atr: float,
        support_level: float,
        tolerance: float = 0.02
    ) -> Dict[str, float]:
        """
        Calculate three-in-one exit prices.
        
        Args:
            entry_price: Entry price
            atr: Average True Range
            support_level: Support level (e.g., MA20)
            tolerance: Tolerance below support (default: 2%)
            
        Returns:
            {
                "stop_loss_price": 63500.00,
                "profit_target_price": 68000.00,
                "trailing_stop_distance": 750.00
            }
        """
        try:
            # 1. Initial stop loss
            # Use the lower of: support - tolerance OR entry - ATR*multiplier
            stop_loss_price = min(
                support_level * (1 - tolerance),
                entry_price - (atr * self.atr_multiplier_stop)
            )
            
            # 2. Profit target
            # Entry + ATR*multiplier
            profit_target_price = entry_price + (atr * self.atr_multiplier_target)
            
            # 3. Trailing stop distance
            # Use ATR as trailing stop distance
            trailing_stop_distance = atr
            
            exits = {
                "stop_loss_price": round(stop_loss_price, 2),
                "profit_target_price": round(profit_target_price, 2),
                "trailing_stop_distance": round(trailing_stop_distance, 2)
            }
            
            logger.debug(
                f"Calculated exits: stop={stop_loss_price:.2f}, "
                f"target={profit_target_price:.2f}, trailing={trailing_stop_distance:.2f}"
            )
            
            return exits
            
        except Exception as e:
            logger.error(f"Error calculating exits: {e}")
            # Fallback: simple percentage-based exits
            return {
                "stop_loss_price": round(entry_price * 0.98, 2),
                "profit_target_price": round(entry_price * 1.04, 2),
                "trailing_stop_distance": round(entry_price * 0.01, 2)
            }
    
    def update_trailing_stop(
        self, 
        current_price: float,
        highest_price: float,
        trailing_stop_distance: float,
        current_stop: float
    ) -> float:
        """
        Update trailing stop loss.
        
        Args:
            current_price: Current market price
            highest_price: Highest price since entry
            trailing_stop_distance: Trailing stop distance (ATR)
            current_stop: Current stop loss price
            
        Returns:
            Updated stop loss price
        """
        # Calculate new trailing stop
        new_stop = highest_price - trailing_stop_distance
        
        # Only move stop up, never down
        updated_stop = max(current_stop, new_stop)
        
        logger.debug(
            f"Trailing stop update: current={current_stop:.2f}, "
            f"new={new_stop:.2f}, updated={updated_stop:.2f}"
        )
        
        return updated_stop
    
    def check_exit_conditions(
        self,
        current_price: float,
        entry_price: float,
        stop_loss_price: float,
        profit_target_price: float
    ) -> Dict[str, Any]:
        """
        Check if any exit condition is met.
        
        Args:
            current_price: Current market price
            entry_price: Entry price
            stop_loss_price: Stop loss price
            profit_target_price: Profit target price
            
        Returns:
            {
                "should_exit": True/False,
                "exit_reason": "STOP_LOSS" | "PROFIT_TARGET" | None,
                "exit_price": current_price
            }
        """
        # Check stop loss
        if current_price <= stop_loss_price:
            return {
                "should_exit": True,
                "exit_reason": "STOP_LOSS",
                "exit_price": current_price
            }
        
        # Check profit target
        if current_price >= profit_target_price:
            return {
                "should_exit": True,
                "exit_reason": "PROFIT_TARGET",
                "exit_price": current_price
            }
        
        # No exit condition met
        return {
            "should_exit": False,
            "exit_reason": None,
            "exit_price": None
        }

