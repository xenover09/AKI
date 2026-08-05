"""
Logging infrastructure for AKI.

This module is the single place in the codebase permitted to touch
Python's `logging` module directly. Every other component obtains its
logger through `get_logger()` rather than calling `logging.getLogger()`
itself, so log configuration stays centralized and consistent.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from config.constants import (
    APP_NAME,
    DEFAULT_LOG_FILE_NAME,
    LOG_DATE_FORMAT,
    LOG_FILE_BACKUP_COUNT,
    LOG_FILE_MAX_BYTES,
    LOG_FORMAT,
)
from config.settings import Settings

_ROOT_LOGGER_NAME = APP_NAME


def configure_logging(settings: Settings) -> logging.Logger:
    """
    Configure and return AKI's root logger.

    Attaches a console handler (for live feedback) and a rotating file
    handler (for persistent history) to the "AKI" logger, then returns
    it. This must be called exactly once, by the Boot Manager, before
    any other component logs a message.

    Args:
        settings: The loaded application settings, used to determine
            the log level and the log file directory.

    Returns:
        The configured root logger for AKI, named "AKI".
    """
    settings.log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    logger.setLevel(settings.log_level)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        filename=settings.log_dir / DEFAULT_LOG_FILE_NAME,
        maxBytes=LOG_FILE_MAX_BYTES,
        backupCount=LOG_FILE_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Retrieve a logger scoped under AKI's root logger.

    Args:
        name: Optional sub-name (e.g. a module or component name). When
            provided, the returned logger is "AKI.<name>" and inherits
            handlers and level from the root "AKI" logger. When omitted,
            the root "AKI" logger itself is returned.

    Returns:
        A `logging.Logger` instance ready for use.
    """
    if name is None:
        return logging.getLogger(_ROOT_LOGGER_NAME)
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")
