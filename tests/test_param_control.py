"""Tests for engine.param_control — Session 149."""
import pytest
from engine.param_control import parse_params, resolve_module, ParsedParams


class TestParamControl:
    def test_parse_frequency(self):
        p = parse_params("play at 440 hz")
        assert p.frequency_hz == 440.0

    def test_parse_duration(self):
        p = parse_params("for 2 seconds")
        assert p.duration_s == 2.0

    def test_resolve_module(self):
        m = resolve_module("sub bass")
        assert isinstance(m, str)

    def test_parsed_params_to_dict(self):
        p = ParsedParams(module="test")
        d = p.to_dict()
        assert isinstance(d, dict)
        assert d["module"] == "test"
