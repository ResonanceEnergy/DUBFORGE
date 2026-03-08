"""Tests for engine.convolution — 20 tests."""

import numpy as np
import pytest

from engine.convolution import (
    ALL_CONVOLUTION_BANKS,
    ConvolutionBank,
    ConvolutionPreset,
    apply_convolution,
    cabinet_ir_bank,
    convolve_signal,
    custom_ir_bank,
    generate_cabinet_ir,
    generate_custom_ir,
    generate_inverse_ir,
    generate_plate_ir,
    generate_room_ir,
    inverse_ir_bank,
    plate_ir_bank,
    room_ir_bank,
    write_convolution_manifest,
)

SR = 44100


def _sine(freq: float = 440.0, dur: float = 0.1, sr: int = SR) -> np.ndarray:
    t = np.arange(int(dur * sr)) / sr
    return np.sin(2.0 * np.pi * freq * t).astype(np.float64)


def _impulse(n: int = 4410) -> np.ndarray:
    sig = np.zeros(n)
    sig[0] = 1.0
    return sig


# ─── DATACLASS ──────────────────────────────────────────────────────────
class TestConvolutionPreset:
    def test_defaults(self):
        p = ConvolutionPreset("test", "room_ir")
        assert p.conv_type == "room_ir"
        assert p.mix == 0.5

    def test_custom_fields(self):
        p = ConvolutionPreset("c", "cabinet_ir", cabinet_size="2x12",
                              speaker_type="modern")
        assert p.cabinet_size == "2x12"


class TestConvolutionBank:
    def test_bank_creation(self):
        b = ConvolutionBank("tb", [ConvolutionPreset("a", "room_ir")])
        assert len(b.presets) == 1


# ─── IR GENERATORS ─────────────────────────────────────────────────────
class TestRoomIR:
    def test_length(self):
        p = ConvolutionPreset("r", "room_ir")
        ir = generate_room_ir(p)
        assert len(ir) > 0

    def test_normalized(self):
        p = ConvolutionPreset("r2", "room_ir")
        ir = generate_room_ir(p)
        assert np.max(np.abs(ir)) <= 1.0 + 1e-6


class TestCabinetIR:
    def test_length(self):
        p = ConvolutionPreset("c", "cabinet_ir")
        ir = generate_cabinet_ir(p)
        assert len(ir) > 0

    def test_all_sizes(self):
        for size in ["1x12", "2x12", "4x12"]:
            p = ConvolutionPreset(f"c_{size}", "cabinet_ir", cabinet_size=size)
            ir = generate_cabinet_ir(p)
            assert np.max(np.abs(ir)) > 0


class TestPlateIR:
    def test_length(self):
        p = ConvolutionPreset("p", "plate_ir", plate_size=0.5)
        ir = generate_plate_ir(p)
        expected = int(0.5 * SR)
        assert len(ir) == expected


class TestInverseIR:
    def test_inverse(self):
        p = ConvolutionPreset("inv", "inverse_ir", regularisation=0.01)
        original = generate_room_ir(ConvolutionPreset("room", "room_ir"))
        inv = generate_inverse_ir(original, p)
        assert len(inv) == len(original)


class TestCustomIR:
    def test_length(self):
        p = ConvolutionPreset("cust", "custom_ir", ir_length_ms=200.0)
        ir = generate_custom_ir(p)
        expected = int(200.0 * SR / 1000.0)
        assert len(ir) == expected


# ─── CONVOLUTION ────────────────────────────────────────────────────────
class TestConvolveSignal:
    def test_output_length(self):
        sig = _sine()
        ir = _impulse(100)
        out = convolve_signal(sig, ir)
        assert len(out) == len(sig)

    def test_identity_convolution(self):
        sig = _sine()
        ir = np.array([1.0])  # delta function
        out = convolve_signal(sig, ir)
        np.testing.assert_allclose(out, sig, atol=1e-10)


# ─── ROUTER ─────────────────────────────────────────────────────────────
class TestRouter:
    def test_all_types(self):
        sig = _sine(440.0, 0.05)
        for ctype in ["room_ir", "cabinet_ir", "plate_ir", "custom_ir"]:
            p = ConvolutionPreset(f"r_{ctype}", ctype, mix=0.3)
            out = apply_convolution(sig, p)
            assert len(out) == len(sig)

    def test_invalid_type(self):
        sig = _sine()
        p = ConvolutionPreset("bad", "nonexistent")
        with pytest.raises(ValueError):
            apply_convolution(sig, p)


# ─── BANKS ──────────────────────────────────────────────────────────────
class TestBanks:
    def test_all_banks_exist(self):
        assert len(ALL_CONVOLUTION_BANKS) == 5

    def test_each_bank_has_4_presets(self):
        for name, gen in ALL_CONVOLUTION_BANKS.items():
            bank = gen()
            assert len(bank.presets) == 4, f"{name} has {len(bank.presets)}"

    def test_room_ir_bank(self):
        b = room_ir_bank()
        assert b.name == "room_ir"

    def test_cabinet_ir_bank(self):
        b = cabinet_ir_bank()
        assert b.name == "cabinet_ir"

    def test_plate_ir_bank(self):
        b = plate_ir_bank()
        assert b.name == "plate_ir"

    def test_inverse_ir_bank(self):
        b = inverse_ir_bank()
        assert b.name == "inverse_ir"

    def test_custom_ir_bank(self):
        b = custom_ir_bank()
        assert b.name == "custom_ir"
        assert all(p.conv_type == "custom_ir" for p in b.presets)


# ─── MANIFEST ───────────────────────────────────────────────────────────
class TestManifest:
    def test_write_manifest(self, tmp_path):
        m = write_convolution_manifest(str(tmp_path))
        assert "banks" in m
        assert len(m["banks"]) == 5
        total = sum(b["preset_count"] for b in m["banks"].values())
        assert total == 20
