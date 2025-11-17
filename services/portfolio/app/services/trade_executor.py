"""
Trade Executor - Executes trades and manages positions.

Responsibilities:
1. Open positions based on signals
2. Close positions (manual or automatic)
3. Update account balance (freeze/unfreeze)
4. Create trade records
"""

import sys
import os
from decimal import Decimal
from typing import Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.portfolio.app.core.config import settings
from services.portfolio.app.models.position import Position
from services.portfolio.app.models.trade import Trade
from services.portfolio.app.models.account import Account
from services.portfolio.app.services.position_sizer import PositionSizer

logger = setup_logging("trade_executor")


class TradeExecutor:
    """
    Trade execution engine.
    
    Responsibilities:
    1. Execute position opening (create Position + Trade ENTRY)
    2. Execute position closing (create Trade EXIT, update Position)
    3. Manage account balance (freeze/unfreeze)
    """
    
    def __init__(self, db: Session):
        """
        Initialize TradeExecutor.
        
        Args:
            db: Database session
        """
        self.db = db
        self.position_sizer = PositionSizer()
        self.commission_rate = settings.COMMISSION_RATE
        self.slippage_rate = settings.SLIPPAGE_RATE
        
        logger.info("TradeExecutor initialized")
    
    def open_position(self, signal_data: Dict[str, Any]) -> Position:
        """
        Open a new position based on signal.
        
        Workflow:
        1. Get account
        2. Calculate position size (PositionSizer)
        3. Check available balance
        4. Create Position record
        5. Create Trade record (ENTRY)
        6. Update Account (freeze balance)
        7. Commit transaction
        
        Args:
            signal_data: Signal event payload
        
        Returns:
            Created Position object
        
        Raises:
            ValueError: If account not found or insufficient balance
        """
        try:
            logger.info(f"Opening position for signal: {signal_data.get('signal_id')}")
            
            # 1. Get account
            account = self.db.query(Account).first()
            if not account:
                raise ValueError("Account not found. Please initialize account first.")
            
            # 2. Calculate position size
            position_size, position_weight, estimated_cost, commission, slippage = \
                self.position_sizer.calculate_position_size(
                    signal_data, account.available_balance
                )
            
            # 3. Check available balance
            total_cost = estimated_cost + commission + slippage
            if total_cost > account.available_balance:
                raise ValueError(
                    f"Insufficient available balance. "
                    f"Required: {total_cost}, Available: {account.available_balance}"
                )
            
            # 4. Create Position
            position = Position(
                market=signal_data['market'],
                signal_id=UUID(signal_data['signal_id']),
                position_size=position_size,
                entry_price=Decimal(str(signal_data['entry_price'])),
                current_price=Decimal(str(signal_data['entry_price'])),
                stop_loss_price=Decimal(str(signal_data['stop_loss_price'])),
                profit_target_price=Decimal(str(signal_data['profit_target_price'])),
                position_weight_used=position_weight,
                status='OPEN',
                unrealized_pnl=Decimal('0')
            )
            self.db.add(position)
            self.db.flush()  # Get position.id
            
            logger.info(
                f"Position created: id={position.id}, "
                f"market={position.market}, size={position_size}, weight={position_weight}"
            )
            
            # 5. Create Trade (ENTRY)
            trade = Trade(
                position_id=position.id,
                trade_type='ENTRY',
                market=signal_data['market'],
                quantity=position_size,
                price=Decimal(str(signal_data['entry_price'])),
                commission=commission
            )
            self.db.add(trade)
            
            logger.info(
                f"Trade created: id={trade.id}, type=ENTRY, "
                f"quantity={position_size}, commission={commission}"
            )
            
            # 6. Update Account (freeze balance)
            account.frozen_balance += total_cost
            account.available_balance -= total_cost
            account.updated_at = datetime.utcnow()
            
            logger.info(
                f"Account updated: frozen={account.frozen_balance}, "
                f"available={account.available_balance}"
            )
            
            # 7. Commit transaction
            self.db.commit()
            self.db.refresh(position)
            
            logger.info(f"Position opened successfully: position_id={position.id}")
            
            return position
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error opening position: {e}")
            raise
    
    def close_position(
        self,
        position: Position,
        exit_price: Decimal,
        exit_reason: str
    ) -> Trade:
        """
        Close an existing position.
        
        Workflow:
        1. Calculate realized P&L
        2. Create Trade record (EXIT)
        3. Update Position status
        4. Update Account (unfreeze balance, update total balance)
        5. Commit transaction
        
        Args:
            position: Position to close
            exit_price: Exit price
            exit_reason: Reason for closing (e.g., PROFIT_TARGET_HIT, STOP_LOSS_HIT)
        
        Returns:
            Created Trade object (EXIT)
        
        Raises:
            ValueError: If position is not OPEN
        """
        try:
            if position.status != 'OPEN':
                raise ValueError(f"Cannot close position with status: {position.status}")
            
            logger.info(
                f"Closing position: id={position.id}, "
                f"exit_price={exit_price}, reason={exit_reason}"
            )
            
            # 1. Calculate realized P&L
            entry_cost = position.position_size * position.entry_price
            exit_value = position.position_size * exit_price
            exit_commission = exit_value * self.commission_rate
            realized_pnl = exit_value - entry_cost - exit_commission
            
            logger.info(
                f"P&L calculation: entry_cost={entry_cost}, "
                f"exit_value={exit_value}, exit_commission={exit_commission}, "
                f"realized_pnl={realized_pnl}"
            )
            
            # 2. Create Trade (EXIT)
            trade = Trade(
                position_id=position.id,
                trade_type='EXIT',
                market=position.market,
                quantity=position.position_size,
                price=exit_price,
                commission=exit_commission,
                realized_pnl=realized_pnl
            )
            self.db.add(trade)
            
            logger.info(f"Trade created: id={trade.id}, type=EXIT, realized_pnl={realized_pnl}")
            
            # 3. Update Position
            position.status = 'CLOSED'
            position.current_price = exit_price
            position.closed_at = datetime.utcnow()
            position.exit_reason = exit_reason
            
            # 4. Update Account
            account = self.db.query(Account).first()
            if account:
                # Unfreeze the original frozen amount (entry cost + entry commission)
                entry_commission = entry_cost * self.commission_rate
                frozen_amount = entry_cost + entry_commission
                
                account.frozen_balance -= frozen_amount
                account.balance += realized_pnl
                account.available_balance = account.balance - account.frozen_balance
                account.updated_at = datetime.utcnow()
                
                logger.info(
                    f"Account updated: balance={account.balance}, "
                    f"frozen={account.frozen_balance}, available={account.available_balance}"
                )
            
            # 5. Commit transaction
            self.db.commit()
            self.db.refresh(trade)
            
            logger.info(f"Position closed successfully: position_id={position.id}")
            
            return trade
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error closing position: {e}")
            raise

