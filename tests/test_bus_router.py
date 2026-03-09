"""Tests for engine.bus_router — Session 218."""
import pytest
from engine.bus_router import BusRouter


class TestBusRouter:
    def test_create(self):
        br = BusRouter()
        assert isinstance(br, BusRouter)

    def test_add_bus(self):
        br = BusRouter()
        br.add_bus("drums")
        assert "drums" in br.buses
