"""
Metrics endpoint

Provides Prometheus-compatible metrics.
"""

import sys
import os
from fastapi import APIRouter, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.logger import setup_logging

logger = setup_logging("metrics_api")

router = APIRouter()


# ============================================
# Prometheus Metrics
# ============================================

# Signal generation metrics
signal_generated_total = Counter(
    "signal_generated_total",
    "Total number of signals generated",
    ["market", "signal_type"]
)

signal_generation_duration = Histogram(
    "signal_generation_duration_seconds",
    "Time spent generating signals",
    ["market"]
)

rule_engine_score_histogram = Histogram(
    "rule_engine_score",
    "Distribution of rule engine scores",
    buckets=[0, 50, 60, 70, 80, 85, 90, 95, 100]
)

# API request metrics
api_requests_total = Counter(
    "api_requests_total",
    "Total number of API requests",
    ["endpoint", "method", "status"]
)

api_request_duration = Histogram(
    "api_request_duration_seconds",
    "API request duration",
    ["endpoint", "method"]
)


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ============================================
# Metric Helper Functions
# ============================================

def record_signal_generated(market: str, signal_type: str):
    """Record a signal generation event."""
    signal_generated_total.labels(market=market, signal_type=signal_type).inc()


def record_rule_engine_score(score: float):
    """Record a rule engine score."""
    rule_engine_score_histogram.observe(score)


def record_api_request(endpoint: str, method: str, status: int):
    """Record an API request."""
    api_requests_total.labels(endpoint=endpoint, method=method, status=status).inc()

