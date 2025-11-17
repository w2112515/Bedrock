"""
Redis connection management.

Provides Redis client for caching and Celery broker.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")))

from shared.utils.redis_client import get_redis_client

# Export get_redis_client for convenience
__all__ = ["get_redis_client"]

