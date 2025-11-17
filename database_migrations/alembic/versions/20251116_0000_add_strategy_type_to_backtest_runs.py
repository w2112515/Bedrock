"""add strategy_type to backtest_runs

Revision ID: 20251116_0000
Revises: 20251112_1400
Create Date: 2025-11-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251116_0000'
down_revision = '20251112_1400'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add strategy_type column to backtest_runs table.
    
    Three-step process to handle existing rows:
    1. Add column as nullable
    2. Update existing rows with default value
    3. Set column to NOT NULL with server_default
    """
    # Step 1: Add column (nullable)
    op.add_column(
        'backtest_runs',
        sa.Column('strategy_type', sa.String(length=20), nullable=True)
    )
    
    # Step 2: Update existing rows with default value
    op.execute(
        "UPDATE backtest_runs SET strategy_type = 'rules_only' WHERE strategy_type IS NULL"
    )
    
    # Step 3: Set NOT NULL constraint and server_default
    op.alter_column(
        'backtest_runs',
        'strategy_type',
        nullable=False,
        server_default='rules_only'
    )


def downgrade() -> None:
    """Remove strategy_type column from backtest_runs table."""
    op.drop_column('backtest_runs', 'strategy_type')

