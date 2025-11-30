"""
Logging configuration for structured logging with observability

Uses structlog for structured JSON logging with tracing support.
"""

import structlog
import logging
import sys
from typing import Dict, Any


def setup_logging(config: Dict[str, Any] = None):
    """
    Configure structured logging.

    Args:
        config: Logging configuration dictionary
    """
    if config is None:
        config = {"level": "INFO", "format": "json"}

    log_level = getattr(logging, config.get("level", "INFO").upper())

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() if config.get("format") == "json"
            else structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True
    )

    # Also configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level
    )


def get_logger(name: str = None):
    """
    Get a structured logger instance.

    Args:
        name: Logger name (optional)

    Returns:
        Logger instance
    """
    return structlog.get_logger(name)