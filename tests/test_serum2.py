"""Tests for engine.serum2 — Serum 2 synthesizer engine."""
from engine.config_loader import PHI
from engine.serum2 import (
    SERUM2_ARCHITECTURE,
    SERUM_FRAME_SIZE,
    SERUM_MAX_FRAMES,
    WAVETABLE_MAP,
    EnvelopeConfig,
    FilterType,
    LFOShape,
    ModulationRoute,
    OscillatorConfig,
    OscillatorType,
    VoicingMode,
    WavetableSlot,
    build_dubstep_patches,
    build_init_template,
    fibonacci_lfo_rates,
    fibonacci_wavetable_frames,
    phi_effect_mix,
    phi_envelope,
    phi_filter_cutoff,
    phi_fm_ratio,
    phi_macro_scaling,
    phi_unison_detune,
)

# ── Constants ────────────────────────────────────────────────────

class TestConstants:
    def test_frame_size(self):
        assert SERUM_FRAME_SIZE == 2048

    def test_max_frames(self):
        assert SERUM_MAX_FRAMES == 256

    def test_architecture(self):
        assert isinstance(SERUM2_ARCHITECTURE, dict)

    def test_wavetable_map(self):
        assert isinstance(WAVETABLE_MAP, dict)


# ── Enums ────────────────────────────────────────────────────────

class TestEnums:
    def test_oscillator_type(self):
        assert OscillatorType.WAVETABLE is not None

    def test_filter_type(self):
        assert FilterType is not None

    def test_lfo_shape(self):
        assert LFOShape is not None

    def test_voicing_mode(self):
        assert VoicingMode is not None


# ── Dataclasses ──────────────────────────────────────────────────

class TestWavetableSlot:
    def test_defaults(self):
        wt = WavetableSlot()
        assert wt.name == "Default"
        assert wt.frames == 256
        assert wt.frame_size == 2048


class TestOscillatorConfig:
    def test_defaults(self):
        osc = OscillatorConfig()
        assert osc.enabled is True
        assert osc.level == 0.80
        assert osc.unison_voices == 1


class TestEnvelopeConfig:
    def test_defaults(self):
        env = EnvelopeConfig()
        assert env.attack_ms == 1.0
        assert env.sustain == 0.75
        assert env.release_ms == 100.0


class TestModulationRoute:
    def test_defaults(self):
        mod = ModulationRoute()
        assert mod.source == "LFO 1"
        assert mod.bipolar is True


# ── phi_unison_detune ────────────────────────────────────────────

class TestPhiUnisonDetune:
    def test_single_voice(self):
        result = phi_unison_detune(1)
        assert result == [0.0]

    def test_multiple_voices(self):
        result = phi_unison_detune(8)
        assert isinstance(result, list)
        assert len(result) == 8
        assert result == sorted(result)

    def test_symmetric(self):
        result = phi_unison_detune(5)
        # Should be roughly symmetric around 0
        assert abs(sum(result)) < 1.0  # not exactly 0, but close

    def test_zero_voices(self):
        result = phi_unison_detune(0)
        assert result == [0.0]


# ── phi_envelope ─────────────────────────────────────────────────

class TestPhiEnvelope:
    def test_returns_envelope(self):
        env = phi_envelope()
        assert isinstance(env, EnvelopeConfig)

    def test_phi_relationships(self):
        env = phi_envelope(base_attack_ms=5.0)
        # Decay should be attack * PHI
        assert abs(env.decay_ms - 5.0 * PHI) < 0.1
        # Sustain should be ~0.618
        assert abs(env.sustain - (1.0 / PHI)) < 0.01

    def test_custom_attack(self):
        env = phi_envelope(base_attack_ms=10.0)
        assert env.attack_ms == 10.0
        assert abs(env.decay_ms - 10.0 * PHI) < 0.1


# ── phi_filter_cutoff ───────────────────────────────────────────

class TestPhiFilterCutoff:
    def test_returns_list(self):
        cutoffs = phi_filter_cutoff()
        assert isinstance(cutoffs, list)
        assert len(cutoffs) == 8

    def test_phi_ratio(self):
        cutoffs = phi_filter_cutoff(root_hz=100.0, n_steps=4)
        assert len(cutoffs) == 4
        # Each step should be PHI * previous
        for i in range(1, len(cutoffs)):
            ratio = cutoffs[i] / cutoffs[i - 1]
            assert abs(ratio - PHI) < 0.01

    def test_starts_at_root(self):
        cutoffs = phi_filter_cutoff(root_hz=55.0)
        assert abs(cutoffs[0] - 55.0) < 0.01


# ── fibonacci_lfo_rates ─────────────────────────────────────────

class TestFibonacciLfoRates:
    def test_returns_list(self):
        rates = fibonacci_lfo_rates()
        assert isinstance(rates, list)
        assert len(rates) == 9

    def test_contains_standard_rates(self):
        rates = fibonacci_lfo_rates()
        assert "1/1" in rates
        assert "1/8" in rates


# ── phi_macro_scaling ────────────────────────────────────────────

class TestPhiMacroScaling:
    def test_zero(self):
        assert phi_macro_scaling(0.0) == 0.0

    def test_one(self):
        assert abs(phi_macro_scaling(1.0) - 1.0) < 0.001

    def test_mid_value(self):
        result = phi_macro_scaling(0.5)
        assert 0.0 < result < 1.0
        # x^(1/PHI) where PHI≈1.618, so 0.5^0.618 ≈ 0.651
        assert abs(result - 0.5 ** (1.0 / PHI)) < 0.001


# ── phi_fm_ratio ─────────────────────────────────────────────────

class TestPhiFmRatio:
    def test_ratio(self):
        result = phi_fm_ratio(100.0)
        assert abs(result - 100.0 * PHI) < 0.01


# ── fibonacci_wavetable_frames ───────────────────────────────────

class TestFibonacciWavetableFrames:
    def test_returns_list(self):
        frames = fibonacci_wavetable_frames()
        assert isinstance(frames, list)
        assert 256 in frames  # max frames always present

    def test_contains_fibonacci(self):
        frames = fibonacci_wavetable_frames()
        for fib in [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]:
            assert fib in frames


# ── phi_effect_mix ───────────────────────────────────────────────

class TestPhiEffectMix:
    def test_default(self):
        mix = phi_effect_mix()
        assert mix == 0.618

    def test_clamped(self):
        mix = phi_effect_mix(depth=2.0)
        assert mix == 1.0

    def test_custom(self):
        mix = phi_effect_mix(depth=0.3)
        assert abs(mix - 0.3) < 0.001


# ── build_dubstep_patches ────────────────────────────────────────

class TestBuildDubstepPatches:
    def test_returns_list(self):
        patches = build_dubstep_patches()
        assert isinstance(patches, list)
        assert len(patches) == 8

    def test_patch_structure(self):
        patches = build_dubstep_patches()
        for patch in patches:
            assert isinstance(patch, dict)
            assert "name" in patch
            assert "osc_a" in patch
            assert "filter_1" in patch


# ── build_init_template ─────────────────────────────────────────

class TestBuildInitTemplate:
    def test_returns_dict(self):
        template = build_init_template()
        assert isinstance(template, dict)
        assert "name" in template
        assert "DUBFORGE" in template["name"]

    def test_has_oscillators(self):
        template = build_init_template()
        assert "osc_a" in template
        assert "osc_b" in template
