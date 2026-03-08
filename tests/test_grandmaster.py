"""Tests for engine.grandmaster — Fibonacci session 144 report."""

import json
from pathlib import Path

from engine.grandmaster import (
    FIBONACCI,
    GRANDMASTER_BANNER,
    GRANDMASTER_SESSION,
    GrandmasterReport,
    build_grandmaster_report,
    export_grandmaster_report,
    main,
)

# ── Constants ────────────────────────────────────────────────────────────

class TestConstants:
    def test_grandmaster_session_is_144(self):
        assert GRANDMASTER_SESSION == 144

    def test_144_in_fibonacci(self):
        assert 144 in FIBONACCI

    def test_fibonacci_starts_correctly(self):
        assert FIBONACCI[:5] == [1, 1, 2, 3, 5]

    def test_grandmaster_banner_nonempty(self):
        assert isinstance(GRANDMASTER_BANNER, str)
        assert len(GRANDMASTER_BANNER) > 0

    def test_grandmaster_banner_contains_grandmaster(self):
        assert "G R A N D M A S T E R" in GRANDMASTER_BANNER


# ── GrandmasterReport ───────────────────────────────────────────────────

class TestGrandmasterReport:
    def test_default_fields(self):
        r = GrandmasterReport()
        assert r.session == 144
        assert r.belt == "GRANDMASTER"
        assert r.phases_completed == 5

    def test_is_grandmaster_true(self):
        r = GrandmasterReport(
            session=144, engine_modules=55, total_tests=1200,
            health_score=0.9,
        )
        assert r.is_grandmaster is True

    def test_is_grandmaster_false_low_modules(self):
        r = GrandmasterReport(
            session=144, engine_modules=10, total_tests=1200,
            health_score=0.9,
        )
        assert r.is_grandmaster is False

    def test_is_grandmaster_false_low_tests(self):
        r = GrandmasterReport(
            session=144, engine_modules=55, total_tests=500,
            health_score=0.9,
        )
        assert r.is_grandmaster is False

    def test_is_grandmaster_false_low_health(self):
        r = GrandmasterReport(
            session=144, engine_modules=55, total_tests=1200,
            health_score=0.5,
        )
        assert r.is_grandmaster is False

    def test_milestones_default_empty(self):
        r = GrandmasterReport()
        assert r.milestones == []


# ── build_grandmaster_report ─────────────────────────────────────────────

class TestBuildGrandmasterReport:
    def test_returns_report(self):
        report = build_grandmaster_report()
        assert isinstance(report, GrandmasterReport)

    def test_populates_engine_modules(self):
        report = build_grandmaster_report()
        assert report.engine_modules > 0

    def test_populates_milestones(self):
        report = build_grandmaster_report()
        assert len(report.milestones) > 0

    def test_timestamp_set(self):
        report = build_grandmaster_report()
        assert report.timestamp > 0

    def test_version_set(self):
        report = build_grandmaster_report()
        assert report.version != ""


# ── export_grandmaster_report ────────────────────────────────────────────

class TestExportGrandmasterReport:
    def test_creates_file(self, tmp_path):
        report = GrandmasterReport(engine_modules=50, total_tests=1000,
                                   health_score=0.9)
        path = export_grandmaster_report(report, str(tmp_path))
        assert Path(path).exists()

    def test_valid_json(self, tmp_path):
        report = GrandmasterReport(engine_modules=50, total_tests=1000,
                                   health_score=0.9)
        path = export_grandmaster_report(report, str(tmp_path))
        with open(path) as f:
            data = json.load(f)
        assert data["session"] == 144
        assert data["belt"] == "GRANDMASTER"
        assert "is_grandmaster" in data


# ── main ─────────────────────────────────────────────────────────────────

class TestMain:
    def test_main_runs(self, capsys):
        main()
        captured = capsys.readouterr()
        assert "GRANDMASTER" in captured.out
