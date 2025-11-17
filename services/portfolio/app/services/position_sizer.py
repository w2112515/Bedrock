"""
Position Sizer - Calculates position size based on signal and account balance.

Implements 方案A: Prioritizes suggested_position_weight from signal.
Falls back to default fixed risk algorithm if not provided.
"""

import sys
import os
from decimal import Decimal
from typing import Tuple, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.portfolio.app.core.config import settings

logger = setup_logging("position_sizer")


class PositionSizer:
    """
    Position size calculator.
    
    Responsibilities:
    1. Calculate position size based on signal and account balance
    2. Prioritize suggested_position_weight from signal (方案A)
    3. Apply commission and slippage costs
    4. Ensure position doesn't exceed available balance
    """
    
    def __init__(self):
        """Initialize PositionSizer with configuration."""
        self.default_risk_per_trade = settings.DEFAULT_RISK_PER_TRADE
        self.max_position_weight = settings.MAX_POSITION_WEIGHT
        self.commission_rate = settings.COMMISSION_RATE
        self.slippage_rate = settings.SLIPPAGE_RATE
        
        logger.info(
            f"PositionSizer initialized: "
            f"default_risk={self.default_risk_per_trade}, "
            f"max_weight={self.max_position_weight}, "
            f"commission={self.commission_rate}, "
            f"slippage={self.slippage_rate}"
        )
    
    def calculate_position_size(
        self,
        signal_data: Dict[str, Any],
        account_balance: Decimal
    ) -> Tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
        """
        Calculate position size based on signal and account balance.
        
        方案A Implementation:
        1. Check if signal has suggested_position_weight
        2. If yes: Use suggested_position_weight
        3. If no: Use default fixed risk algorithm
        4. Apply max_position_weight limit
        5. Calculate costs (commission + slippage)
        6. Ensure total cost doesn't exceed available balance
        
        Args:
            signal_data: Signal event payload containing:
                - entry_price: Entry price
                - risk_unit_r: Risk unit (R) in quote currency
                - suggested_position_weight: Optional suggested weight (0.0-1.0)
            account_balance: Available account balance
        
        Returns:
            Tuple of (position_size, position_weight_used, estimated_cost, commission, slippage)
        """
        try:
            # Extract signal data
            entry_price = Decimal(str(signal_data['entry_price']))
            risk_unit_r = Decimal(str(signal_data.get('risk_unit_r', 0)))
            suggested_weight = signal_data.get('suggested_position_weight')
            
            logger.info(
                f"Calculating position size: "
                f"entry_price={entry_price}, "
                f"risk_unit_r={risk_unit_r}, "
                f"suggested_weight={suggested_weight}, "
                f"account_balance={account_balance}"
            )
            
            # 方案A: Prioritize suggested_position_weight
            if suggested_weight is not None:
                position_weight = Decimal(str(suggested_weight))
                position_weight = min(position_weight, self.max_position_weight)
                
                # Calculate position size from weight
                position_size = (account_balance * position_weight) / entry_price
                
                logger.info(
                    f"Using suggested_position_weight: "
                    f"weight={position_weight}, size={position_size}"
                )
            else:
                # Default fixed risk algorithm
                if risk_unit_r > 0:
                    position_size = (account_balance * self.default_risk_per_trade) / risk_unit_r
                    position_weight = (position_size * entry_price) / account_balance
                    position_weight = min(position_weight, self.max_position_weight)
                else:
                    # Fallback: Use default risk percentage
                    position_weight = self.default_risk_per_trade
                    position_size = (account_balance * position_weight) / entry_price
                
                logger.info(
                    f"Using default risk algorithm: "
                    f"weight={position_weight}, size={position_size}"
                )
            
            # Calculate costs
            estimated_cost = position_size * entry_price
            commission = estimated_cost * self.commission_rate
            slippage = estimated_cost * self.slippage_rate
            total_cost = estimated_cost + commission + slippage
            
            # Ensure total cost doesn't exceed available balance
            if total_cost > account_balance:
                logger.warning(
                    f"Total cost ({total_cost}) exceeds available balance ({account_balance}). "
                    f"Adjusting position size."
                )
                
                # Adjust position size to fit within available balance
                # total_cost = position_size * entry_price * (1 + commission_rate + slippage_rate)
                # position_size = account_balance * 0.95 / (entry_price * (1 + commission_rate + slippage_rate))
                adjustment_factor = Decimal('1') + self.commission_rate + self.slippage_rate
                position_size = (account_balance * Decimal('0.95')) / (entry_price * adjustment_factor)
                position_weight = (position_size * entry_price) / account_balance
                
                # Recalculate costs
                estimated_cost = position_size * entry_price
                commission = estimated_cost * self.commission_rate
                slippage = estimated_cost * self.slippage_rate
                total_cost = estimated_cost + commission + slippage
                
                logger.info(
                    f"Adjusted position: "
                    f"size={position_size}, weight={position_weight}, total_cost={total_cost}"
                )
            
            logger.info(
                f"Position size calculated: "
                f"size={position_size}, weight={position_weight}, "
                f"cost={estimated_cost}, commission={commission}, slippage={slippage}"
            )
            
            return position_size, position_weight, estimated_cost, commission, slippage
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            raise
    
    def estimate_position(
        self,
        signal_data: Dict[str, Any],
        account_balance: Decimal
    ) -> Dict[str, Any]:
        """
        Estimate position details for /v1/positions/estimate endpoint.
        
        Args:
            signal_data: Signal data
            account_balance: Available account balance
        
        Returns:
            Dictionary with estimation details
        """
        try:
            position_size, position_weight, estimated_cost, commission, slippage = \
                self.calculate_position_size(signal_data, account_balance)
            
            entry_price = Decimal(str(signal_data['entry_price']))
            stop_loss_price = Decimal(str(signal_data['stop_loss_price']))
            risk_unit_r = Decimal(str(signal_data.get('risk_unit_r', 0)))
            
            # Calculate risk percentage
            if account_balance > 0:
                risk_percentage = (risk_unit_r * position_size / account_balance) * Decimal('100')
            else:
                risk_percentage = Decimal('0')
            
            return {
                "signal_id": signal_data.get('signal_id'),  # Optional for estimate endpoint
                "market": signal_data['market'],
                "estimated_position_size": position_size,
                "estimated_cost": estimated_cost + commission + slippage,
                "position_weight_used": position_weight,
                "commission": commission,
                "slippage": slippage,
                "risk_percentage": risk_percentage,
                "entry_price": entry_price,
                "stop_loss_price": stop_loss_price,
                "profit_target_price": Decimal(str(signal_data.get('profit_target_price', 0)))
            }
            
        except Exception as e:
            logger.error(f"Error estimating position: {e}")
            raise

