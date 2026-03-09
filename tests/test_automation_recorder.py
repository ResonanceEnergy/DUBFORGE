"""Tests for engine.automation_recorder — Session 207."""
import pytest
from engine.automation_recorder import AutomationRecorder


class TestAutomationRecorder:
    def test_create(self):
        ar = AutomationRecorder()
        assert isinstance(ar, AutomationRecorder)

    def test_record_point(self):
        ar = AutomationRecorder()
        ar.create_lane("volume", target_module="mixer", target_param="vol")
        ar.add_point("volume", 0.0, 0.8)
        ar.add_point("volume", 1.0, 0.5)
        val = ar.get_value_at("volume", 0.5)
        assert isinstance(val, float)
