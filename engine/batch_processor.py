"""
DUBFORGE — Batch Processor  (Session 194)

Batch processing pipeline for applying chains of
operations to multiple audio files.
"""

import os
import time
from dataclasses import dataclass, field

PHI = 1.6180339887
SAMPLE_RATE = 48000


@dataclass
class ProcessingStep:
    """A single operation in a batch pipeline."""
    operation: str
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"operation": self.operation, "params": self.params}


@dataclass
class BatchJob:
    """A batch processing job."""
    job_id: str
    files: list[str]
    steps: list[ProcessingStep]
    status: str = "pending"
    results: list[dict] = field(default_factory=list)
    created: float = 0.0
    completed: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.job_id,
            "files": len(self.files),
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status,
            "results": len(self.results),
        }


# Operation registry — maps operation names to processor functions
OPERATIONS: dict[str, callable] = {}


def register_operation(name: str):
    """Decorator to register a batch operation."""
    def wrapper(func):
        OPERATIONS[name] = func
        return func
    return wrapper


@register_operation("normalize")
def _op_normalize(samples: list[float], params: dict) -> list[float]:
    """Normalize to peak level."""
    target_db = params.get("target_db", -1.0)
    peak = max(abs(s) for s in samples) if samples else 1.0
    if peak == 0:
        return samples
    target = 10.0 ** (target_db / 20.0)
    gain = target / peak
    return [s * gain for s in samples]


@register_operation("gain")
def _op_gain(samples: list[float], params: dict) -> list[float]:
    """Apply gain in dB."""
    db = params.get("db", 0.0)
    gain = 10.0 ** (db / 20.0)
    return [min(1.0, max(-1.0, s * gain)) for s in samples]


@register_operation("fade_in")
def _op_fade_in(samples: list[float], params: dict) -> list[float]:
    """Apply fade in."""
    ms = params.get("ms", 10.0)
    fade_samples = int(SAMPLE_RATE * ms / 1000)
    result = list(samples)
    for i in range(min(fade_samples, len(result))):
        result[i] *= i / fade_samples
    return result


@register_operation("fade_out")
def _op_fade_out(samples: list[float], params: dict) -> list[float]:
    """Apply fade out."""
    ms = params.get("ms", 50.0)
    fade_samples = int(SAMPLE_RATE * ms / 1000)
    result = list(samples)
    for i in range(min(fade_samples, len(result))):
        idx = len(result) - 1 - i
        result[idx] *= i / fade_samples
    return result


@register_operation("trim_silence")
def _op_trim(samples: list[float], params: dict) -> list[float]:
    """Trim silence from edges."""
    threshold_db = params.get("threshold_db", -60.0)
    threshold = 10.0 ** (threshold_db / 20.0)

    start = 0
    for i, s in enumerate(samples):
        if abs(s) > threshold:
            start = i
            break

    end = len(samples) - 1
    for i in range(len(samples) - 1, -1, -1):
        if abs(samples[i]) > threshold:
            end = i
            break

    return samples[start:end + 1]


@register_operation("reverse")
def _op_reverse(samples: list[float], params: dict) -> list[float]:
    """Reverse audio."""
    return list(reversed(samples))


@register_operation("invert")
def _op_invert(samples: list[float], params: dict) -> list[float]:
    """Phase invert."""
    return [-s for s in samples]


@register_operation("dc_offset")
def _op_dc_offset(samples: list[float], params: dict) -> list[float]:
    """Remove DC offset."""
    if not samples:
        return samples
    mean = sum(samples) / len(samples)
    return [s - mean for s in samples]


@register_operation("hard_clip")
def _op_hard_clip(samples: list[float], params: dict) -> list[float]:
    """Hard clip at threshold."""
    threshold = params.get("threshold", 0.95)
    return [max(-threshold, min(threshold, s)) for s in samples]


@register_operation("phi_compress")
def _op_phi_compress(samples: list[float], params: dict) -> list[float]:
    """PHI-ratio soft compression."""
    import math
    return [math.tanh(s * PHI) / PHI for s in samples]


class BatchProcessor:
    """Execute batch processing pipelines."""

    def __init__(self, output_dir: str = "output/batch"):
        self.output_dir = output_dir
        self.jobs: list[BatchJob] = []
        os.makedirs(output_dir, exist_ok=True)

    def create_pipeline(self, *steps: tuple[str, dict]) -> list[ProcessingStep]:
        """Create a processing pipeline from step tuples."""
        return [ProcessingStep(op, params) for op, params in steps]

    def create_job(self, files: list[str],
                   steps: list[ProcessingStep]) -> BatchJob:
        """Create a new batch job."""
        import hashlib
        job_id = hashlib.sha1(
            f"{time.time()}{len(files)}".encode()
        ).hexdigest()[:10]

        job = BatchJob(
            job_id=job_id,
            files=files,
            steps=steps,
            created=time.time(),
        )
        self.jobs.append(job)
        return job

    def _read_wav(self, path: str) -> tuple[list[float], int]:
        """Read WAV as float samples."""
        import struct
        import wave
        with wave.open(path, "r") as wf:
            sr = wf.getframerate()
            sw = wf.getsampwidth()
            raw = wf.readframes(wf.getnframes())
        if sw == 2:
            vals = struct.unpack(f"<{len(raw) // 2}h", raw)
            return [v / 32768.0 for v in vals], sr
        return [], sr

    def _write_wav(self, path: str, samples: list[float],
                   sr: int = SAMPLE_RATE) -> None:
        """Write float samples to WAV."""
        import struct
        import wave
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            data = struct.pack(
                f"<{len(samples)}h",
                *[max(-32768, min(32767, int(s * 32767))) for s in samples]
            )
            wf.writeframes(data)

    def process_samples(self, samples: list[float],
                        steps: list[ProcessingStep]) -> list[float]:
        """Apply processing steps to samples."""
        result = samples
        for step in steps:
            op_func = OPERATIONS.get(step.operation)
            if op_func:
                result = op_func(result, step.params)
        return result

    def execute(self, job: BatchJob) -> BatchJob:
        """Execute a batch job."""
        job.status = "running"

        for filepath in job.files:
            result: dict = {"file": filepath, "status": "pending"}
            try:
                if os.path.exists(filepath):
                    samples, sr = self._read_wav(filepath)
                else:
                    # Generate test signal
                    import math
                    n = int(SAMPLE_RATE * 0.5)
                    samples = [0.8 * math.sin(2 * math.pi * 432 * i / SAMPLE_RATE)
                               for i in range(n)]
                    sr = SAMPLE_RATE

                processed = self.process_samples(samples, job.steps)

                base = os.path.splitext(os.path.basename(filepath))[0]
                out_path = os.path.join(self.output_dir,
                                         f"{base}_processed.wav")
                self._write_wav(out_path, processed, sr)

                result["status"] = "success"
                result["output"] = out_path
                result["input_samples"] = len(samples)
                result["output_samples"] = len(processed)

            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)

            job.results.append(result)

        job.status = "completed"
        job.completed = time.time()
        return job

    def get_available_operations(self) -> list[str]:
        """List registered operations."""
        return sorted(OPERATIONS.keys())

    def get_summary(self) -> dict:
        """Get processor summary."""
        return {
            "total_jobs": len(self.jobs),
            "completed": sum(1 for j in self.jobs
                              if j.status == "completed"),
            "operations": self.get_available_operations(),
        }


def main() -> None:
    import math
    print("Batch Processor")

    processor = BatchProcessor()

    # Create test WAV
    n = int(SAMPLE_RATE * 0.5)
    samples = [0.8 * math.sin(2 * math.pi * 432 * i / SAMPLE_RATE)
               for i in range(n)]
    test_path = os.path.join(processor.output_dir, "test_input.wav")
    processor._write_wav(test_path, samples)

    # Build pipeline
    steps = processor.create_pipeline(
        ("normalize", {"target_db": -3.0}),
        ("fade_in", {"ms": 20}),
        ("fade_out", {"ms": 50}),
        ("phi_compress", {}),
    )

    job = processor.create_job([test_path], steps)
    result = processor.execute(job)

    print(f"  Job: {result.job_id}")
    print(f"  Status: {result.status}")
    for r in result.results:
        print(f"    {r['status']}: {r.get('output', 'N/A')}")

    print(f"\n  Available ops: {processor.get_available_operations()}")
    print("Done.")


if __name__ == "__main__":
    main()
