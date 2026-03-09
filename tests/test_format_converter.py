"""Tests for engine.format_converter — Session 193."""
import pytest
from engine.format_converter import FormatConverter


class TestFormatConverter:
    def test_create(self):
        fc = FormatConverter()
        assert isinstance(fc, FormatConverter)
