"""
Redis connection management for DecisionEngine Service.
Reuses shared Redis utilities.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from shared.utils.redis_client import get_redis_client, close_redis_client

# Re-export for convenience
__all__ = ["get_redis_client", "close_redis_client"]

