"""
DUBFORGE Engine — Percussion One-Shot Synthesizer

Synthesizes individual percussion hits from scratch:
  - Kick:  sub sine + transient click + distortion
  - Snare: noise burst + tonal body + snap
  - Clap:  layered noise bursts with micro-delays
  - Hat:   high-passed filtered noise with decay
  - Rim:   short pitched click

All sounds use phi-ratio envelopes and tuning.
Output as 16-bit mono WAV files at 44100 Hz.

Based on Subtronics production analysis:
  - Synthesized kicks for sub weight
  - Layered snares for punch
  - Tight hats for groove
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

_log = get_logger("dubforge.perc_synth")


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PercPreset:
    """Settings for a single percussion hit."""
    name: str
    perc_type: str          # kick | snare | clap | hat | rim | cowbell | tambourine
    duration_s: float = 0.3
    pitch: float = 60.0     # Hz (fundamental for tonal percs)
    decay_s: float = 0.15
    tone_mix: float = 0.5   # 0=noise only, 1=tone only
    brightness: float = 0.7
    distortion: float = 0.0
    attack_s: float = 0.001


@dataclass
class PercBank:
    """Collection of percussion presets."""
    name: str
    presets: list[PercPreset] = field(default_factory=list)


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
    _log.info("Wrote perc WAV: %s (%d samples)", out.name, len(signal))
    return str(out)


def _normalize(signal: np.ndarray) -> np.ndarray:
    """Normalize to 0.95 peak."""
    peak = np.max(np.abs(signal))
    return signal / peak * 0.95 if peak > 0 else signal


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIZERS
# ═══════════════════════════════════════════════════════════════════════════

def synthesize_kick(preset: PercPreset,
                    sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Kick drum — sub sine with pitch sweep + click transient."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate

    # Pitch envelope: starts high, drops to fundamental
    pitch_env = preset.pitch * (1 + 8 * np.exp(-t * 40))
    phase = np.cumsum(2 * math.pi * pitch_env / sample_rate)
    body = np.sin(phase)

    # Click transient
    click_len = min(n, int(0.003 * sample_rate))
    click = np.zeros(n)
    click[:click_len] = np.random.default_rng(42).uniform(-1, 1, click_len)
    click[:click_len] *= np.linspace(1, 0, click_len) ** 2
    click *= preset.brightness

    # Amplitude envelope
    decay_samples = max(1, int(preset.decay_s * sample_rate))
    env = np.exp(-np.arange(n) / max(1, decay_samples) * 4)
    env[:max(1, int(preset.attack_s * sample_rate))] = np.linspace(
        0, 1, max(1, int(preset.attack_s * sample_rate)))

    signal = (body * preset.tone_mix + click * (1 - preset.tone_mix)) * env

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 5))

    return _normalize(signal)


def synthesize_snare(preset: PercPreset,
                     sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Snare drum — tonal body + noise burst + snap."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate

    # Tonal body (two sine harmonics)
    body = np.sin(2 * math.pi * preset.pitch * t)
    body += 0.5 * np.sin(2 * math.pi * preset.pitch * 1.5 * t)

    # Noise burst (filtered)
    rng = np.random.default_rng(99)
    noise = rng.uniform(-1, 1, n)
    # Simple highpass: difference filter
    noise_hp = np.diff(noise, prepend=0) * preset.brightness * 3

    # Snap transient
    snap_len = min(n, int(0.005 * sample_rate))
    snap = np.zeros(n)
    snap[:snap_len] = np.linspace(1, 0, snap_len) ** PHI

    # Envelope
    body_env = np.exp(-t / max(0.001, preset.decay_s) * 3)
    noise_env = np.exp(-t / max(0.001, preset.decay_s * 0.7) * 4)

    signal = (body * body_env * preset.tone_mix
              + noise_hp * noise_env * (1 - preset.tone_mix)
              + snap * 0.5)

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 4))

    return _normalize(signal)


def synthesize_clap(preset: PercPreset,
                    sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Hand clap — layered noise bursts with micro-delays."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.default_rng(77)

    signal = np.zeros(n)
    # 4 layered micro-bursts with random delays
    burst_len = min(n, int(0.008 * sample_rate))
    for i in range(4):
        offset = min(n - burst_len, int(i * 0.003 * sample_rate))
        burst = rng.uniform(-1, 1, burst_len)
        burst *= np.linspace(1, 0, burst_len) ** 2
        end = min(n, offset + burst_len)
        signal[offset:end] += burst[:end - offset]

    # Noise tail
    tail = rng.uniform(-1, 1, n)
    tail_env = np.exp(-np.arange(n) / max(1, int(preset.decay_s * sample_rate)) * 3)
    tail *= tail_env * 0.3 * preset.brightness

    signal += tail

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))

    return _normalize(signal)


def synthesize_hat(preset: PercPreset,
                   sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Hi-hat — high-passed noise with sharp decay."""
    n = int(preset.duration_s * sample_rate)
    rng = np.random.default_rng(55)

    noise = rng.uniform(-1, 1, n)

    # Simple highpass via second-order difference
    hp = np.diff(np.diff(noise, prepend=0), prepend=0)
    hp *= preset.brightness * 2

    # Add metallic ring (6 inharmonic partials)
    t = np.arange(n) / sample_rate
    ring = np.zeros(n)
    freqs = [preset.pitch * r for r in [1.0, 1.47, 1.83, 2.17, 2.57, 3.13]]
    for f in freqs:
        ring += 0.15 * np.sin(2 * math.pi * f * t)

    env = np.exp(-np.arange(n) / max(1, int(preset.decay_s * sample_rate)) * 6)
    attack = max(1, int(preset.attack_s * sample_rate))
    env[:attack] = np.linspace(0, 1, attack)

    signal = (hp * 0.6 + ring * preset.tone_mix * 0.4) * env

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))

    return _normalize(signal)


def synthesize_rim(preset: PercPreset,
                   sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Rim shot — short pitched click with high harmonics."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate

    # High-pitched tone cluster
    signal = np.sin(2 * math.pi * preset.pitch * 3 * t)
    signal += 0.6 * np.sin(2 * math.pi * preset.pitch * 5.3 * t)
    signal += 0.3 * np.sin(2 * math.pi * preset.pitch * 7.1 * t)

    # Very fast decay
    env = np.exp(-np.arange(n) / max(1, int(preset.decay_s * sample_rate * 0.5)) * 8)
    attack = max(1, int(preset.attack_s * sample_rate))
    env[:attack] = np.linspace(0, 1, attack)

    signal *= env * preset.brightness

    if preset.distortion > 0:
        signal = np.tanh(signal * (1 + preset.distortion * 3))

    return _normalize(signal)


def synthesize_cowbell(preset: PercPreset,
                       sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Cowbell — dual-tone metallic hit with fast decay."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate

    # Two inharmonic tones (classic 808 cowbell frequencies)
    freq1 = preset.pitch
    freq2 = preset.pitch * 1.504  # Slightly inharmonic
    tone1 = np.sin(2 * math.pi * freq1 * t)
    tone2 = np.sin(2 * math.pi * freq2 * t)

    # Fast exponential decay
    decay = np.exp(-t / max(0.001, preset.decay_s))

    # Mix tones
    signal = (tone1 * 0.6 + tone2 * 0.4) * decay
    signal *= preset.tone_mix + (1 - preset.tone_mix) * 0.3

    # Brightness: high-pass emphasis
    if preset.brightness > 0.5:
        signal += np.diff(np.concatenate([[0], signal])) * preset.brightness * 0.3

    # Optional distortion
    if preset.distortion > 0:
        gain = 1.0 + preset.distortion * 4.0
        signal = np.tanh(signal * gain) / np.tanh(gain)

    signal /= np.max(np.abs(signal)) + 1e-10
    return signal


def synthesize_tambourine(preset: PercPreset,
                          sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Tambourine — jingle noise burst with resonant ring."""
    n = int(preset.duration_s * sample_rate)
    t = np.arange(n) / sample_rate
    rng = np.random.default_rng(42)

    # Noise burst (jingles)
    noise = rng.standard_normal(n)
    # Band-pass: high-pass then smooth
    hp = np.diff(np.concatenate([[0], noise]))
    k = max(1, int(sample_rate / (preset.pitch * 8)))
    kernel = np.ones(k) / k
    bp = np.convolve(hp, kernel, mode="same")

    # Tonal ring component
    ring = np.sin(2 * math.pi * preset.pitch * 2 * t) * 0.3

    # Envelope: sharp attack + decay
    attack_n = max(1, int(preset.attack_s * sample_rate))
    env = np.exp(-t / max(0.001, preset.decay_s))
    env[:attack_n] *= np.linspace(0, 1, attack_n)

    signal = (bp * (1 - preset.tone_mix) + ring * preset.tone_mix) * env

    if preset.distortion > 0:
        gain = 1.0 + preset.distortion * 3.0
        signal = np.tanh(signal * gain) / np.tanh(gain)

    signal /= np.max(np.abs(signal)) + 1e-10
    return signal


def synthesize_perc(preset: PercPreset,
                    sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct percussion synthesizer."""
    synthesizers = {
        "kick": synthesize_kick,
        "snare": synthesize_snare,
        "clap": synthesize_clap,
        "hat": synthesize_hat,
        "rim": synthesize_rim,
        "cowbell": synthesize_cowbell,
        "tambourine": synthesize_tambourine,
    }
    fn = synthesizers.get(preset.perc_type)
    if fn is None:
        raise ValueError(f"Unknown perc_type: {preset.perc_type!r}")
    return fn(preset, sample_rate)


# ═══════════════════════════════════════════════════════════════════════════
# PRESETS — 20 Subtronics-calibrated percussion one-shots
# ═══════════════════════════════════════════════════════════════════════════

def kick_bank() -> PercBank:
    """Kick drum variants — sub-heavy to punchy."""
    return PercBank(
        name="KICKS",
        presets=[
            PercPreset("kick_sub", "kick", 0.4, pitch=45, decay_s=0.25,
                       tone_mix=0.85, brightness=0.3, distortion=0.0),
            PercPreset("kick_punch", "kick", 0.25, pitch=55, decay_s=0.15,
                       tone_mix=0.7, brightness=0.6, distortion=0.2),
            PercPreset("kick_attack", "kick", 0.2, pitch=60, decay_s=0.1,
                       tone_mix=0.6, brightness=0.8, distortion=0.3),
            PercPreset("kick_808", "kick", 0.6, pitch=40, decay_s=0.4,
                       tone_mix=0.9, brightness=0.2, distortion=0.1),
        ],
    )


def snare_bank() -> PercBank:
    """Snare drum variants — tight to wide."""
    return PercBank(
        name="SNARES",
        presets=[
            PercPreset("snare_tight", "snare", 0.2, pitch=200, decay_s=0.08,
                       tone_mix=0.4, brightness=0.7, distortion=0.1),
            PercPreset("snare_fat", "snare", 0.35, pitch=180, decay_s=0.15,
                       tone_mix=0.5, brightness=0.6, distortion=0.2),
            PercPreset("snare_crack", "snare", 0.15, pitch=250, decay_s=0.06,
                       tone_mix=0.3, brightness=0.9, distortion=0.3),
            PercPreset("snare_long", "snare", 0.5, pitch=160, decay_s=0.25,
                       tone_mix=0.45, brightness=0.5, distortion=0.05),
        ],
    )


def clap_bank() -> PercBank:
    """Hand clap variants — tight to lush."""
    return PercBank(
        name="CLAPS",
        presets=[
            PercPreset("clap_tight", "clap", 0.15, decay_s=0.06,
                       brightness=0.7, distortion=0.0),
            PercPreset("clap_room", "clap", 0.4, decay_s=0.2,
                       brightness=0.5, distortion=0.0),
            PercPreset("clap_stack", "clap", 0.25, decay_s=0.1,
                       brightness=0.8, distortion=0.2),
            PercPreset("clap_distorted", "clap", 0.2, decay_s=0.08,
                       brightness=0.9, distortion=0.5),
        ],
    )


def hat_bank() -> PercBank:
    """Hi-hat variants — closed to open."""
    return PercBank(
        name="HATS",
        presets=[
            PercPreset("hat_closed", "hat", 0.05, pitch=8000,
                       decay_s=0.02, tone_mix=0.3, brightness=0.8),
            PercPreset("hat_medium", "hat", 0.12, pitch=7000,
                       decay_s=0.06, tone_mix=0.4, brightness=0.7),
            PercPreset("hat_open", "hat", 0.35, pitch=6000,
                       decay_s=0.2, tone_mix=0.5, brightness=0.6),
            PercPreset("hat_sizzle", "hat", 0.5, pitch=9000,
                       decay_s=0.3, tone_mix=0.2, brightness=0.9),
        ],
    )


def rim_bank() -> PercBank:
    """Rim shot variants — bright to dark."""
    return PercBank(
        name="RIMS",
        presets=[
            PercPreset("rim_bright", "rim", 0.08, pitch=500,
                       decay_s=0.03, brightness=1.0),
            PercPreset("rim_wood", "rim", 0.1, pitch=400,
                       decay_s=0.04, brightness=0.6),
            PercPreset("rim_metallic", "rim", 0.12, pitch=700,
                       decay_s=0.05, brightness=0.8, distortion=0.1),
            PercPreset("rim_muted", "rim", 0.06, pitch=350,
                       decay_s=0.02, brightness=0.4),
        ],
    )


def cowbell_bank() -> PercBank:
    """Cowbell hits — metallic dual-tone percussion."""
    return PercBank(
        name="COWBELLS",
        presets=[
            PercPreset("cowbell_808", "cowbell", duration_s=0.2,
                       pitch=540.0, decay_s=0.1, tone_mix=0.8, brightness=0.6),
            PercPreset("cowbell_lo", "cowbell", duration_s=0.25,
                       pitch=420.0, decay_s=0.12, tone_mix=0.7, brightness=0.5),
            PercPreset("cowbell_bright", "cowbell", duration_s=0.15,
                       pitch=600.0, decay_s=0.08, tone_mix=0.9, brightness=0.9),
            PercPreset("cowbell_muted", "cowbell", duration_s=0.12,
                       pitch=480.0, decay_s=0.06, tone_mix=0.6, brightness=0.4,
                       distortion=0.1),
        ],
    )


def tambourine_bank() -> PercBank:
    """Tambourine hits — jingly noise bursts."""
    return PercBank(
        name="TAMBOURINES",
        presets=[
            PercPreset("tambourine_bright", "tambourine", duration_s=0.3,
                       pitch=800.0, decay_s=0.15, tone_mix=0.3, brightness=0.8),
            PercPreset("tambourine_dark", "tambourine", duration_s=0.25,
                       pitch=600.0, decay_s=0.12, tone_mix=0.4, brightness=0.4),
            PercPreset("tambourine_short", "tambourine", duration_s=0.15,
                       pitch=900.0, decay_s=0.06, tone_mix=0.2, brightness=0.7),
            PercPreset("tambourine_long", "tambourine", duration_s=0.5,
                       pitch=700.0, decay_s=0.25, tone_mix=0.35, brightness=0.6),
        ],
    )


ALL_PERC_BANKS: dict[str, callable] = {
    "kicks":  kick_bank,
    "snares": snare_bank,
    "claps":  clap_bank,
    "hats":   hat_bank,
    "rims":   rim_bank,
    # v2.1
    "cowbells":     cowbell_bank,
    "tambourines":  tambourine_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

def write_perc_manifest(banks: dict[str, PercBank], out_dir: str) -> str:
    """Write JSON manifest of generated percussion sounds."""
    manifest = {
        "generator": "DUBFORGE Percussion Synthesizer",
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
                    "type": p.perc_type,
                    "duration_s": round(p.duration_s, 3),
                }
                for p in bank.presets
            ],
        }

    out = Path(out_dir) / "perc_synth_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2))
    _log.info("Wrote perc manifest → %s", out)
    return str(out)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Generate all percussion one-shot WAV files."""
    wav_dir = "output/wavetables"
    analysis_dir = "output/analysis"

    banks: dict[str, PercBank] = {}
    total = 0

    for bank_name, gen_fn in ALL_PERC_BANKS.items():
        bank = gen_fn()
        banks[bank_name] = bank
        for preset in bank.presets:
            signal = synthesize_perc(preset)
            path = f"{wav_dir}/perc_{preset.name}.wav"
            _write_wav(signal, path)
            total += 1

    write_perc_manifest(banks, analysis_dir)
    _log.info("Percussion synthesis complete — %d WAVs across %d banks",
              total, len(banks))


if __name__ == "__main__":
    main()
