"""
Redis configuration for Portfolio Service.

Uses shared Redis client from shared/utils/redis_client.py.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from shared.utils.redis_client import get_redis_client, cache_get, cache_set

# Re-export for convenience
__all__ = ['get_redis_client', 'cache_get', 'cache_set']

