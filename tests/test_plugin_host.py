"""Tests for engine.plugin_host — Session 229."""
import pytest
from engine.plugin_host import PluginHost


class TestPluginHost:
    def test_create(self):
        ph = PluginHost()
        assert isinstance(ph, PluginHost)

    def test_create_plugin(self):
        ph = PluginHost()
        p = ph.create_plugin("gain", "gain_1")
        assert p is not None

    def test_process(self):
        ph = PluginHost()
        ph.create_plugin("gain", "g1")
        signal = [0.8] * 100
        result = ph.process(signal)
        assert len(result) == 100

    def test_chain(self):
        ph = PluginHost()
        ph.create_plugin("gain", "g1")
        ph.create_plugin("saturate", "s1")
        signal = [0.3] * 100
        result = ph.process(signal)
        assert len(result) == 100

    def test_remove(self):
        ph = PluginHost()
        ph.create_plugin("gain", "g1")
        assert ph.remove_plugin("g1") is True
