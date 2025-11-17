"""
Signal Generation Scheduler

Periodically triggers signal generation using APScheduler.

Phase 2: Integrated with ML adapter for confidence scoring.
"""

import sys
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.decision_engine.app.core.config import settings
from services.decision_engine.app.core.database import SessionLocal
from services.decision_engine.app.engines.rule_engine import RuleEngine
from services.decision_engine.app.events.publisher import event_publisher
from services.decision_engine.app.adapters.xgboost_adapter import XGBoostAdapter
from services.decision_engine.app.adapters.llm_factory import LLMAdapterFactory

logger = setup_logging("scheduler")


class SignalScheduler:
    """
    Scheduler for periodic signal generation.

    Responsibilities:
    1. Start/stop APScheduler
    2. Schedule periodic signal generation job
    3. Handle job execution and errors
    4. (Phase 2) Initialize ML adapter for RuleEngine
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

        # Initialize ML adapter (Phase 2)
        ml_adapter = None
        if settings.ML_ENABLED:
            try:
                ml_adapter = XGBoostAdapter(
                    model_path=settings.ML_MODEL_PATH,
                    fallback_score=settings.ML_FALLBACK_SCORE,
                    feature_names_path=settings.ML_FEATURE_NAMES_PATH  # 支持动态指定特征名称文件
                )
                if ml_adapter.is_loaded():
                    logger.info(f"ML adapter initialized successfully (version: {settings.ML_MODEL_VERSION})")
                else:
                    logger.warning("ML adapter initialized but model not loaded")
            except Exception as e:
                logger.warning(f"Failed to initialize ML adapter: {e}")
                ml_adapter = None
        else:
            logger.info("ML adapter disabled (ML_ENABLED=False)")

        # Initialize LLM adapter (Phase 2)
        llm_adapter = None
        if settings.LLM_ENABLED:
            try:
                llm_adapter = LLMAdapterFactory.create_adapter()
                if llm_adapter and llm_adapter.is_available():
                    logger.info(f"LLM adapter initialized successfully (provider: {settings.LLM_PROVIDER})")
                else:
                    logger.warning("LLM adapter initialized but not available")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM adapter: {e}")
                llm_adapter = None
        else:
            logger.info("LLM adapter disabled (LLM_ENABLED=False)")

        # Initialize RuleEngine with ML, LLM adapters, and event publisher
        self.rule_engine = RuleEngine(
            ml_adapter=ml_adapter,
            llm_adapter=llm_adapter,
            event_publisher=event_publisher
        )
        self.interval_minutes = settings.SIGNAL_GENERATION_INTERVAL_MINUTES
        
    def start(self):
        """
        Start the scheduler.
        
        Adds the signal generation job with interval trigger.
        """
        try:
            # Add signal generation job
            self.scheduler.add_job(
                func=self._generate_signals_job,
                trigger=IntervalTrigger(minutes=self.interval_minutes),
                id="signal_generation",
                name="Periodic Signal Generation",
                replace_existing=True,
                max_instances=1  # Prevent concurrent executions
            )
            
            # Start scheduler
            self.scheduler.start()
            
            logger.info(
                f"Scheduler started: signal generation every {self.interval_minutes} minutes"
            )
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    def stop(self):
        """Stop the scheduler."""
        try:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    async def _generate_signals_job(self):
        """
        Scheduled job for signal generation.

        Workflow:
        1. Get configured trading symbols
        2. Call RuleEngine to analyze markets (events published inside RuleEngine)
        3. Log results
        """
        logger.info("Starting scheduled signal generation")
        
        db = SessionLocal()
        
        try:
            # Get trading symbols from config
            symbols = settings.TRADING_SYMBOLS
            
            if not symbols:
                logger.warning("No trading symbols configured, skipping signal generation")
                return
            
            logger.info(f"Analyzing {len(symbols)} symbols: {symbols}")
            
            # Generate signals (events are published inside RuleEngine)
            signals = await self.rule_engine.analyze(
                symbols=symbols,
                db=db,
                interval="1h"
            )

            # Count APPROVED vs REJECTED signals
            approved_count = sum(1 for s in signals if s.final_decision == "APPROVED")
            rejected_count = sum(1 for s in signals if s.final_decision == "REJECTED")

            logger.info(
                f"Signal generation completed: "
                f"{len(signals)} total signals ({approved_count} approved, {rejected_count} rejected)"
            )
            
        except Exception as e:
            logger.error(f"Error in scheduled signal generation: {e}")
            
        finally:
            db.close()
    
    async def trigger_manual_generation(self):
        """
        Manually trigger signal generation.
        
        Can be called from API endpoint for on-demand generation.
        """
        logger.info("Manual signal generation triggered")
        await self._generate_signals_job()


# Global scheduler instance
signal_scheduler = SignalScheduler()

