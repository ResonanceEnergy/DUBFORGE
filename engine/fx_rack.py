"""DUBFORGE — FX Rack.

Audio effects chain processor with named presets.
Used throughout the pipeline for per-stem and bus processing.
"""
from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

# Lazy-import SAMPLE_RATE
_SAMPLE_RATE = None

def _get_sr():
    global _SAMPLE_RATE
    if _SAMPLE_RATE is None:
        try:
            from engine.dsp_core import SAMPLE_RATE as _sr
            _SAMPLE_RATE = _sr
        except ImportError:
            _SAMPLE_RATE = 48000
    return _SAMPLE_RATE


# ═══════════════════════════════════════════════════════════════════
# Effect processors
# ═══════════════════════════════════════════════════════════════════

def _apply_eq(audio: np.ndarray, bands: list[dict], sr: int) -> np.ndarray:
    """Simple parametric EQ using biquad filters."""
    try:
        from scipy.signal import sosfilt, iirpeak, iirnotch
    except ImportError:
        return audio

    out = audio.copy()
    for band in bands:
        freq = band.get("freq", 1000)
        gain_db = band.get("gain", 0.0)
        q = band.get("q", 1.0)
        if abs(gain_db) < 0.1:
            continue
        w0 = freq / (sr / 2)
        if w0 >= 1.0 or w0 <= 0.0:
            continue
        try:
            if gain_db > 0:
                b, a = iirpeak(w0, q)
            else:
                b, a = iirnotch(w0, q)
            from scipy.signal import lfilter
            out = lfilter(b, a, out)
            if gain_db > 0:
                out *= 10 ** (gain_db / 40)  # half the gain since peak adds
            else:
                out *= 10 ** (gain_db / 40)
        except Exception:
            pass
    return out


def _apply_compression(audio: np.ndarray, threshold_db: float = -12.0,
                       ratio: float = 3.0, attack_ms: float = 15.0,
                       release_ms: float = 200.0, sr: int = 48000
                       ) -> np.ndarray:
    """Simple feed-forward compressor."""
    out = audio.copy()
    threshold = 10 ** (threshold_db / 20)
    attack_coeff = math.exp(-1.0 / (attack_ms / 1000.0 * sr))
    release_coeff = math.exp(-1.0 / (release_ms / 1000.0 * sr))

    env = 0.0
    for i in range(len(out)):
        level = abs(out[i])
        if level > env:
            env = level + attack_coeff * (env - level)
        else:
            env = level + release_coeff * (env - level)

        if env > threshold and env > 0:
            gain_reduction = threshold * (env / threshold) ** (1.0 / ratio - 1.0) / env
            out[i] *= gain_reduction
    return out


def _apply_reverb(audio: np.ndarray, decay: float = 0.3,
                  mix: float = 0.15, sr: int = 48000) -> np.ndarray:
    """Simple comb-filter reverb."""
    delays_ms = [29.7, 37.1, 41.1, 43.7]  # prime-ish delays
    wet = np.zeros_like(audio)
    for delay_ms in delays_ms:
        d_samps = int(delay_ms / 1000.0 * sr)
        feedback = decay * 0.7
        buf = np.zeros(len(audio) + d_samps, dtype=np.float64)
        for i in range(len(audio)):
            buf[i] += audio[i]
            if i >= d_samps:
                buf[i] += buf[i - d_samps] * feedback
        wet += buf[:len(audio)] * 0.25

    return audio * (1.0 - mix) + wet * mix


def _apply_saturation(audio: np.ndarray, drive: float = 1.5) -> np.ndarray:
    """Warm tape-style saturation."""
    return np.tanh(audio * drive) / np.tanh(drive) if drive > 0 else audio


def _apply_delay(audio: np.ndarray, time_ms: float = 250.0,
                 feedback: float = 0.3, mix: float = 0.2,
                 sr: int = 48000) -> np.ndarray:
    """Simple feedback delay."""
    d_samps = int(time_ms / 1000.0 * sr)
    buf = np.zeros(len(audio) + d_samps * 5, dtype=np.float64)
    buf[:len(audio)] = audio.copy()
    for tap in range(1, 5):
        start = tap * d_samps
        gain = feedback ** tap
        if start < len(buf):
            end = min(start + len(audio), len(buf))
            buf[start:end] += audio[:end - start] * gain

    wet = buf[:len(audio)]
    return audio * (1.0 - mix) + wet * mix


def _apply_chorus(audio: np.ndarray, rate: float = 1.5,
                  depth_ms: float = 3.0, mix: float = 0.3,
                  sr: int = 48000) -> np.ndarray:
    """Simple chorus effect."""
    n = len(audio)
    t = np.arange(n) / sr
    lfo = np.sin(2 * np.pi * rate * t) * (depth_ms / 1000.0 * sr)
    base_delay = int(10.0 / 1000.0 * sr)

    wet = np.zeros(n, dtype=np.float64)
    for i in range(n):
        idx = i - base_delay - int(lfo[i])
        if 0 <= idx < n:
            wet[i] = audio[idx]

    return audio * (1.0 - mix) + wet * mix


# ═══════════════════════════════════════════════════════════════════
# Preset definitions
# ═══════════════════════════════════════════════════════════════════

_PRESETS: dict[str, list[dict[str, Any]]] = {
    "mix_vocals": [
        {"type": "eq", "bands": [
            {"freq": 200, "gain": -3, "q": 1.0},  # HP shelf proxy
            {"freq": 3000, "gain": 2, "q": 0.8},   # presence
            {"freq": 8000, "gain": 1.5, "q": 0.7},  # air
        ]},
        {"type": "compression", "threshold_db": -18, "ratio": 3.0,
         "attack_ms": 10, "release_ms": 150},
        {"type": "reverb", "decay": 0.25, "mix": 0.12},
        {"type": "delay", "time_ms": 200, "feedback": 0.15, "mix": 0.08},
    ],
    "mix_drums": [
        {"type": "compression", "threshold_db": -15, "ratio": 4.0,
         "attack_ms": 5, "release_ms": 100},
        {"type": "saturation", "drive": 1.2},
    ],
    "mix_bass": [
        {"type": "eq", "bands": [
            {"freq": 60, "gain": 2, "q": 1.5},
            {"freq": 300, "gain": -2, "q": 1.0},
        ]},
        {"type": "compression", "threshold_db": -12, "ratio": 4.0,
         "attack_ms": 8, "release_ms": 120},
        {"type": "saturation", "drive": 1.3},
    ],
    "mix_lead": [
        {"type": "eq", "bands": [
            {"freq": 800, "gain": 2, "q": 0.8},
            {"freq": 5000, "gain": 3, "q": 0.6},
        ]},
        {"type": "saturation", "drive": 1.8},
        {"type": "reverb", "decay": 0.2, "mix": 0.10},
    ],
    "mix_atmos": [
        {"type": "reverb", "decay": 0.5, "mix": 0.30},
        {"type": "chorus", "rate": 0.8, "depth_ms": 5.0, "mix": 0.25},
    ],
    "master_glue": [
        {"type": "compression", "threshold_db": -10, "ratio": 2.5,
         "attack_ms": 20, "release_ms": 250},
        {"type": "saturation", "drive": 1.1},
    ],
}


# ═══════════════════════════════════════════════════════════════════
# FXRack class
# ═══════════════════════════════════════════════════════════════════

class FXRack:
    """Audio effects rack with named presets."""

    @classmethod
    def preset(cls, name: str) -> list[dict[str, Any]]:
        """Get a preset chain by name."""
        if name not in _PRESETS:
            log.warning(f"FXRack: unknown preset '{name}', returning empty chain")
            return []
        return _PRESETS[name]

    @classmethod
    def process(cls, audio: np.ndarray, chain: list[dict[str, Any]],
                sr: int | None = None) -> np.ndarray:
        """Process audio through an effects chain.

        Args:
            audio: float64 mono audio array
            chain: list of effect dicts from preset()
            sr: sample rate (defaults to engine SAMPLE_RATE)
        """
        if sr is None:
            sr = _get_sr()

        audio = np.asarray(audio, dtype=np.float64)
        if len(audio) == 0:
            return audio

        for fx in chain:
            fx_type = fx.get("type", "")

            if fx_type == "eq":
                audio = _apply_eq(audio, fx.get("bands", []), sr)

            elif fx_type == "compression":
                audio = _apply_compression(
                    audio,
                    threshold_db=fx.get("threshold_db", -12),
                    ratio=fx.get("ratio", 3.0),
                    attack_ms=fx.get("attack_ms", 15),
                    release_ms=fx.get("release_ms", 200),
                    sr=sr,
                )

            elif fx_type == "reverb":
                audio = _apply_reverb(
                    audio,
                    decay=fx.get("decay", 0.3),
                    mix=fx.get("mix", 0.15),
                    sr=sr,
                )

            elif fx_type == "saturation":
                audio = _apply_saturation(audio, drive=fx.get("drive", 1.5))

            elif fx_type == "delay":
                audio = _apply_delay(
                    audio,
                    time_ms=fx.get("time_ms", 250),
                    feedback=fx.get("feedback", 0.3),
                    mix=fx.get("mix", 0.2),
                    sr=sr,
                )

            elif fx_type == "chorus":
                audio = _apply_chorus(
                    audio,
                    rate=fx.get("rate", 1.5),
                    depth_ms=fx.get("depth_ms", 3.0),
                    mix=fx.get("mix", 0.3),
                    sr=sr,
                )

            else:
                log.warning(f"FXRack: unknown effect type '{fx_type}'")

        return audio
