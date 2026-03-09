"""Tests for engine.ep_builder — Session 195."""
import pytest
from engine.ep_builder import EPBuilder


class TestEPBuilder:
    def test_create(self):
        eb = EPBuilder()
        assert isinstance(eb, EPBuilder)
