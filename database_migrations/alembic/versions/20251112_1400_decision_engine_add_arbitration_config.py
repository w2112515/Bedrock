"""decision_engine_add_arbitration_config

Revision ID: 20251112_1400
Revises: 20251111_0000
Create Date: 2025-11-12 14:00:00.000000

Phase 2 - Task 2.3: Decision Arbitration
Creates arbitration_config table for storing arbitration weights and thresholds.
Adds rejection_reason column and final_decision index to signals table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251112_1400'
down_revision: Union[str, None] = '20251111_0000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create arbitration_config table
    op.create_table(
        'arbitration_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, comment='Configuration version number, increments with each update'),
        sa.Column('rule_weight', sa.DECIMAL(precision=5, scale=4), nullable=False, comment='Weight for rule engine score (0.0000-1.0000)'),
        sa.Column('ml_weight', sa.DECIMAL(precision=5, scale=4), nullable=False, comment='Weight for ML confidence score (0.0000-1.0000)'),
        sa.Column('llm_weight', sa.DECIMAL(precision=5, scale=4), nullable=False, comment='Weight for LLM sentiment score (0.0000-1.0000)'),
        sa.Column('min_approval_score', sa.DECIMAL(precision=5, scale=2), nullable=False, comment='Minimum weighted score for APPROVED decision (0.00-100.00)'),
        sa.Column('adaptive_threshold_enabled', sa.Boolean(), nullable=False, server_default='false', comment='Enable adaptive threshold based on market volatility (Phase 3)'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false', comment='Whether this config is currently active (only one can be active)'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('now()'), comment='Configuration creation timestamp'),
        sa.CheckConstraint('ABS((rule_weight + ml_weight + llm_weight) - 1.0) < 0.0001', name='check_weights_sum_to_one'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for arbitration_config
    op.create_index(op.f('ix_arbitration_config_id'), 'arbitration_config', ['id'], unique=False)
    op.create_index('idx_arbitration_config_version', 'arbitration_config', ['version'], unique=False)
    op.create_index('idx_arbitration_config_active_unique', 'arbitration_config', ['is_active'], unique=True, postgresql_where=sa.text('is_active = true'))
    
    # Add rejection_reason column to signals table
    op.add_column('signals', sa.Column('rejection_reason', sa.Text(), nullable=True, comment='Reason for rejection if final_decision is REJECTED, Phase 2'))
    
    # Add index for final_decision column in signals table
    op.create_index('idx_signal_final_decision', 'signals', ['final_decision'], unique=False)
    
    # Insert default arbitration config (version 1)
    op.execute("""
        INSERT INTO arbitration_config (id, version, rule_weight, ml_weight, llm_weight, min_approval_score, adaptive_threshold_enabled, is_active, created_at)
        VALUES (
            gen_random_uuid(),
            1,
            0.4,
            0.3,
            0.3,
            70.0,
            false,
            true,
            now()
        )
    """)


def downgrade() -> None:
    # Remove index from signals table
    op.drop_index('idx_signal_final_decision', table_name='signals')
    
    # Remove rejection_reason column from signals table
    op.drop_column('signals', 'rejection_reason')
    
    # Drop indexes from arbitration_config
    op.drop_index('idx_arbitration_config_active_unique', table_name='arbitration_config')
    op.drop_index('idx_arbitration_config_version', table_name='arbitration_config')
    op.drop_index(op.f('ix_arbitration_config_id'), table_name='arbitration_config')
    
    # Drop arbitration_config table
    op.drop_table('arbitration_config')

