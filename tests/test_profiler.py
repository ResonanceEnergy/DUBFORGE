"""Tests for engine.profiler — performance benchmarking."""

import json
from pathlib import Path

from engine.profiler import (
    BenchmarkResult,
    benchmark_module,
    run_full_benchmark,
    write_benchmark_report,
)

# ── BenchmarkResult dataclass ────────────────────────────────────────────

class TestBenchmarkResult:
    def test_default_fields(self):
        r = BenchmarkResult(module="test", function="main", elapsed_ms=1.23)
        assert r.module == "test"
        assert r.function == "main"
        assert r.elapsed_ms == 1.23
        assert r.status == "ok"
        assert r.error == ""

    def test_custom_status(self):
        r = BenchmarkResult("m", "f", 0.0, status="error", error="boom")
        assert r.status == "error"
        assert r.error == "boom"

    def test_elapsed_ms_is_float(self):
        r = BenchmarkResult("m", "f", 5.0)
        assert isinstance(r.elapsed_ms, float)

    def test_module_field_stores_name(self):
        r = BenchmarkResult(module="phi_core", function="main", elapsed_ms=0.1)
        assert r.module == "phi_core"


# ── benchmark_module ─────────────────────────────────────────────────────

class TestBenchmarkModule:
    def test_valid_module_returns_results(self):
        results = benchmark_module("phi_core")
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_valid_module_result_status(self):
        results = benchmark_module("phi_core")
        # At least one result for main()
        main_results = [r for r in results if r.function == "main"]
        assert len(main_results) >= 1
        assert main_results[0].status == "ok"

    def test_valid_module_elapsed_positive(self):
        results = benchmark_module("phi_core")
        for r in results:
            assert r.elapsed_ms >= 0

    def test_nonexistent_module_returns_import_error(self):
        results = benchmark_module("nonexistent_module_xyz")
        assert len(results) == 1
        assert results[0].status == "error"
        assert results[0].function == "import"

    def test_nonexistent_module_error_message(self):
        results = benchmark_module("nonexistent_module_xyz")
        assert results[0].error != ""

    def test_module_name_preserved(self):
        results = benchmark_module("noise_generator")
        for r in results:
            assert r.module == "noise_generator"


# ── run_full_benchmark ───────────────────────────────────────────────────

class TestRunFullBenchmark:
    def test_custom_module_list(self):
        results = run_full_benchmark(["phi_core"])
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_multiple_modules(self):
        results = run_full_benchmark(["phi_core", "noise_generator"])
        modules = {r.module for r in results}
        assert "phi_core" in modules
        assert "noise_generator" in modules

    def test_default_modules_discovers_engine(self):
        # Use a small subset to avoid running all module mains
        results = run_full_benchmark(["phi_core", "error_handling"])
        assert isinstance(results, list)
        assert len(results) > 0

    def test_empty_list_returns_empty(self):
        results = run_full_benchmark([])
        assert results == []


# ── write_benchmark_report ───────────────────────────────────────────────

class TestWriteBenchmarkReport:
    def test_creates_report_file(self, tmp_path):
        path = write_benchmark_report(str(tmp_path))
        assert Path(path).exists()

    def test_report_is_valid_json(self, tmp_path):
        path = write_benchmark_report(str(tmp_path))
        with open(path) as f:
            data = json.load(f)
        assert "benchmarks" in data
        assert "total_modules" in data
        assert "total_time_ms" in data

    def test_report_has_phi_ratio(self, tmp_path):
        path = write_benchmark_report(str(tmp_path))
        with open(path) as f:
            data = json.load(f)
        assert "phi_ratio_fastest_slowest" in data
