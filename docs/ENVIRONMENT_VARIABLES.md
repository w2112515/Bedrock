# Environment Variables Documentation

## Overview

This document lists all environment variables used in Project Bedrock. All variables should be defined in the `.env` file at the project root.

## Database Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_HOST` | Yes | `localhost` | PostgreSQL host address |
| `POSTGRES_PORT` | Yes | `5432` | PostgreSQL port |
| `POSTGRES_USER` | Yes | `bedrock` | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes | `bedrock_password` | PostgreSQL password |
| `POSTGRES_DB` | Yes | `bedrock_db` | PostgreSQL database name |
| `DATABASE_URL` | Yes | (computed) | Full PostgreSQL connection URL |

## Redis Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_HOST` | Yes | `localhost` | Redis host address |
| `REDIS_PORT` | Yes | `6379` | Redis port |
| `REDIS_DB` | Yes | `0` | Redis database number |
| `REDIS_URL` | Yes | (computed) | Full Redis connection URL |

## Application Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEBUG` | No | `false` | Enable debug mode |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `SECRET_KEY` | Yes | - | Secret key for encryption (change in production!) |

## External API Keys

### Binance API

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BINANCE_API_KEY` | Yes | - | Binance API key |
| `BINANCE_API_SECRET` | Yes | - | Binance API secret |

**How to obtain**:
1. Register at https://www.binance.com
2. Go to API Management
3. Create new API key
4. Enable "Enable Reading" permission
5. Copy API Key and Secret Key

### Bitquery API

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BITQUERY_API_KEY` | Yes | - | Bitquery API key |
| `BITQUERY_API_URL` | Yes | `https://graphql.bitquery.io` | Bitquery GraphQL endpoint |

**How to obtain**:
1. Register at https://bitquery.io
2. Go to API section
3. Copy API key
4. Free tier: 10,000 queries/month

### Qwen LLM API

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `QWEN_API_KEY` | Yes | - | Qwen API key |
| `QWEN_API_URL` | Yes | `https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation` | Qwen API endpoint |

**How to obtain**:
1. Register at https://dashscope.aliyun.com
2. Go to API Keys section
3. Create new API key
4. Free tier: Limited requests/day

## Service Ports

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATAHUB_PORT` | No | `8001` | DataHub service port |
| `DECISION_ENGINE_PORT` | No | `8002` | DecisionEngine service port |
| `PORTFOLIO_PORT` | No | `8003` | Portfolio service port |
| `BACKTESTING_PORT` | No | `8004` | Backtesting service port |
| `MLOPS_PORT` | No | `8005` | MLOps service port |
| `NOTIFICATION_PORT` | No | `8006` | Notification service port |
| `WEBAPP_PORT` | No | `3000` | Frontend webapp port |

## Celery Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CELERY_BROKER_URL` | Yes | `${REDIS_URL}` | Celery broker URL (Redis) |
| `CELERY_RESULT_BACKEND` | Yes | `${REDIS_URL}` | Celery result backend URL |

## MLflow Configuration (Phase 3)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MLFLOW_TRACKING_URI` | No | `http://localhost:5000` | MLflow tracking server URL |

## Environment-Specific Configuration

### Development (.env.development)

```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

### Staging (.env.staging)

```bash
DEBUG=false
LOG_LEVEL=INFO
```

### Production (.env.production)

```bash
DEBUG=false
LOG_LEVEL=WARNING
SECRET_KEY=<strong-random-key>
```

## Security Best Practices

1. **Never commit `.env` file to version control**
   - Add `.env` to `.gitignore`
   - Use `.env.example` as template

2. **Use strong passwords**
   - Minimum 16 characters
   - Mix of letters, numbers, symbols

3. **Rotate API keys regularly**
   - Change keys every 90 days
   - Revoke unused keys

4. **Restrict API key permissions**
   - Only enable required permissions
   - Use read-only keys when possible

5. **Use secrets management in production**
   - Kubernetes Secrets
   - AWS Secrets Manager
   - HashiCorp Vault

## Validation

Use the `scripts/validate_env.py` script to validate environment variables:

```bash
python scripts/validate_env.py
```

This script checks:
- All required variables are set
- Variable types are correct (URL, integer, boolean)
- Dependencies are satisfied (e.g., if QWEN_API_KEY is set, QWEN_API_URL must also be set)
- Sensitive file permissions

## Troubleshooting

### Problem: "Environment variable not found"

**Solution**: Check that the variable is defined in `.env` file

### Problem: "Invalid database URL"

**Solution**: Verify `DATABASE_URL` format: `postgresql://user:password@host:port/database`

### Problem: "Redis connection failed"

**Solution**: Verify `REDIS_URL` format: `redis://host:port/db`

### Problem: "API key invalid"

**Solution**: 
1. Check API key is correct (no extra spaces)
2. Verify API key is active
3. Check API key permissions

## References

- [Twelve-Factor App: Config](https://12factor.net/config)
- [Environment Variables Best Practices](https://www.doppler.com/blog/environment-variables-best-practices)

---

**Last Updated**: 2025-11-09

