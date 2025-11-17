"""
Stats Service - Business logic for portfolio statistics.
"""

import sys
import os
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.portfolio.app.models.position import Position
from services.portfolio.app.models.trade import Trade

logger = setup_logging("stats_service")


class StatsService:
    """
    Portfolio statistics service.
    
    Calculates portfolio performance metrics.
    """
    
    def __init__(self, db: Session):
        """
        Initialize StatsService.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_stats(self) -> dict:
        """
        Calculate portfolio statistics.
        
        Returns:
            Dictionary with statistics:
            - total_pnl: Total realized profit/loss
            - win_rate: Win rate (0.0-1.0)
            - total_trades: Total number of closed positions
            - winning_trades: Number of winning trades
            - losing_trades: Number of losing trades
            - avg_win: Average profit per winning trade
            - avg_loss: Average loss per losing trade
            - profit_factor: Profit factor (total wins / total losses)
            - open_positions: Number of currently open positions
            - total_commission: Total commission paid
        """
        try:
            # Get all closed positions
            closed_positions = self.db.query(Position).filter(
                Position.status == 'CLOSED'
            ).all()
            
            # Get all EXIT trades (which have realized_pnl)
            exit_trades = self.db.query(Trade).filter(
                Trade.trade_type == 'EXIT'
            ).all()
            
            # Calculate statistics
            total_trades = len(exit_trades)
            winning_trades = len([t for t in exit_trades if t.realized_pnl and t.realized_pnl > 0])
            losing_trades = len([t for t in exit_trades if t.realized_pnl and t.realized_pnl <= 0])
            
            total_pnl = sum([t.realized_pnl for t in exit_trades if t.realized_pnl]) or Decimal('0')
            total_wins = sum([t.realized_pnl for t in exit_trades if t.realized_pnl and t.realized_pnl > 0]) or Decimal('0')
            total_losses = abs(sum([t.realized_pnl for t in exit_trades if t.realized_pnl and t.realized_pnl < 0])) or Decimal('0')
            
            win_rate = Decimal(winning_trades) / Decimal(total_trades) if total_trades > 0 else Decimal('0')
            avg_win = total_wins / Decimal(winning_trades) if winning_trades > 0 else Decimal('0')
            avg_loss = total_losses / Decimal(losing_trades) if losing_trades > 0 else Decimal('0')
            profit_factor = total_wins / total_losses if total_losses > 0 else Decimal('0')
            
            # Get open positions count
            open_positions = self.db.query(Position).filter(
                Position.status == 'OPEN'
            ).count()
            
            # Calculate total commission
            total_commission = self.db.query(func.sum(Trade.commission)).scalar() or Decimal('0')
            
            stats = {
                "total_pnl": total_pnl,
                "win_rate": win_rate,
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": profit_factor,
                "open_positions": open_positions,
                "total_commission": total_commission
            }
            
            logger.info(
                f"Calculated stats: total_pnl={total_pnl}, win_rate={win_rate:.2f}, "
                f"total_trades={total_trades}, open_positions={open_positions}"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating stats: {e}")
            raise

