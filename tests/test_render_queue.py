"""Tests for engine.render_queue — Session 150."""
import pytest
from engine.render_queue import RenderQueue, RenderJob, JobStatus


class TestRenderQueue:
    def test_enqueue(self):
        q = RenderQueue()
        job = q.enqueue("make a sub")
        assert isinstance(job, RenderJob)
        assert job.status == JobStatus.QUEUED

    def test_cancel(self):
        q = RenderQueue()
        job = q.enqueue("test")
        assert q.cancel(job.job_id) is True

    def test_get_status(self):
        q = RenderQueue()
        job = q.enqueue("test")
        s = q.get_status(job.job_id)
        assert s is not None
        assert s.job_id == job.job_id

    def test_clear(self):
        q = RenderQueue()
        q.enqueue("a")
        q.enqueue("b")
        count = q.clear()
        assert count >= 2

    def test_queue_status(self):
        q = RenderQueue()
        s = q.get_queue_status()
        assert isinstance(s, dict)
