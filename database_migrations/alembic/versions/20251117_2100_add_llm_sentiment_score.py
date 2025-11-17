"""add_llm_sentiment_score

Revision ID: 20251117_2100
Revises: 20251116_2000
Create Date: 2025-11-17 21:00:00.000000

Phase 2 - Task 3.7: LLM Sentiment Score Field
Adds llm_sentiment_score column to signals table for storing LLM sentiment converted to numerical score (0-100).

Description:
    This field stores the numerical score (0-100) converted from llm_sentiment.
    Conversion formula: base_score + (confidence - 50) * 0.2
    - BULLISH: base=90
    - NEUTRAL: base=50
    - BEARISH: base=10
    
    Historical data will be backfilled using default confidence=50.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20251117_2100'
down_revision: Union[str, None] = '20251116_2000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add llm_sentiment_score column
    op.add_column(
        'signals',
        sa.Column(
            'llm_sentiment_score',
            sa.Float(),
            nullable=True,
            comment='LLM sentiment converted to numerical score (0-100). '
                    'Calculated from llm_sentiment using convert_sentiment_to_score(). '
                    'Historical data uses default confidence=50.'
        )
    )
    
    # Add CHECK constraint (ensure score is in 0-100 range)
    op.create_check_constraint(
        'ck_signals_llm_sentiment_score_range',
        'signals',
        'llm_sentiment_score IS NULL OR (llm_sentiment_score >= 0 AND llm_sentiment_score <= 100)'
    )
    
    # Add index (optimize statistics query performance)
    op.create_index(
        'ix_signals_llm_sentiment_score',
        'signals',
        ['llm_sentiment_score'],
        unique=False
    )


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_signals_llm_sentiment_score', table_name='signals')
    
    # Drop CHECK constraint
    op.drop_constraint('ck_signals_llm_sentiment_score_range', 'signals', type_='check')
    
    # Drop column
    op.drop_column('signals', 'llm_sentiment_score')

