# Database Migration Coordination Strategy

## Overview

This document defines the centralized database migration strategy for Project Bedrock. All services share a single PostgreSQL database, and all schema changes must be managed through a centralized Alembic configuration to avoid migration conflicts.

## Centralized Migration Management

### Directory Structure

```
database_migrations/
├── alembic.ini              # Alembic configuration
├── alembic/
│   ├── env.py               # Environment configuration (imports all models)
│   ├── script.py.mako       # Migration template
│   └── versions/            # Migration files
│       ├── 20250109_datahub_add_klines_table.py
│       ├── 20250110_decision_engine_add_signals_table.py
│       └── ...
```

### Migration Naming Convention

All migration files must follow this naming pattern:

```
{timestamp}_{service_name}_{description}.py
```

**Examples:**
- `20250109_120000_datahub_add_klines_table.py`
- `20250110_143000_decision_engine_add_signals_table.py`
- `20250111_090000_portfolio_add_positions_table.py`

**Naming Rules:**
1. **Timestamp**: `YYYYMMDD_HHMMSS` format
2. **Service Name**: `datahub`, `decision_engine`, `portfolio`, `backtesting`, `mlops`, `notification`
3. **Description**: Snake_case description of the change (e.g., `add_klines_table`, `add_ml_confidence_score_column`)

## Migration Workflow

### 1. Creating a New Migration

**Step 1: Ensure all models are imported in `database_migrations/alembic/env.py`**

```python
# Example: Adding DataHub models
from services.datahub.app.models.kline import KLine
from services.datahub.app.models.chain_data import ChainData
```

**Step 2: Generate migration**

```bash
cd database_migrations
alembic revision --autogenerate -m "{service_name}_{description}"
```

**Example:**
```bash
cd database_migrations
alembic revision --autogenerate -m "datahub_add_klines_table"
```

**Step 3: Review and edit migration file**

- Check the generated migration file in `database_migrations/alembic/versions/`
- Verify the `upgrade()` and `downgrade()` functions
- Add any custom SQL or data migrations if needed

**Step 4: Apply migration**

```bash
cd database_migrations
alembic upgrade head
```

### 2. Checking Migration Status

```bash
cd database_migrations
alembic current
alembic history
```

### 3. Rolling Back Migrations

```bash
cd database_migrations
alembic downgrade -1  # Rollback one migration
alembic downgrade {revision_id}  # Rollback to specific revision
```

## Table Ownership Rules

To avoid conflicts, each database table is owned by exactly one service. Only the owning service can modify the table's schema.

### Table Ownership Registry

| Table Name | Owner Service | Purpose | Notes |
|------------|---------------|---------|-------|
| `klines` | DataHubService | Store K-line data | Read-only for other services |
| `chain_data` | DataHubService | Store on-chain data | Read-only for other services |
| `signals` | DecisionEngineService | Store trading signals | Read-only for PortfolioService |
| `positions` | PortfolioService | Store positions | Read-only for other services |
| `trades` | PortfolioService | Store trade history | Read-only for other services |
| `backtest_tasks` | BacktestingService | Store backtest tasks | Read-only for other services |
| `backtest_reports` | BacktestingService | Store backtest reports | Read-only for other services |
| `training_jobs` | MLOpsService | Store ML training jobs | Read-only for other services |
| `ml_models` | MLOpsService | Store ML model metadata | Read-only for DecisionEngineService |

### Ownership Rules

1. **Schema Changes**: Only the owner service can add/remove/modify columns in its tables
2. **Read Access**: All services can read from any table
3. **Write Access**: Only the owner service can write to its tables (except for specific cases documented below)
4. **Foreign Keys**: Avoid cross-service foreign keys; use application-level references instead

### Exception: Shared Write Access

In rare cases, multiple services may need to write to the same table. These cases must be documented here:

| Table | Primary Owner | Secondary Writers | Reason |
|-------|---------------|-------------------|--------|
| (None yet) | - | - | - |

## Conflict Resolution Process

If multiple services need to modify the same table:

1. **Identify the Conflict**: Document the conflicting requirements
2. **Team Discussion**: Schedule a meeting to discuss the conflict
3. **Update Ownership**: Update the Table Ownership Registry with the decision
4. **Document Decision**: Add an entry to `docs/ARCHITECTURE_DECISION_RECORDS.md`
5. **Create Migration**: Create a single migration that satisfies all requirements

## Best Practices

### 1. Always Use Centralized Migrations

❌ **DON'T** create service-specific Alembic configurations:
```bash
# DON'T DO THIS
cd services/datahub
alembic init alembic  # This will cause conflicts!
```

✅ **DO** use the centralized migration directory:
```bash
# DO THIS
cd database_migrations
alembic revision --autogenerate -m "datahub_add_klines_table"
```

### 2. Import Models in env.py

Whenever you create a new model, immediately add it to `database_migrations/alembic/env.py`:

```python
# Add this line when creating a new model
from services.datahub.app.models.kline import KLine
```

### 3. Test Migrations Locally

Before committing a migration:

1. Apply the migration: `alembic upgrade head`
2. Verify the schema: `docker exec projectbedrock_postgres psql -U bedrock -d bedrock_db -c "\d {table_name}"`
3. Test rollback: `alembic downgrade -1`
4. Re-apply: `alembic upgrade head`

### 4. Never Edit Applied Migrations

Once a migration has been applied to any environment (dev, staging, production), **never edit it**. Instead, create a new migration to fix issues.

### 5. Coordinate with Team

Before creating a migration that affects shared tables:

1. Announce in team chat
2. Check if anyone else is working on migrations
3. Pull latest changes before generating migration
4. Push migration immediately after creation

## CI/CD Integration

### Pre-Deployment Checks

The CI/CD pipeline should:

1. **Check Migration Consistency**: Verify all migrations can be applied cleanly
2. **Run Migration Tests**: Apply migrations to a test database
3. **Check for Conflicts**: Ensure no duplicate revision IDs

### Deployment Process

1. **Backup Database**: Always backup before applying migrations
2. **Apply Migrations**: Run `alembic upgrade head` during deployment
3. **Verify Schema**: Check that all tables exist and have correct columns
4. **Rollback Plan**: Document rollback steps in case of failure

## Troubleshooting

### Problem: "Can't locate revision identified by 'xxxxx'"

**Cause**: Migration history is out of sync

**Solution**:
```bash
cd database_migrations
alembic stamp head  # Mark current state as up-to-date
```

### Problem: "Target database is not up to date"

**Cause**: Migrations haven't been applied

**Solution**:
```bash
cd database_migrations
alembic upgrade head
```

### Problem: "Multiple head revisions are present"

**Cause**: Conflicting migrations created in parallel

**Solution**:
```bash
cd database_migrations
alembic merge heads -m "merge_conflicting_migrations"
alembic upgrade head
```

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- Project Bedrock Architecture Documentation: `docs/ARCHITECTURE.md`

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2025-11-09 | AI Assistant | Initial version |

