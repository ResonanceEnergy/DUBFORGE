"""Tests for engine.psbs — Phase-Separated Bass System."""

import os
import tempfile

import numpy as np

from engine.psbs import (
    PSBSPreset,
    calculate_phase_coherence,
    default_psbs,
    export_wavetable,
    phi_crossovers,
    render_psbs_cycle,
    weapon_psbs,
    wook_psbs,
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


class TestRenderPSBSCycle:
    def test_returns_numpy_array(self):
        p = default_psbs()
        cycle = render_psbs_cycle(p)
        assert isinstance(cycle, np.ndarray)
        assert len(cycle) == 2048

    def test_custom_size(self):
        p = default_psbs()
        cycle = render_psbs_cycle(p, n_samples=4096)
        assert len(cycle) == 4096

    def test_normalized(self):
        p = weapon_psbs()
        cycle = render_psbs_cycle(p)
        assert np.max(np.abs(cycle)) <= 1.0 + 1e-6


class TestExportWavetable:
    def test_writes_wav_file(self):
        p = default_psbs()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_wavetable(p, out_dir=tmpdir)
            assert os.path.exists(path)
            assert path.endswith(".wav")

    def test_all_presets_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for preset_fn in [default_psbs, weapon_psbs, wook_psbs]:
                p = preset_fn()
                path = export_wavetable(p, out_dir=tmpdir)
                assert os.path.exists(path)
