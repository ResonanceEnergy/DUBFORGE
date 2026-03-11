"""
DUBFORGE Engine — Stem Mixer

Mix multiple rendered stems with phi-weighted gain staging.
Outputs stereo mixdown with per-stem volume, pan, and mute controls.

Modes:
    simple      — equal gain sum
    phi_weight  — golden-ratio weighted gain cascade
    frequency   — frequency-band weighted mixing
    dynamic     — envelope-following dynamic mix
    parallel    — parallel compression mix

Banks: 5 modes × 4 presets = 20 presets
"""

import json
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engine.phi_core import SAMPLE_RATE

from engine.config_loader import PHI
# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class StemChannel:
    """Individual stem in a mix."""
    name: str
    gain_db: float = 0.0
    pan: float = 0.0  # -1 left, 0 center, +1 right
    mute: bool = False


@dataclass
class MixPreset:
    """Configuration for a stereo mixdown."""
    name: str
    mix_type: str  # simple, phi_weight, frequency, dynamic, parallel
    channels: list[StemChannel] = field(default_factory=list)
    master_gain_db: float = 0.0
    ceiling: float = 0.95


@dataclass
class MixBank:
    name: str
    presets: list[MixPreset]


# ═══════════════════════════════════════════════════════════════════════════
# MIXING ENGINES
# ═══════════════════════════════════════════════════════════════════════════

def _db_to_linear(db: float) -> float:
    return 10 ** (db / 20)


def _pan_to_lr(pan: float) -> tuple[float, float]:
    """Convert pan (-1..+1) to left/right gain."""
    left = np.cos((pan + 1) * np.pi / 4)
    right = np.sin((pan + 1) * np.pi / 4)
    return float(left), float(right)


def mix_stems_simple(stems: list[np.ndarray], preset: MixPreset) -> np.ndarray:
    """Equal-gain sum with per-channel panning."""
    if not stems:
        return np.zeros((SAMPLE_RATE, 2))
    max_len = max(len(s) for s in stems)
    out = np.zeros((max_len, 2))

    for i, stem in enumerate(stems):
        ch = preset.channels[i] if i < len(preset.channels) else StemChannel(f"stem_{i}")
        if ch.mute:
            continue
        gain = _db_to_linear(ch.gain_db)
        left_g, right_g = _pan_to_lr(ch.pan)
        padded = np.zeros(max_len)
        padded[:len(stem)] = stem
        out[:, 0] += padded * gain * left_g
        out[:, 1] += padded * gain * right_g

    master = _db_to_linear(preset.master_gain_db)
    return np.clip(out * master, -1, 1)


def mix_stems_phi_weight(stems: list[np.ndarray], preset: MixPreset) -> np.ndarray:
    """Phi-weighted gain cascade: each successive stem is 1/PHI quieter."""
    if not stems:
        return np.zeros((SAMPLE_RATE, 2))
    max_len = max(len(s) for s in stems)
    out = np.zeros((max_len, 2))

    for i, stem in enumerate(stems):
        ch = preset.channels[i] if i < len(preset.channels) else StemChannel(f"stem_{i}")
        if ch.mute:
            continue
        phi_gain = 1.0 / (PHI ** i)
        gain = _db_to_linear(ch.gain_db) * phi_gain
        left_g, right_g = _pan_to_lr(ch.pan)
        padded = np.zeros(max_len)
        padded[:len(stem)] = stem
        out[:, 0] += padded * gain * left_g
        out[:, 1] += padded * gain * right_g

    master = _db_to_linear(preset.master_gain_db)
    return np.clip(out * master, -1, 1)


def mix_stems_frequency(stems: list[np.ndarray], preset: MixPreset) -> np.ndarray:
    """Frequency-band weighted mixing using spectral centroid placement."""
    if not stems:
        return np.zeros((SAMPLE_RATE, 2))
    max_len = max(len(s) for s in stems)
    out = np.zeros((max_len, 2))

    for i, stem in enumerate(stems):
        ch = preset.channels[i] if i < len(preset.channels) else StemChannel(f"stem_{i}")
        if ch.mute:
            continue
        gain = _db_to_linear(ch.gain_db)
        # Spectral centroid determines stereo position
        fft_mag = np.abs(np.fft.rfft(stem[:min(len(stem), 4096)]))
        freqs = np.fft.rfftfreq(min(len(stem), 4096), 1 / SAMPLE_RATE)
        total = np.sum(fft_mag) + 1e-10
        centroid = np.sum(freqs * fft_mag) / total
        # Map centroid to pan: low=center, high=wide
        auto_pan = np.clip((centroid - 200) / 2000, -1, 1) * 0.5 + ch.pan * 0.5
        left_g, right_g = _pan_to_lr(float(auto_pan))
        padded = np.zeros(max_len)
        padded[:len(stem)] = stem
        out[:, 0] += padded * gain * left_g
        out[:, 1] += padded * gain * right_g

    master = _db_to_linear(preset.master_gain_db)
    return np.clip(out * master, -1, 1)


def mix_stems_dynamic(stems: list[np.ndarray], preset: MixPreset) -> np.ndarray:
    """Dynamic mixing: louder stems get compressed."""
    if not stems:
        return np.zeros((SAMPLE_RATE, 2))
    max_len = max(len(s) for s in stems)
    out = np.zeros((max_len, 2))

    for i, stem in enumerate(stems):
        ch = preset.channels[i] if i < len(preset.channels) else StemChannel(f"stem_{i}")
        if ch.mute:
            continue
        gain = _db_to_linear(ch.gain_db)
        # Simple envelope follower for compression
        env = np.abs(stem)
        smooth = np.convolve(env, np.ones(256) / 256, mode="same")
        comp_ratio = 1.0 / (1.0 + smooth * 2)
        compressed = stem * comp_ratio * gain
        left_g, right_g = _pan_to_lr(ch.pan)
        padded = np.zeros(max_len)
        padded[:len(compressed)] = compressed
        out[:, 0] += padded * left_g
        out[:, 1] += padded * right_g

    master = _db_to_linear(preset.master_gain_db)
    return np.clip(out * master, -1, 1)


def mix_stems_parallel(stems: list[np.ndarray], preset: MixPreset) -> np.ndarray:
    """Parallel compression mix: sum clean + heavily compressed."""
    if not stems:
        return np.zeros((SAMPLE_RATE, 2))
    max_len = max(len(s) for s in stems)
    clean = np.zeros((max_len, 2))
    compressed = np.zeros((max_len, 2))

    for i, stem in enumerate(stems):
        ch = preset.channels[i] if i < len(preset.channels) else StemChannel(f"stem_{i}")
        if ch.mute:
            continue
        gain = _db_to_linear(ch.gain_db)
        left_g, right_g = _pan_to_lr(ch.pan)
        padded = np.zeros(max_len)
        padded[:len(stem)] = stem
        clean[:, 0] += padded * gain * left_g
        clean[:, 1] += padded * gain * right_g
        # Hard compressed version
        comp = np.tanh(padded * 3) * 0.5
        compressed[:, 0] += comp * gain * left_g
        compressed[:, 1] += comp * gain * right_g

    mix = clean * 0.6 + compressed * 0.4
    master = _db_to_linear(preset.master_gain_db)
    return np.clip(mix * master, -1, 1)


MIX_ENGINES = {
    "simple": mix_stems_simple,
    "phi_weight": mix_stems_phi_weight,
    "frequency": mix_stems_frequency,
    "dynamic": mix_stems_dynamic,
    "parallel": mix_stems_parallel,
}


def mix_stems(stems: list[np.ndarray], preset: MixPreset) -> np.ndarray:
    """Route to appropriate mix engine."""
    fn = MIX_ENGINES.get(preset.mix_type, mix_stems_simple)
    return fn(stems, preset)


# ═══════════════════════════════════════════════════════════════════════════
# WAV EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def _write_wav_stereo(path: Path, samples: np.ndarray,
                      sample_rate: int = SAMPLE_RATE) -> None:
    """Write 16-bit stereo WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1, 1)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def _generate_test_stems(n_stems: int = 4, sr: int = SAMPLE_RATE) -> list[np.ndarray]:
    """Generate test stems with different frequency content."""
    dur = 1.0
    n = int(sr * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    stems: list[np.ndarray] = []
    freqs = [55.0, 220.0, 440.0, 880.0, 1760.0]
    for i in range(n_stems):
        f = freqs[i % len(freqs)]
        sig = 0.7 * np.sin(2 * np.pi * f * t)
        sig += 0.3 * np.sin(2 * np.pi * f * PHI * t)
        stems.append(sig)
    return stems


# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS
# ═══════════════════════════════════════════════════════════════════════════

def _default_channels() -> list[StemChannel]:
    return [
        StemChannel("bass", 0.0, 0.0),
        StemChannel("mid", -2.0, -0.3),
        StemChannel("high", -3.0, 0.3),
        StemChannel("fx", -6.0, 0.5),
    ]


def simple_mix_bank() -> MixBank:
    return MixBank("simple", [
        MixPreset("simple_balanced", "simple", _default_channels()),
        MixPreset("simple_bass_heavy", "simple", _default_channels(), master_gain_db=2.0),
        MixPreset("simple_wide", "simple", [
            StemChannel("bass", 0.0, 0.0),
            StemChannel("mid", -1.0, -0.7),
            StemChannel("high", -2.0, 0.7),
            StemChannel("fx", -4.0, -0.9),
        ]),
        MixPreset("simple_mono", "simple", [
            StemChannel("bass", 0.0, 0.0),
            StemChannel("mid", -2.0, 0.0),
            StemChannel("high", -3.0, 0.0),
            StemChannel("fx", -6.0, 0.0),
        ]),
    ])


def phi_weight_mix_bank() -> MixBank:
    return MixBank("phi_weight", [
        MixPreset("phi_balanced", "phi_weight", _default_channels()),
        MixPreset("phi_warm", "phi_weight", _default_channels(), master_gain_db=1.0),
        MixPreset("phi_subtle", "phi_weight", _default_channels(), master_gain_db=-2.0),
        MixPreset("phi_wide", "phi_weight", [
            StemChannel("bass", 0.0, 0.0),
            StemChannel("mid", 0.0, -0.5),
            StemChannel("high", 0.0, 0.5),
            StemChannel("fx", 0.0, 0.8),
        ]),
    ])


def frequency_mix_bank() -> MixBank:
    return MixBank("frequency", [
        MixPreset("freq_auto", "frequency", _default_channels()),
        MixPreset("freq_wide", "frequency", _default_channels(), master_gain_db=1.0),
        MixPreset("freq_tight", "frequency", _default_channels(), ceiling=0.8),
        MixPreset("freq_phi", "frequency", _default_channels(), master_gain_db=-1.0),
    ])


def dynamic_mix_bank() -> MixBank:
    return MixBank("dynamic", [
        MixPreset("dyn_standard", "dynamic", _default_channels()),
        MixPreset("dyn_heavy", "dynamic", _default_channels(), master_gain_db=3.0),
        MixPreset("dyn_light", "dynamic", _default_channels(), master_gain_db=-2.0),
        MixPreset("dyn_phi", "dynamic", _default_channels()),
    ])


def parallel_mix_bank() -> MixBank:
    return MixBank("parallel", [
        MixPreset("par_standard", "parallel", _default_channels()),
        MixPreset("par_heavy", "parallel", _default_channels(), master_gain_db=2.0),
        MixPreset("par_subtle", "parallel", _default_channels(), master_gain_db=-3.0),
        MixPreset("par_wide", "parallel", [
            StemChannel("bass", 0.0, 0.0),
            StemChannel("mid", 0.0, -0.6),
            StemChannel("high", 0.0, 0.6),
            StemChannel("fx", -3.0, 0.0),
        ]),
    ])


ALL_MIX_BANKS: dict[str, callable] = {
    "simple": simple_mix_bank,
    "phi_weight": phi_weight_mix_bank,
    "frequency": frequency_mix_bank,
    "dynamic": dynamic_mix_bank,
    "parallel": parallel_mix_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def export_mix_demos(output_dir: str = "output") -> list[str]:
    """Render all mix presets to stereo .wav."""
    out = Path(output_dir) / "wavetables" / "mixes"
    paths: list[str] = []
    stems = _generate_test_stems(4)
    for bank_name, bank_fn in ALL_MIX_BANKS.items():
        bank = bank_fn()
        for preset in bank.presets:
            mixed = mix_stems(stems, preset)
            fname = f"mix_{preset.name}.wav"
            _write_wav_stereo(out / fname, mixed)
            paths.append(str(out / fname))
    return paths


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST + MAIN
# ═══════════════════════════════════════════════════════════════════════════

def write_mix_manifest(output_dir: str = "output") -> dict:
    """Write stem mixer manifest JSON."""
    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"banks": {}}
    for bank_name, bank_fn in ALL_MIX_BANKS.items():
        bank = bank_fn()
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }
    path = out / "stem_mixer_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_mix_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    wavs = export_mix_demos()
    print(f"Stem Mixer: {len(manifest['banks'])} banks, {total} presets, {len(wavs)} .wav")


if __name__ == "__main__":
    main()
