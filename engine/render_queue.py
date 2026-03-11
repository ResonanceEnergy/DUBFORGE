"""
DUBFORGE — Render Queue Engine  (Session 150)

Async-style render queue with progress tracking for SUBPHONICS.
Processes render jobs sequentially with callbacks and status.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from engine.config_loader import PHI
class JobStatus(Enum):
    QUEUED = "queued"
    RENDERING = "rendering"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class RenderJob:
    """A single render job in the queue."""
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    module: str = ""
    command: str = ""
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0  # 0.0 to 1.0
    result_text: str = ""
    output_path: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    finished_at: float = 0.0

    @property
    def elapsed_ms(self) -> float:
        if self.finished_at and self.started_at:
            return round((self.finished_at - self.started_at) * 1000, 1)
        if self.started_at:
            return round((time.time() - self.started_at) * 1000, 1)
        return 0.0

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "module": self.module,
            "command": self.command,
            "status": self.status.value,
            "progress": self.progress,
            "result_text": self.result_text,
            "output_path": self.output_path,
            "elapsed_ms": self.elapsed_ms,
            "metadata": self.metadata,
        }


class RenderQueue:
    """Thread-safe render queue with progress tracking."""

    def __init__(self, max_history: int = 100):
        self._queue: list[RenderJob] = []
        self._history: list[RenderJob] = []
        self._max_history = max_history
        self._lock = threading.Lock()
        self._running = False
        self._worker: threading.Thread | None = None
        self._engine = None

    def set_engine(self, engine) -> None:
        """Set the SUBPHONICS engine for processing."""
        self._engine = engine

    def enqueue(self, command: str, module: str = "") -> RenderJob:
        """Add a render job to the queue."""
        job = RenderJob(command=command, module=module)
        with self._lock:
            self._queue.append(job)
        return job

    def cancel(self, job_id: str) -> bool:
        """Cancel a queued job."""
        with self._lock:
            for job in self._queue:
                if job.job_id == job_id and job.status == JobStatus.QUEUED:
                    job.status = JobStatus.CANCELLED
                    job.finished_at = time.time()
                    self._history.append(job)
                    self._queue.remove(job)
                    return True
        return False

    def get_status(self, job_id: str) -> RenderJob | None:
        """Get status of a specific job."""
        with self._lock:
            for job in self._queue:
                if job.job_id == job_id:
                    return job
            for job in self._history:
                if job.job_id == job_id:
                    return job
        return None

    def get_queue_status(self) -> dict:
        """Get overall queue status."""
        with self._lock:
            queued = [j for j in self._queue if j.status == JobStatus.QUEUED]
            rendering = [j for j in self._queue
                         if j.status == JobStatus.RENDERING]
            done = [j for j in self._history if j.status == JobStatus.DONE]
            errors = [j for j in self._history if j.status == JobStatus.ERROR]
        return {
            "queued": len(queued),
            "rendering": len(rendering),
            "done": len(done),
            "errors": len(errors),
            "total_processed": len(self._history),
            "queue": [j.to_dict() for j in self._queue],
            "recent": [j.to_dict() for j in self._history[-5:]],
        }

    def process_next(self) -> RenderJob | None:
        """Process the next job in the queue synchronously."""
        with self._lock:
            pending = [j for j in self._queue
                       if j.status == JobStatus.QUEUED]
            if not pending:
                return None
            job = pending[0]
            job.status = JobStatus.RENDERING
            job.started_at = time.time()

        try:
            if self._engine:
                msg = self._engine.process_message(job.command)
                job.result_text = msg.content
                job.metadata = msg.metadata
            else:
                job.result_text = f"[dry-run] Would execute: {job.command}"
            job.progress = 1.0
            job.status = JobStatus.DONE
        except Exception as e:
            job.result_text = f"Error: {e}"
            job.status = JobStatus.ERROR

        job.finished_at = time.time()
        with self._lock:
            if job in self._queue:
                self._queue.remove(job)
            self._history.append(job)
            # Trim history
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
        return job

    def process_all(self) -> list[RenderJob]:
        """Process all queued jobs sequentially."""
        results = []
        while True:
            job = self.process_next()
            if job is None:
                break
            results.append(job)
        return results

    def start_worker(self) -> None:
        """Start background worker thread."""
        if self._running:
            return
        self._running = True
        self._worker = threading.Thread(
            target=self._worker_loop, daemon=True,
        )
        self._worker.start()

    def stop_worker(self) -> None:
        """Stop background worker thread."""
        self._running = False
        if self._worker:
            self._worker.join(timeout=2.0)
            self._worker = None

    def _worker_loop(self) -> None:
        """Background worker loop."""
        while self._running:
            job = self.process_next()
            if job is None:
                time.sleep(0.1)  # Idle polling interval

    def clear(self) -> int:
        """Clear all queued (not rendering) jobs."""
        with self._lock:
            count = 0
            to_remove = []
            for job in self._queue:
                if job.status == JobStatus.QUEUED:
                    job.status = JobStatus.CANCELLED
                    job.finished_at = time.time()
                    to_remove.append(job)
                    count += 1
            for job in to_remove:
                self._queue.remove(job)
                self._history.append(job)
            return count


# Module-level singleton
_queue: RenderQueue | None = None


def get_queue() -> RenderQueue:
    """Get or create the global render queue."""
    global _queue
    if _queue is None:
        _queue = RenderQueue()
    return _queue


def queue_status_text() -> str:
    """Get human-readable queue status."""
    q = get_queue()
    status = q.get_queue_status()
    lines = [
        f"**Render Queue** — {status['queued']} queued, "
        f"{status['rendering']} rendering, "
        f"{status['done']} done, {status['errors']} errors",
    ]
    if status["queue"]:
        lines.append("\n**Active:**")
        for j in status["queue"]:
            lines.append(f"  [{j['status']}] {j['command']} "
                          f"({j['elapsed_ms']}ms)")
    if status["recent"]:
        lines.append("\n**Recent:**")
        for j in status["recent"]:
            lines.append(f"  [{j['status']}] {j['command']} "
                          f"({j['elapsed_ms']}ms)")
    return "\n".join(lines)


def main() -> None:
    print("Render Queue Engine")
    q = get_queue()
    q.enqueue("render sub bass", "sub_bass")
    q.enqueue("make drums", "drum_generator")
    q.enqueue("generate wobble", "wobble_bass")
    results = q.process_all()
    for r in results:
        print(f"  [{r.status.value}] {r.command} — {r.elapsed_ms}ms")
    print(queue_status_text())
    print("Done.")


if __name__ == "__main__":
    main()
