"""Tests for engine.signal_chain — Session 204."""
import pytest
from engine.signal_chain import SignalChainBuilder


class TestSignalChain:
    def test_create(self):
        sc = SignalChainBuilder()
        assert isinstance(sc, SignalChainBuilder)

    def test_create_and_process_chain(self):
        sc = SignalChainBuilder()
        chain = sc.create_chain("test")
        chain.add("gain", params={"gain_db": -6})
        signal = [0.8] * 1000
        result = chain.process(signal)
        assert len(result) > 0
