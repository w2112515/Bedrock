"""create backtesting tables

Revision ID: 20251111_0000
Revises: 20251110_2100
Create Date: 2025-11-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251111_0000'
down_revision: Union[str, None] = '20251110_2100'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create backtest_runs table
    op.create_table(
        'backtest_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_name', sa.String(length=100), nullable=False),
        sa.Column('market', sa.String(length=50), nullable=False),
        sa.Column('interval', sa.String(length=10), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('initial_balance', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('final_balance', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('progress', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backtest_runs_id'), 'backtest_runs', ['id'], unique=False)
    op.create_index(op.f('ix_backtest_runs_market'), 'backtest_runs', ['market'], unique=False)
    op.create_index(op.f('ix_backtest_runs_status'), 'backtest_runs', ['status'], unique=False)
    
    # Create backtest_trades table
    op.create_table(
        'backtest_trades',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('backtest_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('market', sa.String(length=50), nullable=False),
        sa.Column('signal_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('trade_type', sa.String(length=10), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('price', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('commission', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('slippage', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('realized_pnl', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['backtest_run_id'], ['backtest_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backtest_trades_id'), 'backtest_trades', ['id'], unique=False)
    op.create_index(op.f('ix_backtest_trades_backtest_run_id'), 'backtest_trades', ['backtest_run_id'], unique=False)
    op.create_index(op.f('ix_backtest_trades_timestamp'), 'backtest_trades', ['timestamp'], unique=False)
    
    # Create backtest_metrics table
    op.create_table(
        'backtest_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('backtest_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('total_trades', sa.Integer(), nullable=False),
        sa.Column('winning_trades', sa.Integer(), nullable=False),
        sa.Column('losing_trades', sa.Integer(), nullable=False),
        sa.Column('win_rate', sa.Float(), nullable=False),
        sa.Column('avg_win', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('avg_loss', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('profit_factor', sa.Float(), nullable=False),
        sa.Column('max_drawdown', sa.Float(), nullable=False),
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('calmar_ratio', sa.Float(), nullable=True),
        sa.Column('sortino_ratio', sa.Float(), nullable=True),
        sa.Column('omega_ratio', sa.Float(), nullable=True),
        sa.Column('total_commission', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('total_slippage', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('roi', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['backtest_run_id'], ['backtest_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('backtest_run_id')
    )
    op.create_index(op.f('ix_backtest_metrics_id'), 'backtest_metrics', ['id'], unique=False)
    op.create_index(op.f('ix_backtest_metrics_backtest_run_id'), 'backtest_metrics', ['backtest_run_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_backtest_metrics_backtest_run_id'), table_name='backtest_metrics')
    op.drop_index(op.f('ix_backtest_metrics_id'), table_name='backtest_metrics')
    op.drop_table('backtest_metrics')
    
    op.drop_index(op.f('ix_backtest_trades_timestamp'), table_name='backtest_trades')
    op.drop_index(op.f('ix_backtest_trades_backtest_run_id'), table_name='backtest_trades')
    op.drop_index(op.f('ix_backtest_trades_id'), table_name='backtest_trades')
    op.drop_table('backtest_trades')
    
    op.drop_index(op.f('ix_backtest_runs_status'), table_name='backtest_runs')
    op.drop_index(op.f('ix_backtest_runs_market'), table_name='backtest_runs')
    op.drop_index(op.f('ix_backtest_runs_id'), table_name='backtest_runs')
    op.drop_table('backtest_runs')

