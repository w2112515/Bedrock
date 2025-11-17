"""
ReportGenerator - Generates backtest reports in various formats.

Supports:
- JSON format
- CSV format
- (PDF format - Phase 2)
"""

import sys
import os
import json
import csv
from typing import Dict, Any, List
from io import StringIO
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging

logger = setup_logging("report_generator")


class ReportGenerator:
    """
    Backtest report generator.
    
    Generates comprehensive reports in multiple formats.
    """
    
    def __init__(self):
        """Initialize ReportGenerator."""
        logger.info("ReportGenerator initialized")

    def _get_attr(self, obj, attr, default=None):
        """Get attribute from object or dict."""
        if isinstance(obj, dict):
            return obj.get(attr, default)
        else:
            return getattr(obj, attr, default)

    def generate_json_report(
        self,
        backtest_run: Dict[str, Any],
        trades: List[Dict[str, Any]],
        metrics: Dict[str, Any]
    ) -> str:
        """
        Generate JSON format report.
        
        Args:
            backtest_run: Backtest run data
            trades: List of trades
            metrics: Performance metrics
        
        Returns:
            JSON string
        """
        try:
            start_date = self._get_attr(backtest_run, 'start_date')
            end_date = self._get_attr(backtest_run, 'end_date')
            created_at = self._get_attr(backtest_run, 'created_at')
            completed_at = self._get_attr(backtest_run, 'completed_at')

            report = {
                "backtest_run": {
                    "id": str(self._get_attr(backtest_run, 'id')),
                    "strategy_name": self._get_attr(backtest_run, 'strategy_name'),
                    "market": self._get_attr(backtest_run, 'market'),
                    "interval": self._get_attr(backtest_run, 'interval'),
                    "start_date": start_date.isoformat() if hasattr(start_date, 'isoformat') else str(start_date) if start_date else None,
                    "end_date": end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date) if end_date else None,
                    "initial_balance": float(self._get_attr(backtest_run, 'initial_balance')),
                    "final_balance": float(self._get_attr(backtest_run, 'final_balance', 0.0)),
                    "status": self._get_attr(backtest_run, 'status'),
                    "created_at": created_at.isoformat() if hasattr(created_at, 'isoformat') else str(created_at) if created_at else None,
                    "completed_at": completed_at.isoformat() if hasattr(completed_at, 'isoformat') else str(completed_at) if completed_at else None
                },
                "metrics": {
                    "total_trades": self._get_attr(metrics, 'total_trades', 0),
                    "winning_trades": self._get_attr(metrics, 'winning_trades', 0),
                    "losing_trades": self._get_attr(metrics, 'losing_trades', 0),
                    "win_rate": str(self._get_attr(metrics, 'win_rate', 0.0)),
                    "avg_win": float(self._get_attr(metrics, 'avg_win', 0.0)),
                    "avg_loss": float(self._get_attr(metrics, 'avg_loss', 0.0)),
                    "profit_factor": float(self._get_attr(metrics, 'profit_factor', 0.0)),
                    "max_drawdown": float(self._get_attr(metrics, 'max_drawdown', 0.0)),
                    "sharpe_ratio": float(self._get_attr(metrics, 'sharpe_ratio', 0.0)),
                    "calmar_ratio": float(self._get_attr(metrics, 'calmar_ratio', 0.0)),
                    "sortino_ratio": float(self._get_attr(metrics, 'sortino_ratio', 0.0)),
                    "omega_ratio": float(self._get_attr(metrics, 'omega_ratio', 0.0)),
                    "total_commission": float(self._get_attr(metrics, 'total_commission', 0.0)),
                    "total_slippage": float(self._get_attr(metrics, 'total_slippage', 0.0)),
                    "roi": float(self._get_attr(metrics, 'roi', 0.0))
                },
                "trades": [
                    {
                        "id": str(self._get_attr(trade, 'id')),
                        "trade_type": self._get_attr(trade, 'trade_type'),
                        "quantity": float(self._get_attr(trade, 'quantity')),
                        "price": float(self._get_attr(trade, 'price')),
                        "timestamp": self._get_attr(trade, 'timestamp').isoformat() if hasattr(self._get_attr(trade, 'timestamp'), 'isoformat') else str(self._get_attr(trade, 'timestamp')) if self._get_attr(trade, 'timestamp') else None,
                        "commission": float(self._get_attr(trade, 'commission')),
                        "slippage": float(self._get_attr(trade, 'slippage')),
                        "realized_pnl": float(self._get_attr(trade, 'realized_pnl')) if self._get_attr(trade, 'realized_pnl') is not None else None
                    }
                    for trade in trades
                ],
                "summary": {
                    "total_trades": len([t for t in trades if self._get_attr(t, 'trade_type') == 'EXIT']),
                    "roi": float(self._get_attr(metrics, 'roi', 0.0)),
                    "sharpe_ratio": float(self._get_attr(metrics, 'sharpe_ratio', 0.0)),
                    "max_drawdown": float(self._get_attr(metrics, 'max_drawdown', 0.0)),
                    "win_rate": float(self._get_attr(metrics, 'win_rate', 0.0))
                },
                "generated_at": datetime.utcnow().isoformat()
            }
            
            json_str = json.dumps(report, indent=2, default=str)
            
            logger.info(f"Generated JSON report: {len(json_str)} bytes")
            
            return json_str
            
        except Exception as e:
            logger.error(f"Error generating JSON report: {e}")
            raise
    
    def generate_csv_report(
        self,
        backtest_run: Dict[str, Any],
        trades: List[Dict[str, Any]],
        metrics: Dict[str, Any]
    ) -> str:
        """
        Generate CSV format report (trades only).
        
        Args:
            backtest_run: Backtest run data
            trades: List of trades
            metrics: Performance metrics
        
        Returns:
            CSV string
        """
        try:
            output = StringIO()
            
            # Write header
            output.write(f"# Backtest Report\n")
            output.write(f"# Strategy: {self._get_attr(backtest_run, 'strategy_name')}\n")
            output.write(f"# Market: {self._get_attr(backtest_run, 'market')}\n")
            output.write(f"# Period: {self._get_attr(backtest_run, 'start_date')} to {self._get_attr(backtest_run, 'end_date')}\n")
            output.write(f"# Initial Balance: {self._get_attr(backtest_run, 'initial_balance')}\n")
            output.write(f"# Final Balance: {self._get_attr(backtest_run, 'final_balance')}\n")
            output.write(f"# ROI: {float(self._get_attr(metrics, 'roi', 0.0)):.2%}\n")
            output.write(f"# Sharpe Ratio: {float(self._get_attr(metrics, 'sharpe_ratio', 0.0))}\n")
            output.write(f"# Max Drawdown: {float(self._get_attr(metrics, 'max_drawdown', 0.0)):.2%}\n")
            output.write(f"# Win Rate: {float(self._get_attr(metrics, 'win_rate', 0.0)):.2%}\n")
            output.write(f"#\n")

            # Write trades CSV
            fieldnames = [
                'timestamp',
                'trade_type',
                'quantity',
                'price',
                'commission',
                'slippage',
                'realized_pnl'
            ]

            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

            for trade in trades:
                timestamp = self._get_attr(trade, 'timestamp')
                writer.writerow({
                    'timestamp': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp) if timestamp else '',
                    'trade_type': self._get_attr(trade, 'trade_type'),
                    'quantity': float(self._get_attr(trade, 'quantity')),
                    'price': float(self._get_attr(trade, 'price')),
                    'commission': float(self._get_attr(trade, 'commission')),
                    'slippage': float(self._get_attr(trade, 'slippage')),
                    'realized_pnl': float(self._get_attr(trade, 'realized_pnl')) if self._get_attr(trade, 'realized_pnl') is not None else ''
                })
            
            csv_str = output.getvalue()
            output.close()
            
            logger.info(f"Generated CSV report: {len(csv_str)} bytes")
            
            return csv_str
            
        except Exception as e:
            logger.error(f"Error generating CSV report: {e}")
            raise
    
    def generate_summary(
        self,
        backtest_run: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate summary statistics.
        
        Args:
            backtest_run: Backtest run data
            metrics: Performance metrics
        
        Returns:
            Summary dictionary
        """
        try:
            initial_balance = float(backtest_run.get('initial_balance', 0))
            final_balance = float(backtest_run.get('final_balance', 0))
            
            summary = {
                "backtest_id": str(backtest_run.get('id')),
                "strategy_name": backtest_run.get('strategy_name'),
                "market": backtest_run.get('market'),
                "period": {
                    "start": backtest_run.get('start_date').isoformat() if backtest_run.get('start_date') else None,
                    "end": backtest_run.get('end_date').isoformat() if backtest_run.get('end_date') else None
                },
                "balance": {
                    "initial": initial_balance,
                    "final": final_balance,
                    "change": final_balance - initial_balance,
                    "change_percent": ((final_balance - initial_balance) / initial_balance * 100) if initial_balance > 0 else 0
                },
                "performance": {
                    "roi": metrics.get('roi'),
                    "total_trades": metrics.get('total_trades'),
                    "win_rate": metrics.get('win_rate'),
                    "profit_factor": metrics.get('profit_factor')
                },
                "risk_metrics": {
                    "max_drawdown": metrics.get('max_drawdown'),
                    "sharpe_ratio": metrics.get('sharpe_ratio'),
                    "sortino_ratio": metrics.get('sortino_ratio'),
                    "calmar_ratio": metrics.get('calmar_ratio')
                },
                "costs": {
                    "total_commission": metrics.get('total_commission'),
                    "total_slippage": metrics.get('total_slippage')
                }
            }
            
            logger.info(f"Generated summary for backtest {backtest_run.get('id')}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            raise

