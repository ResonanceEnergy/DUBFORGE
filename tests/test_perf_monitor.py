"""Tests for engine.perf_monitor — Session 232."""
import math
import pytest
from engine.perf_monitor import PerformanceMonitor, TimingResult

SR = 44100


class TestPerformanceMonitor:
    def test_create(self):
        pm = PerformanceMonitor()
        assert isinstance(pm, PerformanceMonitor)

    def test_timer(self):
        pm = PerformanceMonitor()
        pm.start_timer("test")
        result = pm.stop_timer(1000)
        assert isinstance(result, TimingResult)
        assert result.duration_ms > 0

    def test_benchmark(self):
        pm = PerformanceMonitor()
        samples = [0.5] * 10000
        result = pm.benchmark(lambda s: [x * 0.5 for x in s], samples, 3, "gain")
        assert result.duration_ms > 0

    def test_report(self):
        pm = PerformanceMonitor()
        pm.start_timer("test")
        pm.stop_timer(44100)
        report = pm.get_report()
        assert report.total_render_ms > 0

    def test_format(self):
        pm = PerformanceMonitor()
        pm.start_timer("test")
        pm.stop_timer(44100)
        text = pm.format_report()
        assert "Performance Report" in text
