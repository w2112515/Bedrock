"""
MetricsCalculator - Calculates performance metrics for backtesting.

Implements:
- Sharpe Ratio
- Sortino Ratio
- Calmar Ratio
- Omega Ratio
- Maximum Drawdown
- Win Rate, Profit Factor, etc.
"""

import sys
import os
from typing import List, Dict, Any
from decimal import Decimal
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging

logger = setup_logging("metrics_calculator")


class MetricsCalculator:
    """
    Performance metrics calculator for backtesting.
    
    Calculates comprehensive performance metrics including:
    - Basic metrics: win rate, profit factor, avg win/loss
    - Risk metrics: max drawdown
    - Risk-adjusted returns: Sharpe, Sortino, Calmar, Omega ratios
    """
    
    def __init__(self):
        """Initialize MetricsCalculator."""
        logger.info("MetricsCalculator initialized")
    
    def calculate_all_metrics(
        self,
        trades: List[Dict[str, Any]],
        equity_curve: List[float],
        initial_balance: float,
        final_balance: float
    ) -> Dict[str, Any]:
        """
        Calculate all performance metrics.
        
        Args:
            trades: List of trade dictionaries with realized_pnl
            equity_curve: List of equity values over time
            initial_balance: Initial account balance
            final_balance: Final account balance
        
        Returns:
            Dictionary with all metrics
        """
        try:
            # Extract P&L values
            pnl_values = [
                float(trade.get('realized_pnl', 0))
                for trade in trades
                if trade.get('trade_type') == 'EXIT' and trade.get('realized_pnl') is not None
            ]
            
            # Calculate basic metrics
            total_trades = len(pnl_values)
            winning_trades = len([pnl for pnl in pnl_values if pnl > 0])
            losing_trades = len([pnl for pnl in pnl_values if pnl < 0])
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
            
            wins = [pnl for pnl in pnl_values if pnl > 0]
            losses = [pnl for pnl in pnl_values if pnl < 0]
            
            avg_win = np.mean(wins) if wins else 0.0
            avg_loss = np.mean(losses) if losses else 0.0
            
            gross_profit = sum(wins) if wins else 0.0
            gross_loss = abs(sum(losses)) if losses else 0.0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
            
            # Calculate ROI
            roi = (final_balance - initial_balance) / initial_balance if initial_balance > 0 else 0.0
            
            # Calculate max drawdown
            max_drawdown = self.calculate_max_drawdown(equity_curve)
            
            # Calculate returns for ratio calculations
            returns = self._calculate_returns(pnl_values, initial_balance)
            
            # Calculate risk-adjusted ratios
            sharpe_ratio = self.calculate_sharpe_ratio(returns)
            sortino_ratio = self.calculate_sortino_ratio(returns)
            calmar_ratio = self.calculate_calmar_ratio(roi, max_drawdown)
            omega_ratio = self.calculate_omega_ratio(returns)
            
            # Calculate total costs
            total_commission = sum([
                float(trade.get('commission', 0))
                for trade in trades
            ])
            total_slippage = sum([
                float(trade.get('slippage', 0))
                for trade in trades
            ])
            
            metrics = {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 4),
                "avg_win": round(float(avg_win), 2),
                "avg_loss": round(float(avg_loss), 2),
                "profit_factor": round(profit_factor, 4),
                "max_drawdown": round(max_drawdown, 4),
                "sharpe_ratio": round(sharpe_ratio, 4) if sharpe_ratio is not None else None,
                "sortino_ratio": round(sortino_ratio, 4) if sortino_ratio is not None else None,
                "calmar_ratio": round(calmar_ratio, 4) if calmar_ratio is not None else None,
                "omega_ratio": round(omega_ratio, 4) if omega_ratio is not None else None,
                "total_commission": round(total_commission, 2),
                "total_slippage": round(total_slippage, 2),
                "roi": round(roi, 4)
            }
            
            logger.info(f"Calculated metrics: ROI={roi:.2%}, Sharpe={sharpe_ratio:.2f}, Max DD={max_drawdown:.2%}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            raise
    
    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.0) -> float:
        """
        Calculate Sharpe Ratio.
        
        Sharpe Ratio = (Mean Return - Risk Free Rate) / Std Dev of Returns
        
        Args:
            returns: List of returns
            risk_free_rate: Risk-free rate (default 0.0)
        
        Returns:
            Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)
        
        if std_return == 0:
            return 0.0
        
        return (mean_return - risk_free_rate) / std_return
    
    def calculate_sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.0) -> float:
        """
        Calculate Sortino Ratio.
        
        Sortino Ratio = (Mean Return - Risk Free Rate) / Downside Std Dev
        Only considers negative returns for volatility.
        
        Args:
            returns: List of returns
            risk_free_rate: Risk-free rate (default 0.0)
        
        Returns:
            Sortino ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        downside_returns = [r for r in returns if r < 0]
        
        if not downside_returns:
            return float('inf') if mean_return > 0 else 0.0
        
        downside_std = np.std(downside_returns, ddof=1)
        
        if downside_std == 0:
            return 0.0
        
        return (mean_return - risk_free_rate) / downside_std
    
    def calculate_calmar_ratio(self, total_return: float, max_drawdown: float) -> float:
        """
        Calculate Calmar Ratio.
        
        Calmar Ratio = Annualized Return / Maximum Drawdown
        
        Args:
            total_return: Total return (ROI)
            max_drawdown: Maximum drawdown
        
        Returns:
            Calmar ratio
        """
        if max_drawdown == 0:
            return 0.0
        
        return total_return / abs(max_drawdown)
    
    def calculate_omega_ratio(self, returns: List[float], threshold: float = 0.0) -> float:
        """
        Calculate Omega Ratio.
        
        Omega Ratio = Sum of gains above threshold / Sum of losses below threshold
        
        Args:
            returns: List of returns
            threshold: Threshold return (default 0.0)
        
        Returns:
            Omega ratio
        """
        if not returns:
            return 0.0
        
        gains = sum([r - threshold for r in returns if r > threshold])
        losses = sum([threshold - r for r in returns if r < threshold])
        
        if losses == 0:
            return float('inf') if gains > 0 else 0.0
        
        return gains / losses
    
    def calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """
        Calculate Maximum Drawdown.
        
        Max Drawdown = (Peak - Trough) / Peak
        
        Args:
            equity_curve: List of equity values over time
        
        Returns:
            Maximum drawdown (0.0-1.0)
        """
        if not equity_curve or len(equity_curve) < 2:
            return 0.0
        
        peak = equity_curve[0]
        max_dd = 0.0
        
        for value in equity_curve:
            if value > peak:
                peak = value
            
            dd = (peak - value) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def _calculate_returns(self, pnl_values: List[float], initial_balance: float) -> List[float]:
        """
        Calculate returns from P&L values.
        
        Args:
            pnl_values: List of P&L values
            initial_balance: Initial balance
        
        Returns:
            List of returns
        """
        if not pnl_values or initial_balance <= 0:
            return []
        
        returns = []
        current_balance = initial_balance
        
        for pnl in pnl_values:
            if current_balance > 0:
                ret = pnl / current_balance
                returns.append(ret)
                current_balance += pnl
        
        return returns

