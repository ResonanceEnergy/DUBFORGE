"""Tests for engine.chain_commands — Session 148."""
import pytest
from engine.chain_commands import parse_chain, is_chain, ChainStep, ChainResult


class TestChainCommands:
    def test_parse_chain_simple(self):
        result = parse_chain("make a sub then add wobble")
        assert len(result) >= 2

    def test_is_chain_true(self):
        assert is_chain("make a pad then add reverb") is True

    def test_is_chain_false(self):
        assert is_chain("make a pad") is False

    def test_chain_step(self):
        s = ChainStep(command="test")
        assert s.status == "pending"

    def test_chain_result(self):
        r = ChainResult(steps=[ChainStep(command="a")], success_count=1)
        assert r.all_success
