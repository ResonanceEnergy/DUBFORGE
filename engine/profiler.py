"""
DUBFORGE — Performance Profiler  (Session 134)

Benchmark every render pipeline. Measure timing for all export functions.
Provides timing reports and identifies hot paths.
"""

import importlib
import time
from dataclasses import dataclass
from pathlib import Path

PHI = 1.6180339887


@dataclass
class BenchmarkResult:
    module: str
    function: str
    elapsed_ms: float
    status: str = "ok"
    error: str = ""


def benchmark_module(module_name: str, output_dir: str = "output") -> list[BenchmarkResult]:
    """Benchmark the main() function of a module."""
    results: list[BenchmarkResult] = []
    try:
        mod = importlib.import_module(f"engine.{module_name}")
    except ImportError as e:
        return [BenchmarkResult(module_name, "import", 0, "error", str(e))]

    # Benchmark main()
    if hasattr(mod, "main"):
        t0 = time.perf_counter()
        try:
            mod.main()
            elapsed = (time.perf_counter() - t0) * 1000
            results.append(BenchmarkResult(module_name, "main", round(elapsed, 2)))
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000
            results.append(BenchmarkResult(module_name, "main", round(elapsed, 2), "error", str(e)))

    return results


def run_full_benchmark(modules: list[str] | None = None) -> list[BenchmarkResult]:
    """Benchmark all or specified modules."""
    if modules is None:
        eng_dir = Path(__file__).parent
        modules = sorted(
            f.stem for f in eng_dir.glob("*.py")
            if not f.stem.startswith("_") and f.stem not in ("cli", "profiler", "log")
        )

    all_results: list[BenchmarkResult] = []
    for mod_name in modules:
        all_results.extend(benchmark_module(mod_name))

    return all_results


def write_benchmark_report(output_dir: str = "output") -> str:
    """Run benchmarks on key modules and write report."""
    import json

    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    # Benchmark a subset of fast modules
    fast_modules = [
        "phi_core", "noise_generator", "sub_bass", "lead_synth",
        "pad_synth", "arp_synth", "pluck_synth",
    ]
    results = run_full_benchmark(fast_modules)

    report = {
        "benchmarks": [
            {"module": r.module, "function": r.function,
             "elapsed_ms": r.elapsed_ms, "status": r.status, "error": r.error}
            for r in results
        ],
        "total_modules": len(fast_modules),
        "total_time_ms": round(sum(r.elapsed_ms for r in results), 2),
        "phi_ratio_fastest_slowest": round(
            max(r.elapsed_ms for r in results) / max(min(r.elapsed_ms for r in results), 0.01), 4
        ) if results else 0,
    }

    path = out / "benchmark_report.json"
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    return str(path)


def main() -> None:
    path = write_benchmark_report()
    print(f"Performance Profiler: benchmark report written to {path}")


if __name__ == "__main__":
    main()
