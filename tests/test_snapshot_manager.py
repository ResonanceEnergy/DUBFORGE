"""Tests for engine.snapshot_manager — Session 206."""
import pytest
from engine.snapshot_manager import SnapshotManager


class TestSnapshotManager:
    def test_create(self, tmp_path):
        sm = SnapshotManager(data_dir=str(tmp_path / "snapshots"))
        assert isinstance(sm, SnapshotManager)

    def test_capture_recall(self, tmp_path):
        sm = SnapshotManager(data_dir=str(tmp_path / "snapshots"))
        state = {"volume": 0.8, "freq": 440}
        snap = sm.capture("snap1", state)
        recalled = sm.recall(snap.snapshot_id)
        assert recalled["volume"] == 0.8
