"""Tests for engine.vocal_processor — 20 tests."""

import numpy as np
import pytest

from engine.vocal_processor import (
    ALL_VOCAL_BANKS,
    VocalBank,
    VocalPreset,
    apply_formant_shift,
    apply_harmonizer,
    apply_pitch_correct,
    apply_telephone,
    apply_vocal_processing,
    apply_vocoder,
    formant_shift_bank,
    harmonizer_bank,
    pitch_correct_bank,
    telephone_bank,
    vocoder_bank,
    write_vocal_processor_manifest,
)

SR = 44100


def _sine(freq: float = 440.0, dur: float = 0.1, sr: int = SR) -> np.ndarray:
    t = np.arange(int(dur * sr)) / sr
    return np.sin(2.0 * np.pi * freq * t).astype(np.float64)


# ─── DATACLASS ──────────────────────────────────────────────────────────
class TestVocalPreset:
    def test_defaults(self):
        p = VocalPreset("test", "pitch_correct")
        assert p.name == "test"
        assert p.vocal_type == "pitch_correct"
        assert p.mix == 1.0

    def test_custom_fields(self):
        p = VocalPreset("v", "vocoder", num_bands=32, carrier_freq=220.0)
        assert p.num_bands == 32
        assert p.carrier_freq == 220.0


class TestVocalBank:
    def test_bank_creation(self):
        b = VocalBank("tb", [VocalPreset("a", "vocoder")])
        assert b.name == "tb"
        assert len(b.presets) == 1


# ─── PITCH CORRECT ─────────────────────────────────────────────────────
class TestPitchCorrect:
    def test_output_length(self):
        sig = _sine(440.0)
        p = VocalPreset("pc", "pitch_correct")
        out = apply_pitch_correct(sig, p)
        assert len(out) == len(sig)

    def test_empty_signal(self):
        out = apply_pitch_correct(np.array([]), VocalPreset("e", "pitch_correct"))
        assert len(out) == 0

    def test_hard_snap(self):
        sig = _sine(445.0, 0.2)
        p = VocalPreset("snap", "pitch_correct", correction_speed=1.0)
        out = apply_pitch_correct(sig, p)
        assert out is not None
        assert len(out) == len(sig)


# ─── VOCODER ────────────────────────────────────────────────────────────
class TestVocoder:
    def test_output_length(self):
        sig = _sine(220.0)
        p = VocalPreset("voc", "vocoder")
        out = apply_vocoder(sig, p)
        assert len(out) == len(sig)

    def test_phi_band_spacing(self):
        sig = _sine(200.0, 0.05)
        p = VocalPreset("voc2", "vocoder", num_bands=8)
        out = apply_vocoder(sig, p)
        assert np.max(np.abs(out)) > 0


# ─── FORMANT SHIFT ─────────────────────────────────────────────────────
class TestFormantShift:
    def test_output_length(self):
        sig = _sine(300.0)
        p = VocalPreset("fs", "formant_shift", shift_semitones=5.0)
        out = apply_formant_shift(sig, p)
        assert len(out) == len(sig)


# ─── HARMONIZER ─────────────────────────────────────────────────────────
class TestHarmonizer:
    def test_output_length(self):
        sig = _sine(440.0)
        p = VocalPreset("h", "harmonizer")
        out = apply_harmonizer(sig, p)
        assert len(out) == len(sig)

    def test_normalized_output(self):
        sig = _sine(440.0)
        p = VocalPreset("h2", "harmonizer", harmony_intervals=[7], harmony_mix=0.5)
        out = apply_harmonizer(sig, p)
        assert np.max(np.abs(out)) <= np.max(np.abs(sig)) + 1e-6


# ─── TELEPHONE ──────────────────────────────────────────────────────────
class TestTelephone:
    def test_output_length(self):
        sig = _sine(1000.0)
        p = VocalPreset("tel", "telephone")
        out = apply_telephone(sig, p)
        assert len(out) == len(sig)


# ─── ROUTER ─────────────────────────────────────────────────────────────
class TestRouter:
    def test_routes_all_types(self):
        sig = _sine(440.0)
        for vtype in ["pitch_correct", "vocoder", "formant_shift",
                       "harmonizer", "telephone"]:
            p = VocalPreset(f"r_{vtype}", vtype)
            out = apply_vocal_processing(sig, p)
            assert len(out) == len(sig)

    def test_invalid_type(self):
        sig = _sine()
        p = VocalPreset("bad", "nonexistent")
        with pytest.raises(ValueError):
            apply_vocal_processing(sig, p)

    def test_wet_dry_mix(self):
        sig = _sine(440.0)
        p = VocalPreset("mix", "telephone", mix=0.0)
        out = apply_vocal_processing(sig, p)
        np.testing.assert_allclose(out, sig, atol=1e-6)


# ─── BANKS ──────────────────────────────────────────────────────────────
class TestBanks:
    def test_all_banks_exist(self):
        assert len(ALL_VOCAL_BANKS) == 5

    def test_each_bank_has_4_presets(self):
        for name, gen in ALL_VOCAL_BANKS.items():
            bank = gen()
            assert len(bank.presets) == 4, f"{name} has {len(bank.presets)}"

    def test_pitch_correct_bank(self):
        b = pitch_correct_bank()
        assert b.name == "pitch_correct"

    def test_vocoder_bank(self):
        b = vocoder_bank()
        assert b.name == "vocoder"

    def test_formant_shift_bank(self):
        b = formant_shift_bank()
        assert b.name == "formant_shift"
        assert all(p.vocal_type == "formant_shift" for p in b.presets)

    def test_harmonizer_bank(self):
        b = harmonizer_bank()
        assert b.name == "harmonizer"

    def test_telephone_bank(self):
        b = telephone_bank()
        assert b.name == "telephone"


# ─── MANIFEST ───────────────────────────────────────────────────────────
class TestManifest:
    def test_write_manifest(self, tmp_path):
        m = write_vocal_processor_manifest(str(tmp_path))
        assert "banks" in m
        assert len(m["banks"]) == 5
        total = sum(b["preset_count"] for b in m["banks"].values())
        assert total == 20
