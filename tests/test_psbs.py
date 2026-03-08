"""Tests for engine.psbs — Phase-Separated Bass System (v2.8.0)."""

import os
import tempfile

import numpy as np

from engine.psbs import (
    PSBSPreset,
    _render_layer,
    calculate_phase_coherence,
    default_psbs,
    export_layer_stems,
    export_phi_ladder,
    export_wavetable,
    phi_crossovers,
    render_psbs_cycle,
    render_psbs_layer_stem,
    render_psbs_multiframe,
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

    def test_default_custom_root_hz(self):
        p = default_psbs(root_hz=110.0)
        assert p.root_hz == 110.0

    def test_weapon_custom_root_hz(self):
        p = weapon_psbs(root_hz=82.0)
        assert p.root_hz == 82.0


class TestPhaseCoherence:
    def test_coherence_is_dict(self):
        p = default_psbs()
        result = calculate_phase_coherence(p.layers, 40.0)
        assert isinstance(result, dict)
        assert "root_hz" in result


class TestRenderLayer:
    """Tests for the per-layer render function."""

    def test_sine_layer(self):
        p = default_psbs()
        layer = p.layers[0]  # sub — sine
        rendered = _render_layer(layer, p.root_hz, 2048, morph=0.0)
        assert isinstance(rendered, np.ndarray)
        assert len(rendered) == 2048

    def test_morph_changes_output(self):
        p = default_psbs()
        layer = p.layers[0]
        a = _render_layer(layer, p.root_hz, 2048, morph=0.0)
        b = _render_layer(layer, p.root_hz, 2048, morph=1.0)
        # Morph should change the output when distortion > 0
        if layer.distortion > 0:
            assert not np.allclose(a, b)

    def test_noise_waveform(self):
        from engine.psbs import BassLayer
        layer = BassLayer(
            name="noise_test", freq_low=200, freq_high=800,
            waveform="noise", gain_db=0, phase_offset_deg=0,
            distortion=0, stereo_width=0, note=""
        )
        rendered = _render_layer(layer, 55.0, 2048, morph=0.5)
        assert len(rendered) == 2048

    def test_fm_waveform(self):
        from engine.psbs import BassLayer
        layer = BassLayer(
            name="fm_test", freq_low=100, freq_high=400,
            waveform="fm", gain_db=0, phase_offset_deg=0,
            distortion=0.5, stereo_width=0, note=""
        )
        rendered = _render_layer(layer, 55.0, 2048, morph=0.0)
        assert len(rendered) == 2048

    def test_saw_waveform(self):
        from engine.psbs import BassLayer
        layer = BassLayer(
            name="saw_test", freq_low=100, freq_high=400,
            waveform="saw", gain_db=0, phase_offset_deg=0,
            distortion=0, stereo_width=0, note=""
        )
        rendered = _render_layer(layer, 55.0, 1024, morph=0.0)
        assert len(rendered) == 1024

    def test_square_waveform(self):
        from engine.psbs import BassLayer
        layer = BassLayer(
            name="sq_test", freq_low=100, freq_high=400,
            waveform="square", gain_db=0, phase_offset_deg=0,
            distortion=0, stereo_width=0, note=""
        )
        rendered = _render_layer(layer, 55.0, 2048, morph=0.0)
        assert len(rendered) == 2048
        # Square wave: values should be +1 or -1
        assert np.all(np.isin(rendered, [-1.0, 0.0, 1.0]))

    def test_triangle_waveform(self):
        from engine.psbs import BassLayer
        layer = BassLayer(
            name="tri_test", freq_low=100, freq_high=400,
            waveform="triangle", gain_db=-6, phase_offset_deg=0,
            distortion=0, stereo_width=0, note=""
        )
        rendered = _render_layer(layer, 55.0, 2048, morph=0.0)
        assert len(rendered) == 2048

    def test_distortion_increases_rms(self):
        from engine.psbs import BassLayer
        layer_clean = BassLayer(
            name="clean", freq_low=100, freq_high=400,
            waveform="sine", gain_db=0, phase_offset_deg=0,
            distortion=0.0, stereo_width=0, note=""
        )
        layer_dirty = BassLayer(
            name="dirty", freq_low=100, freq_high=400,
            waveform="sine", gain_db=0, phase_offset_deg=0,
            distortion=0.8, stereo_width=0, note=""
        )
        clean = _render_layer(layer_clean, 55.0, 2048, morph=0.5)
        dirty = _render_layer(layer_dirty, 55.0, 2048, morph=0.5)
        # Distortion (tanh saturation) should increase RMS relative to peak
        rms_clean = np.sqrt(np.mean(clean ** 2))
        rms_dirty = np.sqrt(np.mean(dirty ** 2))
        assert rms_dirty > rms_clean


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

    def test_morph_zero(self):
        p = default_psbs()
        cycle = render_psbs_cycle(p, morph=0.0)
        assert isinstance(cycle, np.ndarray)
        assert len(cycle) == 2048

    def test_morph_one(self):
        p = default_psbs()
        cycle = render_psbs_cycle(p, morph=1.0)
        assert isinstance(cycle, np.ndarray)
        assert np.max(np.abs(cycle)) <= 1.0 + 1e-6


class TestRenderMultiframe:
    """Tests for the 256-frame multi-frame renderer."""

    def test_returns_correct_number_of_frames(self):
        p = default_psbs()
        frames = render_psbs_multiframe(p, n_frames=256, n_samples=2048)
        assert len(frames) == 256

    def test_each_frame_correct_length(self):
        p = default_psbs()
        frames = render_psbs_multiframe(p, n_frames=64, n_samples=1024)
        for frame in frames:
            assert isinstance(frame, np.ndarray)
            assert len(frame) == 1024

    def test_frames_are_normalized(self):
        p = weapon_psbs()
        frames = render_psbs_multiframe(p, n_frames=16, n_samples=2048)
        for frame in frames:
            assert np.max(np.abs(frame)) <= 1.0 + 1e-6

    def test_first_and_last_frame_differ(self):
        p = weapon_psbs()
        frames = render_psbs_multiframe(p, n_frames=256, n_samples=2048)
        # Morph changes sound — first vs last should differ
        assert not np.allclose(frames[0], frames[-1])

    def test_single_frame(self):
        p = default_psbs()
        frames = render_psbs_multiframe(p, n_frames=1, n_samples=2048)
        assert len(frames) == 1
        assert len(frames[0]) == 2048


class TestRenderLayerStem:
    """Tests for per-layer multi-frame stem rendering."""

    def test_renders_sub_layer(self):
        p = default_psbs()
        layer_name = p.layers[0].name
        frames = render_psbs_layer_stem(p, layer_name, n_frames=32,
                                        n_samples=2048)
        assert len(frames) == 32
        for frame in frames:
            assert len(frame) == 2048

    def test_each_frame_normalized(self):
        p = default_psbs()
        layer_name = p.layers[0].name
        frames = render_psbs_layer_stem(p, layer_name, n_frames=16,
                                        n_samples=2048)
        for frame in frames:
            assert np.max(np.abs(frame)) <= 1.0 + 1e-6

    def test_invalid_layer_raises(self):
        p = default_psbs()
        try:
            render_psbs_layer_stem(p, "NONEXISTENT_LAYER")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_all_layers_render(self):
        p = default_psbs()
        for layer in p.layers:
            frames = render_psbs_layer_stem(p, layer.name, n_frames=4,
                                            n_samples=512)
            assert len(frames) == 4


class TestExportWavetable:
    def test_writes_wav_file(self):
        p = default_psbs()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_wavetable(p, out_dir=tmpdir)
            assert os.path.exists(path)
            assert path.endswith(".wav")

    def test_multiframe_file_size(self):
        """256 frames × 2048 samples × 2 bytes = 1,048,576 bytes minimum."""
        p = default_psbs()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_wavetable(p, out_dir=tmpdir, n_frames=256,
                                    n_samples=2048)
            size = os.path.getsize(path)
            # WAV header + clm chunk + data ≈ 1 MB+
            assert size > 1_000_000

    def test_custom_frame_count(self):
        p = default_psbs()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_wavetable(p, out_dir=tmpdir, n_frames=64,
                                    n_samples=2048)
            assert os.path.exists(path)

    def test_weapon_preset_exports(self):
        p = weapon_psbs()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_wavetable(p, out_dir=tmpdir)
            assert os.path.exists(path)


class TestExportLayerStems:
    """Tests for per-layer stem export."""

    def test_exports_all_layers(self):
        p = default_psbs()
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = export_layer_stems(p, out_dir=tmpdir, n_frames=16,
                                       n_samples=1024)
            assert len(paths) == len(p.layers)
            for path in paths:
                assert os.path.exists(path)
                assert path.endswith(".wav")

    def test_stem_filenames_contain_layer_name(self):
        p = default_psbs()
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = export_layer_stems(p, out_dir=tmpdir, n_frames=4,
                                       n_samples=512)
            for layer, path in zip(p.layers, paths):
                assert layer.name in os.path.basename(path)


class TestExportPhiLadder:
    """Tests for phi-ladder multi-root export."""

    def test_exports_eight_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = export_phi_ladder(default_psbs, out_dir=tmpdir,
                                      n_frames=8)
            assert len(paths) == 8
            for path in paths:
                assert os.path.exists(path)
                assert path.endswith(".wav")

    def test_files_differ(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = export_phi_ladder(default_psbs, out_dir=tmpdir,
                                      n_frames=4)
            sizes = [os.path.getsize(p) for p in paths]
            # All same frame count, so sizes should be equal
            assert len(set(sizes)) == 1

    def test_all_presets_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for preset_fn in [default_psbs, weapon_psbs, wook_psbs]:
                p = preset_fn()
                path = export_wavetable(p, out_dir=tmpdir)
                assert os.path.exists(path)
