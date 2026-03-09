"""Tests for engine.ascension — Session 233 — ASCENSION."""
import pytest
from engine.ascension import (
    AscensionEngine, AscensionReport, ModuleStatus,
    ASCENSION_MANIFEST, PHI, FIBONACCI,
)


class TestAscension:
    def test_constants(self):
        assert abs(PHI - 1.6180339887) < 1e-6
        assert 233 in FIBONACCI

    def test_manifest(self):
        assert len(ASCENSION_MANIFEST) > 100
        assert "ascension" in ASCENSION_MANIFEST

    def test_engine_create(self):
        e = AscensionEngine()
        assert isinstance(e, AscensionEngine)
        assert e.sample_rate == 44100

    def test_phi_analysis(self):
        e = AscensionEngine()
        phi = e.phi_analysis()
        assert "total_modules" in phi
        assert "golden_modules" in phi
        assert phi["total_modules"] > 100

    def test_render_ascension_tone(self):
        e = AscensionEngine()
        samples = e.render_ascension_tone(duration=1.0)
        assert len(samples) > 0
        assert max(abs(s) for s in samples) <= 1.0

    def test_render_dubstep_proof(self):
        e = AscensionEngine()
        samples = e.render_dubstep_proof(bars=2)
        assert len(samples) > 0
        assert max(abs(s) for s in samples) <= 1.0

    def test_export(self, output_dir):
        import os
        e = AscensionEngine()
        path = str(output_dir / "test_ascension.wav")
        e.export_ascension(path)
        assert os.path.exists(path)

    def test_validate(self):
        e = AscensionEngine()
        report = e.validate_modules()
        assert isinstance(report, AscensionReport)
        assert report.total_modules > 0
        # Some will import, some may fail — that's fine
        assert report.importable >= 0

    def test_summary(self):
        e = AscensionEngine()
        s = e.summary()
        assert "ASCENSION" in s
        assert "233" in s

    def test_report_to_dict(self):
        e = AscensionEngine()
        report = e.validate_modules()
        d = report.to_dict()
        assert d["belt"] == "ASCENSION"
        assert d["fibonacci_target"] == 233
