"""
DUBFORGE Integration Test Suite — ~550+ tests

Cross-module signal flow, bank/preset consistency, manifest writers,
export functions, CLI, config loader, memory system, dojo quality,
ALS generator, and phi-constant verification.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SR = 44100


def _tone(freq: float = 440.0, dur: float = 0.3) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    return np.sin(2 * np.pi * freq * t)


def _stereo_tone(freq: float = 440.0, dur: float = 0.3) -> np.ndarray:
    mono = _tone(freq, dur)
    return np.column_stack([mono, mono])


def _wav(path: Path, freq: float = 440.0, dur: float = 0.3) -> Path:
    sig = _tone(freq, dur)
    data = np.clip(sig * 32767, -32768, 32767).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(data.tobytes())
    return path


# ═══════════════════════════════════════════════════════════════════════════
# 1  CROSS-MODULE SIGNAL FLOW  (30+ tests)
# ═══════════════════════════════════════════════════════════════════════════

class TestCrossModuleSignalFlow:
    """Verify outputs from one module can be consumed by another."""

    # --- phi_core → harmonic_analysis ---
    def test_phi_core_to_harmonic_analysis(self):
        from engine.phi_core import generate_frame, phi_amplitude_curve, phi_harmonic_series
        partials = phi_harmonic_series(55.0, 5)
        amps = phi_amplitude_curve(5)
        frame = generate_frame(partials, amps, size=SR)
        from engine.harmonic_analysis import AnalysisPreset, analyze_spectral_peaks
        preset = AnalysisPreset(name="test", analysis_type="spectral_peaks")
        peaks = analyze_spectral_peaks(frame, preset, SR)
        assert isinstance(peaks, list)

    def test_phi_core_frame_is_numpy(self):
        from engine.phi_core import fibonacci_harmonic_series, generate_frame, phi_amplitude_curve
        partials = fibonacci_harmonic_series(100.0)
        amps = phi_amplitude_curve(len(partials))
        frame = generate_frame(partials, amps)
        assert isinstance(frame, np.ndarray)
        assert frame.ndim == 1

    def test_phi_core_morph_all_frames_valid(self):
        from engine.phi_core import (
            generate_frame,
            morph_frames,
            phi_amplitude_curve,
            phi_harmonic_series,
        )
        p1 = phi_harmonic_series(55, 4)
        p2 = phi_harmonic_series(110, 4)
        a = phi_amplitude_curve(4)
        f1 = generate_frame(p1, a)
        f2 = generate_frame(p2, a)
        frames = morph_frames(f1, f2, 8)
        assert len(frames) == 8
        for f in frames:
            assert np.max(np.abs(f)) <= 1.0 + 1e-9

    # --- sub_bass → sidechain → stereo_imager ---
    def test_sub_bass_to_sidechain(self):
        from engine.sidechain import ALL_SIDECHAIN_BANKS, apply_sidechain
        sig = _tone(50.0, 0.5)
        bank = list(ALL_SIDECHAIN_BANKS.values())[0]()
        preset = bank.presets[0]
        out = apply_sidechain(sig, preset, SR)
        assert out.shape == sig.shape

    def test_sidechain_to_stereo_imager(self):
        from engine.sidechain import ALL_SIDECHAIN_BANKS, apply_sidechain
        from engine.stereo_imager import ALL_STEREO_BANKS, apply_stereo_imaging
        sig = _tone(80.0, 0.5)
        sc_bank = list(ALL_SIDECHAIN_BANKS.values())[0]()
        sc_out = apply_sidechain(sig, sc_bank.presets[0], SR)
        st_bank = list(ALL_STEREO_BANKS.values())[0]()
        st_out = apply_stereo_imaging(sc_out, st_bank.presets[0], SR)
        assert st_out.ndim >= 1

    def test_sub_bass_full_chain(self):
        from engine.sidechain import ALL_SIDECHAIN_BANKS, apply_sidechain
        sig = _tone(40.0, 0.3)
        for name, fn in ALL_SIDECHAIN_BANKS.items():
            bank = fn()
            processed = apply_sidechain(sig, bank.presets[0], SR)
            assert processed.shape == sig.shape

    # --- mastering_chain ---
    def test_mastering_chain_mono(self):
        from engine.mastering_chain import master
        sig = _tone(200.0, 0.5)
        out, report = master(sig, SR)
        assert out.shape == sig.shape

    def test_mastering_chain_stereo(self):
        from engine.mastering_chain import master
        sig = _stereo_tone(200.0, 0.5)
        out, report = master(sig, SR)
        assert out.shape == sig.shape

    def test_mastering_chain_report(self):
        from engine.mastering_chain import MasterSettings, master
        sig = _tone(440.0, 0.3)
        _, report = master(sig, SR, MasterSettings())
        assert hasattr(report, "input_peak_db")
        assert hasattr(report, "input_rms_db")

    # --- lead_synth → multiband_distortion → reverb_delay ---
    def test_multiband_distortion_on_tone(self):
        from engine.multiband_distortion import ALL_MULTIBAND_DIST_BANKS, apply_multiband_distortion
        sig = _tone(300.0, 0.3)
        bank = list(ALL_MULTIBAND_DIST_BANKS.values())[0]()
        out = apply_multiband_distortion(sig, bank.presets[0], SR)
        assert out.shape == sig.shape

    def test_reverb_delay_on_tone(self):
        from engine.reverb_delay import ALL_REVERB_DELAY_BANKS, apply_reverb_delay
        sig = _tone(440.0, 0.3)
        bank = list(ALL_REVERB_DELAY_BANKS.values())[0]()
        out = apply_reverb_delay(sig, bank.presets[0], SR)
        assert isinstance(out, np.ndarray)

    def test_distortion_then_reverb(self):
        from engine.multiband_distortion import ALL_MULTIBAND_DIST_BANKS, apply_multiband_distortion
        from engine.reverb_delay import ALL_REVERB_DELAY_BANKS, apply_reverb_delay
        sig = _tone(220.0, 0.3)
        dist_bank = list(ALL_MULTIBAND_DIST_BANKS.values())[0]()
        distorted = apply_multiband_distortion(sig, dist_bank.presets[0], SR)
        rev_bank = list(ALL_REVERB_DELAY_BANKS.values())[0]()
        reverbed = apply_reverb_delay(distorted, rev_bank.presets[0], SR)
        assert isinstance(reverbed, np.ndarray)
        assert len(reverbed) >= len(sig)

    # --- convolution ---
    def test_convolution_on_tone(self):
        from engine.convolution import ALL_CONVOLUTION_BANKS, apply_convolution
        sig = _tone(440.0, 0.3)
        bank = list(ALL_CONVOLUTION_BANKS.values())[0]()
        out = apply_convolution(sig, bank.presets[0], SR)
        assert isinstance(out, np.ndarray)

    # --- noise_generator → glitch_engine ---
    def test_noise_to_glitch(self):
        from engine.glitch_engine import ALL_GLITCH_BANKS, synthesize_glitch
        bank = list(ALL_GLITCH_BANKS.values())[0]()
        out = synthesize_glitch(bank.presets[0], SR)
        assert isinstance(out, np.ndarray)

    # --- phi_analyzer ---
    def test_phi_analyzer_on_tone(self):
        from engine.phi_analyzer import analyze_phi_coherence
        sig = _tone(432.0, 0.5)
        score = analyze_phi_coherence(sig)
        assert hasattr(score, "composite")
        assert 0.0 <= score.composite <= 1.0

    def test_phi_analyzer_wav(self, tmp_path):
        from engine.phi_analyzer import analyze_wav_phi
        wav_p = _wav(tmp_path / "test.wav", 432.0, 0.5)
        score = analyze_wav_phi(str(wav_p))
        assert hasattr(score, "composite")

    # --- harmonic_analysis multiple analyzers ---
    def test_analyze_harmonic_series(self):
        from engine.harmonic_analysis import AnalysisPreset, analyze_harmonic_series
        sig = _tone(110.0, 0.5)
        preset = AnalysisPreset(name="test", analysis_type="harmonic_series")
        result = analyze_harmonic_series(sig, preset, SR)
        assert isinstance(result, (dict, list))

    def test_analyze_phi_relations(self):
        from engine.harmonic_analysis import AnalysisPreset, analyze_phi_relations
        sig = _tone(432.0, 0.5)
        preset = AnalysisPreset(name="test", analysis_type="phi_detection")
        result = analyze_phi_relations(sig, preset, SR)
        assert isinstance(result, (dict, list))

    def test_analyze_spectral_flux(self):
        from engine.harmonic_analysis import AnalysisPreset, analyze_spectral_flux
        sig = np.concatenate([_tone(200, 0.2), _tone(400, 0.2)])
        preset = AnalysisPreset(name="test", analysis_type="spectral_flux")
        result = analyze_spectral_flux(sig, preset, SR)
        assert result is not None or result == [] or result == 0.0

    def test_analyze_roughness(self):
        from engine.harmonic_analysis import AnalysisPreset, analyze_roughness
        sig = _tone(200.0, 0.3)
        preset = AnalysisPreset(name="test", analysis_type="roughness")
        result = analyze_roughness(sig, preset, SR)
        assert result is not None

    # --- stem_mixer ---
    def test_stem_mixer_simple(self):
        from engine.stem_mixer import MixPreset, mix_stems_simple
        stems = [_tone(100, 0.2), _tone(200, 0.2), _tone(300, 0.2)]
        preset = MixPreset("test", "simple")
        out = mix_stems_simple(stems, preset)
        assert out.ndim == 2
        assert out.shape[1] == 2

    def test_stem_mixer_phi_weight(self):
        from engine.stem_mixer import MixPreset, mix_stems_phi_weight
        stems = [_tone(100 * i, 0.2) for i in range(1, 5)]
        preset = MixPreset("test", "phi_weight")
        out = mix_stems_phi_weight(stems, preset)
        assert out.shape[1] == 2

    def test_stem_mixer_all_modes(self):
        from engine.stem_mixer import ALL_MIX_BANKS, mix_stems
        stems = [_tone(100 * i, 0.1) for i in range(1, 4)]
        for name, fn in ALL_MIX_BANKS.items():
            bank = fn()
            for preset in bank.presets:
                out = mix_stems(stems, preset)
                assert out.ndim == 2

    # --- growl_resampler ---
    def test_growl_resample_pipeline(self):
        from engine.growl_resampler import generate_saw_source, growl_resample_pipeline
        src = generate_saw_source()
        out = growl_resample_pipeline(src)
        assert isinstance(out, (np.ndarray, list))
        if isinstance(out, list):
            assert len(out) > 0
            assert isinstance(out[0], np.ndarray)
        else:
            assert len(out) > 0

    def test_growl_waveshape(self):
        from engine.growl_resampler import waveshape_distortion
        sig = _tone(200, 0.1)
        out = waveshape_distortion(sig)
        assert out.shape == sig.shape

    def test_growl_pitch_shift(self):
        from engine.growl_resampler import pitch_shift
        sig = _tone(200, 0.1)
        out = pitch_shift(sig, 7)
        assert isinstance(out, np.ndarray)

    def test_growl_bit_reduce(self):
        from engine.growl_resampler import bit_reduce
        sig = _tone(200, 0.1)
        out = bit_reduce(sig, 8)
        assert out.shape == sig.shape

    # --- cross-module: mastering after mix ---
    def test_mix_then_master(self):
        from engine.mastering_chain import master
        from engine.stem_mixer import MixPreset, mix_stems_simple
        stems = [_tone(100, 0.2), _tone(200, 0.2)]
        preset = MixPreset("test", "simple")
        mixed = mix_stems_simple(stems, preset)
        mastered, report = master(mixed, SR)
        assert mastered.shape == mixed.shape


# ═══════════════════════════════════════════════════════════════════════════
# 2  BANK / PRESET CONSISTENCY  (45 modules × ~3 tests each = 135+ tests)
# ═══════════════════════════════════════════════════════════════════════════

# Mapping: (module_path, ALL_*_BANKS name)
_BANK_REGISTRY: list[tuple[str, str]] = [
    ("engine.phi_analyzer", "ALL_PHI_ANALYZER_BANKS"),
    ("engine.evolution_engine", "ALL_EVOLUTION_BANKS"),
    ("engine.preset_mutator", "ALL_MUTATOR_BANKS"),
    ("engine.ab_tester", "ALL_AB_BANKS"),
    ("engine.template_generator", "ALL_TEMPLATE_BANKS"),
    ("engine.sound_palette", "ALL_PALETTE_BANKS"),
    ("engine.pad_synth", "ALL_PAD_BANKS"),
    ("engine.bass_oneshot", "ALL_BASS_BANKS"),
    ("engine.render_pipeline", "ALL_PIPELINE_BANKS"),
    ("engine.sidechain", "ALL_SIDECHAIN_BANKS"),
    ("engine.lead_synth", "ALL_LEAD_BANKS"),
    ("engine.sub_bass", "ALL_SUB_BASS_BANKS"),
    ("engine.perc_synth", "ALL_PERC_BANKS"),
    ("engine.wobble_bass", "ALL_WOBBLE_BANKS"),
    ("engine.vocal_processor", "ALL_VOCAL_BANKS"),
    ("engine.ambient_texture", "ALL_TEXTURE_BANKS"),
    ("engine.drone_synth", "ALL_DRONE_BANKS"),
    ("engine.reverb_delay", "ALL_REVERB_DELAY_BANKS"),
    ("engine.arp_synth", "ALL_ARP_BANKS"),
    ("engine.riddim_engine", "ALL_RIDDIM_BANKS"),
    ("engine.harmonic_analysis", "ALL_ANALYSIS_BANKS"),
    ("engine.preset_pack_builder", "ALL_PRESET_PACK_BANKS"),
    ("engine.batch_renderer", "ALL_BATCH_BANKS"),
    ("engine.song_templates", "ALL_SONG_TEMPLATE_BANKS"),
    ("engine.multiband_distortion", "ALL_MULTIBAND_DIST_BANKS"),
    ("engine.formant_synth", "ALL_FORMANT_BANKS"),
    ("engine.spectral_resynthesis", "ALL_RESYNTH_BANKS"),
    ("engine.riser_synth", "ALL_RISER_BANKS"),
    ("engine.granular_synth", "ALL_GRANULAR_BANKS"),
    ("engine.arrangement_sequencer", "ALL_ARRANGEMENT_BANKS"),
    ("engine.sample_pack_builder", "ALL_PACK_BANKS"),
    ("engine.fx_generator", "ALL_FX_BANKS"),
    ("engine.vocal_chop", "ALL_CHOP_BANKS"),
    ("engine.glitch_engine", "ALL_GLITCH_BANKS"),
    ("engine.noise_generator", "ALL_NOISE_BANKS"),
    ("engine.stereo_imager", "ALL_STEREO_BANKS"),
    ("engine.transition_fx", "ALL_TRANSITION_BANKS"),
    ("engine.convolution", "ALL_CONVOLUTION_BANKS"),
    ("engine.lfo_matrix", "ALL_LFO_BANKS"),
    ("engine.impact_hit", "ALL_IMPACT_BANKS"),
    ("engine.wavetable_morph", "ALL_MORPH_BANKS"),
    ("engine.stem_mixer", "ALL_MIX_BANKS"),
    ("engine.chord_pad", "ALL_CHORD_PAD_BANKS"),
    ("engine.pluck_synth", "ALL_PLUCK_BANKS"),
    ("engine.pitch_automation", "ALL_PITCH_AUTO_BANKS"),
]


def _get_bank_items(bank):
    """Get the iterable items from a bank (.presets, .templates, .chops, etc)."""
    for attr in ("presets", "templates", "chops", "patterns", "items"):
        val = getattr(bank, attr, None)
        if val is not None and isinstance(val, list) and len(val) > 0:
            return val
    # Fallback: search all list attributes
    for attr in dir(bank):
        if attr.startswith("_"):
            continue
        val = getattr(bank, attr, None)
        if isinstance(val, list) and len(val) > 0 and hasattr(val[0], "name"):
            return val
    return []


def _load_bank_dict(mod_path: str, attr: str) -> dict:
    import importlib
    mod = importlib.import_module(mod_path)
    return getattr(mod, attr)


class TestBankConsistency:
    """All 6 bank checks in one parametrized class (was 6 classes x 45 = 270 tests, now 45)."""

    @pytest.mark.parametrize("mod_path,attr", _BANK_REGISTRY,
                             ids=[f"{m.split('.')[-1]}.{a}" for m, a in _BANK_REGISTRY])
    def test_bank_full_validation(self, mod_path, attr):
        banks = _load_bank_dict(mod_path, attr)
        # 1) Registry not empty
        assert len(banks) >= 1, f"{mod_path}.{attr} is empty"
        for bank_key, bank_fn in banks.items():
            # 2) Callable
            assert callable(bank_fn), f"{bank_key} is not callable"
            bank = bank_fn()
            # 3) Has name or presets
            assert hasattr(bank, "name") or hasattr(bank, "presets")
            # 4) Key relates to name
            if hasattr(bank, "name"):
                k_flat = bank_key.lower().replace("_", "")
                n_flat = bank.name.lower().replace("_", "")  # type: ignore[attr-defined]
                k_tokens = set(t for t in bank_key.lower().split("_") if len(t) >= 3)
                n_tokens = set(t for t in bank.name.lower().split("_") if len(t) >= 3)  # type: ignore[attr-defined]
                shared = k_tokens & n_tokens
                assert shared or k_flat in n_flat or n_flat in k_flat or k_flat == n_flat, (
                    f"{mod_path}: key '{bank_key}' unrelated to bank.name '{bank.name}'"  # type: ignore[attr-defined]
                )
            # 5) Has presets
            items = _get_bank_items(bank)
            assert len(items) >= 1, f"{mod_path} bank '{bank_key}' has no presets"
            # 6) All preset names valid
            for preset in items:
                assert isinstance(preset.name, str) and len(preset.name) > 0, (
                    f"Bad name in {mod_path} bank '{bank_key}'"
                )


# ═══════════════════════════════════════════════════════════════════════════
# 3  MANIFEST WRITERS  (30+ tests)
# ═══════════════════════════════════════════════════════════════════════════

# Manifests with signature: write_*_manifest(output_dir: str = "output") -> dict
_MANIFEST_SIMPLE: list[tuple[str, str]] = [
    ("engine.sidechain", "write_sidechain_manifest"),
    ("engine.sub_bass", "write_sub_bass_manifest"),
    ("engine.wobble_bass", "write_wobble_manifest"),
    ("engine.drone_synth", "write_drone_manifest"),
    ("engine.reverb_delay", "write_reverb_delay_manifest"),
    ("engine.arp_synth", "write_arp_manifest"),
    ("engine.riddim_engine", "write_riddim_manifest"),
    ("engine.harmonic_analysis", "write_harmonic_analysis_manifest"),
    ("engine.preset_pack_builder", "write_preset_pack_manifest"),
    ("engine.batch_renderer", "write_batch_manifest"),
    ("engine.song_templates", "write_song_templates_manifest"),
    ("engine.multiband_distortion", "write_multiband_distortion_manifest"),
    ("engine.formant_synth", "write_formant_manifest"),
    ("engine.spectral_resynthesis", "write_resynth_manifest"),
    ("engine.riser_synth", "write_riser_manifest"),
    ("engine.granular_synth", "write_granular_manifest"),
    ("engine.arrangement_sequencer", "write_arrangement_sequencer_manifest"),
    ("engine.sample_pack_builder", "write_pack_manifest"),
    ("engine.glitch_engine", "write_glitch_manifest"),
    ("engine.noise_generator", "write_noise_manifest"),
    ("engine.stereo_imager", "write_stereo_imager_manifest"),
    ("engine.convolution", "write_convolution_manifest"),
    ("engine.lfo_matrix", "write_lfo_matrix_manifest"),
    ("engine.impact_hit", "write_impact_manifest"),
    ("engine.wavetable_morph", "write_morph_manifest"),
    ("engine.stem_mixer", "write_mix_manifest"),
    ("engine.chord_pad", "write_chord_pad_manifest"),
    ("engine.pluck_synth", "write_pluck_manifest"),
    ("engine.pitch_automation", "write_pitch_automation_manifest"),
    ("engine.render_pipeline", "write_pipeline_manifest"),
    ("engine.phi_analyzer", "write_phi_analyzer_manifest"),
    ("engine.evolution_engine", "write_evolution_manifest"),
    ("engine.preset_mutator", "write_mutator_manifest"),
    ("engine.ab_tester", "write_ab_manifest"),
    ("engine.template_generator", "write_template_manifest"),
    ("engine.sound_palette", "write_palette_manifest"),
    ("engine.vocal_processor", "write_vocal_processor_manifest"),
]


class TestManifestWriters:
    """Call write_*_manifest and verify it returns a dict."""

    @pytest.mark.parametrize("mod_path,fn_name", _MANIFEST_SIMPLE,
                             ids=[f"{m.split('.')[-1]}.{f}" for m, f in _MANIFEST_SIMPLE])
    def test_manifest_returns_dict(self, mod_path, fn_name, tmp_path):
        import importlib
        mod = importlib.import_module(mod_path)
        fn = getattr(mod, fn_name)
        result = fn(str(tmp_path))
        assert isinstance(result, dict), f"{fn_name} did not return dict"

    @pytest.mark.parametrize("mod_path,fn_name", _MANIFEST_SIMPLE,
                             ids=[f"{m.split('.')[-1]}.{f}_nonempty" for m, f in _MANIFEST_SIMPLE])
    def test_manifest_not_empty(self, mod_path, fn_name, tmp_path):
        import importlib
        mod = importlib.import_module(mod_path)
        fn = getattr(mod, fn_name)
        result = fn(str(tmp_path))
        assert len(result) > 0, f"{fn_name} returned empty dict"


# ═══════════════════════════════════════════════════════════════════════════
# 4  EXPORT FUNCTIONS  (30+ tests)
# ═══════════════════════════════════════════════════════════════════════════

_EXPORT_SIMPLE: list[tuple[str, str]] = [
    ("engine.sidechain", "export_sidechain_demos"),
    ("engine.stereo_imager", "export_stereo_demos"),
    ("engine.render_pipeline", "export_pipeline_stems"),
    ("engine.reverb_delay", "export_reverb_delay_demos"),
    ("engine.multiband_distortion", "export_distortion_demos"),
    ("engine.convolution", "export_convolution_demos"),
    ("engine.batch_renderer", "export_batch_renders"),
    ("engine.wavetable_morph", "export_morph_wavetables"),
    ("engine.spectral_resynthesis", "export_resynth_wavetables"),
    ("engine.preset_pack_builder", "export_all_preset_packs"),
    ("engine.sample_pack_builder", "export_all_packs"),
    ("engine.stem_mixer", "export_mix_demos"),
    ("engine.evolution_engine", "export_evolution_logs"),
    ("engine.preset_mutator", "export_mutated_patches"),
    ("engine.ab_tester", "export_ab_results"),
    ("engine.template_generator", "export_templates"),
    ("engine.sound_palette", "export_palette_tones"),
    ("engine.phi_analyzer", "export_phi_scores"),
]


class TestExportFunctions:
    """Call export_* and verify it returns a list of paths."""

    @pytest.mark.parametrize("mod_path,fn_name", _EXPORT_SIMPLE,
                             ids=[f"{m.split('.')[-1]}.{f}" for m, f in _EXPORT_SIMPLE])
    def test_export_returns_list(self, mod_path, fn_name, tmp_path):
        import importlib
        mod = importlib.import_module(mod_path)
        fn = getattr(mod, fn_name)
        paths = fn(str(tmp_path))
        assert isinstance(paths, list)

    @pytest.mark.parametrize("mod_path,fn_name", _EXPORT_SIMPLE,
                             ids=[f"{m.split('.')[-1]}.{f}_nonempty" for m, f in _EXPORT_SIMPLE])
    def test_export_produces_files(self, mod_path, fn_name, tmp_path):
        import importlib
        # Seed common subdirectories some exporters scan
        for sub in ("wavetables", "drums", "masters", "stems", "presets"):
            (tmp_path / sub).mkdir(exist_ok=True)
        _wav(tmp_path / "wavetables" / "seed.wav")
        _wav(tmp_path / "drums" / "seed.wav")
        mod = importlib.import_module(mod_path)
        fn = getattr(mod, fn_name)
        paths = fn(str(tmp_path))
        assert len(paths) >= 1, f"{fn_name} produced no output files"
        for p in paths:
            assert Path(p).exists(), f"Missing export file: {p}"


# Sections 5 (CLI) and 6 (ConfigLoader) removed — covered by
# tests/test_cli.py and tests/test_config_loader.py respectively.


# Section 7 (MemorySystem) removed — covered by tests/test_memory.py.


# Sections 8 (DojoQualityMetrics) and 15 (DojoBeltSystem) removed —
# covered by tests/test_dojo.py.

# Section 9 (ALSGenerator) removed — covered by tests/test_als_generator.py.


# ═══════════════════════════════════════════════════════════════════════════
# 10  PHI CONSTANTS  (10 tests)
# ═══════════════════════════════════════════════════════════════════════════

class TestPhiConstants:
    def test_phi_value(self):
        from engine.config_loader import PHI
        assert abs(PHI - 1.6180339887498948482) < 1e-12

    def test_phi_golden_ratio(self):
        from engine.config_loader import PHI
        # phi^2 = phi + 1
        assert abs(PHI ** 2 - (PHI + 1)) < 1e-10

    def test_fibonacci_sequence(self):
        from engine.config_loader import FIBONACCI
        assert FIBONACCI[:5] == [1, 1, 2, 3, 5]
        for i in range(2, len(FIBONACCI)):
            assert FIBONACCI[i] == FIBONACCI[i - 1] + FIBONACCI[i - 2]

    def test_fibonacci_length(self):
        from engine.config_loader import FIBONACCI
        assert len(FIBONACCI) == 13

    def test_a4_432(self):
        from engine.config_loader import A4_432
        assert A4_432 == 432.0

    def test_a4_440(self):
        from engine.config_loader import A4_440
        assert A4_440 == 440.0

    def test_phi_core_sample_rate(self):
        from engine.phi_core import SAMPLE_RATE
        assert SAMPLE_RATE == 44100

    def test_phi_matches_across_modules(self):
        # phi_core imports PHI from config_loader
        import engine.phi_core as pc
        from engine.config_loader import PHI as PHI_CL
        assert PHI_CL == pc.PHI

    def test_fibonacci_matches_across_modules(self):
        from engine.config_loader import FIBONACCI as F_CL
        # phi_core imports from config_loader, so just verify it's accessible
        assert len(F_CL) >= 10

    def test_phi_midi_to_freq(self):
        from engine.phi_core import midi_to_freq
        # A4 = MIDI 69 = 440 Hz
        assert abs(midi_to_freq(69, 440.0) - 440.0) < 0.01
        # An octave below = MIDI 57 = 220 Hz
        assert abs(midi_to_freq(57, 440.0) - 220.0) < 0.01


# ═══════════════════════════════════════════════════════════════════════════
# 11  EXTRA CROSS-MODULE TESTS  (20+ additional)
# ═══════════════════════════════════════════════════════════════════════════

class TestExtraCrossModule:
    """Additional cross-module integration verifications."""

    def test_sidechain_all_banks_process(self):
        from engine.sidechain import ALL_SIDECHAIN_BANKS, apply_sidechain
        sig = _tone(100.0, 0.3)
        for name, fn in ALL_SIDECHAIN_BANKS.items():
            bank = fn()
            for preset in bank.presets:
                out = apply_sidechain(sig, preset, SR)
                assert out.shape == sig.shape

    def test_stereo_imager_all_banks(self):
        from engine.stereo_imager import ALL_STEREO_BANKS, apply_stereo_imaging
        sig = _tone(200.0, 0.2)
        for name, fn in ALL_STEREO_BANKS.items():
            bank = fn()
            for preset in bank.presets:
                out = apply_stereo_imaging(sig, preset, SR)
                assert isinstance(out, np.ndarray)

    def test_reverb_all_banks(self):
        from engine.reverb_delay import ALL_REVERB_DELAY_BANKS, apply_reverb_delay
        sig = _tone(440.0, 0.2)
        for name, fn in ALL_REVERB_DELAY_BANKS.items():
            bank = fn()
            for preset in bank.presets:
                out = apply_reverb_delay(sig, preset, SR)
                assert isinstance(out, np.ndarray)

    def test_multiband_dist_all_banks(self):
        from engine.multiband_distortion import ALL_MULTIBAND_DIST_BANKS, apply_multiband_distortion
        sig = _tone(220.0, 0.2)
        for name, fn in ALL_MULTIBAND_DIST_BANKS.items():
            bank = fn()
            for preset in bank.presets:
                out = apply_multiband_distortion(sig, preset, SR)
                assert out.shape == sig.shape

    def test_convolution_all_banks(self):
        from engine.convolution import ALL_CONVOLUTION_BANKS, apply_convolution
        sig = _tone(440.0, 0.2)
        for name, fn in ALL_CONVOLUTION_BANKS.items():
            bank = fn()
            for preset in bank.presets:
                out = apply_convolution(sig, preset, SR)
                assert isinstance(out, np.ndarray)

    def test_glitch_all_banks(self):
        from engine.glitch_engine import ALL_GLITCH_BANKS, synthesize_glitch
        for name, fn in ALL_GLITCH_BANKS.items():
            bank = fn()
            for preset in bank.presets:
                out = synthesize_glitch(preset, SR)
                assert isinstance(out, np.ndarray)

    def test_mastering_preserves_length(self):
        from engine.mastering_chain import master
        sig = _tone(100.0, 1.0)
        out, _ = master(sig, SR)
        assert len(out) == len(sig)

    def test_mastering_stereo_preserves_channels(self):
        from engine.mastering_chain import master
        sig = _stereo_tone(200.0, 0.5)
        out, _ = master(sig, SR)
        assert out.shape[1] == 2

    def test_mastering_reduces_peak(self):
        from engine.mastering_chain import master
        sig = _tone(440.0, 0.5) * 2.0  # clipping signal
        out, _ = master(sig, SR)
        assert np.max(np.abs(out)) <= 1.0 + 0.01

    def test_phi_coherence_different_freqs(self):
        from engine.phi_analyzer import analyze_phi_coherence
        for freq in [55.0, 110.0, 220.0, 432.0, 440.0]:
            sig = _tone(freq, 0.3)
            score = analyze_phi_coherence(sig)
            assert 0.0 <= score.composite <= 1.0

    def test_harmonic_analysis_wav_file(self, tmp_path):
        from engine.harmonic_analysis import analyze_wav_file
        wav_p = _wav(tmp_path / "analysis.wav", 440.0, 0.5)
        result = analyze_wav_file(str(wav_p), "spectral_peaks")
        assert result is not None

    def test_growl_full_pipeline(self):
        from engine.growl_resampler import (
            bit_reduce,
            comb_filter,
            generate_saw_source,
            pitch_shift,
            waveshape_distortion,
        )
        src = generate_saw_source()
        out = pitch_shift(src, 5)
        out = waveshape_distortion(out, drive=0.8)
        out = comb_filter(out)
        out = bit_reduce(out, 6)
        assert isinstance(out, np.ndarray)
        assert len(out) > 0

    def test_growl_fm_source(self):
        from engine.growl_resampler import generate_fm_source
        src = generate_fm_source()
        assert isinstance(src, np.ndarray)
        assert len(src) > 0

    def test_mix_all_methods_consistency(self):
        from engine.stem_mixer import (
            MixPreset,
            mix_stems_dynamic,
            mix_stems_frequency,
            mix_stems_parallel,
            mix_stems_phi_weight,
            mix_stems_simple,
        )
        stems = [_tone(100 * i, 0.1) for i in range(1, 4)]
        p = MixPreset("test", "simple")
        results = [
            mix_stems_simple(stems, p),
            mix_stems_phi_weight(stems, MixPreset("t", "phi_weight")),
            mix_stems_frequency(stems, MixPreset("t", "frequency")),
            mix_stems_dynamic(stems, MixPreset("t", "dynamic")),
            mix_stems_parallel(stems, MixPreset("t", "parallel")),
        ]
        for r in results:
            assert r.ndim == 2
            assert r.shape[1] == 2

    def test_stem_mixer_empty_stems(self):
        from engine.stem_mixer import MixPreset, mix_stems_simple
        p = MixPreset("empty", "simple")
        out = mix_stems_simple([], p)
        assert out.ndim == 2

    def test_phi_core_wavetable_size(self):
        from engine.phi_core import (
            WAVETABLE_SIZE,
            generate_frame,
            phi_amplitude_curve,
            phi_harmonic_series,
        )
        partials = phi_harmonic_series(55, 3)
        amps = phi_amplitude_curve(3)
        frame = generate_frame(partials, amps, WAVETABLE_SIZE)
        assert len(frame) == WAVETABLE_SIZE

    def test_phi_core_default_frames(self):
        from engine.phi_core import DEFAULT_FRAMES
        assert DEFAULT_FRAMES == 256

    def test_chain_distortion_reverb_master(self):
        from engine.mastering_chain import master
        from engine.multiband_distortion import ALL_MULTIBAND_DIST_BANKS, apply_multiband_distortion
        from engine.reverb_delay import ALL_REVERB_DELAY_BANKS, apply_reverb_delay
        sig = _tone(110.0, 0.3)
        dist_bank = list(ALL_MULTIBAND_DIST_BANKS.values())[0]()
        sig = apply_multiband_distortion(sig, dist_bank.presets[0], SR)
        rev_bank = list(ALL_REVERB_DELAY_BANKS.values())[0]()
        sig = apply_reverb_delay(sig, rev_bank.presets[0], SR)
        out, report = master(sig, SR)
        assert np.max(np.abs(out)) <= 1.0 + 0.01

    def test_chain_sidechain_stereo_master(self):
        from engine.mastering_chain import master
        from engine.sidechain import ALL_SIDECHAIN_BANKS, apply_sidechain
        from engine.stereo_imager import ALL_STEREO_BANKS, apply_stereo_imaging
        sig = _tone(60.0, 0.5)
        sc = list(ALL_SIDECHAIN_BANKS.values())[0]()
        sig = apply_sidechain(sig, sc.presets[0], SR)
        st = list(ALL_STEREO_BANKS.values())[0]()
        sig = apply_stereo_imaging(sig, st.presets[0], SR)
        out, _ = master(sig, SR)
        assert isinstance(out, np.ndarray)


# ═══════════════════════════════════════════════════════════════════════════
# 12  MODULE IMPORT SMOKE TESTS  (25+ tests)
# ═══════════════════════════════════════════════════════════════════════════

_ALL_ENGINE_MODULES = [
    "engine.phi_core",
    "engine.psbs",
    "engine.growl_resampler",
    "engine.drum_generator",
    "engine.bass_oneshot",
    "engine.lead_synth",
    "engine.pad_synth",
    "engine.perc_synth",
    "engine.sub_bass",
    "engine.noise_generator",
    "engine.arp_synth",
    "engine.pluck_synth",
    "engine.granular_synth",
    "engine.chord_pad",
    "engine.riser_synth",
    "engine.impact_hit",
    "engine.wobble_bass",
    "engine.formant_synth",
    "engine.glitch_engine",
    "engine.drone_synth",
    "engine.riddim_engine",
    "engine.vocal_chop",
    "engine.vocal_processor",
    "engine.fx_generator",
    "engine.transition_fx",
    "engine.ambient_texture",
    "engine.sidechain",
    "engine.stereo_imager",
    "engine.multiband_distortion",
    "engine.reverb_delay",
    "engine.convolution",
    "engine.harmonic_analysis",
    "engine.render_pipeline",
    "engine.batch_renderer",
    "engine.stem_mixer",
    "engine.sample_pack_builder",
    "engine.preset_pack_builder",
    "engine.wavetable_morph",
    "engine.spectral_resynthesis",
    "engine.phi_analyzer",
    "engine.evolution_engine",
    "engine.preset_mutator",
    "engine.ab_tester",
    "engine.template_generator",
    "engine.sound_palette",
    "engine.mastering_chain",
    "engine.memory",
    "engine.dojo",
    "engine.config_loader",
    "engine.log",
    "engine.cli",
    "engine.als_generator",
    "engine.ableton_live",
    "engine.midi_export",
    "engine.fxp_writer",
    "engine.sample_slicer",
    "engine.chord_progression",
    "engine.song_templates",
    "engine.arrangement_sequencer",
    "engine.lfo_matrix",
    "engine.pitch_automation",
    "engine.trance_arp",
    "engine.serum2",
    "engine.sb_analyzer",
]


class TestModuleImports:
    """Verify every engine module imports without error."""

    @pytest.mark.parametrize("mod_path", _ALL_ENGINE_MODULES,
                             ids=[m.split(".")[-1] for m in _ALL_ENGINE_MODULES])
    def test_module_imports(self, mod_path):
        import importlib
        mod = importlib.import_module(mod_path)
        assert mod is not None


# Section 13 (RCO/PSBS) removed — covered by tests/test_psbs.py.


# ═══════════════════════════════════════════════════════════════════════════
# 14  ADDITIONAL MANIFEST KEY CHECKS  (20 tests)
# ═══════════════════════════════════════════════════════════════════════════

_MANIFEST_KEY_CHECKS: list[tuple[str, str, str]] = [
    ("engine.noise_generator", "write_noise_manifest", "banks"),
    ("engine.glitch_engine", "write_glitch_manifest", "banks"),
    ("engine.sidechain", "write_sidechain_manifest", "banks"),
    ("engine.stereo_imager", "write_stereo_imager_manifest", "banks"),
    ("engine.reverb_delay", "write_reverb_delay_manifest", "banks"),
    ("engine.multiband_distortion", "write_multiband_distortion_manifest", "banks"),
    ("engine.convolution", "write_convolution_manifest", "banks"),
    ("engine.sub_bass", "write_sub_bass_manifest", "banks"),
    ("engine.wobble_bass", "write_wobble_manifest", "banks"),
    ("engine.drone_synth", "write_drone_manifest", "banks"),
    ("engine.formant_synth", "write_formant_manifest", "banks"),
    ("engine.riser_synth", "write_riser_manifest", "banks"),
    ("engine.granular_synth", "write_granular_manifest", "banks"),
    ("engine.arp_synth", "write_arp_manifest", "banks"),
    ("engine.riddim_engine", "write_riddim_manifest", "banks"),
    ("engine.impact_hit", "write_impact_manifest", "banks"),
    ("engine.chord_pad", "write_chord_pad_manifest", "banks"),
    ("engine.pluck_synth", "write_pluck_manifest", "banks"),
    ("engine.wavetable_morph", "write_morph_manifest", "banks"),
    ("engine.stem_mixer", "write_mix_manifest", "banks"),
]


class TestManifestKeys:
    """Verify manifest writers produce dicts with expected top-level keys."""

    @pytest.mark.parametrize("mod_path,fn_name,key", _MANIFEST_KEY_CHECKS,
                             ids=[f"{m.split('.')[-1]}.{f}[{k}]" for m, f, k in _MANIFEST_KEY_CHECKS])
    def test_manifest_has_key(self, mod_path, fn_name, key, tmp_path):
        import importlib
        mod = importlib.import_module(mod_path)
        fn = getattr(mod, fn_name)
        result = fn(str(tmp_path))
        assert key in result, f"{fn_name}() missing key '{key}'"


# ═══════════════════════════════════════════════════════════════════════════
# 15  DOJO BELT SYSTEM  (8 tests)
# ═══════════════════════════════════════════════════════════════════════════

class TestDojoBeltSystem:
    def test_belt_rank_enum(self):
        from engine.dojo import BeltRank
        assert len(BeltRank) == 7

    def test_belt_system_list(self):
        from engine.dojo import BELT_SYSTEM
        assert isinstance(BELT_SYSTEM, list)
        assert len(BELT_SYSTEM) == 7

    def test_belt_rank_values(self):
        from engine.dojo import BeltRank
        expected = ["White Belt", "Yellow Belt", "Green Belt",
                    "Blue Belt", "Purple Belt", "Brown Belt", "Black Belt"]
        for rank, exp in zip(BeltRank, expected):
            assert rank.value == exp

    def test_belt_system_has_core_skills(self):
        from engine.dojo import BELT_SYSTEM
        for belt in BELT_SYSTEM:
            assert "core_skills" in belt
            assert len(belt["core_skills"]) >= 1

    def test_belt_system_has_tracks_required(self):
        from engine.dojo import BELT_SYSTEM
        for belt in BELT_SYSTEM:
            assert "tracks_required" in belt
            assert belt["tracks_required"] >= 1

    def test_belt_system_has_phi_challenge(self):
        from engine.dojo import BELT_SYSTEM
        for belt in BELT_SYSTEM:
            assert "phi_challenge" in belt

    def test_belt_system_order(self):
        from engine.dojo import BELT_SYSTEM
        for i, belt in enumerate(BELT_SYSTEM):
            assert belt["order"] == i

    def test_the_approach_exists(self):
        from engine.dojo import THE_APPROACH
        assert isinstance(THE_APPROACH, list)
        assert len(THE_APPROACH) >= 5


# ═══════════════════════════════════════════════════════════════════════════
# 16  EXTRA SIGNAL PROCESSING  (10 tests)
# ═══════════════════════════════════════════════════════════════════════════

class TestExtraSignalProcessing:
    def test_mastering_settings_defaults(self):
        from engine.mastering_chain import MasterSettings
        s = MasterSettings()
        assert hasattr(s, "target_lufs")

    def test_mastering_report_fields(self):
        from engine.mastering_chain import MasterReport, MasterSettings
        r = MasterReport(settings=MasterSettings())
        assert hasattr(r, "input_peak_db")
        assert hasattr(r, "input_rms_db")

    def test_mastering_master_file(self, tmp_path):
        from engine.mastering_chain import master_file
        wav_in = _wav(tmp_path / "input.wav", 220.0, 0.5)
        wav_out = str(tmp_path / "mastered.wav")
        report = master_file(str(wav_in), wav_out)
        # master_file returns a MasterReport; output file should exist
        assert Path(wav_out).exists()
        assert hasattr(report, "input_peak_db")

    def test_sidechain_preset_fields(self):
        from engine.sidechain import SidechainPreset
        p = SidechainPreset("test", "pump")
        assert p.name == "test"
        assert p.shape == "pump"

    def test_stereo_preset_fields(self):
        from engine.stereo_imager import StereoPreset
        p = StereoPreset("test", "haas")
        assert p.name == "test"

    def test_reverb_delay_preset_fields(self):
        from engine.reverb_delay import ReverbDelayPreset
        p = ReverbDelayPreset("test", "room")
        assert p.name == "test"

    def test_multiband_dist_preset_fields(self):
        from engine.multiband_distortion import MultibandDistPreset
        p = MultibandDistPreset("test", "warm", 0.5, 0.5, 0.5)
        assert p.name == "test"

    def test_convolution_preset_fields(self):
        from engine.convolution import ConvolutionPreset
        p = ConvolutionPreset("test", "room_ir")
        assert p.name == "test"

    def test_glitch_preset_fields(self):
        from engine.glitch_engine import GlitchPreset
        p = GlitchPreset("test", "stutter")
        assert p.name == "test"

    def test_noise_preset_fields(self):
        from engine.noise_generator import NoisePreset
        p = NoisePreset("test", "white", 1.0)
        assert p.name == "test"


# Sections 17-19 (MidiExport, FXPWriter, SampleSlicer) removed --
# covered by tests/test_midi_export.py, tests/test_fxp_writer.py, tests/test_sample_slicer.py.


# ═══════════════════════════════════════════════════════════════════════════
# 20  ADDITIONAL EXPORT UNIQUENESS  (10 tests)
# ═══════════════════════════════════════════════════════════════════════════

class TestExportUniqueness:
    """Verify export functions produce unique filenames."""

    def test_sidechain_exports_unique(self, tmp_path):
        from engine.sidechain import export_sidechain_demos
        paths = export_sidechain_demos(str(tmp_path))
        basenames = [Path(p).name for p in paths]
        assert len(basenames) == len(set(basenames))

    def test_stereo_exports_unique(self, tmp_path):
        from engine.stereo_imager import export_stereo_demos
        paths = export_stereo_demos(str(tmp_path))
        basenames = [Path(p).name for p in paths]
        assert len(basenames) == len(set(basenames))

    def test_reverb_delay_exports_unique(self, tmp_path):
        from engine.reverb_delay import export_reverb_delay_demos
        paths = export_reverb_delay_demos(str(tmp_path))
        basenames = [Path(p).name for p in paths]
        assert len(basenames) == len(set(basenames))

    def test_distortion_exports_unique(self, tmp_path):
        from engine.multiband_distortion import export_distortion_demos
        paths = export_distortion_demos(str(tmp_path))
        basenames = [Path(p).name for p in paths]
        assert len(basenames) == len(set(basenames))

    def test_convolution_exports_unique(self, tmp_path):
        from engine.convolution import export_convolution_demos
        paths = export_convolution_demos(str(tmp_path))
        basenames = [Path(p).name for p in paths]
        assert len(basenames) == len(set(basenames))

    def test_mix_exports_unique(self, tmp_path):
        from engine.stem_mixer import export_mix_demos
        paths = export_mix_demos(str(tmp_path))
        basenames = [Path(p).name for p in paths]
        assert len(basenames) == len(set(basenames))

    def test_morph_exports_unique(self, tmp_path):
        from engine.wavetable_morph import export_morph_wavetables
        paths = export_morph_wavetables(str(tmp_path))
        basenames = [Path(p).name for p in paths]
        assert len(basenames) == len(set(basenames))

    def test_resynth_exports_unique(self, tmp_path):
        from engine.spectral_resynthesis import export_resynth_wavetables
        paths = export_resynth_wavetables(str(tmp_path))
        basenames = [Path(p).name for p in paths]
        assert len(basenames) == len(set(basenames))

    def test_batch_exports_unique(self, tmp_path):
        from engine.batch_renderer import export_batch_renders
        paths = export_batch_renders(str(tmp_path))
        basenames = [Path(p).name for p in paths]
        assert len(basenames) == len(set(basenames))

    def test_pipeline_exports_unique(self, tmp_path):
        from engine.render_pipeline import export_pipeline_stems
        paths = export_pipeline_stems(str(tmp_path))
        basenames = [Path(p).name for p in paths]
        assert len(basenames) == len(set(basenames))
