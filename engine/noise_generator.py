"""
DUBFORGE Engine — Noise Generator

Synthesizes noise textures from scratch:
  - White:  flat-spectrum random noise
  - Pink:   1/f noise (spectral rolloff)
  - Brown:  1/f² noise (random walk / Brownian)
  - Vinyl:  crackle + hiss emulation
  - Tape:   tape hiss + flutter emulation

All sounds use phi-ratio envelopes and timing.
Output as 16-bit mono WAV files at 44100 Hz.

Outputs:
    output/wavetables/noise_*.wav
    output/analysis/noise_manifest.json
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

_log = get_logger("dubforge.noise_generator")


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class NoisePreset:
    """Settings for a single noise texture."""
    name: str
    noise_type: str          # white | pink | brown | vinyl | tape
    duration_s: float = 4.0
    brightness: float = 0.5  # high-shelf control 0..1
    density: float = 0.5     # event density for vinyl/tape crackle
    modulation: float = 0.0  # slow amplitude modulation depth 0..1
    mod_rate: float = 0.0    # modulation rate Hz
    attack_s: float = 0.1
    release_s: float = 0.5
    gain: float = 0.8        # output level


@dataclass
class NoiseBank:
    """Collection of noise presets."""
    name: str
    presets: list[NoisePreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIS HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _fade_envelope(n: int, preset: NoisePreset,
                   sample_rate: int) -> np.ndarray:
    """Build fade-in / fade-out envelope."""
    env = np.ones(n)
    a = max(1, min(int(preset.attack_s * sample_rate), n // 2))
    r = max(1, min(int(preset.release_s * sample_rate), n // 2))
    env[:a] = np.linspace(0, 1, a)
    env[-r:] = np.linspace(1, 0, r)
    return env


def _amplitude_mod(t: np.ndarray, preset: NoisePreset) -> np.ndarray:
    """Slow amplitude modulation."""
    if preset.modulation <= 0 or preset.mod_rate <= 0:
        return np.ones_like(t)
    return 1.0 - preset.modulation * 0.5 * (
        1 - np.cos(2 * math.pi * preset.mod_rate * t)
    )


# ═══════════════════════════════════════════════════════════════════════════
# NOISE SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_white(preset: NoisePreset,
                     sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Flat-spectrum white noise."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    rng = np.random.default_rng(42)

    noise = rng.standard_normal(n)

    # Brightness: simple high-shelf boost/cut via mixing filtered version
    if preset.brightness < 0.5:
        k = max(1, int(sample_rate / 4000))
        kernel = np.ones(k) / k
        smooth = np.convolve(noise, kernel, mode="same")
        mix = 1.0 - preset.brightness * 2  # 0→1 (all smooth), 0.5→0 (none)
        noise = noise * (1 - mix) + smooth * mix

    env = _fade_envelope(n, preset, sample_rate)
    mod = _amplitude_mod(t, preset)
    signal = noise * env * mod * preset.gain
    return signal / (np.max(np.abs(signal)) + 1e-10)


def synthesize_pink(preset: NoisePreset,
                    sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """1/f pink noise using Voss-McCartney algorithm."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    rng = np.random.default_rng(42)

    # Simple spectral shaping: filter white noise
    white = rng.standard_normal(n)
    # 3-stage accumulator for pink approximation
    b = [0.0, 0.0, 0.0]
    pink = np.zeros(n)
    for i in range(n):
        b[0] = 0.99886 * b[0] + white[i] * 0.0555179
        b[1] = 0.99332 * b[1] + white[i] * 0.0750759
        b[2] = 0.96900 * b[2] + white[i] * 0.1538520
        pink[i] = b[0] + b[1] + b[2] + white[i] * 0.5362
    pink /= np.max(np.abs(pink)) + 1e-10

    env = _fade_envelope(n, preset, sample_rate)
    mod = _amplitude_mod(t, preset)
    signal = pink * env * mod * preset.gain
    return signal / (np.max(np.abs(signal)) + 1e-10)


def synthesize_brown(preset: NoisePreset,
                     sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """1/f² Brownian noise (random walk)."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    rng = np.random.default_rng(42)

    steps = rng.standard_normal(n) * 0.02
    brown = np.cumsum(steps)
    # Remove DC drift
    brown -= np.linspace(brown[0], brown[-1], n)
    brown /= np.max(np.abs(brown)) + 1e-10

    env = _fade_envelope(n, preset, sample_rate)
    mod = _amplitude_mod(t, preset)
    signal = brown * env * mod * preset.gain
    return signal / (np.max(np.abs(signal)) + 1e-10)


def synthesize_vinyl(preset: NoisePreset,
                     sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Vinyl crackle + hiss emulation."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    rng = np.random.default_rng(42)

    # Base hiss layer (quiet white noise)
    hiss = rng.standard_normal(n) * 0.15

    # Crackle events (sparse impulses)
    crackle_density = preset.density * 200  # events per second
    num_crackles = int(crackle_density * preset.duration_s)
    crackle = np.zeros(n)
    positions = rng.integers(0, n, num_crackles)
    amplitudes = rng.uniform(0.3, 1.0, num_crackles)
    for pos, amp in zip(positions, amplitudes):
        decay_len = min(rng.integers(20, 80), n - pos)
        crackle[pos:pos + decay_len] += amp * np.exp(
            -np.arange(decay_len) / (decay_len * 0.3)
        )

    signal = hiss + crackle * 0.6
    env = _fade_envelope(n, preset, sample_rate)
    mod = _amplitude_mod(t, preset)
    signal = signal * env * mod * preset.gain
    return signal / (np.max(np.abs(signal)) + 1e-10)


def synthesize_tape(preset: NoisePreset,
                    sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Tape hiss + flutter emulation."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    rng = np.random.default_rng(42)

    # Tape hiss (band-limited white noise)
    raw = rng.standard_normal(n)
    k = max(1, int(sample_rate / 8000))
    kernel = np.ones(k) / k
    hiss = np.convolve(raw, kernel, mode="same")
    hiss /= np.max(np.abs(hiss)) + 1e-10

    # Flutter (slow pitch wobble effect via amplitude modulation)
    flutter_rate = PHI * 2.5  # ~4 Hz
    flutter = 1.0 + 0.03 * np.sin(2 * math.pi * flutter_rate * t)
    flutter *= 1.0 + 0.01 * np.sin(2 * math.pi * flutter_rate * PHI * t)

    # Optional dropouts (density-based)
    if preset.density > 0.3:
        num_drops = int(preset.density * 5)
        for _ in range(num_drops):
            pos = rng.integers(0, max(1, n - 1000))
            drop_len = rng.integers(100, 500)
            end = min(pos + drop_len, n)
            hiss[pos:end] *= 0.1

    signal = hiss * flutter
    env = _fade_envelope(n, preset, sample_rate)
    mod = _amplitude_mod(t, preset)
    signal = signal * env * mod * preset.gain
    return signal / (np.max(np.abs(signal)) + 1e-10)


def synthesize_digital(preset: NoisePreset,
                      sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Digital noise — bit-crushed aliased texture."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    rng = np.random.default_rng(42)

    # Low sample-rate noise (aliased)
    rate_reduction = max(2, int(4 + (1 - preset.brightness) * 20))
    raw_len = max(1, n // rate_reduction)
    raw = rng.standard_normal(raw_len)
    # Repeat each sample to create staircase
    digital = np.repeat(raw, rate_reduction)[:n]
    if len(digital) < n:
        digital = np.pad(digital, (0, n - len(digital)), mode="edge")

    # Bit-crush
    bits = max(2, int(4 + preset.brightness * 8))
    levels = 2 ** bits
    digital = np.round(digital * levels) / levels

    env = _fade_envelope(n, preset, sample_rate)
    mod = _amplitude_mod(t, preset)
    signal = digital * env * mod * preset.gain
    return signal / (np.max(np.abs(signal)) + 1e-10)


def synthesize_rain_noise(preset: NoisePreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Rain-like noise — bandpass-filtered with droplet transients."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    rng = np.random.default_rng(42)

    # Bandpass base (brown-ish with some high-freq)
    white = rng.standard_normal(n)
    k_lp = max(1, int((1 - preset.brightness) * 15) + 2)
    kernel_lp = np.ones(k_lp) / k_lp
    filtered = np.convolve(white, kernel_lp, mode="same")
    filtered /= np.max(np.abs(filtered)) + 1e-10

    # Random droplets
    num_drops = int(preset.density * preset.duration_s * 40)
    for _ in range(num_drops):
        pos = rng.integers(0, max(1, n - 200))
        drop_len = rng.integers(30, 150)
        end = min(n, pos + drop_len)
        amp = rng.uniform(0.2, 0.6)
        freq = rng.uniform(3000, 8000)
        t_d = np.arange(end - pos) / sample_rate
        drop = amp * np.sin(2 * math.pi * freq * t_d)
        drop *= np.exp(-np.arange(end - pos) / max(1, drop_len * 0.2))
        filtered[pos:end] += drop

    env = _fade_envelope(n, preset, sample_rate)
    mod = _amplitude_mod(t, preset)
    signal = filtered * env * mod * preset.gain
    return signal / (np.max(np.abs(signal)) + 1e-10)


# ═══════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_noise(preset: NoisePreset,
                     sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct noise synthesizer."""
    synthesizers = {
        "white": synthesize_white,
        "pink": synthesize_pink,
        "brown": synthesize_brown,
        "vinyl": synthesize_vinyl,
        "tape": synthesize_tape,
        "digital": synthesize_digital,
        "rain": synthesize_rain_noise,
    }
    fn = synthesizers.get(preset.noise_type)
    if fn is None:
        raise ValueError(f"Unknown noise_type: {preset.noise_type!r}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS — 5 types × 4 variants = 20 presets
# ═══════════════════════════════════════════════════════════════════════════

def white_noise_bank() -> NoiseBank:
    """White noise textures — 4 presets."""
    return NoiseBank(
        name="white",
        presets=[
            NoisePreset("white_bright", "white", 4.0, brightness=0.8, gain=0.7),
            NoisePreset("white_dark", "white", 4.0, brightness=0.2, gain=0.6),
            NoisePreset("white_modulated", "white", 6.0, brightness=0.5,
                        modulation=0.4, mod_rate=PHI, gain=0.65),
            NoisePreset("white_short", "white", 1.0, brightness=0.6,
                        attack_s=0.01, release_s=0.3, gain=0.75),
        ],
    )


def pink_noise_bank() -> NoiseBank:
    """Pink noise textures — 4 presets."""
    return NoiseBank(
        name="pink",
        presets=[
            NoisePreset("pink_natural", "pink", 4.0, brightness=0.5, gain=0.7),
            NoisePreset("pink_warm", "pink", 4.0, brightness=0.3, gain=0.65),
            NoisePreset("pink_pulsing", "pink", 6.0, brightness=0.5,
                        modulation=0.5, mod_rate=PHI * 0.5, gain=0.6),
            NoisePreset("pink_burst", "pink", 1.5, brightness=0.7,
                        attack_s=0.005, release_s=0.4, gain=0.8),
        ],
    )


def brown_noise_bank() -> NoiseBank:
    """Brown noise textures — 4 presets."""
    return NoiseBank(
        name="brown",
        presets=[
            NoisePreset("brown_deep", "brown", 5.0, brightness=0.3, gain=0.7),
            NoisePreset("brown_rumble", "brown", 4.0, brightness=0.2,
                        modulation=0.3, mod_rate=0.5, gain=0.65),
            NoisePreset("brown_drift", "brown", 8.0, brightness=0.4,
                        modulation=0.2, mod_rate=PHI * 0.3, gain=0.6),
            NoisePreset("brown_short", "brown", 2.0, brightness=0.5,
                        attack_s=0.02, release_s=0.5, gain=0.75),
        ],
    )


def vinyl_noise_bank() -> NoiseBank:
    """Vinyl crackle textures — 4 presets."""
    return NoiseBank(
        name="vinyl",
        presets=[
            NoisePreset("vinyl_light", "vinyl", 4.0, density=0.2, gain=0.6),
            NoisePreset("vinyl_heavy", "vinyl", 4.0, density=0.8, gain=0.7),
            NoisePreset("vinyl_worn", "vinyl", 6.0, density=0.5,
                        modulation=0.2, mod_rate=0.3, gain=0.55),
            NoisePreset("vinyl_intro", "vinyl", 2.0, density=0.4,
                        attack_s=0.5, release_s=0.8, gain=0.5),
        ],
    )


def tape_noise_bank() -> NoiseBank:
    """Tape hiss textures — 4 presets."""
    return NoiseBank(
        name="tape",
        presets=[
            NoisePreset("tape_clean", "tape", 4.0, density=0.1, gain=0.6),
            NoisePreset("tape_worn", "tape", 4.0, density=0.6, gain=0.65),
            NoisePreset("tape_flutter", "tape", 6.0, density=0.3,
                        modulation=0.3, mod_rate=PHI, gain=0.55),
            NoisePreset("tape_lo_fi", "tape", 3.0, density=0.7,
                        brightness=0.3, gain=0.7),
        ],
    )


def digital_noise_bank() -> NoiseBank:
    """Digital noise textures — bit-crushed artifacts — 4 presets."""
    return NoiseBank(
        name="digital",
        presets=[
            NoisePreset("digital_clean", "digital", 4.0, brightness=0.7, gain=0.65),
            NoisePreset("digital_harsh", "digital", 4.0, brightness=0.3, gain=0.7),
            NoisePreset("digital_pulsing", "digital", 6.0, brightness=0.5,
                        modulation=0.4, mod_rate=PHI, gain=0.6),
            NoisePreset("digital_glitch", "digital", 2.0, brightness=0.2,
                        density=0.8, gain=0.75),
        ],
    )


def rain_noise_bank() -> NoiseBank:
    """Rain noise textures — bandpass with droplets — 4 presets."""
    return NoiseBank(
        name="rain",
        presets=[
            NoisePreset("rain_light", "rain", 4.0, brightness=0.6,
                        density=0.2, gain=0.6),
            NoisePreset("rain_heavy", "rain", 4.0, brightness=0.5,
                        density=0.8, gain=0.7),
            NoisePreset("rain_tropical", "rain", 6.0, brightness=0.7,
                        density=0.6, modulation=0.2, mod_rate=0.3, gain=0.65),
            NoisePreset("rain_drizzle", "rain", 3.0, brightness=0.4,
                        density=0.1, gain=0.55),
        ],
    )


ALL_NOISE_BANKS: dict[str, callable] = {
    "white": white_noise_bank,
    "pink": pink_noise_bank,
    "brown": brown_noise_bank,
    "vinyl": vinyl_noise_bank,
    "tape": tape_noise_bank,
    # v2.2
    "digital": digital_noise_bank,
    "rain": rain_noise_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# WAV OUTPUT + MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

def _write_wav(path: Path, samples: np.ndarray,
               sample_rate: int = SAMPLE_RATE) -> None:
    """Write 16-bit mono WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1, 1)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def write_noise_manifest(output_dir: str = "output") -> dict:
    """Synthesize all noise presets and write manifest JSON."""
    out = Path(output_dir)
    wav_dir = out / "wavetables"
    manifest: dict = {"module": "noise_generator", "banks": {}}

    for bank_key, bank_fn in ALL_NOISE_BANKS.items():
        bank = bank_fn()
        entries = []
        for preset in bank.presets:
            audio = synthesize_noise(preset)
            fname = f"noise_{preset.name}.wav"
            _write_wav(wav_dir / fname, audio)
            entries.append({
                "name": preset.name,
                "noise_type": preset.noise_type,
                "duration_s": preset.duration_s,
                "file": fname,
            })
            _log.info("  ✓ %s", preset.name)
        manifest["banks"][bank_key] = entries

    manifest_path = out / "analysis" / "noise_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    _log.info("Noise manifest → %s", manifest_path)
    return manifest


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Generate all noise textures."""
    _log.info("═══ DUBFORGE Noise Generator ═══")
    manifest = write_noise_manifest()
    total = sum(len(v) for v in manifest["banks"].values())
    _log.info("Generated %d noise presets across %d banks",
              total, len(manifest["banks"]))


if __name__ == "__main__":
    main()
