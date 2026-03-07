"""Shared test fixtures for DUBFORGE test suite."""
import pytest
from pathlib import Path


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """Provide a temporary output directory for tests that write files."""
    out = tmp_path / "output"
    out.mkdir()
    return out


@pytest.fixture
def configs_dir() -> Path:
    """Path to the project configs directory."""
    return Path(__file__).parent.parent / "configs"
