"""
Celery tasks for backtesting.

Implements asynchronous backtest execution.
"""

import sys
import os
from datetime import datetime
from decimal import Decimal
from uuid import UUID
import asyncio

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.backtesting.app.tasks.celery_app import celery_app
from services.backtesting.app.core.database import SessionLocal
from services.backtesting.app.models.backtest_run import BacktestRun
from services.backtesting.app.models.backtest_trade import BacktestTrade
from services.backtesting.app.models.backtest_metrics import BacktestMetrics
from services.backtesting.app.engines.backtest_engine import BacktestEngine
from services.backtesting.app.engines.metrics_calculator import MetricsCalculator

logger = setup_logging("backtest_tasks")


@celery_app.task(bind=True, name='services.backtesting.app.tasks.run_backtest_task')
def run_backtest_task(self, backtest_run_id: str):
    """
    Run backtest task asynchronously.
    
    Args:
        backtest_run_id: Backtest run ID (string UUID)
    
    Returns:
        Task result dictionary
    """
    db = SessionLocal()
    
    try:
        logger.info(f"Starting backtest task: backtest_run_id={backtest_run_id}")
        
        # 1. Load backtest run
        backtest_run = db.query(BacktestRun).filter(
            BacktestRun.id == UUID(backtest_run_id)
        ).first()
        
        if not backtest_run:
            raise ValueError(f"Backtest run not found: {backtest_run_id}")
        
        # 2. Update status to RUNNING
        backtest_run.status = "RUNNING"
        backtest_run.started_at = datetime.utcnow()
        backtest_run.progress = 0.0
        db.commit()
        
        logger.info(
            f"Backtest run loaded: "
            f"strategy={backtest_run.strategy_name}, "
            f"market={backtest_run.market}, "
            f"period={backtest_run.start_date} to {backtest_run.end_date}"
        )
        
        # 3. Initialize backtest engine
        from services.backtesting.app.core.config import settings

        engine = BacktestEngine(
            backtest_run_id=backtest_run.id,
            initial_balance=backtest_run.initial_balance,
            decision_engine_url=settings.DECISION_ENGINE_URL
        )
        
        # 4. Define progress callback
        async def update_progress(progress: float):
            """Update backtest progress."""
            backtest_run.progress = progress
            db.commit()
            logger.debug(f"Progress updated: {progress:.1%}")
        
        # 5. Run backtest (async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        results = loop.run_until_complete(
            engine.run(
                market=backtest_run.market,
                interval=backtest_run.interval,
                start_date=backtest_run.start_date,
                end_date=backtest_run.end_date,
                progress_callback=update_progress
            )
        )
        
        loop.close()
        
        logger.info(f"Backtest completed: {len(results['trades'])} trades executed")
        
        # 6. Save trades to database
        for trade_data in results['trades']:
            trade = BacktestTrade(**trade_data)
            db.add(trade)
        
        db.commit()
        
        logger.info(f"Saved {len(results['trades'])} trades to database")
        
        # 7. Calculate metrics
        metrics_calculator = MetricsCalculator()
        
        # Convert trades to dict format for metrics calculation
        trades_for_metrics = [
            {
                'trade_type': t['trade_type'],
                'realized_pnl': t['realized_pnl'],
                'commission': t['commission'],
                'slippage': t['slippage']
            }
            for t in results['trades']
        ]
        
        metrics = metrics_calculator.calculate_all_metrics(
            trades=trades_for_metrics,
            equity_curve=results['equity_curve'],
            initial_balance=float(backtest_run.initial_balance),
            final_balance=results['final_balance']
        )
        
        logger.info(f"Calculated metrics: ROI={metrics['roi']:.2%}, Sharpe={metrics.get('sharpe_ratio')}")
        
        # 8. Save metrics to database
        backtest_metrics = BacktestMetrics(
            backtest_run_id=backtest_run.id,
            **metrics
        )
        db.add(backtest_metrics)
        
        # 9. Update backtest run status
        backtest_run.final_balance = Decimal(str(results['final_balance']))
        backtest_run.status = "COMPLETED"
        backtest_run.completed_at = datetime.utcnow()
        backtest_run.progress = 1.0
        
        db.commit()
        
        logger.info(
            f"Backtest task completed successfully: "
            f"backtest_run_id={backtest_run_id}, "
            f"final_balance={results['final_balance']}, "
            f"roi={metrics['roi']:.2%}"
        )
        
        return {
            "status": "success",
            "backtest_run_id": backtest_run_id,
            "final_balance": results['final_balance'],
            "total_trades": len(results['trades']),
            "roi": metrics['roi']
        }
        
    except Exception as e:
        logger.error(f"Error in backtest task: {e}", exc_info=True)
        
        # Update backtest run status to FAILED
        try:
            backtest_run = db.query(BacktestRun).filter(
                BacktestRun.id == UUID(backtest_run_id)
            ).first()
            
            if backtest_run:
                backtest_run.status = "FAILED"
                backtest_run.error_message = str(e)
                backtest_run.completed_at = datetime.utcnow()
                db.commit()
        except Exception as update_error:
            logger.error(f"Error updating backtest run status: {update_error}")
        
        raise
        
    finally:
        db.close()

