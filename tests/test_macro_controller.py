"""Tests for engine.macro_controller — Session 203."""
import pytest
from engine.macro_controller import MacroController


class TestMacroController:
    def test_create(self):
        mc = MacroController()
        assert isinstance(mc, MacroController)

    def test_set_and_get_value(self):
        mc = MacroController()
        mc.add_macro("volume", label="Volume")
        mc.set_value("volume", 0.5)
        v = mc.get_value("volume")
        assert abs(v - 0.5) < 0.01
