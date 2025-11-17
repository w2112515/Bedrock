"""
Prometheus Metrics Middleware

Collects and exposes application metrics for Prometheus monitoring.
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from shared.utils.logger import setup_logging

logger = setup_logging("prometheus_metrics")


# Define Prometheus metrics
REQUEST_COUNT = Counter(
    "datahub_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

REQUEST_DURATION = Histogram(
    "datahub_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)

REQUEST_IN_PROGRESS = Gauge(
    "datahub_http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "endpoint"]
)

KLINE_COLLECTION_COUNT = Counter(
    "datahub_kline_collections_total",
    "Total K-line data collections",
    ["symbol", "interval", "status"]
)

ONCHAIN_COLLECTION_COUNT = Counter(
    "datahub_onchain_collections_total",
    "Total on-chain data collections",
    ["symbol", "network", "type", "status"]
)

DATABASE_QUERY_DURATION = Histogram(
    "datahub_database_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"]
)

EXTERNAL_API_CALL_COUNT = Counter(
    "datahub_external_api_calls_total",
    "Total external API calls",
    ["provider", "status"]
)

EXTERNAL_API_CALL_DURATION = Histogram(
    "datahub_external_api_call_duration_seconds",
    "External API call duration in seconds",
    ["provider"]
)

ERROR_COUNT = Counter(
    "datahub_errors_total",
    "Total errors by type and endpoint",
    ["error_type", "endpoint", "status_code"]
)

ERROR_RATE = Gauge(
    "datahub_error_rate",
    "Current error rate by endpoint",
    ["endpoint"]
)

CIRCUIT_BREAKER_STATE = Gauge(
    "datahub_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half-open, 2=open)",
    ["service"]
)

CIRCUIT_BREAKER_FAILURES = Counter(
    "datahub_circuit_breaker_failures_total",
    "Total circuit breaker failures",
    ["service"]
)


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect Prometheus metrics for HTTP requests.
    
    Metrics collected:
    - Request count by method, endpoint, status code
    - Request duration by method, endpoint
    - Requests in progress by method, endpoint
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and collect metrics.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
        
        Returns:
            HTTP response
        """
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        method = request.method
        path = request.url.path
        
        # Normalize path (replace IDs with placeholders)
        normalized_path = self._normalize_path(path)
        
        # Increment in-progress gauge
        REQUEST_IN_PROGRESS.labels(method=method, endpoint=normalized_path).inc()
        
        # Start timer
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=normalized_path,
                status_code=response.status_code
            ).inc()
            
            REQUEST_DURATION.labels(
                method=method,
                endpoint=normalized_path
            ).observe(duration)
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time
            
            # Record error metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=normalized_path,
                status_code=500
            ).inc()
            
            REQUEST_DURATION.labels(
                method=method,
                endpoint=normalized_path
            ).observe(duration)
            
            # Re-raise exception
            raise
            
        finally:
            # Decrement in-progress gauge
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=normalized_path).dec()
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path by replacing dynamic segments with placeholders.
        
        Examples:
        - /v1/klines/BTCUSDT/1h -> /v1/klines/{symbol}/{interval}
        - /v1/onchain/BTC/eth -> /v1/onchain/{symbol}/{network}
        
        Args:
            path: Original request path
        
        Returns:
            Normalized path
        """
        parts = path.split("/")
        
        # K-lines endpoints
        if len(parts) >= 4 and parts[1] == "v1" and parts[2] == "klines":
            if len(parts) == 4:
                return "/v1/klines/{symbol}/{interval}"
            elif len(parts) == 5 and parts[4] == "latest":
                return "/v1/klines/{symbol}/{interval}/latest"
            elif parts[3] == "collect":
                return "/v1/klines/collect"
        
        # On-chain endpoints
        if len(parts) >= 4 and parts[1] == "v1" and parts[2] == "onchain":
            if parts[3] == "collect":
                return f"/v1/onchain/collect/{parts[4]}" if len(parts) > 4 else "/v1/onchain/collect"
            elif len(parts) == 4:
                return "/v1/onchain/{symbol}/{network}"
            elif len(parts) == 5 and parts[4] == "latest":
                return "/v1/onchain/{symbol}/{network}/latest"
        
        # Default: return as-is
        return path


def get_metrics() -> Response:
    """
    Generate Prometheus metrics response.
    
    Returns:
        Response with Prometheus metrics in text format
    """
    metrics_data = generate_latest()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


# Helper functions to record custom metrics
def record_kline_collection(symbol: str, interval: str, status: str = "success"):
    """Record K-line collection metric."""
    KLINE_COLLECTION_COUNT.labels(symbol=symbol, interval=interval, status=status).inc()


def record_onchain_collection(symbol: str, network: str, collection_type: str, status: str = "success"):
    """Record on-chain collection metric."""
    ONCHAIN_COLLECTION_COUNT.labels(symbol=symbol, network=network, type=collection_type, status=status).inc()


def record_database_query(operation: str, duration: float):
    """Record database query metric."""
    DATABASE_QUERY_DURATION.labels(operation=operation).observe(duration)


def record_external_api_call(provider: str, status: str, duration: float):
    """Record external API call metric."""
    EXTERNAL_API_CALL_COUNT.labels(provider=provider, status=status).inc()
    EXTERNAL_API_CALL_DURATION.labels(provider=provider).observe(duration)


def record_error(error_type: str, endpoint: str, status_code: int):
    """Record error metric."""
    ERROR_COUNT.labels(error_type=error_type, endpoint=endpoint, status_code=status_code).inc()


def update_error_rate(endpoint: str, error_rate: float):
    """Update error rate metric."""
    ERROR_RATE.labels(endpoint=endpoint).set(error_rate)


def update_circuit_breaker_state(service: str, state: int):
    """
    Update circuit breaker state metric.

    Args:
        service: Service name
        state: 0=closed, 1=half-open, 2=open
    """
    CIRCUIT_BREAKER_STATE.labels(service=service).set(state)


def record_circuit_breaker_failure(service: str):
    """Record circuit breaker failure."""
    CIRCUIT_BREAKER_FAILURES.labels(service=service).inc()

