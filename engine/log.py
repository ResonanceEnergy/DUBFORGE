"""
DUBFORGE — Centralized Logging

Provides a pre-configured logger for all engine modules.
Usage:
    from engine.log import get_logger
    log = get_logger(__name__)
    log.info("message")
"""

import logging
import sys

_CONFIGURED = False


def get_logger(name: str = "dubforge") -> logging.Logger:
    """Return a named logger with DUBFORGE formatting."""
    global _CONFIGURED
    logger = logging.getLogger(name)

    if not _CONFIGURED:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("[%(name)s] %(message)s")
        )
        root = logging.getLogger("dubforge")
        root.addHandler(handler)
        root.setLevel(logging.INFO)
        _CONFIGURED = True

    return logger
