"""create portfolio tables

Revision ID: 20251110_2100
Revises: ab79d1c7c055
Create Date: 2025-11-10 21:00:00.000000

Creates tables for Portfolio Service:
- positions: Trading positions
- trades: Trade executions
- account: Account balance
- failed_signal_events: Failed event retry mechanism
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251110_2100'
down_revision = 'ab79d1c7c055'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # Create account table
    # ============================================
    op.create_table(
        'account',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('balance', sa.DECIMAL(precision=18, scale=2), nullable=False, comment='Total account balance (including frozen balance)'),
        sa.Column('available_balance', sa.DECIMAL(precision=18, scale=2), nullable=False, comment='Available balance for new positions'),
        sa.Column('frozen_balance', sa.DECIMAL(precision=18, scale=2), nullable=False, server_default='0', comment='Frozen balance (locked in open positions)'),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='Last update timestamp'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_account_id'), 'account', ['id'], unique=False)
    
    # ============================================
    # Create positions table
    # ============================================
    op.create_table(
        'positions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('market', sa.String(length=50), nullable=False, comment='Trading pair, e.g., BTC/USDT'),
        sa.Column('signal_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Associated signal ID'),
        sa.Column('position_size', sa.DECIMAL(precision=18, scale=8), nullable=False, comment='Position size (quantity of base asset)'),
        sa.Column('entry_price', sa.DECIMAL(precision=18, scale=8), nullable=False, comment='Actual entry price'),
        sa.Column('current_price', sa.DECIMAL(precision=18, scale=8), nullable=False, comment='Current market price (updated periodically or on close)'),
        sa.Column('stop_loss_price', sa.DECIMAL(precision=18, scale=8), nullable=False, comment='Stop loss price'),
        sa.Column('profit_target_price', sa.DECIMAL(precision=18, scale=8), nullable=False, comment='Profit target price'),
        sa.Column('position_weight_used', sa.DECIMAL(precision=5, scale=4), nullable=False, comment='Actual position weight used (0.0000-1.0000), from signal suggestion or default calculation'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='Position status: OPEN, CLOSED, PENDING'),
        sa.Column('unrealized_pnl', sa.DECIMAL(precision=18, scale=8), nullable=True, comment='Unrealized profit/loss (for OPEN positions)'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='Position open timestamp'),
        sa.Column('closed_at', sa.TIMESTAMP(), nullable=True, comment='Position close timestamp'),
        sa.Column('exit_reason', sa.String(length=50), nullable=True, comment='Exit reason: PROFIT_TARGET_HIT, STOP_LOSS_HIT, TRAILING_STOP_HIT, MANUAL_CLOSE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_positions_id'), 'positions', ['id'], unique=False)
    op.create_index(op.f('ix_positions_market'), 'positions', ['market'], unique=False)
    op.create_index(op.f('ix_positions_status'), 'positions', ['status'], unique=False)
    op.create_index(op.f('ix_positions_created_at'), 'positions', ['created_at'], unique=False)
    op.create_index('idx_position_market_status', 'positions', ['market', 'status'], unique=False)
    op.create_index('idx_position_signal_id', 'positions', ['signal_id'], unique=False)
    
    # ============================================
    # Create trades table
    # ============================================
    op.create_table(
        'trades',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('position_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Associated position ID'),
        sa.Column('trade_type', sa.String(length=20), nullable=False, comment='Trade type: ENTRY, EXIT'),
        sa.Column('market', sa.String(length=50), nullable=False, comment='Trading pair, e.g., BTC/USDT'),
        sa.Column('quantity', sa.DECIMAL(precision=18, scale=8), nullable=False, comment='Trade quantity (amount of base asset)'),
        sa.Column('price', sa.DECIMAL(precision=18, scale=8), nullable=False, comment='Execution price'),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='Trade execution timestamp'),
        sa.Column('commission', sa.DECIMAL(precision=18, scale=8), nullable=False, server_default='0', comment='Trading commission/fee'),
        sa.Column('realized_pnl', sa.DECIMAL(precision=18, scale=8), nullable=True, comment='Realized profit/loss (only for EXIT trades)'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trades_id'), 'trades', ['id'], unique=False)
    op.create_index(op.f('ix_trades_timestamp'), 'trades', ['timestamp'], unique=False)
    op.create_index('idx_trade_position_id', 'trades', ['position_id'], unique=False)
    op.create_index('idx_trade_type', 'trades', ['trade_type'], unique=False)
    
    # ============================================
    # Create failed_signal_events table
    # ============================================
    op.create_table(
        'failed_signal_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('signal_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Signal ID from the failed event'),
        sa.Column('event_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Complete event payload in JSON format'),
        sa.Column('error_message', sa.Text(), nullable=False, comment='Error message from failed processing'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0', comment='Number of retry attempts'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='Status: PENDING, RETRYING, FAILED, RESOLVED'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='Event failure timestamp'),
        sa.Column('last_retry_at', sa.TIMESTAMP(), nullable=True, comment='Last retry attempt timestamp'),
        sa.Column('resolved_at', sa.TIMESTAMP(), nullable=True, comment='Event resolution timestamp'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_failed_signal_events_id'), 'failed_signal_events', ['id'], unique=False)
    op.create_index(op.f('ix_failed_signal_events_created_at'), 'failed_signal_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_failed_signal_events_status'), 'failed_signal_events', ['status'], unique=False)
    op.create_index('idx_failed_event_signal_id', 'failed_signal_events', ['signal_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('idx_failed_event_signal_id', table_name='failed_signal_events')
    op.drop_index(op.f('ix_failed_signal_events_status'), table_name='failed_signal_events')
    op.drop_index(op.f('ix_failed_signal_events_created_at'), table_name='failed_signal_events')
    op.drop_index(op.f('ix_failed_signal_events_id'), table_name='failed_signal_events')
    op.drop_table('failed_signal_events')
    
    op.drop_index('idx_trade_type', table_name='trades')
    op.drop_index('idx_trade_position_id', table_name='trades')
    op.drop_index(op.f('ix_trades_timestamp'), table_name='trades')
    op.drop_index(op.f('ix_trades_id'), table_name='trades')
    op.drop_table('trades')
    
    op.drop_index('idx_position_signal_id', table_name='positions')
    op.drop_index('idx_position_market_status', table_name='positions')
    op.drop_index(op.f('ix_positions_created_at'), table_name='positions')
    op.drop_index(op.f('ix_positions_status'), table_name='positions')
    op.drop_index(op.f('ix_positions_market'), table_name='positions')
    op.drop_index(op.f('ix_positions_id'), table_name='positions')
    op.drop_table('positions')
    
    op.drop_index(op.f('ix_account_id'), table_name='account')
    op.drop_table('account')

