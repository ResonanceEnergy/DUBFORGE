"""Tests for engine.collaboration — Session 196."""
import pytest
from engine.collaboration import CollaborationEngine


class TestCollaboration:
    def test_create(self):
        ce = CollaborationEngine()
        assert isinstance(ce, CollaborationEngine)
