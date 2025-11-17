"""
DataHub Service Middleware
"""

from .request_logging import RequestLoggingMiddleware
from .prometheus_metrics import (
    PrometheusMetricsMiddleware,
    get_metrics,
    record_kline_collection,
    record_onchain_collection,
    record_database_query,
    record_external_api_call,
    record_error,
    update_error_rate,
    update_circuit_breaker_state,
    record_circuit_breaker_failure
)

__all__ = [
    "RequestLoggingMiddleware",
    "PrometheusMetricsMiddleware",
    "get_metrics",
    "record_kline_collection",
    "record_onchain_collection",
    "record_database_query",
    "record_external_api_call",
    "record_error",
    "update_error_rate",
    "update_circuit_breaker_state",
    "record_circuit_breaker_failure"
]

