"""
Data Collection Scheduler

Schedules periodic data collection tasks for K-lines and on-chain metrics.
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from shared.utils.logger import setup_logging
from shared.utils.database import get_db
from services.datahub.app.services.kline_service import KLineService
from services.datahub.app.services.onchain_service import OnChainService
from services.datahub.app.adapters.binance_adapter import BinanceAdapter
from services.datahub.app.adapters.bitquery_adapter import BitqueryAdapter

logger = setup_logging("data_collector_scheduler")


class DataCollectorScheduler:
    """
    Scheduler for periodic data collection tasks.
    
    Responsibilities:
    - Schedule K-line data collection at regular intervals
    - Schedule on-chain data collection at regular intervals
    - Handle task failures and retries
    - Log collection statistics
    """
    
    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.binance_adapter = BinanceAdapter()
        self.bitquery_adapter = BitqueryAdapter()
        
        # Configuration: symbols and intervals to collect
        self.kline_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        self.kline_intervals = ["1m", "5m", "15m", "1h", "4h", "1d"]
        
        self.onchain_symbols = ["BTC", "ETH", "BNB"]
        self.onchain_networks = {"BTC": "eth", "ETH": "eth", "BNB": "bsc"}
        
        logger.info("DataCollectorScheduler initialized")
    
    def start(self):
        """Start the scheduler and register all jobs."""
        logger.info("Starting data collection scheduler...")
        
        # Schedule K-line collection jobs
        self._schedule_kline_jobs()
        
        # Schedule on-chain collection jobs
        self._schedule_onchain_jobs()
        
        # Start the scheduler
        self.scheduler.start()
        logger.info("Data collection scheduler started successfully")
    
    def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping data collection scheduler...")
        self.scheduler.shutdown()
        logger.info("Data collection scheduler stopped")
    
    def _schedule_kline_jobs(self):
        """Schedule K-line data collection jobs."""
        # Collect 1-minute K-lines every minute
        self.scheduler.add_job(
            self._collect_klines_1m,
            trigger=IntervalTrigger(minutes=1),
            id="klines_1m_collection",
            name="Collect 1-minute K-lines",
            replace_existing=True
        )
        
        # Collect 5-minute K-lines every 5 minutes
        self.scheduler.add_job(
            self._collect_klines_5m,
            trigger=IntervalTrigger(minutes=5),
            id="klines_5m_collection",
            name="Collect 5-minute K-lines",
            replace_existing=True
        )
        
        # Collect hourly K-lines every hour
        self.scheduler.add_job(
            self._collect_klines_1h,
            trigger=CronTrigger(minute=0),
            id="klines_1h_collection",
            name="Collect hourly K-lines",
            replace_existing=True
        )
        
        # Collect daily K-lines at midnight
        self.scheduler.add_job(
            self._collect_klines_1d,
            trigger=CronTrigger(hour=0, minute=0),
            id="klines_1d_collection",
            name="Collect daily K-lines",
            replace_existing=True
        )
        
        logger.info("K-line collection jobs scheduled")
    
    def _schedule_onchain_jobs(self):
        """Schedule on-chain data collection jobs."""
        # Collect large transfers every 15 minutes
        self.scheduler.add_job(
            self._collect_large_transfers,
            trigger=IntervalTrigger(minutes=15),
            id="large_transfers_collection",
            name="Collect large transfers",
            replace_existing=True
        )
        
        # Collect smart money activity every 30 minutes
        self.scheduler.add_job(
            self._collect_smart_money,
            trigger=IntervalTrigger(minutes=30),
            id="smart_money_collection",
            name="Collect smart money activity",
            replace_existing=True
        )
        
        # Collect exchange netflow every hour
        self.scheduler.add_job(
            self._collect_exchange_netflow,
            trigger=CronTrigger(minute=0),
            id="exchange_netflow_collection",
            name="Collect exchange netflow",
            replace_existing=True
        )
        
        # Collect active addresses every hour
        self.scheduler.add_job(
            self._collect_active_addresses,
            trigger=CronTrigger(minute=30),
            id="active_addresses_collection",
            name="Collect active addresses",
            replace_existing=True
        )
        
        logger.info("On-chain collection jobs scheduled")
    
    async def _collect_klines_1m(self):
        """Collect 1-minute K-lines for all symbols."""
        await self._collect_klines_for_interval("1m", limit=10)
    
    async def _collect_klines_5m(self):
        """Collect 5-minute K-lines for all symbols."""
        await self._collect_klines_for_interval("5m", limit=10)
    
    async def _collect_klines_1h(self):
        """Collect hourly K-lines for all symbols."""
        await self._collect_klines_for_interval("1h", limit=24)
    
    async def _collect_klines_1d(self):
        """Collect daily K-lines for all symbols."""
        await self._collect_klines_for_interval("1d", limit=30)
    
    async def _collect_klines_for_interval(self, interval: str, limit: int):
        """
        Collect K-lines for a specific interval.
        
        Args:
            interval: K-line interval (e.g., "1m", "1h", "1d")
            limit: Number of K-lines to collect
        """
        logger.info(f"Starting K-line collection for interval: {interval}")
        
        db = next(get_db())
        service = KLineService(db, self.binance_adapter)
        
        success_count = 0
        error_count = 0
        
        for symbol in self.kline_symbols:
            try:
                result = service.collect_klines(
                    symbol=symbol,
                    interval=interval,
                    limit=limit
                )
                success_count += 1
                logger.info(
                    f"Collected K-lines for {symbol}/{interval}",
                    stored_count=result["stored_count"]
                )
            except Exception as e:
                error_count += 1
                logger.error(
                    f"Error collecting K-lines for {symbol}/{interval}",
                    error=str(e)
                )
        
        logger.info(
            f"K-line collection completed for interval: {interval}",
            success_count=success_count,
            error_count=error_count
        )
    
    async def _collect_large_transfers(self):
        """Collect large transfers for all symbols."""
        logger.info("Starting large transfers collection")
        
        db = next(get_db())
        service = OnChainService(db, self.bitquery_adapter)
        
        success_count = 0
        error_count = 0
        
        for symbol in self.onchain_symbols:
            try:
                network = self.onchain_networks[symbol]
                result = service.collect_large_transfers(
                    symbol=symbol,
                    network=network,
                    min_amount=100.0,
                    hours=1,
                    limit=50
                )
                success_count += 1
                logger.info(
                    f"Collected large transfers for {symbol}",
                    stored_count=result["stored_count"]
                )
            except Exception as e:
                error_count += 1
                logger.error(
                    f"Error collecting large transfers for {symbol}",
                    error=str(e)
                )
        
        logger.info(
            "Large transfers collection completed",
            success_count=success_count,
            error_count=error_count
        )
    
    async def _collect_smart_money(self):
        """Collect smart money activity for all symbols."""
        logger.info("Starting smart money collection")
        
        db = next(get_db())
        service = OnChainService(db, self.bitquery_adapter)
        
        success_count = 0
        error_count = 0
        
        for symbol in self.onchain_symbols:
            try:
                network = self.onchain_networks[symbol]
                result = service.collect_smart_money_activity(
                    symbol=symbol,
                    network=network,
                    hours=1,
                    limit=50
                )
                success_count += 1
                logger.info(
                    f"Collected smart money activity for {symbol}",
                    stored_count=result["stored_count"]
                )
            except Exception as e:
                error_count += 1
                logger.error(
                    f"Error collecting smart money activity for {symbol}",
                    error=str(e)
                )
        
        logger.info(
            "Smart money collection completed",
            success_count=success_count,
            error_count=error_count
        )
    
    async def _collect_exchange_netflow(self):
        """Collect exchange netflow for all symbols."""
        logger.info("Starting exchange netflow collection")
        
        db = next(get_db())
        service = OnChainService(db, self.bitquery_adapter)
        
        for symbol in self.onchain_symbols:
            try:
                network = self.onchain_networks[symbol]
                result = service.collect_exchange_netflow(
                    symbol=symbol,
                    network=network,
                    hours=1
                )
                logger.info(f"Collected exchange netflow for {symbol}")
            except Exception as e:
                logger.error(
                    f"Error collecting exchange netflow for {symbol}",
                    error=str(e)
                )
    
    async def _collect_active_addresses(self):
        """Collect active addresses for all symbols."""
        logger.info("Starting active addresses collection")
        
        db = next(get_db())
        service = OnChainService(db, self.bitquery_adapter)
        
        for symbol in self.onchain_symbols:
            try:
                network = self.onchain_networks[symbol]
                result = service.collect_active_addresses(
                    symbol=symbol,
                    network=network,
                    hours=1
                )
                logger.info(f"Collected active addresses for {symbol}")
            except Exception as e:
                logger.error(
                    f"Error collecting active addresses for {symbol}",
                    error=str(e)
                )

