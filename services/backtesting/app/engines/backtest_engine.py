"""
BacktestEngine - Core backtesting engine.

Responsibilities:
1. Fetch historical K-line data from DataHub
2. Replay market data chronologically
3. Generate signals using RuleEngine (reused from DecisionEngine)
4. Execute trades using adapted TradeExecutor logic (reused from Portfolio)
5. Track equity curve and positions
6. Calculate performance metrics
"""

import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import UUID
import httpx

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.backtesting.app.core.config import settings
from services.backtesting.app.models.backtest_trade import BacktestTrade
from services.portfolio.app.services.position_sizer import PositionSizer
from services.backtesting.app.clients import DecisionEngineClient

logger = setup_logging("backtest_engine")


class BacktestEngine:
    """
    Core backtesting engine.
    
    Simulates trading strategy on historical data and tracks performance.
    """
    
    def __init__(
        self,
        backtest_run_id: UUID,
        initial_balance: Decimal,
        commission_rate: Optional[Decimal] = None,
        slippage_rate: Optional[Decimal] = None,
        decision_engine_url: Optional[str] = None
    ):
        """
        Initialize BacktestEngine.

        Args:
            backtest_run_id: Backtest run ID
            initial_balance: Initial account balance
            commission_rate: Commission rate (default from settings)
            slippage_rate: Slippage rate (default from settings)
            decision_engine_url: DecisionEngine URL (default from settings)
        """
        self.backtest_run_id = backtest_run_id
        self.initial_balance = initial_balance
        self.commission_rate = commission_rate or settings.DEFAULT_COMMISSION_RATE
        self.slippage_rate = slippage_rate or settings.DEFAULT_SLIPPAGE_RATE

        # Virtual account state
        self.balance = initial_balance
        self.available_balance = initial_balance
        self.frozen_balance = Decimal("0")

        # Position tracking
        self.current_position = None

        # Trade history
        self.trades: List[Dict[str, Any]] = []

        # Equity curve
        self.equity_curve: List[float] = [float(initial_balance)]

        # Reuse Portfolio Service's PositionSizer
        self.position_sizer = PositionSizer()

        # Initialize DecisionEngineClient
        self.decision_engine_client = DecisionEngineClient(
            base_url=decision_engine_url or settings.DECISION_ENGINE_URL,
            timeout=30,
            max_retries=3
        )

        logger.info(
            f"BacktestEngine initialized: "
            f"backtest_run_id={backtest_run_id}, "
            f"initial_balance={initial_balance}, "
            f"commission={self.commission_rate}, "
            f"slippage={self.slippage_rate}"
        )
    
    async def fetch_historical_klines(
        self,
        market: str,
        interval: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical K-line data from DataHub.
        
        Args:
            market: Trading pair (e.g., "BTC/USDT")
            interval: K-line interval (e.g., "1h")
            start_date: Start date
            end_date: End date
        
        Returns:
            List of K-line data dictionaries
        """
        try:
            # Convert market format: "BTC/USDT" -> "BTCUSDT"
            symbol = market.replace("/", "")
            
            logger.info(
                f"Fetching historical K-lines: "
                f"symbol={symbol}, interval={interval}, "
                f"start={start_date}, end={end_date}"
            )
            
            # Convert dates to datetime
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{settings.DATAHUB_URL}/v1/klines/{symbol}/{interval}",
                    params={
                        "start_time": start_datetime.isoformat(),
                        "end_time": end_datetime.isoformat(),
                        "limit": settings.MAX_KLINES_PER_REQUEST
                    }
                )
                response.raise_for_status()
                klines = response.json()
            
            logger.info(f"Fetched {len(klines)} K-lines from DataHub")
            
            return klines
            
        except Exception as e:
            logger.error(f"Error fetching historical K-lines: {e}")
            raise
    
    async def generate_signal(
        self,
        market: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate trading signal by calling DecisionEngine.

        DecisionEngine will internally:
        1. Fetch K-line data from DataHub
        2. Run MarketFilter and PullbackEntryStrategy
        3. Run ML/LLM adapters if enabled
        4. Return signal or None

        Args:
            market: Trading pair (e.g., "BTCUSDT")

        Returns:
            Signal dictionary or None
        """
        try:
            signal = await self.decision_engine_client.generate_signal(
                market=market,
                force_analysis=True  # Force analysis for each backtest iteration
            )
            return signal

        except Exception as e:
            logger.error(f"Error generating signal for {market}: {e}", exc_info=True)
            return None
    
    def open_position(
        self,
        signal: Dict[str, Any],
        price: Decimal,
        timestamp: datetime,
        market: str
    ) -> Optional[Dict[str, Any]]:
        """
        Open a position based on signal.

        Reuses Portfolio Service's PositionSizer logic.

        Args:
            signal: Signal dictionary from DecisionEngine
            price: Entry price
            timestamp: Trade timestamp
            market: Trading pair (e.g., "BTCUSDT")

        Returns:
            Trade dictionary or None
        """
        try:
            if self.current_position is not None:
                logger.debug("Position already open, skipping")
                return None

            # Calculate position size using PositionSizer (reused from Portfolio)
            position_size, position_weight, estimated_cost, commission, slippage = \
                self.position_sizer.calculate_position_size(
                    signal, self.available_balance
                )

            total_cost = estimated_cost + commission + slippage

            if total_cost > self.available_balance:
                logger.warning(f"Insufficient balance: required={total_cost}, available={self.available_balance}")
                return None

            # Create ENTRY trade
            entry_trade = {
                "backtest_run_id": self.backtest_run_id,
                "market": market,
                "signal_id": signal.get("signal_id"),  # Safe access
                "trade_type": "ENTRY",
                "quantity": position_size,
                "price": price,
                "timestamp": timestamp,
                "commission": commission,
                "slippage": slippage,
                "realized_pnl": None
            }

            # Update virtual account
            self.frozen_balance += total_cost
            self.available_balance -= total_cost

            # Track position (safe access for optional fields)
            self.current_position = {
                "entry_price": price,
                "stop_loss_price": signal["stop_loss_price"],
                "profit_target_price": signal["profit_target_price"],
                "position_size": position_size,
                "entry_cost": estimated_cost,
                "entry_commission": commission,
                "entry_timestamp": timestamp,
                "signal_id": signal.get("signal_id"),  # Safe access
                "ml_confidence_score": signal.get("ml_confidence_score"),  # Safe access
                "llm_sentiment": signal.get("llm_sentiment")  # Safe access
            }

            self.trades.append(entry_trade)

            logger.info(
                f"Position opened: market={market}, "
                f"size={position_size}, price={price}, "
                f"cost={total_cost}"
            )

            return entry_trade

        except Exception as e:
            logger.error(f"Error opening position: {e}", exc_info=True)
            return None
    
    def close_position(self, exit_price: Decimal, timestamp: datetime, exit_reason: str) -> Optional[Dict[str, Any]]:
        """
        Close current position.
        
        Args:
            exit_price: Exit price
            timestamp: Trade timestamp
            exit_reason: Exit reason
        
        Returns:
            Trade dictionary or None
        """
        try:
            if self.current_position is None:
                return None
            
            position_size = self.current_position['position_size']
            entry_price = self.current_position['entry_price']
            entry_cost = self.current_position['entry_cost']
            entry_commission = self.current_position['entry_commission']
            
            # Calculate exit value and costs
            exit_value = position_size * exit_price
            exit_commission = exit_value * self.commission_rate
            
            # Calculate realized P&L
            realized_pnl = exit_value - entry_cost - entry_commission - exit_commission
            
            # Create EXIT trade
            exit_trade = {
                "backtest_run_id": self.backtest_run_id,
                "market": "BTC/USDT",
                "signal_id": None,
                "trade_type": "EXIT",
                "quantity": position_size,
                "price": exit_price,
                "timestamp": timestamp,
                "commission": exit_commission,
                "slippage": Decimal("0"),  # Slippage only on entry
                "realized_pnl": realized_pnl
            }
            
            # Update virtual account
            frozen_amount = entry_cost + entry_commission
            self.frozen_balance -= frozen_amount
            self.balance += realized_pnl
            self.available_balance = self.balance - self.frozen_balance
            
            # Update equity curve
            self.equity_curve.append(float(self.balance))
            
            # Clear position
            self.current_position = None
            
            self.trades.append(exit_trade)
            
            logger.info(
                f"Position closed: "
                f"exit_price={exit_price}, pnl={realized_pnl}, "
                f"reason={exit_reason}, balance={self.balance}"
            )
            
            return exit_trade
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return None

    def check_exit_conditions(self, current_price: Decimal) -> Optional[str]:
        """
        Check if exit conditions are met.

        Args:
            current_price: Current market price

        Returns:
            Exit reason or None
        """
        if self.current_position is None:
            return None

        stop_loss = self.current_position['stop_loss_price']
        profit_target = self.current_position['profit_target_price']

        if current_price <= stop_loss:
            return "STOP_LOSS_HIT"
        elif current_price >= profit_target:
            return "PROFIT_TARGET_HIT"

        return None

    async def run(
        self,
        market: str,
        interval: str,
        start_date: date,
        end_date: date,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Run backtest simulation.

        Args:
            market: Trading pair (e.g., "BTC/USDT")
            interval: K-line interval (e.g., "1h")
            start_date: Start date
            end_date: End date
            progress_callback: Optional callback for progress updates

        Returns:
            Backtest results dictionary
        """
        try:
            logger.info(
                f"Starting backtest: "
                f"market={market}, interval={interval}, "
                f"start={start_date}, end={end_date}"
            )

            # 1. Fetch historical K-lines
            klines = await self.fetch_historical_klines(market, interval, start_date, end_date)

            if not klines:
                raise ValueError("No historical data available")

            total_klines = len(klines)
            logger.info(f"Processing {total_klines} K-lines")

            # 2. Replay market data
            for i, kline in enumerate(klines):
                # Update progress
                if progress_callback and i % 100 == 0:
                    progress = i / total_klines
                    await progress_callback(progress)

                current_price = Decimal(str(kline['close_price']))
                timestamp = datetime.fromtimestamp(kline['open_time'] / 1000)

                # Check exit conditions if position is open
                if self.current_position:
                    exit_reason = self.check_exit_conditions(current_price)
                    if exit_reason:
                        self.close_position(current_price, timestamp, exit_reason)

                # Generate signal if no position
                if self.current_position is None:
                    # Call DecisionEngine to generate signal
                    # DecisionEngine will internally fetch K-line data from DataHub
                    signal = await self.generate_signal(market=market)

                    if signal:
                        self.open_position(
                            signal=signal,
                            price=current_price,
                            timestamp=timestamp,
                            market=market
                        )

            # Close any remaining position at end
            if self.current_position:
                last_kline = klines[-1]
                last_price = Decimal(str(last_kline['close_price']))
                last_timestamp = datetime.fromtimestamp(last_kline['open_time'] / 1000)
                self.close_position(last_price, last_timestamp, "BACKTEST_END")

            # Update final progress
            if progress_callback:
                await progress_callback(1.0)

            # 3. Return results
            results = {
                "initial_balance": float(self.initial_balance),
                "final_balance": float(self.balance),
                "trades": self.trades,
                "equity_curve": self.equity_curve,
                "total_klines_processed": total_klines
            }

            logger.info(
                f"Backtest completed: "
                f"initial={self.initial_balance}, final={self.balance}, "
                f"trades={len(self.trades)}, roi={(self.balance - self.initial_balance) / self.initial_balance:.2%}"
            )

            return results

        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            raise

