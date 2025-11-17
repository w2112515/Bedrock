"""
DataHub Service Custom Exceptions

Defines a unified exception hierarchy for the DataHub service.
All custom exceptions inherit from DataHubException.
"""

from typing import Optional, Dict, Any
from shared.utils.exceptions import BaseServiceException


class DataHubException(BaseServiceException):
    """
    Base exception for all DataHub service errors.
    
    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code
        details: Additional error details
        status_code: HTTP status code (default: 500)
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "DATAHUB_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        super().__init__(message, error_code, details, status_code)


class ExternalAPIException(DataHubException):
    """
    Exception raised when external API calls fail.
    
    Used for errors from Binance, Bitquery, and other external services.
    """
    
    def __init__(
        self,
        message: str,
        provider: str,
        error_code: str = "EXTERNAL_API_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 502
    ):
        details = details or {}
        details["provider"] = provider
        super().__init__(message, error_code, details, status_code)


class BinanceAPIException(ExternalAPIException):
    """Exception raised when Binance API calls fail."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "BINANCE_API_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "binance", error_code, details)


class BitqueryAPIException(ExternalAPIException):
    """Exception raised when Bitquery API calls fail."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "BITQUERY_API_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, "bitquery", error_code, details)


class DataCollectionException(DataHubException):
    """
    Exception raised during data collection operations.
    
    Used for errors in K-line or on-chain data collection.
    """
    
    def __init__(
        self,
        message: str,
        collection_type: str,
        error_code: str = "DATA_COLLECTION_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        details = details or {}
        details["collection_type"] = collection_type
        super().__init__(message, error_code, details, status_code)


class KLineCollectionException(DataCollectionException):
    """Exception raised during K-line data collection."""
    
    def __init__(
        self,
        message: str,
        symbol: str,
        interval: str,
        error_code: str = "KLINE_COLLECTION_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details.update({"symbol": symbol, "interval": interval})
        super().__init__(message, "kline", error_code, details)


class OnChainCollectionException(DataCollectionException):
    """Exception raised during on-chain data collection."""
    
    def __init__(
        self,
        message: str,
        symbol: str,
        network: str,
        error_code: str = "ONCHAIN_COLLECTION_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details.update({"symbol": symbol, "network": network})
        super().__init__(message, "onchain", error_code, details)


class ValidationException(DataHubException):
    """
    Exception raised when input validation fails.
    
    Used for invalid parameters, missing required fields, etc.
    """
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        error_code: str = "VALIDATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 400
    ):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, error_code, details, status_code)


class DatabaseException(DataHubException):
    """
    Exception raised when database operations fail.
    
    Used for connection errors, query errors, transaction errors, etc.
    """
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        error_code: str = "DATABASE_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        details = details or {}
        if operation:
            details["operation"] = operation
        super().__init__(message, error_code, details, status_code)


class CacheException(DataHubException):
    """
    Exception raised when cache operations fail.
    
    Used for Redis connection errors, cache read/write errors, etc.
    """
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        error_code: str = "CACHE_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        details = details or {}
        if operation:
            details["operation"] = operation
        super().__init__(message, error_code, details, status_code)


class RateLimitException(DataHubException):
    """
    Exception raised when rate limits are exceeded.
    
    Used for API rate limiting, request throttling, etc.
    """
    
    def __init__(
        self,
        message: str,
        limit: Optional[int] = None,
        retry_after: Optional[int] = None,
        error_code: str = "RATE_LIMIT_EXCEEDED",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 429
    ):
        details = details or {}
        if limit:
            details["limit"] = limit
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, error_code, details, status_code)


class CircuitBreakerOpenException(DataHubException):
    """
    Exception raised when circuit breaker is open.
    
    Used to prevent cascading failures when external services are down.
    """
    
    def __init__(
        self,
        message: str,
        service: str,
        error_code: str = "CIRCUIT_BREAKER_OPEN",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 503
    ):
        details = details or {}
        details["service"] = service
        super().__init__(message, error_code, details, status_code)


class ResourceNotFoundException(DataHubException):
    """
    Exception raised when a requested resource is not found.
    
    Used for missing K-lines, missing on-chain data, etc.
    """
    
    def __init__(
        self,
        message: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        error_code: str = "RESOURCE_NOT_FOUND",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 404
    ):
        details = details or {}
        details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, error_code, details, status_code)


class ConfigurationException(DataHubException):
    """
    Exception raised when configuration is invalid or missing.
    
    Used for missing environment variables, invalid settings, etc.
    """
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        error_code: str = "CONFIGURATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        details = details or {}
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, error_code, details, status_code)

