"""
DUBFORGE — Reverb & Delay Engine

Phi-spaced early reflections, Fibonacci delay taps, and lush reverb tails.
5 types × 4 presets = 20 presets.

Types:
  room     — small early-reflection reverb
  hall     — long diffuse tail with phi decay
  plate    — dense metallic reverb
  shimmer  — pitch-shifted feedback reverb
  delay    — Fibonacci-spaced multi-tap delay
"""

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
class ReverbDelayPreset:
    """Preset for reverb and delay processing."""
    name: str
    effect_type: str  # room | hall | plate | shimmer | delay
    # Reverb common
    decay_time: float = 1.5        # seconds
    pre_delay_ms: float = 20.0     # milliseconds
    diffusion: float = 0.7         # 0..1
    damping: float = 0.5           # high-freq damping 0..1
    # Room
    room_size: float = 0.4         # 0=tiny .. 1=large
    # Shimmer
    shimmer_pitch: float = 12.0    # semitones up per feedback cycle
    shimmer_feedback: float = 0.6
    # Delay
    bpm: float = 150.0
    delay_feedback: float = 0.5
    num_taps: int = 5
    ping_pong: bool = False
    # Common
    mix: float = 0.35
    stereo_width: float = 0.8


@dataclass
class ReverbDelayBank:
    """Bank of reverb/delay presets."""
    name: str
    presets: list[ReverbDelayPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# DSP HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _allpass(signal: np.ndarray, delay_samples: int,
             gain: float = 0.5) -> np.ndarray:
    """Schroeder allpass filter for diffusion."""
    n = len(signal)
    buf = np.zeros(n + delay_samples)
    buf[:n] = signal
    out = np.zeros(n)
    for i in range(n):
        d = i - delay_samples
        buf_d = buf[d] if d >= 0 else 0.0
        out[i] = -gain * buf[i] + buf_d + gain * (
            out[i - delay_samples] if i >= delay_samples else 0.0
        )
    return out


def _comb(signal: np.ndarray, delay_samples: int,
          feedback: float = 0.5, damping: float = 0.5) -> np.ndarray:
    """Feedback comb filter with damping for reverb tail."""
    n = len(signal)
    out = np.zeros(n)
    damp_state = 0.0
    for i in range(n):
        d = i - delay_samples
        delayed = out[d] if d >= 0 else 0.0
        # One-pole damping
        damp_state = delayed * (1.0 - damping) + damp_state * damping
        out[i] = signal[i] + damp_state * feedback
    return out


def _phi_early_reflections(signal: np.ndarray, room_size: float,
                           sample_rate: int) -> np.ndarray:
    """Generate early reflections at phi-ratio spaced delay times."""
    base_ms = 5.0 + room_size * 40.0  # 5ms to 45ms
    out = np.zeros_like(signal)
    n = len(signal)
    amplitude = 0.8
    for i in range(7):
        delay_ms = base_ms * (PHI ** i)
        delay_samp = int(delay_ms * sample_rate / 1000.0)
        if delay_samp >= n:
            break
        reflected = np.zeros(n)
        reflected[delay_samp:] = signal[:n - delay_samp] * amplitude
        out += reflected
        amplitude /= PHI

    peak = np.max(np.abs(out))
    if peak > 1e-8:
        out = out / peak * np.max(np.abs(signal)) * 0.6
    return out


# ═══════════════════════════════════════════════════════════════════════════
# PROCESSORS
# ═══════════════════════════════════════════════════════════════════════════

def apply_room(signal: np.ndarray, preset: ReverbDelayPreset,
               sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Small room reverb with phi-spaced early reflections."""
    n = len(signal)
    if n == 0:
        return signal.copy()

    # Pre-delay
    pd_samp = int(preset.pre_delay_ms * sample_rate / 1000.0)
    padded = np.zeros(n)
    if pd_samp < n:
        padded[pd_samp:] = signal[:n - pd_samp]
    else:
        padded = signal.copy()

    # Early reflections
    er = _phi_early_reflections(padded, preset.room_size, sample_rate)

    # Short comb for tail
    tail_ms = preset.decay_time * 200  # room = shorter
    delay_samp = max(1, int(tail_ms * sample_rate / 1000.0))
    fb = min(0.9, preset.decay_time * 0.3)
    tail = _comb(padded, delay_samp, fb, preset.damping)

    wet = er * 0.6 + tail * 0.4
    peak = np.max(np.abs(wet))
    if peak > 1e-8:
        wet = wet / peak * np.max(np.abs(signal))
    return wet


def apply_hall(signal: np.ndarray, preset: ReverbDelayPreset,
               sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Large hall reverb with long diffuse tail."""
    n = len(signal)
    if n == 0:
        return signal.copy()

    # Pre-delay
    pd_samp = int(preset.pre_delay_ms * sample_rate / 1000.0)
    padded = np.zeros(n)
    if pd_samp < n:
        padded[pd_samp:] = signal[:n - pd_samp]
    else:
        padded = signal.copy()

    # Parallel combs at phi-ratio spacings
    base_delay = int(30.0 * sample_rate / 1000.0)
    fb = min(0.95, 1.0 - 1.0 / (preset.decay_time * 5.0 + 1.0))
    combs_out = np.zeros(n)
    for i in range(4):
        d = int(base_delay * (PHI ** (i * 0.5)))
        d = min(d, n - 1)
        combs_out += _comb(padded, d, fb, preset.damping)
    combs_out /= 4.0

    # Series allpass for diffusion
    out = combs_out
    for i in range(2):
        ap_delay = int((5.0 + i * 3.0) * sample_rate / 1000.0)
        ap_delay = min(ap_delay, n - 1)
        out = _allpass(out, ap_delay, preset.diffusion * 0.7)

    peak = np.max(np.abs(out))
    if peak > 1e-8:
        out = out / peak * np.max(np.abs(signal))
    return out


def apply_plate(signal: np.ndarray, preset: ReverbDelayPreset,
                sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Dense plate reverb — high diffusion, metallic character."""
    n = len(signal)
    if n == 0:
        return signal.copy()

    # Dense allpass chain for plate character
    out = signal.copy()
    delays_ms = [3.1, 5.0, 8.1, 13.1, 21.2]  # Fibonacci-ish
    for dm in delays_ms:
        d = max(1, int(dm * sample_rate / 1000.0))
        d = min(d, n - 1)
        out = _allpass(out, d, preset.diffusion)

    # Feedback comb for decay
    base_d = max(1, int(20.0 * sample_rate / 1000.0))
    base_d = min(base_d, n - 1)
    fb = min(0.92, 1.0 - 1.0 / (preset.decay_time * 4.0 + 1.0))
    out = _comb(out, base_d, fb, preset.damping * 0.7)

    peak = np.max(np.abs(out))
    if peak > 1e-8:
        out = out / peak * np.max(np.abs(signal))
    return out


def apply_shimmer(signal: np.ndarray, preset: ReverbDelayPreset,
                  sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Shimmer reverb — pitch-shifted feedback for ethereal washes."""
    n = len(signal)
    if n == 0:
        return signal.copy()

    pitch_ratio = 2.0 ** (preset.shimmer_pitch / 12.0)
    delay_samp = max(1, int(preset.decay_time * sample_rate * 0.25))
    delay_samp = min(delay_samp, n - 1)

    out = np.zeros(n)
    fb_buf = np.zeros(n)

    for i in range(n):
        d = i - delay_samp
        fb_val = fb_buf[d] if d >= 0 else 0.0
        out[i] = signal[i] + fb_val * preset.shimmer_feedback

        # Pitch-shift the feedback via resampling
        src_idx = i / pitch_ratio
        idx_int = int(src_idx)
        idx_frac = src_idx - idx_int
        if 0 <= idx_int < n - 1:
            fb_buf[i] = out[idx_int] * (1.0 - idx_frac) + out[idx_int + 1] * idx_frac
        elif 0 <= idx_int < n:
            fb_buf[i] = out[idx_int]

    # Diffusion pass
    ap_d = max(1, int(7.0 * sample_rate / 1000.0))
    ap_d = min(ap_d, n - 1)
    out = _allpass(out, ap_d, preset.diffusion * 0.6)

    peak = np.max(np.abs(out))
    if peak > 1e-8:
        out = out / peak * np.max(np.abs(signal))
    return out


def apply_delay(signal: np.ndarray, preset: ReverbDelayPreset,
                sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Multi-tap delay with Fibonacci-spaced taps."""
    n = len(signal)
    if n == 0:
        return signal.copy()

    beat_samples = int(60.0 / preset.bpm * sample_rate)

    # Fibonacci tap times (in beats)
    fib = [1, 1]
    while len(fib) < preset.num_taps:
        fib.append(fib[-1] + fib[-2])
    tap_times = fib[:preset.num_taps]

    out = signal.copy()
    for i, tap_beats in enumerate(tap_times):
        delay_samp = int(tap_beats * beat_samples / 4.0)  # sub-beat taps
        amplitude = preset.delay_feedback ** (i + 1)
        if delay_samp < n:
            delayed = np.zeros(n)
            delayed[delay_samp:] = signal[:n - delay_samp] * amplitude
            out += delayed

    peak = np.max(np.abs(out))
    orig_peak = np.max(np.abs(signal))
    if peak > 1e-8 and orig_peak > 1e-8:
        out = out / peak * orig_peak
    return out


# ═══════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════

def apply_reverb_delay(signal: np.ndarray, preset: ReverbDelayPreset,
                       sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Route to the correct reverb/delay processor based on preset type."""
    processors = {
        "room": apply_room,
        "hall": apply_hall,
        "plate": apply_plate,
        "shimmer": apply_shimmer,
        "delay": apply_delay,
    }
    proc = processors.get(preset.effect_type)
    if proc is None:
        raise ValueError(f"Unknown reverb/delay type: {preset.effect_type}")
    processed = proc(signal, preset, sample_rate)
    # Wet/dry mix
    if preset.mix < 1.0:
        mn = min(len(signal), len(processed))
        processed[:mn] = signal[:mn] * (1.0 - preset.mix) + processed[:mn] * preset.mix
    return processed


# ═══════════════════════════════════════════════════════════════════════════
# PRESET BANKS
# ═══════════════════════════════════════════════════════════════════════════

def room_bank() -> ReverbDelayBank:
    return ReverbDelayBank("room", [
        ReverbDelayPreset("room_tight", "room", decay_time=0.3,
                          room_size=0.2, pre_delay_ms=5.0, mix=0.2),
        ReverbDelayPreset("room_medium", "room", decay_time=0.8,
                          room_size=0.5, pre_delay_ms=15.0, mix=0.3),
        ReverbDelayPreset("room_large", "room", decay_time=1.5,
                          room_size=0.8, pre_delay_ms=25.0, mix=0.35),
        ReverbDelayPreset("room_phi_size", "room", decay_time=1.0 / PHI,
                          room_size=1.0 / PHI, pre_delay_ms=20.0 / PHI,
                          mix=0.3),
    ])


def hall_bank() -> ReverbDelayBank:
    return ReverbDelayBank("hall", [
        ReverbDelayPreset("hall_cathedral", "hall", decay_time=4.0,
                          diffusion=0.9, damping=0.3, mix=0.4),
        ReverbDelayPreset("hall_concert", "hall", decay_time=2.5,
                          diffusion=0.7, damping=0.5, mix=0.35),
        ReverbDelayPreset("hall_dark", "hall", decay_time=3.0,
                          diffusion=0.8, damping=0.8, mix=0.3),
        ReverbDelayPreset("hall_phi_decay", "hall", decay_time=PHI,
                          diffusion=1.0 / PHI, damping=1.0 / PHI, mix=0.35),
    ])


def plate_bank() -> ReverbDelayBank:
    return ReverbDelayBank("plate", [
        ReverbDelayPreset("plate_bright", "plate", decay_time=1.5,
                          diffusion=0.9, damping=0.2, mix=0.3),
        ReverbDelayPreset("plate_dark", "plate", decay_time=2.0,
                          diffusion=0.8, damping=0.7, mix=0.3),
        ReverbDelayPreset("plate_snare", "plate", decay_time=0.8,
                          diffusion=0.95, damping=0.4, mix=0.25),
        ReverbDelayPreset("plate_phi", "plate", decay_time=PHI,
                          diffusion=1.0 / PHI, damping=0.5, mix=0.3),
    ])


def shimmer_bank() -> ReverbDelayBank:
    return ReverbDelayBank("shimmer", [
        ReverbDelayPreset("shimmer_octave", "shimmer", shimmer_pitch=12.0,
                          shimmer_feedback=0.5, decay_time=2.0, mix=0.35),
        ReverbDelayPreset("shimmer_fifth", "shimmer", shimmer_pitch=7.0,
                          shimmer_feedback=0.6, decay_time=2.5, mix=0.3),
        ReverbDelayPreset("shimmer_minor3", "shimmer", shimmer_pitch=3.0,
                          shimmer_feedback=0.7, decay_time=3.0, mix=0.35),
        ReverbDelayPreset("shimmer_phi", "shimmer",
                          shimmer_pitch=12.0 / PHI,
                          shimmer_feedback=1.0 / PHI, decay_time=PHI,
                          mix=0.3),
    ])


def delay_bank() -> ReverbDelayBank:
    return ReverbDelayBank("delay", [
        ReverbDelayPreset("delay_fib_5", "delay", num_taps=5,
                          delay_feedback=0.5, bpm=150.0, mix=0.4),
        ReverbDelayPreset("delay_fib_8", "delay", num_taps=8,
                          delay_feedback=0.4, bpm=140.0, mix=0.35),
        ReverbDelayPreset("delay_dark", "delay", num_taps=5,
                          delay_feedback=0.6, bpm=150.0, mix=0.3),
        ReverbDelayPreset("delay_phi_fb", "delay", num_taps=5,
                          delay_feedback=1.0 / PHI, bpm=150.0, mix=0.35),
    ])


ALL_REVERB_DELAY_BANKS: dict[str, callable] = {
    "room": room_bank,
    "hall": hall_bank,
    "plate": plate_bank,
    "shimmer": shimmer_bank,
    "delay": delay_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# WAV EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def _write_wav(path: Path, samples: np.ndarray,
               sample_rate: int = SAMPLE_RATE) -> None:
    """Write 16-bit mono WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def _test_signal(duration_s: float = 1.0, freq: float = 200.0,
                 sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Generate a test sine for processing demos."""
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    return 0.8 * np.sin(2.0 * np.pi * freq * t)


def export_reverb_delay_demos(output_dir: str = "output") -> list[str]:
    """Render all reverb/delay presets applied to a test signal and write .wav."""
    sig = _test_signal()
    out = Path(output_dir) / "wavetables" / "reverb_delay"
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for bank_name, bank_fn in ALL_REVERB_DELAY_BANKS.items():
        bank = bank_fn()
        for preset in bank.presets:
            processed = apply_reverb_delay(sig, preset, SAMPLE_RATE)
            fname = f"rvb_{preset.name}.wav"
            _write_wav(out / fname, processed)
            paths.append(str(out / fname))
    return paths


# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST + MAIN
# ═══════════════════════════════════════════════════════════════════════════

def write_reverb_delay_manifest(output_dir: str = "output") -> dict:
    """Write JSON manifest of all reverb/delay presets."""
    import json
    from pathlib import Path

    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    manifest = {"banks": {}}
    for bank_name, gen_fn in ALL_REVERB_DELAY_BANKS.items():
        bank = gen_fn()
        manifest["banks"][bank_name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "reverb_delay_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_reverb_delay_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    wavs = export_reverb_delay_demos()
    print(f"Reverb & Delay: {len(manifest['banks'])} banks, {total} presets, {len(wavs)} .wav")


if __name__ == "__main__":
    main()
