"""Tests for engine.full_integration — full pipeline integration run."""

import json
from pathlib import Path

from engine.full_integration import (
    IntegrationResult,
    export_integration_report,
    main,
)

# ── IntegrationResult dataclass ──────────────────────────────────────────

class TestIntegrationResult:
    def test_default_fields(self):
        r = IntegrationResult()
        assert r.modules_tested == 0
        assert r.modules_passed == 0
        assert r.modules_failed == 0
        assert r.failures == []
        assert r.elapsed_s == 0.0
        assert r.outputs == {}

    def test_success_when_no_failures(self):
        r = IntegrationResult(modules_tested=5, modules_passed=5, modules_failed=0)
        assert r.success is True

    def test_not_success_when_failures(self):
        r = IntegrationResult(modules_tested=5, modules_passed=3, modules_failed=2)
        assert r.success is False

    def test_success_property_edge_zero(self):
        r = IntegrationResult()
        assert r.success is True  # 0 failed = success

    def test_failures_list_mutable(self):
        r = IntegrationResult()
        r.failures.append("module_x: error")
        assert len(r.failures) == 1

    def test_outputs_dict_mutable(self):
        r = IntegrationResult()
        r.outputs["sub_bass"] = "ok"
        assert r.outputs["sub_bass"] == "ok"


# ── run_full_integration (lightweight) ────────────────────────────────────

class TestRunFullIntegration:
    """Test integration structure without running all module mains."""

    def test_returns_integration_result(self):
        from engine.full_integration import _try_module
        result = IntegrationResult()
        _try_module("error_handling", lambda: None, result)
        assert isinstance(result, IntegrationResult)
        assert result.modules_tested == 1

    def test_modules_tested_positive(self):
        from engine.full_integration import _try_module
        result = IntegrationResult()
        _try_module("m1", lambda: None, result)
        _try_module("m2", lambda: None, result)
        assert result.modules_tested == 2

    def test_elapsed_tracking(self):
        result = IntegrationResult()
        result.elapsed_s = 1.5
        assert result.elapsed_s > 0

    def test_passed_plus_failed_equals_tested(self):
        from engine.full_integration import _try_module
        result = IntegrationResult()
        _try_module("ok_mod", lambda: None, result)

        def fail_fn():
            raise ValueError("boom")
        _try_module("bad_mod", fail_fn, result)
        assert result.modules_passed + result.modules_failed == result.modules_tested


# ── export_integration_report ────────────────────────────────────────────

class TestExportIntegrationReport:
    def test_creates_file(self, tmp_path):
        r = IntegrationResult(modules_tested=1, modules_passed=1)
        path = export_integration_report(r, str(tmp_path))
        assert Path(path).exists()

    def test_valid_json(self, tmp_path):
        r = IntegrationResult(modules_tested=2, modules_passed=1,
                              modules_failed=1, failures=["x: err"])
        path = export_integration_report(r, str(tmp_path))
        with open(path) as f:
            data = json.load(f)
        assert data["modules_tested"] == 2
        assert data["success"] is False
        assert "x: err" in data["failures"]


# ── main ─────────────────────────────────────────────────────────────────

class TestMain:
    def test_main_callable(self):
        assert callable(main)
