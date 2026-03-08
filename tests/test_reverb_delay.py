"""Tests for engine.reverb_delay — 20 tests."""

import numpy as np
import pytest

from engine.reverb_delay import (
    ALL_REVERB_DELAY_BANKS,
    ReverbDelayBank,
    ReverbDelayPreset,
    apply_delay,
    apply_hall,
    apply_plate,
    apply_reverb_delay,
    apply_room,
    apply_shimmer,
    delay_bank,
    export_reverb_delay_demos,
    hall_bank,
    plate_bank,
    room_bank,
    shimmer_bank,
    write_reverb_delay_manifest,
)

SR = 44100


def _sine(freq: float = 440.0, dur: float = 0.1, sr: int = SR) -> np.ndarray:
    t = np.arange(int(dur * sr)) / sr
    return np.sin(2.0 * np.pi * freq * t).astype(np.float64)


# ─── DATACLASS ──────────────────────────────────────────────────────────
class TestReverbDelayPreset:
    def test_defaults(self):
        p = ReverbDelayPreset("test", "room")
        assert p.effect_type == "room"
        assert p.mix == 0.35

    def test_custom_fields(self):
        p = ReverbDelayPreset("d", "delay", bpm=140.0, num_taps=8)
        assert p.bpm == 140.0
        assert p.num_taps == 8


class TestReverbDelayBank:
    def test_bank_creation(self):
        b = ReverbDelayBank("tb", [ReverbDelayPreset("a", "hall")])
        assert len(b.presets) == 1


# ─── ROOM ───────────────────────────────────────────────────────────────
class TestRoom:
    def test_output_length(self):
        sig = _sine()
        p = ReverbDelayPreset("r", "room")
        out = apply_room(sig, p)
        assert len(out) == len(sig)

    def test_empty_signal(self):
        out = apply_room(np.array([]), ReverbDelayPreset("e", "room"))
        assert len(out) == 0


# ─── HALL ───────────────────────────────────────────────────────────────
class TestHall:
    def test_output_length(self):
        sig = _sine()
        p = ReverbDelayPreset("h", "hall", decay_time=1.0)
        out = apply_hall(sig, p)
        assert len(out) == len(sig)


# ─── PLATE ──────────────────────────────────────────────────────────────
class TestPlate:
    def test_output_length(self):
        sig = _sine()
        p = ReverbDelayPreset("pl", "plate")
        out = apply_plate(sig, p)
        assert len(out) == len(sig)


# ─── SHIMMER ────────────────────────────────────────────────────────────
class TestShimmer:
    def test_output_length(self):
        sig = _sine(220.0)
        p = ReverbDelayPreset("sh", "shimmer")
        out = apply_shimmer(sig, p)
        assert len(out) == len(sig)


# ─── DELAY ──────────────────────────────────────────────────────────────
class TestDelay:
    def test_output_length(self):
        sig = _sine()
        p = ReverbDelayPreset("dl", "delay", bpm=150.0, num_taps=5)
        out = apply_delay(sig, p)
        assert len(out) == len(sig)

    def test_fibonacci_taps(self):
        sig = _sine(440.0, 0.5)
        p = ReverbDelayPreset("dl2", "delay", num_taps=5, delay_feedback=0.5)
        out = apply_delay(sig, p)
        # Output should be normalized to original peak
        assert np.max(np.abs(out)) <= np.max(np.abs(sig)) + 1e-6


# ─── ROUTER ─────────────────────────────────────────────────────────────
class TestRouter:
    def test_routes_all_types(self):
        sig = _sine(440.0)
        for etype in ["room", "hall", "plate", "shimmer", "delay"]:
            p = ReverbDelayPreset(f"r_{etype}", etype)
            out = apply_reverb_delay(sig, p)
            assert len(out) == len(sig)

    def test_invalid_type(self):
        sig = _sine()
        p = ReverbDelayPreset("bad", "nonexistent")
        with pytest.raises(ValueError):
            apply_reverb_delay(sig, p)

    def test_wet_dry_mix(self):
        sig = _sine(440.0)
        p = ReverbDelayPreset("mix", "delay", mix=0.0)
        out = apply_reverb_delay(sig, p)
        np.testing.assert_allclose(out, sig, atol=1e-6)


# ─── BANKS ──────────────────────────────────────────────────────────────
class TestBanks:
    def test_all_banks_exist(self):
        assert len(ALL_REVERB_DELAY_BANKS) == 5

    def test_each_bank_has_4_presets(self):
        for name, gen in ALL_REVERB_DELAY_BANKS.items():
            bank = gen()
            assert len(bank.presets) == 4, f"{name} has {len(bank.presets)}"

    def test_room_bank(self):
        b = room_bank()
        assert b.name == "room"

    def test_hall_bank(self):
        b = hall_bank()
        assert b.name == "hall"

    def test_plate_bank(self):
        b = plate_bank()
        assert b.name == "plate"

    def test_shimmer_bank(self):
        b = shimmer_bank()
        assert b.name == "shimmer"

    def test_delay_bank(self):
        b = delay_bank()
        assert b.name == "delay"
        assert all(p.effect_type == "delay" for p in b.presets)


# ─── MANIFEST ───────────────────────────────────────────────────────────
class TestManifest:
    def test_write_manifest(self, tmp_path):
        m = write_reverb_delay_manifest(str(tmp_path))
        assert "banks" in m
        assert len(m["banks"]) == 5
        total = sum(b["preset_count"] for b in m["banks"].values())
        assert total == 20


# ─── WAV EXPORT ─────────────────────────────────────────────────────────
class TestExportReverbDelayDemos:
    def test_export_creates_wav_files(self, tmp_path):
        paths = export_reverb_delay_demos(str(tmp_path))
        assert len(paths) == 20
        for p in paths:
            assert p.endswith(".wav")

    def test_export_wav_valid(self, tmp_path):
        import wave as wave_mod
        paths = export_reverb_delay_demos(str(tmp_path))
        with wave_mod.open(paths[0], "r") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 44100
            assert wf.getnframes() > 0

    def test_export_all_banks_represented(self, tmp_path):
        paths = export_reverb_delay_demos(str(tmp_path))
        names = [p.split("/")[-1] for p in paths]
        for bank_name in ALL_REVERB_DELAY_BANKS:
            bank = ALL_REVERB_DELAY_BANKS[bank_name]()
            for preset in bank.presets:
                assert f"rvb_{preset.name}.wav" in names

    def test_export_wav_nonzero(self, tmp_path):
        import struct
        import wave as wave_mod
        paths = export_reverb_delay_demos(str(tmp_path))
        with wave_mod.open(paths[0], "r") as wf:
            frames = wf.readframes(wf.getnframes())
            samples = struct.unpack(f"<{wf.getnframes()}h", frames)
            assert any(s != 0 for s in samples)
