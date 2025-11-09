"""
Shared Redis client utilities.
Provides Redis connection pool and pub/sub functionality.
"""
import redis
from redis.connection import ConnectionPool
import os
import json
from typing import Any, Optional

# Read Redis URL from environment variable
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Redis connection pool
redis_pool = ConnectionPool.from_url(
    REDIS_URL,
    max_connections=50,  # Maximum connections in pool
    decode_responses=True,  # Automatically decode responses to strings
)


def get_redis_client() -> redis.Redis:
    """
    Get Redis client from connection pool.
    Returns:
        redis.Redis: Redis client instance
    """
    return redis.Redis(connection_pool=redis_pool)


def publish_event(channel: str, event_data: dict) -> int:
    """
    Publish event to Redis channel.
    Args:
        channel: Redis channel name (e.g., "signal.created")
        event_data: Event data dictionary
    Returns:
        int: Number of subscribers that received the message
    """
    client = get_redis_client()
    message = json.dumps(event_data)
    return client.publish(channel, message)


def subscribe_to_channel(channel: str):
    """
    Subscribe to Redis channel.
    Args:
        channel: Redis channel name
    Returns:
        redis.client.PubSub: PubSub object for listening to messages
    Usage:
        pubsub = subscribe_to_channel("signal.created")
        for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                # Process event data
    """
    client = get_redis_client()
    pubsub = client.pubsub()
    pubsub.subscribe(channel)
    return pubsub


def cache_set(key: str, value: Any, expire: Optional[int] = None) -> bool:
    """
    Set cache value in Redis.
    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        expire: Expiration time in seconds (optional)
    Returns:
        bool: True if successful
    """
    client = get_redis_client()
    serialized_value = json.dumps(value)
    return client.set(key, serialized_value, ex=expire)


def cache_get(key: str) -> Optional[Any]:
    """
    Get cache value from Redis.
    Args:
        key: Cache key
    Returns:
        Any: Cached value (JSON deserialized) or None if not found
    """
    client = get_redis_client()
    value = client.get(key)
    if value:
        return json.loads(value)
    return None


def cache_delete(key: str) -> int:
    """
    Delete cache key from Redis.
    Args:
        key: Cache key
    Returns:
        int: Number of keys deleted
    """
    client = get_redis_client()
    return client.delete(key)


def close_redis():
    """
    Close Redis connection pool.
    Should be called during application shutdown.
    """
    redis_pool.disconnect()

