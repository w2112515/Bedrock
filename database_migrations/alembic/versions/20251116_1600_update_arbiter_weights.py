"""Update arbiter weights: ML 0.3→0.15, Rule 0.4→0.55

Revision ID: 20251116_1600
Revises: 20251112_1400_decision_engine_add_arbitration_config
Create Date: 2025-11-16 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251116_1600'
down_revision = '20251112_1400'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Insert new arbitration config (version 2) with updated weights
    op.execute("""
        -- Deactivate old config
        UPDATE arbitration_config SET is_active = false WHERE is_active = true;
        
        -- Insert new config with updated weights
        INSERT INTO arbitration_config (
            id, version, rule_weight, ml_weight, llm_weight, 
            min_approval_score, adaptive_threshold_enabled, is_active, created_at
        )
        VALUES (
            gen_random_uuid(),
            2,  -- version 2
            0.55,  -- rule_weight: 0.4 → 0.55 (+0.15)
            0.15,  -- ml_weight: 0.3 → 0.15 (-0.15)
            0.3,   -- llm_weight: unchanged
            70.0,  -- min_approval_score: unchanged
            false, -- adaptive_threshold_enabled
            true,  -- is_active
            now()
        );
    """)


def downgrade() -> None:
    # Rollback: reactivate version 1 config
    op.execute("""
        -- Deactivate version 2
        UPDATE arbitration_config SET is_active = false WHERE version = 2;
        
        -- Reactivate version 1
        UPDATE arbitration_config SET is_active = true WHERE version = 1;
    """)

