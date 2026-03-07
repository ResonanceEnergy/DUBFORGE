"""Tests for engine.config_loader — YAML loading, constants, validation."""

import pytest
from engine.config_loader import (
    PHI, FIBONACCI, A4_432, A4_440,
    load_config, get_config_value, list_configs,
    validate_config, validate_all_configs,
)


# ── Constants ─────────────────────────────────────────────────────────────

class TestConstants:
    def test_phi_value(self):
        assert abs(PHI - 1.618033988749894) < 1e-12

    def test_fibonacci_starts_with_1_1(self):
        assert FIBONACCI[:2] == [1, 1]

    def test_fibonacci_sequence_valid(self):
        for i in range(2, len(FIBONACCI)):
            assert FIBONACCI[i] == FIBONACCI[i - 1] + FIBONACCI[i - 2]

    def test_a4_432(self):
        assert A4_432 == 432.0

    def test_a4_440(self):
        assert A4_440 == 440.0


# ── Config Loading ────────────────────────────────────────────────────────

class TestLoadConfig:
    def test_load_known_config(self):
        """fibonacci_blueprint_pack_v1.yaml should load without error."""
        data = load_config("fibonacci_blueprint_pack_v1")
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_load_missing_config_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent_config_xyz")

    def test_list_configs_returns_names(self):
        names = list_configs()
        assert isinstance(names, list)
        assert "fibonacci_blueprint_pack_v1" in names


class TestGetConfigValue:
    def test_nested_lookup(self):
        val = get_config_value("fibonacci_blueprint_pack_v1", "version", default=None)
        assert val is not None

    def test_missing_key_returns_default(self):
        val = get_config_value("fibonacci_blueprint_pack_v1", "no_such_key_xyz", default=42)
        assert val == 42

    def test_missing_config_raises(self):
        with pytest.raises(FileNotFoundError):
            get_config_value("no_such_config_xyz", "key", default="fallback")


# ── Validation ────────────────────────────────────────────────────────────

class TestValidation:
    def test_validate_known_config(self):
        errors = validate_config("fibonacci_blueprint_pack_v1")
        assert errors == [], f"Unexpected errors: {errors}"

    def test_validate_sb_corpus(self):
        errors = validate_config("sb_corpus_v1")
        assert errors == []

    def test_validate_missing_config(self):
        errors = validate_config("no_such_xyz")
        assert len(errors) == 1
        assert "not found" in errors[0]

    def test_validate_all_configs_runs(self):
        results = validate_all_configs()
        assert isinstance(results, dict)
