"""
Shared logging utilities.
Provides structured logging with consistent format across all services.
"""
import structlog
import logging
import sys
import os


def setup_logging(service_name: str, log_level: str = None):
    """
    Setup structured logging for a service.
    Args:
        service_name: Name of the service (e.g., "datahub", "decision_engine")
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO")

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Get logger with service name
    logger = structlog.get_logger(service_name)
    return logger


def get_logger(name: str = None):
    """
    Get a logger instance.
    Args:
        name: Logger name (optional)
    Returns:
        structlog.BoundLogger: Logger instance
    """
    return structlog.get_logger(name)

