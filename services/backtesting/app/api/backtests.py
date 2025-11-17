"""
Backtest API endpoints.

Implements:
- POST /v1/backtests - Create backtest
- GET /v1/backtests/{backtest_id} - Get backtest details
- GET /v1/backtests/{backtest_id}/trades - Get backtest trades
- GET /v1/backtests/{backtest_id}/metrics - Get backtest metrics
- GET /v1/backtests - List all backtests
- GET /v1/backtests/{backtest_id}/export - Export backtest report
"""

import sys
import os
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging
from services.backtesting.app.core.database import get_db
from services.backtesting.app.models.backtest_run import BacktestRun
from services.backtesting.app.models.backtest_trade import BacktestTrade
from services.backtesting.app.models.backtest_metrics import BacktestMetrics
from services.backtesting.app.schemas.backtest import (
    CreateBacktestRequest,
    BacktestRunResponse,
    BacktestListResponse
)
from services.backtesting.app.schemas.trade import BacktestTradeResponse
from services.backtesting.app.schemas.metrics import BacktestMetricsResponse
from services.backtesting.app.tasks.backtest_tasks import run_backtest_task
from services.backtesting.app.engines.report_generator import ReportGenerator

logger = setup_logging("backtests_api")

router = APIRouter()


@router.post("", response_model=BacktestRunResponse, status_code=201)
async def create_backtest(
    request: CreateBacktestRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new backtest task.
    
    Creates a backtest run record and submits it to Celery for async execution.
    
    Args:
        request: Backtest creation request
        db: Database session
    
    Returns:
        Created backtest run
    """
    try:
        logger.info(
            f"Creating backtest: "
            f"strategy={request.strategy_name}, "
            f"strategy_type={request.strategy_type}, "
            f"market={request.market}, "
            f"period={request.start_date} to {request.end_date}"
        )

        # Validate date range
        if request.end_date <= request.start_date:
            raise HTTPException(
                status_code=400,
                detail="end_date must be after start_date"
            )

        # Create backtest run record
        backtest_run = BacktestRun(
            id=uuid4(),
            strategy_name=request.strategy_name,
            strategy_type=request.strategy_type,
            market=request.market,
            interval=request.interval,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_balance=request.initial_balance,
            status="PENDING",
            progress=0.0
        )
        
        db.add(backtest_run)
        db.commit()
        db.refresh(backtest_run)
        
        logger.info(f"Backtest run created: id={backtest_run.id}")
        
        # Submit to Celery
        task = run_backtest_task.delay(str(backtest_run.id))
        
        logger.info(f"Backtest task submitted: task_id={task.id}, backtest_run_id={backtest_run.id}")
        
        return backtest_run
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating backtest: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{backtest_id}", response_model=BacktestRunResponse)
async def get_backtest(
    backtest_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get backtest run details.
    
    Args:
        backtest_id: Backtest run ID
        db: Database session
    
    Returns:
        Backtest run details
    """
    try:
        backtest_run = db.query(BacktestRun).filter(
            BacktestRun.id == backtest_id
        ).first()
        
        if not backtest_run:
            raise HTTPException(status_code=404, detail="Backtest not found")
        
        return backtest_run
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{backtest_id}/trades", response_model=List[BacktestTradeResponse])
async def get_backtest_trades(
    backtest_id: UUID,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get backtest trades.
    
    Args:
        backtest_id: Backtest run ID
        limit: Maximum number of trades to return
        offset: Number of trades to skip
        db: Database session
    
    Returns:
        List of backtest trades
    """
    try:
        # Check if backtest exists
        backtest_run = db.query(BacktestRun).filter(
            BacktestRun.id == backtest_id
        ).first()
        
        if not backtest_run:
            raise HTTPException(status_code=404, detail="Backtest not found")
        
        # Get trades
        trades = db.query(BacktestTrade).filter(
            BacktestTrade.backtest_run_id == backtest_id
        ).order_by(
            BacktestTrade.timestamp
        ).limit(limit).offset(offset).all()
        
        return trades
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting backtest trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{backtest_id}/metrics", response_model=BacktestMetricsResponse)
async def get_backtest_metrics(
    backtest_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get backtest performance metrics.
    
    Args:
        backtest_id: Backtest run ID
        db: Database session
    
    Returns:
        Backtest metrics
    """
    try:
        # Check if backtest exists
        backtest_run = db.query(BacktestRun).filter(
            BacktestRun.id == backtest_id
        ).first()
        
        if not backtest_run:
            raise HTTPException(status_code=404, detail="Backtest not found")
        
        # Get metrics
        metrics = db.query(BacktestMetrics).filter(
            BacktestMetrics.backtest_run_id == backtest_id
        ).first()
        
        if not metrics:
            raise HTTPException(
                status_code=404,
                detail="Metrics not found. Backtest may not be completed yet."
            )
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting backtest metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=BacktestListResponse)
async def list_backtests(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    market: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    List all backtests with pagination.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        status: Filter by status (optional)
        market: Filter by market (optional)
        db: Database session
    
    Returns:
        Paginated list of backtests
    """
    try:
        # Build query
        query = db.query(BacktestRun)
        
        if status:
            query = query.filter(BacktestRun.status == status)
        
        if market:
            query = query.filter(BacktestRun.market == market)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        offset = (page - 1) * page_size
        backtests = query.order_by(
            BacktestRun.created_at.desc()
        ).limit(page_size).offset(offset).all()
        
        return BacktestListResponse(
            backtests=backtests,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing backtests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{backtest_id}/export")
async def export_backtest_report(
    backtest_id: UUID,
    format: str = Query(default="json", regex="^(json|csv)$"),
    db: Session = Depends(get_db)
):
    """
    Export backtest report in specified format.
    
    Args:
        backtest_id: Backtest run ID
        format: Export format (json or csv)
        db: Database session
    
    Returns:
        Report file
    """
    try:
        # Get backtest run
        backtest_run = db.query(BacktestRun).filter(
            BacktestRun.id == backtest_id
        ).first()
        
        if not backtest_run:
            raise HTTPException(status_code=404, detail="Backtest not found")
        
        if backtest_run.status != "COMPLETED":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot export report for backtest with status: {backtest_run.status}"
            )
        
        # Get trades
        trades = db.query(BacktestTrade).filter(
            BacktestTrade.backtest_run_id == backtest_id
        ).order_by(BacktestTrade.timestamp).all()
        
        # Get metrics
        metrics = db.query(BacktestMetrics).filter(
            BacktestMetrics.backtest_run_id == backtest_id
        ).first()
        
        if not metrics:
            raise HTTPException(status_code=404, detail="Metrics not found")
        
        # Convert to dict
        backtest_dict = {
            'id': backtest_run.id,
            'strategy_name': backtest_run.strategy_name,
            'market': backtest_run.market,
            'interval': backtest_run.interval,
            'start_date': backtest_run.start_date,
            'end_date': backtest_run.end_date,
            'initial_balance': backtest_run.initial_balance,
            'final_balance': backtest_run.final_balance,
            'status': backtest_run.status,
            'created_at': backtest_run.created_at,
            'completed_at': backtest_run.completed_at
        }
        
        trades_dict = [
            {
                'id': t.id,
                'trade_type': t.trade_type,
                'quantity': t.quantity,
                'price': t.price,
                'timestamp': t.timestamp,
                'commission': t.commission,
                'slippage': t.slippage,
                'realized_pnl': t.realized_pnl
            }
            for t in trades
        ]
        
        metrics_dict = {
            'total_trades': metrics.total_trades,
            'winning_trades': metrics.winning_trades,
            'losing_trades': metrics.losing_trades,
            'win_rate': metrics.win_rate,
            'avg_win': metrics.avg_win,
            'avg_loss': metrics.avg_loss,
            'profit_factor': metrics.profit_factor,
            'max_drawdown': metrics.max_drawdown,
            'sharpe_ratio': metrics.sharpe_ratio,
            'calmar_ratio': metrics.calmar_ratio,
            'sortino_ratio': metrics.sortino_ratio,
            'omega_ratio': metrics.omega_ratio,
            'total_commission': metrics.total_commission,
            'total_slippage': metrics.total_slippage,
            'roi': metrics.roi
        }
        
        # Generate report
        report_generator = ReportGenerator()
        
        if format == "json":
            content = report_generator.generate_json_report(
                backtest_dict, trades_dict, metrics_dict
            )
            media_type = "application/json"
            filename = f"backtest_{backtest_id}_report.json"
        else:  # csv
            content = report_generator.generate_csv_report(
                backtest_dict, trades_dict, metrics_dict
            )
            media_type = "text/csv"
            filename = f"backtest_{backtest_id}_report.csv"
        
        logger.info(f"Generated {format} report for backtest {backtest_id}")
        
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting backtest report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

