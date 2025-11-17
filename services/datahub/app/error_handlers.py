"""
Global Error Handlers

Implements FastAPI exception handlers for standardized error responses.
"""

import uuid
from typing import Union
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from shared.utils.logger import setup_logging
from services.datahub.app.exceptions import (
    DataHubException,
    ExternalAPIException,
    ValidationException,
    RateLimitException,
    CircuitBreakerOpenException,
    ResourceNotFoundException
)
from services.datahub.app.models.error_response import (
    ErrorResponse,
    ValidationErrorResponse,
    ExternalAPIErrorResponse,
    RateLimitErrorResponse,
    CircuitBreakerErrorResponse,
    ErrorDetail
)
from services.datahub.app.middleware import record_error

logger = setup_logging("error_handlers")


async def datahub_exception_handler(
    request: Request,
    exc: DataHubException
) -> JSONResponse:
    """
    Handle DataHub custom exceptions.
    
    Args:
        request: FastAPI request
        exc: DataHub exception
    
    Returns:
        JSON response with error details
    """
    request_id = str(uuid.uuid4())
    
    # Log the error
    logger.error(
        "DataHub exception occurred",
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        path=request.url.path,
        request_id=request_id
    )
    
    # Record error metric
    record_error(
        error_type=exc.error_code,
        endpoint=request.url.path,
        status_code=exc.status_code
    )
    
    # Create error response
    error_response = ErrorResponse(
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        path=request.url.path,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def external_api_exception_handler(
    request: Request,
    exc: ExternalAPIException
) -> JSONResponse:
    """
    Handle external API exceptions.
    
    Args:
        request: FastAPI request
        exc: External API exception
    
    Returns:
        JSON response with error details
    """
    request_id = str(uuid.uuid4())
    
    # Log the error
    logger.error(
        "External API exception occurred",
        error_code=exc.error_code,
        message=exc.message,
        provider=exc.details.get("provider"),
        path=request.url.path,
        request_id=request_id
    )
    
    # Record error metric
    record_error(
        error_type=exc.error_code,
        endpoint=request.url.path,
        status_code=exc.status_code
    )
    
    # Create error response
    error_response = ExternalAPIErrorResponse(
        error_code=exc.error_code,
        message=exc.message,
        provider=exc.details.get("provider"),
        details=exc.details,
        path=request.url.path,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def validation_exception_handler(
    request: Request,
    exc: Union[ValidationException, RequestValidationError]
) -> JSONResponse:
    """
    Handle validation exceptions.
    
    Args:
        request: FastAPI request
        exc: Validation exception
    
    Returns:
        JSON response with validation error details
    """
    request_id = str(uuid.uuid4())
    
    # Handle Pydantic validation errors
    if isinstance(exc, RequestValidationError):
        validation_errors = []
        for error in exc.errors():
            validation_errors.append(
                ErrorDetail(
                    field=".".join(str(loc) for loc in error["loc"]),
                    message=error["msg"],
                    type=error["type"]
                )
            )
        
        error_response = ValidationErrorResponse(
            message="Request validation failed",
            validation_errors=validation_errors,
            path=request.url.path,
            request_id=request_id
        )
        
        logger.warning(
            "Request validation failed",
            validation_errors=[e.model_dump() for e in validation_errors],
            path=request.url.path,
            request_id=request_id
        )
    
    # Handle custom validation exceptions
    else:
        error_response = ValidationErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            path=request.url.path,
            request_id=request_id
        )
        
        logger.warning(
            "Validation exception occurred",
            error_code=exc.error_code,
            message=exc.message,
            path=request.url.path,
            request_id=request_id
        )
    
    # Record error metric
    record_error(
        error_type="VALIDATION_ERROR",
        endpoint=request.url.path,
        status_code=status.HTTP_400_BAD_REQUEST
    )
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response.model_dump()
    )


async def rate_limit_exception_handler(
    request: Request,
    exc: RateLimitException
) -> JSONResponse:
    """
    Handle rate limit exceptions.
    
    Args:
        request: FastAPI request
        exc: Rate limit exception
    
    Returns:
        JSON response with rate limit error details
    """
    request_id = str(uuid.uuid4())
    
    # Log the error
    logger.warning(
        "Rate limit exceeded",
        error_code=exc.error_code,
        message=exc.message,
        limit=exc.details.get("limit"),
        retry_after=exc.details.get("retry_after"),
        path=request.url.path,
        request_id=request_id
    )
    
    # Record error metric
    record_error(
        error_type=exc.error_code,
        endpoint=request.url.path,
        status_code=exc.status_code
    )
    
    # Create error response
    error_response = RateLimitErrorResponse(
        message=exc.message,
        limit=exc.details.get("limit"),
        retry_after=exc.details.get("retry_after"),
        path=request.url.path,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
        headers={"Retry-After": str(exc.details.get("retry_after", 60))}
    )


async def circuit_breaker_exception_handler(
    request: Request,
    exc: CircuitBreakerOpenException
) -> JSONResponse:
    """
    Handle circuit breaker exceptions.
    
    Args:
        request: FastAPI request
        exc: Circuit breaker exception
    
    Returns:
        JSON response with circuit breaker error details
    """
    request_id = str(uuid.uuid4())
    
    # Log the error
    logger.error(
        "Circuit breaker open",
        error_code=exc.error_code,
        message=exc.message,
        service=exc.details.get("service"),
        path=request.url.path,
        request_id=request_id
    )
    
    # Record error metric
    record_error(
        error_type=exc.error_code,
        endpoint=request.url.path,
        status_code=exc.status_code
    )
    
    # Create error response
    error_response = CircuitBreakerErrorResponse(
        message=exc.message,
        service=exc.details.get("service"),
        details=exc.details,
        path=request.url.path,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handle HTTP exceptions.
    
    Args:
        request: FastAPI request
        exc: HTTP exception
    
    Returns:
        JSON response with error details
    """
    request_id = str(uuid.uuid4())
    
    # Log the error
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        request_id=request_id
    )
    
    # Record error metric
    record_error(
        error_type="HTTP_ERROR",
        endpoint=request.url.path,
        status_code=exc.status_code
    )
    
    # Create error response
    error_response = ErrorResponse(
        error_code=f"HTTP_{exc.status_code}",
        message=exc.detail,
        path=request.url.path,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle generic exceptions (fallback handler).
    
    Args:
        request: FastAPI request
        exc: Generic exception
    
    Returns:
        JSON response with error details
    """
    request_id = str(uuid.uuid4())
    
    # Log the error
    logger.error(
        "Unhandled exception occurred",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        path=request.url.path,
        request_id=request_id,
        exc_info=True
    )
    
    # Record error metric
    record_error(
        error_type="INTERNAL_ERROR",
        endpoint=request.url.path,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    
    # Create error response (don't expose internal details)
    error_response = ErrorResponse(
        error_code="INTERNAL_ERROR",
        message="An internal error occurred. Please try again later.",
        path=request.url.path,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump()
    )

