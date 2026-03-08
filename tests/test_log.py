"""Tests for engine.log — centralized logging utility."""

import logging

from engine.log import get_logger


class TestGetLogger:
    """get_logger returns a properly configured logger."""

    def test_returns_logger_instance(self):
        log = get_logger("dubforge.test")
        assert isinstance(log, logging.Logger)

    def test_logger_name(self):
        log = get_logger("dubforge.mymod")
        assert log.name == "dubforge.mymod"

    def test_default_name(self):
        log = get_logger()
        assert log.name == "dubforge"

    def test_has_handler(self):
        root = logging.getLogger("dubforge")
        assert len(root.handlers) >= 1

    def test_log_level(self):
        root = logging.getLogger("dubforge")
        assert root.level <= logging.INFO

    def test_idempotent(self):
        """Calling get_logger multiple times doesn't add duplicate handlers."""
        before = len(logging.getLogger("dubforge").handlers)
        get_logger("dubforge.extra1")
        get_logger("dubforge.extra2")
        after = len(logging.getLogger("dubforge").handlers)
        assert after == before

    def test_can_log_without_error(self):
        log = get_logger("dubforge.smoke")
        log.info("smoke test")
        log.debug("debug test")
        log.warning("warning test")
