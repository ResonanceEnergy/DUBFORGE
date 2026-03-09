"""Tests for engine.preset_vcs — Session 185."""
import pytest
from engine.preset_vcs import PresetVCS


class TestPresetVCS:
    def test_create(self):
        vcs = PresetVCS("test_preset")
        assert isinstance(vcs, PresetVCS)

    def test_commit(self):
        vcs = PresetVCS("test_preset")
        data = {"frequency": 55.0, "drive": 3.0}
        result = vcs.commit(data, "initial commit")
        assert result is not None
        assert result.message == "initial commit"

    def test_log(self):
        vcs = PresetVCS("test_preset")
        vcs.commit({"freq": 55}, "v1")
        vcs.commit({"freq": 110}, "v2")
        log = vcs.log()
        assert isinstance(log, list)
        assert len(log) >= 2
