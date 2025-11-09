# API Documentation

## Overview

Project Bedrock provides RESTful APIs for all services. Each service exposes its own API on a dedicated port.

## Service Endpoints

| Service | Port | Base URL | Documentation |
|---------|------|----------|---------------|
| DataHub | 8001 | http://localhost:8001 | http://localhost:8001/docs |
| DecisionEngine | 8002 | http://localhost:8002 | http://localhost:8002/docs |
| Portfolio | 8003 | http://localhost:8003 | http://localhost:8003/docs |
| Backtesting | 8004 | http://localhost:8004 | http://localhost:8004/docs |
| MLOps | 8005 | http://localhost:8005 | http://localhost:8005/docs |
| Notification | 8006 | http://localhost:8006 | http://localhost:8006/docs |

## API Standards

### Request Format

All POST/PUT requests should use JSON format:

```http
POST /v1/signals HTTP/1.1
Content-Type: application/json

{
  "market": "BTCUSDT",
  "signal_type": "PULLBACK_BUY"
}
```

### Response Format

All responses follow a standard format:

**Success Response**:
```json
{
  "status": "success",
  "message": "Operation completed successfully",
  "data": {
    "id": 1,
    "name": "example"
  }
}
```

**Error Response**:
```json
{
  "status": "error",
  "message": "Resource not found",
  "error_code": "NOT_FOUND",
  "details": {
    "resource_id": 123
  }
}
```

### Pagination

List endpoints support pagination:

**Request**:
```http
GET /v1/signals?limit=20&offset=0
```

**Response**:
```json
{
  "status": "success",
  "data": [...],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET, PUT, DELETE |
| 201 | Created | Successful POST |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service down |

## DataHub Service API

### GET /v1/klines

Get K-line data for a market.

**Parameters**:
- `market` (string, required): Market symbol (e.g., "BTCUSDT")
- `interval` (string, required): Time interval (e.g., "1h", "4h", "1d")
- `start_time` (integer, optional): Start timestamp (Unix seconds)
- `end_time` (integer, optional): End timestamp (Unix seconds)
- `limit` (integer, optional): Number of records (default: 100, max: 1000)

**Response**:
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "market": "BTCUSDT",
      "interval": "1h",
      "open_time": 1699488000,
      "open": 35000.0,
      "high": 35500.0,
      "low": 34800.0,
      "close": 35200.0,
      "volume": 1234.56,
      "close_time": 1699491599,
      "created_at": "2025-11-09T12:00:00Z"
    }
  ]
}
```

### GET /v1/chain-data

Get on-chain data.

**Parameters**:
- `data_type` (string, required): Data type ("large_transfer", "smart_money", "exchange_netflow", "active_addresses")
- `start_time` (integer, optional): Start timestamp
- `end_time` (integer, optional): End timestamp
- `limit` (integer, optional): Number of records

**Response**:
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "data_type": "large_transfer",
      "timestamp": 1699488000,
      "metadata": {
        "from": "0x123...",
        "to": "0x456...",
        "amount": 1000.0,
        "token": "BTC"
      },
      "created_at": "2025-11-09T12:00:00Z"
    }
  ]
}
```

## DecisionEngine Service API

### POST /v1/signals/generate

Generate trading signals.

**Request**:
```json
{
  "market": "BTCUSDT",
  "interval": "1h"
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "id": 1,
    "market": "BTCUSDT",
    "signal_type": "PULLBACK_BUY",
    "entry_price": 35000.0,
    "stop_loss_price": 34000.0,
    "profit_target_price": 37000.0,
    "suggested_position_weight": 0.15,
    "reward_risk_ratio": 2.0,
    "rule_engine_score": 85.0,
    "created_at": "2025-11-09T12:00:00Z"
  }
}
```

### GET /v1/signals

List all signals.

**Parameters**:
- `limit` (integer, optional): Number of records (default: 20, max: 100)
- `offset` (integer, optional): Number of records to skip (default: 0)
- `market` (string, optional): Filter by market
- `signal_type` (string, optional): Filter by signal type

**Response**: Paginated list of signals

## Portfolio Service API

### GET /v1/positions

List all positions.

**Parameters**:
- `limit` (integer, optional)
- `offset` (integer, optional)
- `status` (string, optional): Filter by status ("OPEN", "CLOSED")

**Response**: Paginated list of positions

### POST /v1/positions/estimate

Estimate position size.

**Request**:
```json
{
  "signal_id": 1
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "estimated_position_size": 0.5,
    "estimated_cost": 17500.0,
    "risk_percentage": 2.0,
    "position_weight_used": 0.15
  }
}
```

## Health Check Endpoints

All services provide health check endpoints:

### GET /health

Basic health check.

**Response**:
```json
{
  "status": "healthy",
  "service": "datahub",
  "version": "1.0.0",
  "timestamp": "2025-11-09T12:00:00Z"
}
```

### GET /ready

Readiness check (includes dependency checks).

**Response**:
```json
{
  "status": "healthy",
  "service": "datahub",
  "version": "1.0.0",
  "timestamp": "2025-11-09T12:00:00Z",
  "dependencies": {
    "database": "healthy",
    "redis": "healthy"
  }
}
```

## Rate Limiting

API rate limits:
- Development: 1000 requests/minute
- Production: 100 requests/minute per API key

Rate limit headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699488000
```

## Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Input validation failed |
| `NOT_FOUND` | Resource not found |
| `DATABASE_ERROR` | Database operation failed |
| `EXTERNAL_API_ERROR` | External API call failed |
| `CONFIGURATION_ERROR` | Configuration invalid |
| `AUTHENTICATION_ERROR` | Authentication failed |
| `AUTHORIZATION_ERROR` | Insufficient permissions |
| `RATE_LIMIT_ERROR` | Rate limit exceeded |
| `BUSINESS_LOGIC_ERROR` | Business logic validation failed |
| `SERVICE_UNAVAILABLE` | Service unavailable |
| `TIMEOUT_ERROR` | Operation timed out |

## Interactive API Documentation

Each service provides interactive API documentation powered by Swagger UI:

- DataHub: http://localhost:8001/docs
- DecisionEngine: http://localhost:8002/docs
- Portfolio: http://localhost:8003/docs
- Backtesting: http://localhost:8004/docs
- MLOps: http://localhost:8005/docs
- Notification: http://localhost:8006/docs

You can test API endpoints directly from the browser!

---

**Last Updated**: 2025-11-09

