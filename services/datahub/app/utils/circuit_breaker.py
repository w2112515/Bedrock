"""
Circuit Breaker Utilities

Implements circuit breaker pattern for external API calls to prevent cascading failures.
"""

from typing import Callable, Any
from functools import wraps
import pybreaker

from shared.utils.logger import setup_logging
from services.datahub.app.exceptions import CircuitBreakerOpenException

logger = setup_logging("circuit_breaker")


# Circuit breaker configurations for different services
BINANCE_CIRCUIT_BREAKER = pybreaker.CircuitBreaker(
    fail_max=5,  # Open circuit after 5 consecutive failures
    reset_timeout=60,  # Keep circuit open for 60 seconds
    exclude=[],  # Don't exclude any exceptions
    name="binance_api"
)

BITQUERY_CIRCUIT_BREAKER = pybreaker.CircuitBreaker(
    fail_max=5,  # Open circuit after 5 consecutive failures
    reset_timeout=60,  # Keep circuit open for 60 seconds
    exclude=[],  # Don't exclude any exceptions
    name="bitquery_api"
)


class CircuitBreakerLoggingListener(pybreaker.CircuitBreakerListener):
    """
    Custom circuit breaker listener for logging state changes.
    """

    def state_change(self, breaker, old_state, new_state):
        """
        Called when circuit breaker state changes.

        Args:
            breaker: Circuit breaker instance
            old_state: Previous state
            new_state: New state
        """
        if new_state == pybreaker.STATE_OPEN:
            logger.warning(
                f"Circuit breaker opened for {breaker.name}",
                breaker_name=breaker.name,
                fail_count=breaker.fail_counter
            )
        elif new_state == pybreaker.STATE_CLOSED:
            logger.info(
                f"Circuit breaker closed for {breaker.name}",
                breaker_name=breaker.name
            )
        elif new_state == pybreaker.STATE_HALF_OPEN:
            logger.info(
                f"Circuit breaker half-open for {breaker.name}",
                breaker_name=breaker.name
            )


# Register listeners
BINANCE_CIRCUIT_BREAKER.add_listener(CircuitBreakerLoggingListener())
BITQUERY_CIRCUIT_BREAKER.add_listener(CircuitBreakerLoggingListener())


def with_circuit_breaker(breaker: pybreaker.CircuitBreaker):
    """
    Decorator to wrap functions with circuit breaker protection.
    
    Args:
        breaker: Circuit breaker instance to use
    
    Returns:
        Decorated function
    
    Raises:
        CircuitBreakerOpenException: When circuit breaker is open
    
    Example:
        @with_circuit_breaker(BINANCE_CIRCUIT_BREAKER)
        def fetch_data():
            # API call here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return breaker.call(func, *args, **kwargs)
            except pybreaker.CircuitBreakerError as e:
                logger.error(
                    f"Circuit breaker open for {breaker.name}",
                    breaker_name=breaker.name,
                    error=str(e)
                )
                raise CircuitBreakerOpenException(
                    message=f"Service {breaker.name} is temporarily unavailable",
                    service=breaker.name,
                    details={
                        "fail_count": breaker.fail_counter,
                        "state": str(breaker.current_state)
                    }
                )
        return wrapper
    return decorator


def get_circuit_breaker_status(breaker: pybreaker.CircuitBreaker) -> dict:
    """
    Get current status of a circuit breaker.
    
    Args:
        breaker: Circuit breaker instance
    
    Returns:
        Dictionary with circuit breaker status
    """
    return {
        "name": breaker.name,
        "state": str(breaker.current_state),
        "fail_count": breaker.fail_counter,
        "fail_max": breaker.fail_max,
        "timeout_duration": breaker.timeout_duration
    }


def get_all_circuit_breaker_status() -> dict:
    """
    Get status of all circuit breakers.
    
    Returns:
        Dictionary with all circuit breaker statuses
    """
    return {
        "binance": get_circuit_breaker_status(BINANCE_CIRCUIT_BREAKER),
        "bitquery": get_circuit_breaker_status(BITQUERY_CIRCUIT_BREAKER)
    }


def reset_circuit_breaker(breaker: pybreaker.CircuitBreaker):
    """
    Manually reset a circuit breaker.
    
    Args:
        breaker: Circuit breaker instance to reset
    """
    breaker.close()
    logger.info(
        f"Circuit breaker manually reset for {breaker.name}",
        breaker_name=breaker.name
    )


def reset_all_circuit_breakers():
    """Reset all circuit breakers."""
    reset_circuit_breaker(BINANCE_CIRCUIT_BREAKER)
    reset_circuit_breaker(BITQUERY_CIRCUIT_BREAKER)
    logger.info("All circuit breakers reset")

