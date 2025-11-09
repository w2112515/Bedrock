"""
Shared utilities package.
"""
from .database import get_db, init_db, close_db, engine, SessionLocal, Base
from .redis_client import (
    get_redis_client,
    publish_event,
    subscribe_to_channel,
    cache_set,
    cache_get,
    cache_delete,
    close_redis,
)
from .logger import setup_logging, get_logger
from .helpers import (
    get_utc_now,
    to_unix_timestamp,
    from_unix_timestamp,
    generate_hash,
    safe_divide,
    round_decimal,
    truncate_string,
    serialize_json,
    deserialize_json,
    calculate_percentage,
    clamp,
)
from .exceptions import (
    BedrockException,
    ValidationError,
    NotFoundError,
    DatabaseError,
    ExternalAPIError,
    ConfigurationError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    BusinessLogicError,
    DataIntegrityError,
    ServiceUnavailableError,
    TimeoutError,
)

__all__ = [
    # Database utilities
    "get_db",
    "init_db",
    "close_db",
    "engine",
    "SessionLocal",
    "Base",
    # Redis utilities
    "get_redis_client",
    "publish_event",
    "subscribe_to_channel",
    "cache_set",
    "cache_get",
    "cache_delete",
    "close_redis",
    # Logger utilities
    "setup_logging",
    "get_logger",
    # Helper functions
    "get_utc_now",
    "to_unix_timestamp",
    "from_unix_timestamp",
    "generate_hash",
    "safe_divide",
    "round_decimal",
    "truncate_string",
    "serialize_json",
    "deserialize_json",
    "calculate_percentage",
    "clamp",
    # Exceptions
    "BedrockException",
    "ValidationError",
    "NotFoundError",
    "DatabaseError",
    "ExternalAPIError",
    "ConfigurationError",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitError",
    "BusinessLogicError",
    "DataIntegrityError",
    "ServiceUnavailableError",
    "TimeoutError",
]

