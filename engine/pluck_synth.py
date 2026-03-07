"""
DUBFORGE Engine — Pluck Synth

Synthesizes plucked-string one-shot sounds:
  - String:   classical plucked string via Karplus-Strong
  - Bell:     metallic bell pluck with inharmonic partials
  - Key:      piano-key pluck with hammer strike character
  - Harp:     glassy harp pluck with harmonic ring
  - Marimba:  wooden bar pluck with muted decay

All use phi-ratio harmonic relationships.
Output as 16-bit mono WAV files at 44100 Hz.

Outputs:
    output/wavetables/pluck_synth_*.wav
    output/analysis/pluck_synth_manifest.json
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

_log = get_logger("dubforge.pluck_synth")


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PluckPreset:
    """Settings for a single pluck one-shot."""
    name: str
    pluck_type: str          # string | bell | key | harp | marimba
    frequency: float = 220.0  # Hz
    duration_s: float = 1.5
    attack_s: float = 0.001
    decay_s: float = 0.4
    brightness: float = 0.7   # 0..1 — controls harmonic content
    body: float = 0.5         # 0..1 — body/resonance
    damping: float = 0.5      # 0..1 — high-freq damping
    distortion: float = 0.0


@dataclass
class PluckBank:
    """Collection of pluck presets."""
    name: str
    presets: list[PluckPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# ENVELOPES / HELPERS
# ═══════════════════════════════════════════════════════════════════════════

NOTE_A3 = 220.00
NOTE_C4 = 261.63
NOTE_E3 = 164.81
NOTE_G3 = 196.00


def _pluck_envelope(n: int, preset: PluckPreset,
                    sample_rate: int) -> np.ndarray:
    """Attack-decay envelope for pluck sounds."""
    a = max(1, min(int(preset.attack_s * sample_rate), n // 2))
    t_full = np.arange(n) / sample_rate
    env = np.exp(-t_full / max(0.01, preset.decay_s))
    # Attack ramp
    env[:a] *= np.linspace(0, 1, a)
    return env


def _soft_clip(signal: np.ndarray, drive: float) -> np.ndarray:
    """Soft saturation."""
    if drive <= 0:
        return signal
    gain = 1.0 + drive * 4.0
    return np.tanh(signal * gain) / np.tanh(gain)


# ═══════════════════════════════════════════════════════════════════════════
# PLUCK SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_string_pluck(preset: PluckPreset,
                            sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Karplus-Strong inspired plucked string."""
    n = int(preset.duration_s * sample_rate)
    # Delay line length from frequency
    delay_len = max(2, int(sample_rate / preset.frequency))
    # Initialize with noise burst
    buf = np.random.default_rng(42).uniform(-1, 1, delay_len)
    # Brightness sets initial LP
    if preset.brightness < 0.9:
        k = max(1, int((1 - preset.brightness) * 4))
        kernel = np.ones(k) / k
        buf = np.convolve(buf, kernel, mode="same")

    out = np.zeros(n)
    damp = 0.495 + 0.005 * (1 - preset.damping)
    for i in range(n):
        idx = i % delay_len
        out[i] = buf[idx]
        nxt = (idx + 1) % delay_len
        buf[idx] = damp * (buf[idx] + buf[nxt])
    env = _pluck_envelope(n, preset, sample_rate)
    out *= env
    out = _soft_clip(out, preset.distortion)
    out /= np.max(np.abs(out)) + 1e-10
    return out


def synthesize_bell_pluck(preset: PluckPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Metallic bell pluck with inharmonic partials."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    freq = preset.frequency
    # Inharmonic partials (bell-like ratios)
    ratios = [1.0, 2.0 * PHI, 3.0, 4.236, 5.618, 7.0]
    amps = [1.0, 0.6, 0.4, 0.25, 0.15, 0.08]
    osc = np.zeros(n)
    for ratio, amp in zip(ratios, amps):
        partial_freq = freq * ratio
        # Each partial decays at different rate
        decay_rate = preset.decay_s / ratio
        envelope = np.exp(-t / max(0.01, decay_rate))
        osc += amp * envelope * np.sin(2 * math.pi * partial_freq * t)
    # Brightness filtering
    if preset.brightness < 0.8:
        k = max(1, int((1 - preset.brightness) * 6))
        kernel = np.ones(k) / k
        osc = np.convolve(osc, kernel, mode="same")
    env = _pluck_envelope(n, preset, sample_rate)
    osc *= env
    osc = _soft_clip(osc, preset.distortion)
    osc /= np.max(np.abs(osc)) + 1e-10
    return osc


def synthesize_key_pluck(preset: PluckPreset,
                         sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Piano-key pluck with hammer character."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    freq = preset.frequency
    # Harmonic series with inharmonicity (piano stretch)
    osc = np.zeros(n)
    for h in range(1, 8):
        # Slight inharmonicity: each partial slightly sharper
        stretched = freq * h * (1.0 + 0.0003 * h * h)
        amp = 1.0 / (h ** (1.5 - preset.brightness))
        decay = preset.decay_s / (1.0 + h * 0.3)
        env_h = np.exp(-t / max(0.01, decay))
        osc += amp * env_h * np.sin(2 * math.pi * stretched * t)
    # Hammer noise burst at onset
    hammer_len = max(1, int(0.002 * sample_rate))
    hammer = np.random.default_rng(42).uniform(-0.3, 0.3, hammer_len)
    osc[:hammer_len] += hammer * preset.body
    env = _pluck_envelope(n, preset, sample_rate)
    osc *= env
    osc = _soft_clip(osc, preset.distortion)
    osc /= np.max(np.abs(osc)) + 1e-10
    return osc


def synthesize_harp_pluck(preset: PluckPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Glassy harp pluck with harmonic ring."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    freq = preset.frequency
    # Pure harmonics for harp tone
    osc = (np.sin(2 * math.pi * freq * t)
           + 0.3 * np.sin(2 * math.pi * freq * 2 * t)
           + 0.15 * np.sin(2 * math.pi * freq * 3 * t)
           + 0.05 * np.sin(2 * math.pi * freq * 5 * t))
    # Body resonance (low ring)
    if preset.body > 0:
        osc += preset.body * 0.2 * np.sin(
            2 * math.pi * freq * 0.5 * t
        ) * np.exp(-t / max(0.01, preset.decay_s * 1.5))
    env = _pluck_envelope(n, preset, sample_rate)
    osc *= env
    osc = _soft_clip(osc, preset.distortion)
    osc /= np.max(np.abs(osc)) + 1e-10
    return osc


def synthesize_marimba_pluck(preset: PluckPreset,
                             sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Wooden bar pluck with muted decay."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    freq = preset.frequency
    # Marimba: fundamental + 4x harmonic (tuned bar)
    osc = (np.sin(2 * math.pi * freq * t)
           + 0.15 * np.sin(2 * math.pi * freq * 4 * t))
    # Short click/thack at onset
    click_len = max(1, int(0.003 * sample_rate))
    click = np.random.default_rng(42).uniform(-0.5, 0.5, click_len)
    osc[:click_len] += click * preset.body
    # Heavy damping — quick decay of highs
    env = _pluck_envelope(n, preset, sample_rate)
    # Extra decay for muted character
    mute_env = np.exp(-t / max(0.01, preset.decay_s * 0.6))
    osc *= env * mute_env
    # Low-pass
    k = max(1, int((1 - preset.brightness) * 8) + 2)
    kernel = np.ones(k) / k
    osc = np.convolve(osc, kernel, mode="same")
    osc = _soft_clip(osc, preset.distortion)
    osc /= np.max(np.abs(osc)) + 1e-10
    return osc


# ═══════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_pluck(preset: PluckPreset,
                     sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct pluck synthesizer."""
    synthesizers = {
        "string":  synthesize_string_pluck,
        "bell":    synthesize_bell_pluck,
        "key":     synthesize_key_pluck,
        "harp":    synthesize_harp_pluck,
        "marimba": synthesize_marimba_pluck,
    }
    fn = synthesizers.get(preset.pluck_type)
    if fn is None:
        raise ValueError(f"Unknown pluck_type: {preset.pluck_type!r}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS — 5 types × 4 variants = 20 presets
# ═══════════════════════════════════════════════════════════════════════════

def string_pluck_bank() -> PluckBank:
    """Plucked string presets — 4 variants."""
    return PluckBank(
        name="STRING_PLUCKS",
        presets=[
            PluckPreset("string_pluck_A3", "string", NOTE_A3,
                        decay_s=0.5, brightness=0.7, damping=0.4),
            PluckPreset("string_pluck_C4", "string", NOTE_C4,
                        decay_s=0.4, brightness=0.8, damping=0.3),
            PluckPreset("string_pluck_E3", "string", NOTE_E3,
                        decay_s=0.6, brightness=0.6, damping=0.5),
            PluckPreset("string_pluck_G3", "string", NOTE_G3,
                        decay_s=0.45, brightness=0.75, damping=0.35),
        ],
    )


def bell_pluck_bank() -> PluckBank:
    """Bell pluck presets — 4 variants."""
    return PluckBank(
        name="BELL_PLUCKS",
        presets=[
            PluckPreset("bell_pluck_A3", "bell", NOTE_A3,
                        decay_s=0.8, brightness=0.9),
            PluckPreset("bell_pluck_C4", "bell", NOTE_C4,
                        decay_s=1.0, brightness=0.85),
            PluckPreset("bell_pluck_E3", "bell", NOTE_E3,
                        decay_s=0.7, brightness=0.95),
            PluckPreset("bell_pluck_G3", "bell", NOTE_G3,
                        decay_s=0.9, brightness=0.8),
        ],
    )


def key_pluck_bank() -> PluckBank:
    """Piano-key pluck presets — 4 variants."""
    return PluckBank(
        name="KEY_PLUCKS",
        presets=[
            PluckPreset("key_pluck_A3", "key", NOTE_A3,
                        decay_s=0.6, brightness=0.7, body=0.6),
            PluckPreset("key_pluck_C4", "key", NOTE_C4,
                        decay_s=0.5, brightness=0.8, body=0.5),
            PluckPreset("key_pluck_E3", "key", NOTE_E3,
                        decay_s=0.7, brightness=0.65, body=0.7),
            PluckPreset("key_pluck_G3", "key", NOTE_G3,
                        decay_s=0.55, brightness=0.75, body=0.55),
        ],
    )


def harp_pluck_bank() -> PluckBank:
    """Harp pluck presets — 4 variants."""
    return PluckBank(
        name="HARP_PLUCKS",
        presets=[
            PluckPreset("harp_pluck_A3", "harp", NOTE_A3,
                        decay_s=1.0, brightness=0.85, body=0.4),
            PluckPreset("harp_pluck_C4", "harp", NOTE_C4,
                        decay_s=0.9, brightness=0.9, body=0.3),
            PluckPreset("harp_pluck_E3", "harp", NOTE_E3,
                        decay_s=1.1, brightness=0.8, body=0.5),
            PluckPreset("harp_pluck_G3", "harp", NOTE_G3,
                        decay_s=0.95, brightness=0.88, body=0.35),
        ],
    )


def marimba_pluck_bank() -> PluckBank:
    """Marimba pluck presets — 4 variants."""
    return PluckBank(
        name="MARIMBA_PLUCKS",
        presets=[
            PluckPreset("marimba_pluck_A3", "marimba", NOTE_A3,
                        decay_s=0.3, brightness=0.4, body=0.7),
            PluckPreset("marimba_pluck_C4", "marimba", NOTE_C4,
                        decay_s=0.25, brightness=0.45, body=0.6),
            PluckPreset("marimba_pluck_E3", "marimba", NOTE_E3,
                        decay_s=0.35, brightness=0.35, body=0.8),
            PluckPreset("marimba_pluck_G3", "marimba", NOTE_G3,
                        decay_s=0.28, brightness=0.5, body=0.65),
        ],
    )


ALL_PLUCK_BANKS: dict[str, callable] = {
    "string":  string_pluck_bank,
    "bell":    bell_pluck_bank,
    "key":     key_pluck_bank,
    "harp":    harp_pluck_bank,
    "marimba": marimba_pluck_bank,
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


def write_pluck_manifest(output_dir: str = "output") -> dict:
    """Synthesize all pluck presets and write manifest JSON."""
    out = Path(output_dir)
    wav_dir = out / "wavetables"
    manifest: dict = {"module": "pluck_synth", "banks": {}}

    for bank_key, bank_fn in ALL_PLUCK_BANKS.items():
        bank = bank_fn()
        entries = []
        for preset in bank.presets:
            audio = synthesize_pluck(preset)
            fname = f"pluck_synth_{preset.name}.wav"
            _write_wav(wav_dir / fname, audio)
            entries.append({
                "name": preset.name,
                "pluck_type": preset.pluck_type,
                "frequency": preset.frequency,
                "duration_s": preset.duration_s,
                "file": fname,
            })
            _log.info("  ✓ %s", preset.name)
        manifest["banks"][bank_key] = entries

    manifest_path = out / "analysis" / "pluck_synth_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    _log.info("Pluck synth manifest → %s", manifest_path)
    return manifest


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Generate all pluck synth one-shots."""
    _log.info("═══ DUBFORGE Pluck Synth Generator ═══")
    manifest = write_pluck_manifest()
    total = sum(len(v) for v in manifest["banks"].values())
    _log.info("Generated %d pluck presets across %d banks",
              total, len(manifest["banks"]))


if __name__ == "__main__":
    main()
