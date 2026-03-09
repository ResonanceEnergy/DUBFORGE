"""Tests for engine.project_manager — Session 183."""
import pytest
from engine.project_manager import ProjectManager


class TestProjectManager:
    def test_create(self, tmp_path):
        pm = ProjectManager(str(tmp_path))
        assert isinstance(pm, ProjectManager)

    def test_create_project(self, tmp_path):
        pm = ProjectManager(str(tmp_path))
        result = pm.create_project("test_project")
        assert result is not None
