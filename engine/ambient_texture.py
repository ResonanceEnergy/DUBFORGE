"""
DUBFORGE Engine — Ambient Texture Generator

Synthesizes atmospheric ambient textures from scratch:
  - Rain:   filtered noise with droplet transients
  - Wind:   slowly modulated bandpass noise
  - Space:  deep reverb-like shimmer tones
  - Static: lo-fi crackling noise bed
  - Ocean:  rhythmic whoosh with undertow

All textures use phi-ratio modulation for organic feel.
Output as 16-bit mono WAV files at 44100 Hz.

Based on Subtronics production analysis:
  - Atmospheric beds underpin build sections
  - Noise textures add depth behind drops
  - Ambient layers create immersive soundscapes
"""

from __future__ import annotations

import json
import math
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engine.config_loader import PHI
from engine.log import get_logger
from engine.phi_core import SAMPLE_RATE

_log = get_logger("dubforge.ambient_texture")


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TexturePreset:
    """Settings for a single ambient texture."""
    name: str
    texture_type: str       # rain | wind | space | static | ocean
    duration_s: float = 6.0
    brightness: float = 0.5
    density: float = 0.5    # 0-1, element density
    depth: float = 0.5      # 0-1, reverb / spatial depth
    modulation_rate: float = 0.0  # Hz, 0 = auto (1/PHI)
    distortion: float = 0.0


@dataclass
class TextureBank:
    """Collection of texture presets."""
    name: str
    presets: list[TexturePreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# DSP UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def _write_wav(signal: np.ndarray, path: str,
               sample_rate: int = SAMPLE_RATE) -> str:
    """Write signal to 16-bit mono WAV."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = np.clip(signal * 32767, -32768, 32767).astype(np.int16)
        wf.writeframes(data.tobytes())
    _log.info("Wrote texture WAV: %s (%d samples)", out.name, len(signal))
    return str(out)


def _normalize(signal: np.ndarray) -> np.ndarray:
    """Normalize to 0.95 peak."""
    peak = np.max(np.abs(signal))
    return signal / peak * 0.95 if peak > 0 else signal


def _fade_in_out(signal: np.ndarray, fade_s: float = 0.5,
                 sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Apply fade in/out envelope."""
    n = len(signal)
    fade = max(1, min(int(fade_s * sample_rate), n // 2))
    env = np.ones(n)
    env[:fade] = np.linspace(0, 1, fade)
    env[-fade:] = np.linspace(1, 0, fade)
    return signal * env


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_rain(preset: TexturePreset,
                    sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Rain texture — filtered noise with random droplet transients."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.default_rng(101)

    # Base rain noise (bandpass filtered)
    noise = rng.uniform(-1, 1, n) * 0.3
    # Simple lowpass via running average
    kernel_size = max(1, int((1 - preset.brightness) * 20) + 2)
    padded = np.pad(noise, kernel_size, mode="edge")
    rain = np.convolve(padded, np.ones(kernel_size) / kernel_size, "same")
    rain = rain[kernel_size:kernel_size + n]

    # Random droplets
    num_drops = int(preset.density * preset.duration_s * 30)
    for _ in range(num_drops):
        pos = rng.integers(0, n - 200)
        drop_len = rng.integers(50, 200)
        amp = rng.uniform(0.3, 0.8)
        freq = rng.uniform(2000, 6000)
        t_drop = np.arange(drop_len) / sample_rate
        drop = amp * np.sin(2 * math.pi * freq * t_drop)
        drop *= np.exp(-np.arange(drop_len) / (drop_len * 0.2))
        rain[pos:pos + drop_len] += drop

    signal = _fade_in_out(rain, fade_s=1.0)
    return _normalize(signal)


def synthesize_wind(preset: TexturePreset,
                    sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Wind texture — slowly modulated bandpass noise."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.default_rng(202)

    noise = rng.uniform(-1, 1, n)

    # Slow LFO modulation for volume
    mod_rate = preset.modulation_rate if preset.modulation_rate > 0 else 1 / PHI
    t = np.arange(n) / sample_rate
    lfo = 0.5 + 0.5 * np.sin(2 * math.pi * mod_rate * t)
    lfo2 = 0.5 + 0.5 * np.sin(2 * math.pi * mod_rate * PHI * t + 1.0)

    # Brightness controls filter width
    kernel = max(2, int((1 - preset.brightness) * 30) + 2)
    padded = np.pad(noise, kernel, mode="edge")
    filtered = np.convolve(padded, np.ones(kernel) / kernel, "same")
    filtered = filtered[kernel:kernel + n]

    signal = filtered * lfo * preset.depth + filtered * lfo2 * 0.3
    signal = _fade_in_out(signal, fade_s=1.5)
    return _normalize(signal)


def synthesize_space(preset: TexturePreset,
                     sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Space texture — deep shimmer tones with reverb-like decay."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate

    # Layered sine tones at phi-ratio intervals
    base_freq = 60 + preset.brightness * 200
    signal = np.zeros(n)
    for i in range(6):
        freq = base_freq * (PHI ** i)
        if freq > sample_rate / 2:
            break
        amp = 0.3 / (i + 1)
        # Slow phase drift
        phase_drift = np.sin(2 * math.pi * 0.05 * (i + 1) * t) * 0.02
        signal += amp * np.sin(2 * math.pi * freq * t + phase_drift)

    # Depth controls "reverb" via comb-like feedback
    if preset.depth > 0:
        delay = int(0.03 * PHI * sample_rate)
        for i in range(delay, n):
            signal[i] += signal[i - delay] * preset.depth * 0.4

    signal = _fade_in_out(signal, fade_s=2.0)
    return _normalize(signal)


def synthesize_static(preset: TexturePreset,
                      sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Static texture — lo-fi crackling noise bed."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.default_rng(303)

    # Base low-level noise
    noise = rng.uniform(-0.2, 0.2, n)

    # Random crackles
    num_crackles = int(preset.density * preset.duration_s * 50)
    for _ in range(num_crackles):
        pos = rng.integers(0, max(1, n - 50))
        length = rng.integers(5, 50)
        end_pos = min(n, pos + length)
        amp = rng.uniform(0.3, 1.0)
        noise[pos:end_pos] += rng.choice([-1, 1]) * amp * np.exp(
            -np.arange(end_pos - pos) / max(1, length * 0.3))

    # Bit-crush effect for lo-fi character
    bits = max(4, int(16 - preset.distortion * 12))
    levels = 2 ** bits
    signal = np.round(noise * levels) / levels

    # Brightness filter
    if preset.brightness < 0.8:
        kernel = max(2, int((1 - preset.brightness) * 8) + 2)
        padded = np.pad(signal, kernel, mode="edge")
        signal = np.convolve(padded, np.ones(kernel) / kernel, "same")
        signal = signal[kernel:kernel + n]

    signal = _fade_in_out(signal, fade_s=0.5)
    return _normalize(signal)


def synthesize_ocean(preset: TexturePreset,
                     sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Ocean texture — rhythmic wave whoosh with undertow."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.default_rng(404)
    t = np.arange(n) / sample_rate

    # Wave rhythm — slow pulsing
    wave_rate = preset.modulation_rate if preset.modulation_rate > 0 else 0.15
    wave_env = 0.3 + 0.7 * (0.5 + 0.5 * np.sin(2 * math.pi * wave_rate * t)) ** PHI

    # Base surf noise
    noise = rng.uniform(-1, 1, n)
    kernel = max(2, int((1 - preset.brightness) * 15) + 3)
    padded = np.pad(noise, kernel, mode="edge")
    filtered = np.convolve(padded, np.ones(kernel) / kernel, "same")
    filtered = filtered[kernel:kernel + n]

    # Undertow — lower frequency rumble
    undertow = 0.2 * np.sin(2 * math.pi * 30 * t) * wave_env * preset.depth

    signal = filtered * wave_env + undertow
    signal = _fade_in_out(signal, fade_s=2.0)
    return _normalize(signal)


def synthesize_texture(preset: TexturePreset,
                       sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct texture synthesizer."""
    synthesizers = {
        "rain": synthesize_rain,
        "wind": synthesize_wind,
        "space": synthesize_space,
        "static": synthesize_static,
        "ocean": synthesize_ocean,
    }
    fn = synthesizers.get(preset.texture_type)
    if fn is None:
        raise ValueError(f"Unknown texture_type: {preset.texture_type!r}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# PRESETS — 20 ambient textures
# ═══════════════════════════════════════════════════════════════════════════

def rain_texture_bank() -> TextureBank:
    """Rain texture variants — light drizzle to heavy downpour."""
    return TextureBank(
        name="RAIN_TEXTURES",
        presets=[
            TexturePreset("rain_light", "rain", 8.0,
                          brightness=0.4, density=0.2, depth=0.3),
            TexturePreset("rain_medium", "rain", 8.0,
                          brightness=0.5, density=0.5, depth=0.5),
            TexturePreset("rain_heavy", "rain", 8.0,
                          brightness=0.6, density=0.8, depth=0.7),
            TexturePreset("rain_storm", "rain", 8.0,
                          brightness=0.8, density=1.0, depth=0.9),
        ],
    )


def wind_texture_bank() -> TextureBank:
    """Wind texture variants — gentle breeze to gale."""
    return TextureBank(
        name="WIND_TEXTURES",
        presets=[
            TexturePreset("wind_breeze", "wind", 10.0,
                          brightness=0.3, density=0.2, depth=0.4,
                          modulation_rate=0.3),
            TexturePreset("wind_howl", "wind", 10.0,
                          brightness=0.6, density=0.5, depth=0.7,
                          modulation_rate=0.5),
            TexturePreset("wind_gust", "wind", 8.0,
                          brightness=0.7, density=0.7, depth=0.6,
                          modulation_rate=0.8),
            TexturePreset("wind_gale", "wind", 10.0,
                          brightness=0.8, density=0.9, depth=0.9,
                          modulation_rate=1.2),
        ],
    )


def space_texture_bank() -> TextureBank:
    """Space texture variants — ethereal to deep void."""
    return TextureBank(
        name="SPACE_TEXTURES",
        presets=[
            TexturePreset("space_drift", "space", 10.0,
                          brightness=0.3, depth=0.4),
            TexturePreset("space_shimmer", "space", 10.0,
                          brightness=0.7, depth=0.6),
            TexturePreset("space_void", "space", 12.0,
                          brightness=0.2, depth=0.9),
            TexturePreset("space_crystal", "space", 8.0,
                          brightness=0.9, depth=0.5),
        ],
    )


def static_texture_bank() -> TextureBank:
    """Static texture variants — subtle hiss to heavy crackle."""
    return TextureBank(
        name="STATIC_TEXTURES",
        presets=[
            TexturePreset("static_hiss", "static", 6.0,
                          brightness=0.6, density=0.2, distortion=0.1),
            TexturePreset("static_crackle", "static", 6.0,
                          brightness=0.5, density=0.6, distortion=0.3),
            TexturePreset("static_vinyl", "static", 6.0,
                          brightness=0.4, density=0.4, distortion=0.5),
            TexturePreset("static_broken", "static", 6.0,
                          brightness=0.3, density=0.9, distortion=0.7),
        ],
    )


def ocean_texture_bank() -> TextureBank:
    """Ocean texture variants — calm shore to crashing waves."""
    return TextureBank(
        name="OCEAN_TEXTURES",
        presets=[
            TexturePreset("ocean_calm", "ocean", 10.0,
                          brightness=0.3, density=0.2, depth=0.4,
                          modulation_rate=0.1),
            TexturePreset("ocean_shore", "ocean", 10.0,
                          brightness=0.5, density=0.5, depth=0.6,
                          modulation_rate=0.15),
            TexturePreset("ocean_crash", "ocean", 10.0,
                          brightness=0.7, density=0.8, depth=0.8,
                          modulation_rate=0.2),
            TexturePreset("ocean_deep", "ocean", 12.0,
                          brightness=0.2, density=0.3, depth=0.9,
                          modulation_rate=0.08),
        ],
    )


ALL_TEXTURE_BANKS: dict[str, callable] = {
    "rain":   rain_texture_bank,
    "wind":   wind_texture_bank,
    "space":  space_texture_bank,
    "static": static_texture_bank,
    "ocean":  ocean_texture_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

def write_texture_manifest(
    banks: dict[str, TextureBank], out_dir: str,
) -> str:
    """Write JSON manifest of generated textures."""
    manifest = {
        "generator": "DUBFORGE Ambient Texture Generator",
        "sample_rate": SAMPLE_RATE,
        "banks": {},
    }
    for bank_name, bank in banks.items():
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [
                {
                    "name": p.name,
                    "type": p.texture_type,
                    "duration_s": round(p.duration_s, 3),
                }
                for p in bank.presets
            ],
        }

    out = Path(out_dir) / "ambient_texture_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2))
    _log.info("Wrote texture manifest → %s", out)
    return str(out)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Generate all ambient texture WAV files."""
    wav_dir = "output/wavetables"
    analysis_dir = "output/analysis"

    banks: dict[str, TextureBank] = {}
    total = 0

    for bank_name, gen_fn in ALL_TEXTURE_BANKS.items():
        bank = gen_fn()
        banks[bank_name] = bank
        for preset in bank.presets:
            signal = synthesize_texture(preset)
            path = f"{wav_dir}/texture_{preset.name}.wav"
            _write_wav(signal, path)
            total += 1

    write_texture_manifest(banks, analysis_dir)
    _log.info("Texture synthesis complete — %d WAVs across %d banks",
              total, len(banks))


if __name__ == "__main__":
    main()
