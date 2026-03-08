"""Tests for engine.sound_palette — Sound Palette (Phase 4)."""

import wave
from pathlib import Path

import numpy as np
import pytest

from engine.sound_palette import (
    ALL_PALETTE_BANKS,
    PaletteBank,
    PaletteColor,
    PalettePreset,
    _write_wav,
    export_palette_tones,
    generate_palette,
    render_palette_tone,
    write_palette_manifest,
)

# ── dataclass tests ──────────────────────────────────────────────────────

def test_palette_color_defaults():
    c = PaletteColor(name="c")
    assert c.fundamental == 432.0
    assert len(c.harmonics) == 3
    assert c.brightness == 0.5


def test_palette_color_custom():
    c = PaletteColor(name="c", fundamental=220.0, brightness=0.9)
    assert c.fundamental == 220.0
    assert c.brightness == 0.9


def test_palette_preset_defaults():
    p = PalettePreset(name="t", palette_type="warm")
    assert p.num_colors == 5
    assert p.base_freq == 432.0
    assert p.phi_spacing is True


def test_palette_bank_dataclass():
    b = PaletteBank(name="test_bank", presets=[
        PalettePreset(name="a", palette_type="warm"),
    ])
    assert len(b.presets) == 1
    assert b.name == "test_bank"


# ── palette generators ──────────────────────────────────────────────────

def test_generate_warm_palette():
    p = PalettePreset(name="t", palette_type="warm", num_colors=3)
    colors = generate_palette(p)
    assert len(colors) == 3
    assert all(isinstance(c, PaletteColor) for c in colors)


def test_generate_cold_palette():
    p = PalettePreset(name="t", palette_type="cold", num_colors=4)
    colors = generate_palette(p)
    assert len(colors) == 4


def test_generate_metallic_palette():
    p = PalettePreset(name="t", palette_type="metallic", num_colors=5)
    colors = generate_palette(p)
    assert len(colors) == 5


def test_generate_organic_palette():
    p = PalettePreset(name="t", palette_type="organic", num_colors=3)
    colors = generate_palette(p)
    assert len(colors) == 3


def test_generate_hybrid_palette():
    p = PalettePreset(name="t", palette_type="hybrid", num_colors=4)
    colors = generate_palette(p)
    assert len(colors) == 4


def test_generate_palette_unknown_type():
    p = PalettePreset(name="t", palette_type="nonexistent")
    with pytest.raises(ValueError):
        generate_palette(p)


# ── render_palette_tone ─────────────────────────────────────────────────

def test_render_palette_tone_is_numpy_array():
    c = PaletteColor(name="c", fundamental=440.0)
    sig = render_palette_tone(c, duration=0.5)
    assert isinstance(sig, np.ndarray)


def test_render_palette_tone_correct_length():
    c = PaletteColor(name="c", fundamental=440.0)
    dur = 0.5
    sig = render_palette_tone(c, duration=dur)
    expected = int(44100 * dur)
    assert len(sig) == expected


def test_render_palette_tone_normalized():
    c = PaletteColor(name="c", fundamental=440.0)
    sig = render_palette_tone(c, duration=0.5)
    assert np.max(np.abs(sig)) <= 1.0


# ── _write_wav ──────────────────────────────────────────────────────────

def test_write_wav_creates_file(tmp_path):
    sig = np.sin(2 * np.pi * 440 * np.arange(22050) / 44100)
    out = str(tmp_path / "test.wav")
    _write_wav(out, sig)
    assert Path(out).exists()
    with wave.open(out, "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2


# ── banks ────────────────────────────────────────────────────────────────

def test_all_banks_registered():
    assert len(ALL_PALETTE_BANKS) == 5


def test_total_presets_is_20():
    total = sum(len(fn().presets) for fn in ALL_PALETTE_BANKS.values())
    assert total == 20


def test_each_bank_has_4_presets():
    for name, gen_fn in ALL_PALETTE_BANKS.items():
        bank = gen_fn()
        assert len(bank.presets) == 4, f"Bank {name} has {len(bank.presets)} presets"


# ── manifest + export ───────────────────────────────────────────────────

def test_write_manifest(tmp_path):
    manifest = write_palette_manifest(str(tmp_path))
    assert "banks" in manifest
    assert len(manifest["banks"]) == 5
    json_path = tmp_path / "wavetables" / "palettes" / "sound_palette_manifest.json"
    assert json_path.exists()


def test_export_palette_tones_creates_wav_files(tmp_path):
    paths = export_palette_tones(str(tmp_path))
    assert isinstance(paths, list)
    assert len(paths) > 0
    for p in paths:
        assert Path(p).exists()
        assert p.endswith(".wav")


def test_render_palette_tone_different_durations():
    c = PaletteColor(name="c", fundamental=440.0)
    for dur in (0.1, 0.25, 1.0):
        sig = render_palette_tone(c, duration=dur)
        expected = int(44100 * dur)
        assert len(sig) == expected
