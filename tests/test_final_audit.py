"""Tests for engine.final_audit — codebase audit and health scoring."""

import json
from pathlib import Path

from engine.final_audit import (
    AuditReport,
    audit_configs,
    audit_engine_dir,
    audit_tests_dir,
    count_lines,
    count_pattern,
    export_audit_report,
    main,
    read_version,
    run_full_audit,
)

# ── AuditReport dataclass ───────────────────────────────────────────────

class TestAuditReport:
    def test_default_fields(self):
        r = AuditReport()
        assert r.engine_modules == 0
        assert r.test_files == 0
        assert r.total_python_loc == 0
        assert r.issues == []

    def test_health_score_all_pass(self):
        r = AuditReport(
            engine_modules=55, test_files=45, modules_with_main=45,
            total_python_loc=15000, total_test_loc=6000,
            export_functions=25, phi_references=50, wav_writers=15,
        )
        assert r.health_score > 0.8

    def test_health_score_all_fail(self):
        r = AuditReport()
        assert r.health_score < 0.5

    def test_health_score_range(self):
        r = AuditReport()
        assert 0.0 <= r.health_score <= 1.0

    def test_issues_affect_health(self):
        r = AuditReport(
            engine_modules=55, test_files=45, modules_with_main=45,
            total_python_loc=15000, total_test_loc=6000,
            export_functions=25, phi_references=50, wav_writers=15,
            issues=["a", "b", "c", "d", "e"],
        )
        # 5 issues => that check fails
        score_with_issues = r.health_score
        r2 = AuditReport(
            engine_modules=55, test_files=45, modules_with_main=45,
            total_python_loc=15000, total_test_loc=6000,
            export_functions=25, phi_references=50, wav_writers=15,
        )
        assert r2.health_score >= score_with_issues


# ── count_lines ──────────────────────────────────────────────────────────

class TestCountLines:
    def test_existing_file(self):
        # Count lines of this test file itself
        result = count_lines(__file__)
        assert result > 0

    def test_nonexistent_file(self):
        assert count_lines("/tmp/nonexistent_xyz_dubforge.py") == 0

    def test_temp_file(self, tmp_path):
        f = tmp_path / "sample.py"
        f.write_text("line1\nline2\n\nline4\n")
        # 3 non-empty lines
        assert count_lines(str(f)) == 3


# ── count_pattern ────────────────────────────────────────────────────────

class TestCountPattern:
    def test_finds_pattern(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("PHI = 1.618\nuse PHI here\n")
        assert count_pattern(str(f), "PHI") >= 2

    def test_no_match(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("hello world\n")
        assert count_pattern(str(f), "ZZZZZ") == 0

    def test_nonexistent_file(self):
        assert count_pattern("/tmp/no_file_xyz.py", "x") == 0


# ── audit_engine_dir ─────────────────────────────────────────────────────

class TestAuditEngineDir:
    def test_real_engine_dir(self):
        result = audit_engine_dir("engine")
        assert result["module_count"] > 0
        assert result["total_loc"] > 0

    def test_nonexistent_dir(self):
        result = audit_engine_dir("/tmp/no_engine_xyz")
        assert "error" in result


# ── audit_tests_dir ──────────────────────────────────────────────────────

class TestAuditTestsDir:
    def test_real_tests_dir(self):
        result = audit_tests_dir("tests")
        assert result["test_file_count"] > 0

    def test_nonexistent_dir(self):
        result = audit_tests_dir("/tmp/no_tests_xyz")
        assert "error" in result


# ── audit_configs ────────────────────────────────────────────────────────

class TestAuditConfigs:
    def test_real_configs_dir(self):
        result = audit_configs("configs")
        assert result["config_count"] > 0

    def test_nonexistent_dir(self):
        result = audit_configs("/tmp/no_configs_xyz")
        assert "error" in result


# ── read_version ─────────────────────────────────────────────────────────

class TestReadVersion:
    def test_returns_string(self):
        v = read_version()
        assert isinstance(v, str)
        assert len(v) > 0


# ── run_full_audit ───────────────────────────────────────────────────────

class TestRunFullAudit:
    def test_returns_audit_report(self):
        report = run_full_audit()
        assert isinstance(report, AuditReport)

    def test_engine_modules_positive(self):
        report = run_full_audit()
        assert report.engine_modules > 0


# ── export_audit_report ──────────────────────────────────────────────────

class TestExportAuditReport:
    def test_creates_file(self, tmp_path):
        report = AuditReport(engine_modules=10, test_files=5)
        path = export_audit_report(report, str(tmp_path))
        assert Path(path).exists()

    def test_valid_json(self, tmp_path):
        report = AuditReport(engine_modules=10, version="4.0.0")
        path = export_audit_report(report, str(tmp_path))
        with open(path) as f:
            data = json.load(f)
        assert data["engine_modules"] == 10
        assert data["version"] == "4.0.0"


# ── main ─────────────────────────────────────────────────────────────────

class TestMain:
    def test_main_runs(self, capsys):
        main()
        captured = capsys.readouterr()
        assert "Final Audit" in captured.out
