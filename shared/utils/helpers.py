"""
Shared helper utility functions.
"""
from datetime import datetime, timezone
from typing import Any, Optional
import hashlib
import json


def get_utc_now() -> datetime:
    """
    Get current UTC datetime.
    Returns:
        datetime: Current UTC datetime with timezone info
    """
    return datetime.now(timezone.utc)


def to_unix_timestamp(dt: datetime) -> int:
    """
    Convert datetime to Unix timestamp.
    Args:
        dt: Datetime object
    Returns:
        int: Unix timestamp in seconds
    """
    return int(dt.timestamp())


def from_unix_timestamp(timestamp: int) -> datetime:
    """
    Convert Unix timestamp to datetime.
    Args:
        timestamp: Unix timestamp in seconds
    Returns:
        datetime: Datetime object with UTC timezone
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def generate_hash(data: str, algorithm: str = "sha256") -> str:
    """
    Generate hash of string data.
    Args:
        data: String data to hash
        algorithm: Hash algorithm (md5, sha1, sha256, sha512)
    Returns:
        str: Hexadecimal hash string
    """
    hash_func = getattr(hashlib, algorithm)
    return hash_func(data.encode()).hexdigest()


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero
    Returns:
        float: Result of division or default value
    """
    if denominator == 0:
        return default
    return numerator / denominator


def round_decimal(value: float, decimals: int = 2) -> float:
    """
    Round float to specified decimal places.
    Args:
        value: Float value to round
        decimals: Number of decimal places
    Returns:
        float: Rounded value
    """
    return round(value, decimals)


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to maximum length.
    Args:
        text: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    Returns:
        str: Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def serialize_json(data: Any) -> str:
    """
    Serialize data to JSON string with datetime handling.
    Args:
        data: Data to serialize
    Returns:
        str: JSON string
    """
    def default_handler(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    return json.dumps(data, default=default_handler)


def deserialize_json(json_str: str) -> Any:
    """
    Deserialize JSON string to Python object.
    Args:
        json_str: JSON string
    Returns:
        Any: Deserialized Python object
    """
    return json.loads(json_str)


def calculate_percentage(part: float, total: float, decimals: int = 2) -> float:
    """
    Calculate percentage.
    Args:
        part: Part value
        total: Total value
        decimals: Number of decimal places
    Returns:
        float: Percentage value
    """
    if total == 0:
        return 0.0
    return round((part / total) * 100, decimals)


def clamp(value: float, min_value: float, max_value: float) -> float:
    """
    Clamp value between min and max.
    Args:
        value: Value to clamp
        min_value: Minimum value
        max_value: Maximum value
    Returns:
        float: Clamped value
    """
    return max(min_value, min(value, max_value))

