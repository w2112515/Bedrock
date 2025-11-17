"""decision_engine_add_funding_rate_fields

Revision ID: 20251116_2000
Revises: 20251116_0000
Create Date: 2025-11-16 20:00:00.000000

Phase 2 - Task Package B: Funding Rate Strategy
Adds funding_rate and funding_rate_signal columns to signals table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251116_2000'
down_revision: Union[str, None] = '20251116_0000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add funding_rate column to signals table
    op.add_column(
        'signals',
        sa.Column(
            'funding_rate',
            sa.DECIMAL(precision=10, scale=8),
            nullable=True,
            comment='Current funding rate from Binance Futures, Phase 2'
        )
    )
    
    # Add funding_rate_signal column to signals table
    op.add_column(
        'signals',
        sa.Column(
            'funding_rate_signal',
            sa.String(length=20),
            nullable=True,
            comment='Funding rate signal: LONG/SHORT/NEUTRAL, Phase 2'
        )
    )
    
    # Add CHECK constraint to ensure funding_rate_signal is valid
    op.create_check_constraint(
        'check_funding_rate_signal_valid',
        'signals',
        "funding_rate_signal IN ('LONG', 'SHORT', 'NEUTRAL') OR funding_rate_signal IS NULL"
    )


def downgrade() -> None:
    # Drop CHECK constraint
    op.drop_constraint('check_funding_rate_signal_valid', 'signals', type_='check')
    
    # Drop funding_rate_signal column
    op.drop_column('signals', 'funding_rate_signal')
    
    # Drop funding_rate column
    op.drop_column('signals', 'funding_rate')

