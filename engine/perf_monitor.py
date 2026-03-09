"""
DUBFORGE — Performance Monitor  (Session 232)

Monitor engine performance — CPU usage estimation,
memory tracking, render timing, module profiling.
"""

import time
from dataclasses import dataclass

PHI = 1.6180339887
SAMPLE_RATE = 48000


@dataclass
class TimingResult:
    """Timing measurement result."""
    name: str
    duration_ms: float
    samples_processed: int
    realtime_ratio: float  # >1 = faster than realtime

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "duration_ms": round(self.duration_ms, 3),
            "samples_processed": self.samples_processed,
            "realtime_ratio": round(self.realtime_ratio, 2),
            "faster_than_realtime": self.realtime_ratio >= 1.0,
        }


@dataclass
class PerformanceReport:
    """Performance summary report."""
    timings: list[TimingResult]
    total_render_ms: float
    total_samples: int
    avg_realtime_ratio: float
    slowest_module: str
    fastest_module: str

    def to_dict(self) -> dict:
        return {
            "total_render_ms": round(self.total_render_ms, 3),
            "total_samples": self.total_samples,
            "avg_realtime_ratio": round(self.avg_realtime_ratio, 2),
            "slowest": self.slowest_module,
            "fastest": self.fastest_module,
            "module_count": len(self.timings),
            "timings": [t.to_dict() for t in self.timings],
        }


class PerformanceMonitor:
    """Monitor engine performance."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self._timings: list[TimingResult] = []
        self._active_timer: float | None = None
        self._active_name: str = ""

    def start_timer(self, name: str) -> None:
        """Start a timing measurement."""
        self._active_name = name
        self._active_timer = time.perf_counter()

    def stop_timer(self, samples_processed: int = 0) -> TimingResult | None:
        """Stop current timer and record result."""
        if self._active_timer is None:
            return None

        elapsed = time.perf_counter() - self._active_timer
        elapsed_ms = elapsed * 1000

        # Realtime ratio
        audio_duration = samples_processed / self.sample_rate if samples_processed > 0 else 0
        rt_ratio = audio_duration / elapsed if elapsed > 0 else 0

        result = TimingResult(
            name=self._active_name,
            duration_ms=elapsed_ms,
            samples_processed=samples_processed,
            realtime_ratio=rt_ratio,
        )

        self._timings.append(result)
        self._active_timer = None
        return result

    def time_function(self, name: str, fn: callable,
                      *args, **kwargs) -> tuple[any, TimingResult]:
        """Time a function call."""
        self.start_timer(name)
        result = fn(*args, **kwargs)

        samples = 0
        if isinstance(result, list):
            samples = len(result)

        timing = self.stop_timer(samples)
        return result, timing

    def benchmark(self, fn: callable, samples: list[float],
                  iterations: int = 5,
                  name: str = "benchmark") -> TimingResult:
        """Benchmark a processing function."""
        times: list[float] = []

        for _ in range(iterations):
            start = time.perf_counter()
            fn(list(samples))
            times.append(time.perf_counter() - start)

        avg_ms = sum(times) / len(times) * 1000
        audio_dur = len(samples) / self.sample_rate
        rt_ratio = audio_dur / (avg_ms / 1000) if avg_ms > 0 else 0

        result = TimingResult(
            name=name,
            duration_ms=avg_ms,
            samples_processed=len(samples),
            realtime_ratio=rt_ratio,
        )
        self._timings.append(result)
        return result

    def get_report(self) -> PerformanceReport:
        """Generate performance report."""
        if not self._timings:
            return PerformanceReport(
                timings=[], total_render_ms=0, total_samples=0,
                avg_realtime_ratio=0, slowest_module="", fastest_module="",
            )

        total_ms = sum(t.duration_ms for t in self._timings)
        total_samples = sum(t.samples_processed for t in self._timings)
        avg_rt = sum(t.realtime_ratio for t in self._timings) / len(self._timings)

        slowest = max(self._timings, key=lambda t: t.duration_ms)
        fastest = min(self._timings, key=lambda t: t.duration_ms)

        return PerformanceReport(
            timings=list(self._timings),
            total_render_ms=total_ms,
            total_samples=total_samples,
            avg_realtime_ratio=avg_rt,
            slowest_module=slowest.name,
            fastest_module=fastest.name,
        )

    def clear(self) -> None:
        """Clear recorded timings."""
        self._timings.clear()

    def estimate_cpu_load(self, buffer_size: int = 256) -> float:
        """Estimate CPU load based on recent timings."""
        if not self._timings:
            return 0.0

        # Average processing time per buffer
        recent = self._timings[-10:]
        avg_ms = sum(t.duration_ms for t in recent) / len(recent)

        # Available time per buffer
        buffer_ms = buffer_size / self.sample_rate * 1000

        return min(1.0, avg_ms / buffer_ms) if buffer_ms > 0 else 0.0

    def phi_efficiency(self) -> float:
        """PHI-based efficiency score."""
        report = self.get_report()
        if report.avg_realtime_ratio == 0:
            return 0.0
        # Score based on PHI ratio
        return min(1.0, report.avg_realtime_ratio / (PHI * 100))

    def format_report(self) -> str:
        """Format report as readable string."""
        report = self.get_report()
        lines = [
            "═══ Performance Report ═══",
            f"Total render: {report.total_render_ms:.1f}ms",
            f"Avg RT ratio: {report.avg_realtime_ratio:.1f}x",
            f"Slowest: {report.slowest_module}",
            f"Fastest: {report.fastest_module}",
            "",
        ]

        for t in report.timings:
            status = "✓" if t.realtime_ratio >= 1 else "✗"
            lines.append(
                f"  {status} {t.name:20s} {t.duration_ms:8.2f}ms "
                f"({t.realtime_ratio:.1f}x RT)"
            )

        return "\n".join(lines)


def main() -> None:
    import math

    print("Performance Monitor")
    monitor = PerformanceMonitor()

    # Benchmark some operations
    n = SAMPLE_RATE
    samples = [0.8 * math.sin(2 * math.pi * 440 * i / SAMPLE_RATE)
               for i in range(n)]

    # Test 1: Simple gain
    def gain_fn(s):
        return [x * 0.5 for x in s]

    r1 = monitor.benchmark(gain_fn, samples, 3, "gain")
    print(f"  Gain: {r1.duration_ms:.2f}ms ({r1.realtime_ratio:.0f}x RT)")

    # Test 2: Soft clip
    def clip_fn(s):
        return [math.tanh(x * 3) for x in s]

    r2 = monitor.benchmark(clip_fn, samples, 3, "soft_clip")
    print(f"  Soft clip: {r2.duration_ms:.2f}ms ({r2.realtime_ratio:.0f}x RT)")

    # Test 3: Simple filter
    def filter_fn(s):
        out = []
        y = 0
        for x in s:
            y += 0.1 * (x - y)
            out.append(y)
        return out

    r3 = monitor.benchmark(filter_fn, samples, 3, "lowpass")
    print(f"  Lowpass: {r3.duration_ms:.2f}ms ({r3.realtime_ratio:.0f}x RT)")

    # Report
    print(f"\n{monitor.format_report()}")
    print(f"\n  PHI efficiency: {monitor.phi_efficiency():.3f}")

    print("Done.")


if __name__ == "__main__":
    main()
