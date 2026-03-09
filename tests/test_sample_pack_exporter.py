"""Tests for engine.sample_pack_exporter — Session 192."""
import pytest
from engine.sample_pack_exporter import SamplePackExporter


class TestSamplePackExporter:
    def test_create(self):
        spe = SamplePackExporter()
        assert isinstance(spe, SamplePackExporter)
