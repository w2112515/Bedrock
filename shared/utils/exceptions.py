"""
Shared exception classes for consistent error handling across services.
"""
from typing import Optional, Any


class BedrockException(Exception):
    """
    Base exception class for all Project Bedrock exceptions.
    """
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class BaseServiceException(BedrockException):
    """
    Base exception class for service-specific exceptions.
    Extends BedrockException with HTTP status code support.
    """
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict] = None,
        status_code: int = 500
    ):
        super().__init__(message, error_code, details)
        self.status_code = status_code

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API responses."""
        result = super().to_dict()
        result["status_code"] = self.status_code
        return result


class ValidationError(BedrockException):
    """
    Raised when input validation fails.
    """
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)


class NotFoundError(BedrockException):
    """
    Raised when a requested resource is not found.
    """
    def __init__(self, resource: str, resource_id: Any, **kwargs):
        message = f"{resource} with id {resource_id} not found"
        details = kwargs.get("details", {})
        details.update({"resource": resource, "resource_id": resource_id})
        super().__init__(message, error_code="NOT_FOUND", details=details)


class DatabaseError(BedrockException):
    """
    Raised when a database operation fails.
    """
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if operation:
            details["operation"] = operation
        super().__init__(message, error_code="DATABASE_ERROR", details=details)


class ExternalAPIError(BedrockException):
    """
    Raised when an external API call fails.
    """
    def __init__(
        self,
        message: str,
        api_name: str,
        status_code: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        details.update({"api_name": api_name})
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, error_code="EXTERNAL_API_ERROR", details=details)


class ConfigurationError(BedrockException):
    """
    Raised when configuration is invalid or missing.
    """
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if config_key:
            details["config_key"] = config_key
        super().__init__(message, error_code="CONFIGURATION_ERROR", details=details)


class AuthenticationError(BedrockException):
    """
    Raised when authentication fails.
    """
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, error_code="AUTHENTICATION_ERROR", **kwargs)


class AuthorizationError(BedrockException):
    """
    Raised when authorization fails (user doesn't have permission).
    """
    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(message, error_code="AUTHORIZATION_ERROR", **kwargs)


class RateLimitError(BedrockException):
    """
    Raised when rate limit is exceeded.
    """
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, error_code="RATE_LIMIT_ERROR", details=details)


class BusinessLogicError(BedrockException):
    """
    Raised when business logic validation fails.
    """
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="BUSINESS_LOGIC_ERROR", **kwargs)


class DataIntegrityError(BedrockException):
    """
    Raised when data integrity constraints are violated.
    """
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="DATA_INTEGRITY_ERROR", **kwargs)


class ServiceUnavailableError(BedrockException):
    """
    Raised when a required service is unavailable.
    """
    def __init__(self, service_name: str, **kwargs):
        message = f"Service {service_name} is unavailable"
        details = kwargs.get("details", {})
        details["service_name"] = service_name
        super().__init__(message, error_code="SERVICE_UNAVAILABLE", details=details)


class TimeoutError(BedrockException):
    """
    Raised when an operation times out.
    """
    def __init__(
        self,
        message: str = "Operation timed out",
        timeout_seconds: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        super().__init__(message, error_code="TIMEOUT_ERROR", details=details)

