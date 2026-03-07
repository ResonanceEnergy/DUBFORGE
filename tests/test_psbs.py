"""Tests for engine.psbs — Phase-Separated Bass System."""

import pytest
from engine.psbs import (
    BassLayer,
    PSBSPreset,
    phi_crossovers,
    default_psbs,
    weapon_psbs,
    wook_psbs,
    calculate_phase_coherence,
)


class TestPhiCrossovers:
    def test_returns_list(self):
        crossovers = phi_crossovers(40.0)
        assert isinstance(crossovers, list)
        assert len(crossovers) > 0

    def test_ascending_order(self):
        crossovers = phi_crossovers(40.0)
        for i in range(1, len(crossovers)):
            assert crossovers[i] > crossovers[i - 1]


class TestPresets:
    def test_default_has_layers(self):
        p = default_psbs()
        assert isinstance(p, PSBSPreset)
        assert len(p.layers) > 0

    def test_weapon_has_layers(self):
        p = weapon_psbs()
        assert isinstance(p, PSBSPreset)
        assert len(p.layers) > 0

    def test_wook_has_layers(self):
        p = wook_psbs()
        assert isinstance(p, PSBSPreset)
        assert len(p.layers) > 0


class TestPhaseCoherence:
    def test_coherence_is_dict(self):
        p = default_psbs()
        result = calculate_phase_coherence(p.layers, 40.0)
        assert isinstance(result, dict)
        assert "root_hz" in result
