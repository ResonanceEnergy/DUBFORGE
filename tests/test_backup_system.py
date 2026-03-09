"""Tests for engine.backup_system — Session 191."""
import pytest
from engine.backup_system import BackupSystem


class TestBackupSystem:
    def test_create(self, tmp_path):
        bs = BackupSystem(str(tmp_path / "backups"))
        assert isinstance(bs, BackupSystem)
