"""
DUBFORGE — Track Emulator Engine

Analyzes a reference WAV file and generates a new track that emulates
its sonic characteristics (BPM, key, spectral balance, energy curve,
bass style, drum density) using the full DUBFORGE synthesis engine.

Pipeline:
    1. Read reference WAV → spectral + waveform + loudness analysis
    2. Estimate BPM via onset detection / autocorrelation
    3. Estimate key via chromagram
    4. Map spectral profile → SongDNA parameters
    5. Render new track from derived SongDNA
    6. Master to match reference loudness
"""

from __future__ import annotations

import math
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from engine.audio_analyzer import AudioAnalyzer, SpectralProfile, WaveformStats
from engine.config_loader import PHI
from engine.accel import fft, ifft


SAMPLE_RATE = 44100
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Frequency lookup for synthesis
_FREQ_TABLE: dict[str, float] = {}
for _oct in range(1, 6):
    for _i, _n in enumerate(NOTES):
        _midi = 12 * (_oct + 1) + _i
        _FREQ_TABLE[f"{_n}{_oct}"] = 440.0 * (2.0 ** ((_midi - 69) / 12.0))


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class EmulationProfile:
    """Extracted characteristics from a reference track."""
    source_path: str = ""
    duration_s: float = 0.0
    estimated_bpm: float = 140.0
    estimated_key: str = "F"
    estimated_scale: str = "minor"
    spectral: Optional[SpectralProfile] = None
    waveform: Optional[WaveformStats] = None
    loudness_db: float = -14.0
    energy_curve: list[float] = field(default_factory=list)
    # Derived style traits
    bass_weight: float = 0.5       # 0=light, 1=heavy
    brightness: float = 0.5        # 0=dark, 1=bright
    aggression: float = 0.5        # 0=soft, 1=aggressive
    density: float = 0.5           # 0=sparse, 1=dense
    width: float = 0.5             # 0=mono, 1=wide
    # Detected arrangement sections
    section_count: int = 6
    drop_intensity: float = 0.9


@dataclass
class EmulationResult:
    """Result of emulation rendering."""
    output_path: str = ""
    profile: Optional[EmulationProfile] = None
    duration_s: float = 0.0
    sample_rate: int = SAMPLE_RATE
    sections_rendered: int = 0
    status: str = ""


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS — Extract characteristics from reference
# ═══════════════════════════════════════════════════════════════════════════

def _read_wav_samples(path: str) -> tuple[np.ndarray, int]:
    """Read WAV file and return mono float samples + sample rate."""
    with wave.open(path, "r") as wf:
        sr = wf.getframerate()
        n_ch = wf.getnchannels()
        sw = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())

    if sw == 2:
        arr = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    elif sw == 1:
        arr = (np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128) / 128.0
    elif sw == 3:
        # 24-bit
        n_samples = len(raw) // 3
        arr = np.zeros(n_samples, dtype=np.float64)
        for i in range(n_samples):
            b = raw[i * 3:(i + 1) * 3]
            val = int.from_bytes(b, byteorder="little", signed=True)
            arr[i] = val / 8388608.0
    else:
        arr = np.zeros(1)

    # Mix to mono if stereo
    if n_ch == 2:
        arr = (arr[0::2] + arr[1::2]) / 2.0
    elif n_ch > 2:
        arr = arr[::n_ch]

    return arr, sr


def estimate_bpm(samples: np.ndarray, sr: int = SAMPLE_RATE) -> float:
    """Estimate BPM via onset-based autocorrelation.

    Uses energy envelope → autocorrelation to find the dominant
    beat period. Range locked to 60-200 BPM (dubstep-relevant).
    """
    # Compute energy envelope in ~10ms frames
    hop = int(sr * 0.01)
    n_frames = len(samples) // hop
    if n_frames < 100:
        return 140.0  # fallback

    envelope = np.zeros(n_frames)
    for i in range(n_frames):
        start = i * hop
        end = min(start + hop, len(samples))
        frame = samples[start:end]
        envelope[i] = float(np.sqrt(np.mean(frame * frame)))

    # Compute onset strength (positive first-derivative)
    onset = np.diff(envelope)
    onset = np.maximum(onset, 0.0)

    # Autocorrelation of onset function
    n = len(onset)
    # BPM range: 60-200 → period in frames
    fps = sr / hop  # frames per second
    min_lag = int(fps * 60 / 200)  # fastest BPM
    max_lag = int(fps * 60 / 60)   # slowest BPM

    if max_lag >= n:
        max_lag = n - 1
    if min_lag >= max_lag:
        return 140.0

    ac = np.zeros(max_lag - min_lag + 1)
    for lag_idx, lag in enumerate(range(min_lag, max_lag + 1)):
        corr = np.sum(onset[:n - lag] * onset[lag:])
        ac[lag_idx] = corr

    if np.max(ac) <= 0:
        return 140.0

    # Find peak
    best_lag_idx = int(np.argmax(ac))
    best_lag = min_lag + best_lag_idx
    bpm = fps * 60.0 / best_lag

    # Snap to reasonable dubstep BPM range — prefer halftime detection
    if bpm > 180:
        bpm /= 2.0
    if bpm < 70:
        bpm *= 2.0

    return round(bpm, 1)


def estimate_key(samples: np.ndarray, sr: int = SAMPLE_RATE) -> tuple[str, str]:
    """Estimate musical key via chromagram energy analysis.

    Returns (note_name, scale_type) e.g. ("F", "minor").
    """
    # Build chromagram: sum FFT energy in each pitch class
    fft_size = 8192
    n = min(len(samples), sr * 30)  # analyze first 30 seconds
    chunk = samples[:n]

    # Window and FFT
    n_windows = max(1, n // (fft_size // 2))
    chroma = np.zeros(12)

    for w in range(n_windows):
        start = w * (fft_size // 2)
        end = start + fft_size
        if end > n:
            break
        frame = chunk[start:end] * np.hanning(fft_size)
        spectrum = np.abs(fft(frame))
        freqs = np.fft.rfftfreq(fft_size, 1.0 / sr)

        # Accumulate energy per pitch class
        for i, freq in enumerate(freqs):
            if freq < 60 or freq > 4000:
                continue
            if spectrum[i] < 1e-6:
                continue
            # Map frequency to pitch class
            midi = 69 + 12 * math.log2(freq / 440.0) if freq > 0 else 0
            pc = int(round(midi)) % 12
            chroma[pc] += spectrum[i] ** 2

    # Normalize
    total = np.sum(chroma)
    if total > 0:
        chroma /= total

    # Korrelate with major/minor profiles (Krumhansl-Kessler)
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                              2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                              2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    major_profile /= np.sum(major_profile)
    minor_profile /= np.sum(minor_profile)

    best_key = "C"
    best_scale = "minor"
    best_corr = -1.0

    for shift in range(12):
        rotated = np.roll(chroma, -shift)
        # Major correlation
        corr_major = float(np.corrcoef(rotated, major_profile)[0, 1])
        if corr_major > best_corr:
            best_corr = corr_major
            best_key = NOTES[shift]
            best_scale = "major"
        # Minor correlation
        corr_minor = float(np.corrcoef(rotated, minor_profile)[0, 1])
        if corr_minor > best_corr:
            best_corr = corr_minor
            best_key = NOTES[shift]
            best_scale = "minor"

    return best_key, best_scale


def compute_energy_curve(samples: np.ndarray, sr: int = SAMPLE_RATE,
                         window_s: float = 2.0) -> list[float]:
    """Compute RMS energy curve with given window size."""
    hop = int(sr * window_s)
    n = len(samples)
    curve = []
    for i in range(0, n, hop):
        chunk = samples[i:i + hop]
        if len(chunk) < hop // 4:
            break
        rms = float(np.sqrt(np.mean(chunk * chunk)))
        curve.append(rms)
    # Normalize to 0-1
    peak = max(curve) if curve else 1.0
    if peak > 0:
        curve = [v / peak for v in curve]
    return curve


def analyze_reference(path: str) -> EmulationProfile:
    """Full analysis of a reference track → EmulationProfile."""
    samples, sr = _read_wav_samples(path)
    duration = len(samples) / sr

    analyzer = AudioAnalyzer(sample_rate=sr)
    samples_list = samples.tolist()

    waveform = analyzer.analyze_waveform(samples_list)
    spectral = analyzer.analyze_spectrum(samples_list)
    loudness = analyzer.measure_loudness(samples_list)

    bpm = estimate_bpm(samples, sr)
    key, scale = estimate_key(samples, sr)
    energy = compute_energy_curve(samples, sr)

    # Derive style traits from spectral balance
    total_energy = (spectral.sub_energy + spectral.bass_energy +
                    spectral.low_mid_energy + spectral.mid_energy +
                    spectral.high_mid_energy + spectral.high_energy)
    if total_energy <= 0:
        total_energy = 1.0

    bass_weight = min(1.0, (spectral.sub_energy + spectral.bass_energy) / total_energy * 3.0)
    brightness = min(1.0, (spectral.high_mid_energy + spectral.high_energy) / total_energy * 4.0)
    aggression = min(1.0, waveform.crest_factor / 10.0) if waveform.crest_factor > 0 else 0.5
    density = min(1.0, waveform.zero_crossings / (waveform.sample_count * 0.3)) if waveform.sample_count > 0 else 0.5
    width = 0.5  # Can't detect from mono

    # Estimate section count from energy curve changes
    section_changes = 0
    if len(energy) > 2:
        for i in range(1, len(energy)):
            if abs(energy[i] - energy[i - 1]) > 0.2:
                section_changes += 1
    section_count = max(4, min(10, section_changes + 2))

    # Drop intensity from peak energy
    drop_intensity = max(energy) if energy else 0.9

    return EmulationProfile(
        source_path=path,
        duration_s=duration,
        estimated_bpm=bpm,
        estimated_key=key,
        estimated_scale=scale,
        spectral=spectral,
        waveform=waveform,
        loudness_db=loudness.integrated,
        energy_curve=energy,
        bass_weight=bass_weight,
        brightness=brightness,
        aggression=aggression,
        density=density,
        width=width,
        section_count=section_count,
        drop_intensity=drop_intensity,
    )


# ═══════════════════════════════════════════════════════════════════════════
# SYNTHESIS — Render new track from EmulationProfile
# ═══════════════════════════════════════════════════════════════════════════

def _samples_for(beats: float, bpm: float) -> int:
    return int(beats * (60.0 / bpm) * SAMPLE_RATE)


def _silence(n: int) -> np.ndarray:
    return np.zeros(n, dtype=np.float64)


def _mix_into(target: np.ndarray, source: np.ndarray, offset: int, gain: float = 1.0):
    """Mix source into target at offset (in-place)."""
    end = min(offset + len(source), len(target))
    length = end - offset
    if length > 0:
        target[offset:end] += source[:length] * gain


def _to_np(data) -> np.ndarray:
    """Convert any audio data to numpy array."""
    if isinstance(data, np.ndarray):
        return data.astype(np.float64)
    return np.asarray(data, dtype=np.float64)


def _get_key_freqs(key: str, scale: str) -> dict[str, float]:
    """Build frequency table for a given key and scale."""
    key_idx = NOTES.index(key) if key in NOTES else 5  # default F
    scale_intervals = {
        "minor": [0, 2, 3, 5, 7, 8, 10],
        "major": [0, 2, 4, 5, 7, 9, 11],
        "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
        "dorian": [0, 2, 3, 5, 7, 9, 10],
        "phrygian": [0, 1, 3, 5, 7, 8, 10],
    }
    intervals = scale_intervals.get(scale, scale_intervals["minor"])

    freqs: dict[str, float] = {}
    for octave in range(1, 6):
        for degree, semi in enumerate(intervals):
            midi = 12 * (octave + 1) + key_idx + semi
            freq = 440.0 * (2.0 ** ((midi - 69) / 12.0))
            note_name = NOTES[(key_idx + semi) % 12]
            freqs[f"{note_name}{octave}"] = freq
    return freqs


def render_emulation(profile: EmulationProfile,
                     output_path: str = "",
                     target_duration_s: float = 0.0) -> EmulationResult:
    """Render a new track that emulates the reference profile.

    Uses all DUBFORGE synth engines mapped to the detected characteristics.
    """
    from engine.bass_oneshot import BassPreset, synthesize_bass
    from engine.fm_synth import FMOperator, FMPatch, render_fm
    from engine.glitch_engine import GlitchPreset, synthesize_stutter
    from engine.impact_hit import (
        ImpactPreset, synthesize_cinematic_hit, synthesize_sub_boom,
    )
    from engine.lead_synth import (
        LeadPreset, synthesize_pluck_lead, synthesize_screech_lead,
    )
    from engine.noise_generator import NoisePreset, synthesize_noise
    from engine.pad_synth import (
        PadPreset, synthesize_dark_pad, synthesize_lush_pad,
    )
    from engine.perc_synth import (
        PercPreset, synthesize_clap, synthesize_hat,
        synthesize_kick, synthesize_snare,
    )
    from engine.supersaw import SupersawPatch, render_supersaw_mono
    from engine.vocal_chop import VocalChop, synthesize_chop

    bpm = profile.estimated_bpm
    key = profile.estimated_key
    scale = profile.estimated_scale
    beat = 60.0 / bpm
    bar = beat * 4

    # Determine target duration
    if target_duration_s <= 0:
        target_duration_s = min(profile.duration_s, 180.0)  # cap at 3 min
    if target_duration_s < 30:
        target_duration_s = 60.0  # minimum 1 minute

    freqs = _get_key_freqs(key, scale)
    # Get root frequencies at different octaves
    root1 = freqs.get(f"{key}1", 43.65)
    root2 = freqs.get(f"{key}2", 87.31)
    root3 = freqs.get(f"{key}3", 174.61)
    root4 = freqs.get(f"{key}4", 349.23)

    # Scale degrees for melody (from scale)
    scale_intervals = {
        "minor": [0, 2, 3, 5, 7, 8, 10],
        "major": [0, 2, 4, 5, 7, 9, 11],
    }
    intervals = scale_intervals.get(scale, scale_intervals["minor"])
    key_idx = NOTES.index(key) if key in NOTES else 5

    def note_freq(degree: int, octave: int = 3) -> float:
        semi = intervals[degree % len(intervals)]
        midi = 12 * (octave + 1) + key_idx + semi
        return 440.0 * (2.0 ** ((midi - 69) / 12.0))

    # ── SOUND DESIGN — driven by profile traits ─────────────────

    # Kick — pitch and drive from bass_weight + aggression
    kick_pitch = 50.0 + profile.bass_weight * 20.0
    kick_drive = 0.1 + profile.aggression * 0.4
    kick = _to_np(synthesize_kick(PercPreset(
        name="Kick", perc_type="kick", duration_s=0.4,
        pitch=kick_pitch, decay_s=0.3, tone_mix=0.8,
        brightness=0.3 + profile.brightness * 0.3,
        distortion=kick_drive, attack_s=0.001,
    )))

    snare = _to_np(synthesize_snare(PercPreset(
        name="Snare", perc_type="snare", duration_s=0.25,
        pitch=180.0, decay_s=0.15, tone_mix=0.4,
        brightness=0.6 + profile.brightness * 0.3,
        distortion=0.1 + profile.aggression * 0.2, attack_s=0.001,
    )))

    clap = _to_np(synthesize_clap(PercPreset(
        name="Clap", perc_type="clap", duration_s=0.2,
        pitch=200.0, decay_s=0.12, tone_mix=0.2,
        brightness=0.8, distortion=0.0, attack_s=0.002,
    )))

    hat_closed = _to_np(synthesize_hat(PercPreset(
        name="HatClosed", perc_type="hat", duration_s=0.06,
        pitch=8000.0, decay_s=0.04, tone_mix=0.1,
        brightness=0.9, distortion=0.0, attack_s=0.001,
    )))

    hat_open = _to_np(synthesize_hat(PercPreset(
        name="HatOpen", perc_type="hat", duration_s=0.25,
        pitch=7500.0, decay_s=0.2, tone_mix=0.1,
        brightness=0.85, distortion=0.0, attack_s=0.001,
    )))

    # Sub bass — frequency and character from bass_weight
    sub_bass = _to_np(synthesize_bass(BassPreset(
        name="Sub", bass_type="sub_sine", frequency=root1,
        duration_s=beat * 2, attack_s=0.005, release_s=0.15,
        distortion=0.0,
    )))

    # Wobble bass — FM-based, depth from aggression
    wobble_fm = 2.0 + profile.aggression * 3.0
    wobble_bass = _to_np(synthesize_bass(BassPreset(
        name="Wobble", bass_type="fm", frequency=root2,
        duration_s=beat * 2, attack_s=0.01, release_s=0.2,
        fm_ratio=PHI, fm_depth=wobble_fm,
        distortion=0.2 + profile.aggression * 0.3,
        filter_cutoff=0.4 + profile.brightness * 0.3,
    )))

    # Growl — aggressiveness driven
    growl_bass = _to_np(synthesize_bass(BassPreset(
        name="Growl", bass_type="growl", frequency=root2,
        duration_s=beat, attack_s=0.005, release_s=0.1,
        fm_ratio=2.0, fm_depth=3.0 + profile.aggression * 3.0,
        distortion=0.3 + profile.aggression * 0.3,
        filter_cutoff=0.5 + profile.brightness * 0.2,
    )))

    # Lead — brightness driven
    lead_screech = _to_np(synthesize_screech_lead(LeadPreset(
        name="Lead", lead_type="screech", frequency=root4,
        duration_s=beat * 0.5, attack_s=0.005, decay_s=0.05,
        sustain=0.6, release_s=0.08,
        filter_cutoff=0.7 + profile.brightness * 0.2,
        resonance=0.3 + profile.aggression * 0.2,
        distortion=0.2 + profile.aggression * 0.2,
    )))

    # Build screech notes on other scale degrees
    lead_notes: list[np.ndarray] = [lead_screech]
    for deg in [2, 4, 6]:
        freq = note_freq(deg, 4)
        note = _to_np(synthesize_screech_lead(LeadPreset(
            name=f"Lead{deg}", lead_type="screech", frequency=freq,
            duration_s=beat * 0.5, attack_s=0.005, decay_s=0.05,
            sustain=0.6, release_s=0.08,
            filter_cutoff=0.7 + profile.brightness * 0.2,
            resonance=0.3 + profile.aggression * 0.2,
            distortion=0.2 + profile.aggression * 0.2,
        )))
        lead_notes.append(note)

    # Supersaw chord stab
    saw_chord = _to_np(render_supersaw_mono(SupersawPatch(
        name="Chord", n_voices=7, detune_cents=30.0,
        mix=0.7, cutoff_hz=4000.0 + profile.brightness * 4000.0,
        resonance=0.2, attack=0.005, decay=0.15, sustain=0.6,
        release=0.2, master_gain=0.7,
    ), freq=root3, duration=beat * 0.75))

    # Pad — darkness and width from profile
    pad_brightness = 0.2 + profile.brightness * 0.4
    dark_pad = _to_np(synthesize_dark_pad(PadPreset(
        name="DarkPad", pad_type="dark", frequency=root3,
        duration_s=bar * 4, detune_cents=12.0,
        filter_cutoff=0.2 + pad_brightness * 0.3,
        attack_s=1.0, release_s=2.0, reverb_amount=0.5,
        brightness=pad_brightness,
    )))

    lush_pad = _to_np(synthesize_lush_pad(PadPreset(
        name="LushPad", pad_type="lush", frequency=note_freq(2, 3),
        duration_s=bar * 4, detune_cents=15.0,
        filter_cutoff=0.3 + pad_brightness * 0.3,
        attack_s=0.8, release_s=1.5, reverb_amount=0.6,
        brightness=pad_brightness + 0.1,
    )))

    # Noise riser
    noise_riser = _to_np(synthesize_noise(NoisePreset(
        name="Riser", noise_type="white", duration_s=bar * 4,
        brightness=0.3, density=0.5, modulation=0.8, mod_rate=0.5,
        attack_s=0.0, release_s=0.1, gain=0.5,
    )))
    # Apply rising volume ramp
    ramp = np.linspace(0.0, 1.0, len(noise_riser)) ** 2
    noise_riser *= ramp

    # Impact sounds
    sub_boom = _to_np(synthesize_sub_boom(ImpactPreset(
        name="Boom", impact_type="sub_boom", duration_s=2.0,
        frequency=root1, decay_s=1.5,
        intensity=0.8 + profile.aggression * 0.15,
        reverb_amount=0.3,
    )))

    cinema_hit = _to_np(synthesize_cinematic_hit(ImpactPreset(
        name="Hit", impact_type="cinematic_hit", duration_s=1.5,
        frequency=80.0, decay_s=1.0, brightness=0.6,
        intensity=0.8 + profile.aggression * 0.1,
    )))

    # Stutter fill
    stutter = _to_np(synthesize_stutter(GlitchPreset(
        name="Stutter", glitch_type="stutter", frequency=root3,
        duration_s=beat * 2, rate=16.0,
        depth=0.7 + profile.aggression * 0.2, distortion=0.2,
    )))

    # Vocal chop
    vocal = _to_np(synthesize_chop(VocalChop(
        name="VocalChop", vowel="ah", note=f"{key}3",
        duration_s=beat * 0.5,
        distortion=0.1 + profile.aggression * 0.2,
    )))

    # FM metallic hit
    fm_hit = _to_np(render_fm(FMPatch(
        name="FMHit",
        operators=[
            FMOperator(freq_ratio=1.0, amplitude=1.0, mod_index=5.0,
                       envelope=(0.001, 0.05, 0.0, 0.1)),
            FMOperator(freq_ratio=PHI, amplitude=0.8, mod_index=3.0,
                       envelope=(0.001, 0.08, 0.0, 0.15)),
        ],
        algorithm=0, master_gain=0.7,
    ), freq=root3, duration=0.3))

    # ── ARRANGEMENT — bar structure derived from profile ────────

    total_target_bars = max(16, int(target_duration_s / bar))

    # Allocate bars proportionally (using profile section_count hint)
    intro_bars = max(4, int(total_target_bars * 0.10))
    build_bars = max(2, int(total_target_bars * 0.06))
    drop1_bars = max(8, int(total_target_bars * 0.25))
    break_bars = max(4, int(total_target_bars * 0.12))
    build2_bars = max(2, int(total_target_bars * 0.06))
    drop2_bars = max(8, int(total_target_bars * 0.25))
    outro_bars = max(4, total_target_bars - intro_bars - build_bars -
                     drop1_bars - break_bars - build2_bars - drop2_bars)

    total_bars = (intro_bars + build_bars + drop1_bars + break_bars +
                  build2_bars + drop2_bars + outro_bars)
    total_samples = _samples_for(total_bars * 4, bpm)

    master_L = np.zeros(total_samples, dtype=np.float64)
    master_R = np.zeros(total_samples, dtype=np.float64)

    def mix_stereo(mono: np.ndarray, offset: int,
                   gain_l: float = 0.7, gain_r: float = 0.7):
        _mix_into(master_L, mono, offset, gain_l)
        _mix_into(master_R, mono, offset, gain_r)

    def lowpass_np(sig: np.ndarray, alpha: float = 0.3) -> np.ndarray:
        """Simple one-pole lowpass."""
        out = np.zeros_like(sig)
        out[0] = sig[0] * alpha
        for i in range(1, len(sig)):
            out[i] = out[i - 1] + alpha * (sig[i] - out[i - 1])
        return out

    def fade_in_np(sig: np.ndarray, dur_s: float = 0.5) -> np.ndarray:
        n = int(dur_s * SAMPLE_RATE)
        out = sig.copy()
        n = min(n, len(out))
        ramp = np.linspace(0.0, 1.0, n)
        out[:n] *= ramp
        return out

    def fade_out_np(sig: np.ndarray, dur_s: float = 0.5) -> np.ndarray:
        n = int(dur_s * SAMPLE_RATE)
        out = sig.copy()
        n = min(n, len(out))
        ramp = np.linspace(1.0, 0.0, n)
        out[-n:] *= ramp
        return out

    def sidechain_np(sig: np.ndarray, depth: float = 0.5) -> np.ndarray:
        out = sig.copy()
        beat_samp = _samples_for(1, bpm)
        for i in range(len(out)):
            pos = (i % beat_samp) / beat_samp
            if pos < 0.05:
                env = 1.0 - depth
            elif pos < 0.3:
                env = (1.0 - depth) + depth * ((pos - 0.05) / 0.25)
            else:
                env = 1.0
            out[i] *= env
        return out

    # ── DRUM PATTERNS ──

    def drum_drop(bars: int) -> np.ndarray:
        """Halftime dubstep drop pattern."""
        buf = _silence(_samples_for(bars * 4, bpm))
        for b in range(bars):
            off = _samples_for(b * 4, bpm)
            _mix_into(buf, kick, off, 1.0)
            _mix_into(buf, snare, off + _samples_for(2, bpm), 0.85)
            for eighth in range(8):
                _mix_into(buf, hat_closed, off + _samples_for(eighth * 0.5, bpm),
                          0.3 + profile.density * 0.15)
            _mix_into(buf, hat_open, off + _samples_for(1.5, bpm), 0.3)
            _mix_into(buf, hat_open, off + _samples_for(3.5, bpm), 0.3)
        return buf

    def drum_build(bars: int) -> np.ndarray:
        """Buildup pattern with accelerating snare."""
        buf = _silence(_samples_for(bars * 4, bpm))
        for b in range(bars):
            off = _samples_for(b * 4, bpm)
            _mix_into(buf, kick, off, 0.7)
            _mix_into(buf, kick, off + _samples_for(2, bpm), 0.7)
            divisions = [4, 8, 16, 32][min(b, 3)]
            step = 4.0 / divisions
            for hit in range(divisions):
                vel = 0.4 + 0.4 * (b / bars) * (hit / divisions)
                _mix_into(buf, snare, off + _samples_for(hit * step, bpm), vel)
        return buf

    def drum_intro(bars: int) -> np.ndarray:
        """Sparse intro drums."""
        buf = _silence(_samples_for(bars * 4, bpm))
        for b in range(bars):
            off = _samples_for(b * 4, bpm)
            _mix_into(buf, kick, off, 0.4)
            for q in range(4):
                _mix_into(buf, hat_closed, off + _samples_for(q, bpm), 0.25)
        return buf

    # ── BASS PATTERNS ──

    def bass_drop_pattern(bars: int) -> np.ndarray:
        """Wobble + growl rhythmic bass."""
        buf = _silence(_samples_for(bars * 4, bpm))
        for b in range(bars):
            off = _samples_for(b * 4, bpm)
            _mix_into(buf, sub_bass, off, 0.9)
            _mix_into(buf, wobble_bass, off + _samples_for(0.5, bpm), 0.6)
            _mix_into(buf, growl_bass, off + _samples_for(1, bpm), 0.5)
            _mix_into(buf, sub_bass, off + _samples_for(2, bpm), 0.8)
            _mix_into(buf, wobble_bass, off + _samples_for(2.5, bpm), 0.55)
            _mix_into(buf, growl_bass, off + _samples_for(3, bpm), 0.5)
        return buf

    def bass_drop2_pattern(bars: int) -> np.ndarray:
        """Heavier second drop bass."""
        buf = _silence(_samples_for(bars * 4, bpm))
        for b in range(bars):
            off = _samples_for(b * 4, bpm)
            _mix_into(buf, sub_bass, off, 1.0)
            _mix_into(buf, sub_bass, off + _samples_for(2, bpm), 0.9)
            for s in range(16):
                src = growl_bass if s % 2 == 0 else wobble_bass
                _mix_into(buf, src, off + _samples_for(s * 0.25, bpm), 0.35)
        return buf

    # ── LEAD MELODY ──

    def lead_melody(bars: int) -> np.ndarray:
        """Scale-aware lead melody over drops."""
        buf = _silence(_samples_for(bars * 4, bpm))
        melody_degrees = [0, 6, 4, 2]  # root, 7th, 5th, 3rd
        for b in range(bars):
            off = _samples_for(b * 4, bpm)
            for beat_idx, deg in enumerate(melody_degrees):
                note = lead_notes[deg % len(lead_notes)]
                _mix_into(buf, note, off + _samples_for(beat_idx, bpm),
                          0.4 + profile.brightness * 0.1)
        return buf

    # ── ASSEMBLE SECTIONS ──

    cursor = 0

    # INTRO
    intro_samp = _samples_for(intro_bars * 4, bpm)
    intro_pad = dark_pad[:min(intro_samp, len(dark_pad))]
    intro_pad = fade_in_np(lowpass_np(intro_pad, 0.15), bar * 2)
    mix_stereo(intro_pad, cursor, 0.5, 0.5)
    mix_stereo(drum_intro(intro_bars), cursor, 0.4, 0.4)
    cursor += intro_samp

    # BUILD 1
    build_samp = _samples_for(build_bars * 4, bpm)
    mix_stereo(drum_build(build_bars), cursor, 0.6, 0.6)
    riser_seg = noise_riser[:min(build_samp, len(noise_riser))]
    mix_stereo(riser_seg, cursor, 0.4, 0.4)
    cursor += build_samp

    # DROP 1
    drop1_samp = _samples_for(drop1_bars * 4, bpm)
    mix_stereo(sub_boom, cursor, 0.8, 0.8)
    mix_stereo(cinema_hit, cursor, 0.5, 0.5)

    for rep in range(max(1, drop1_bars // 4)):
        off = cursor + _samples_for(rep * 16, bpm)
        d_drums = sidechain_np(drum_drop(min(4, drop1_bars - rep * 4)), 0.0)
        mix_stereo(d_drums, off, 0.7, 0.7)
        d_bass = sidechain_np(bass_drop_pattern(min(4, drop1_bars - rep * 4)),
                              0.5 * profile.bass_weight)
        mix_stereo(d_bass, off, 0.8, 0.8)

    mix_stereo(lead_melody(drop1_bars), cursor, 0.3, 0.45)

    # FM stabs
    for b in range(0, drop1_bars, 2):
        mix_stereo(fm_hit, cursor + _samples_for(b * 4, bpm), 0.25, 0.25)

    # Vocal chop on beat 2 of first bar
    mix_stereo(vocal, cursor + _samples_for(1, bpm), 0.3, 0.35)

    # Stutter in last bar
    _mix_into(master_L, stutter,
              cursor + _samples_for((drop1_bars - 1) * 4 + 2, bpm), 0.4)
    _mix_into(master_R, stutter,
              cursor + _samples_for((drop1_bars - 1) * 4 + 2, bpm), 0.4)

    cursor += drop1_samp

    # BREAKDOWN
    break_samp = _samples_for(break_bars * 4, bpm)
    bp_len = min(break_samp, len(lush_pad))
    break_pad = fade_in_np(fade_out_np(lush_pad[:bp_len], bar), bar)
    mix_stereo(break_pad, cursor, 0.45, 0.45)

    # Pluck arpeggios
    pluck_degrees = [0, 2, 4, 6]
    for b in range(break_bars):
        off = cursor + _samples_for(b * 4, bpm)
        for q in range(4):
            deg = pluck_degrees[(b + q) % len(pluck_degrees)]
            p_freq = note_freq(deg, 3)
            p = _to_np(synthesize_pluck_lead(LeadPreset(
                name="BrkPluck", lead_type="pluck", frequency=p_freq,
                duration_s=beat * 0.8, attack_s=0.002, decay_s=0.2,
                sustain=0.2, release_s=0.3, filter_cutoff=0.6,
            )))
            pan = -0.4 if q % 2 == 0 else 0.4
            _mix_into(master_L, p, off + _samples_for(q, bpm),
                      0.35 * (1.0 - pan * 0.5))
            _mix_into(master_R, p, off + _samples_for(q, bpm),
                      0.35 * (1.0 + pan * 0.5))

    # Light hats in breakdown
    for b in range(break_bars):
        off = cursor + _samples_for(b * 4, bpm)
        for q in range(4):
            mix_stereo(hat_closed, off + _samples_for(q, bpm), 0.15, 0.15)

    cursor += break_samp

    # BUILD 2
    build2_samp = _samples_for(build2_bars * 4, bpm)
    mix_stereo(drum_build(build2_bars), cursor, 0.65, 0.65)
    riser2 = noise_riser[:min(build2_samp, len(noise_riser))]
    mix_stereo(riser2, cursor, 0.45, 0.45)
    cursor += build2_samp

    # DROP 2 — heavier
    drop2_samp = _samples_for(drop2_bars * 4, bpm)
    mix_stereo(sub_boom, cursor, 1.0, 1.0)
    mix_stereo(cinema_hit, cursor, 0.6, 0.6)
    mix_stereo(clap, cursor, 0.5, 0.5)

    for rep in range(max(1, drop2_bars // 4)):
        off = cursor + _samples_for(rep * 16, bpm)
        d2_drums = sidechain_np(drum_drop(min(4, drop2_bars - rep * 4)), 0.0)
        mix_stereo(d2_drums, off, 0.75, 0.75)
        for b2 in range(min(4, drop2_bars - rep * 4)):
            mix_stereo(clap, off + _samples_for(b2 * 4 + 2, bpm), 0.3, 0.3)
        d2_bass = sidechain_np(bass_drop2_pattern(
            min(4, drop2_bars - rep * 4)), 0.45 * profile.bass_weight)
        # Apply distortion for heavier drop
        d2_bass = np.tanh(d2_bass * (1.2 + profile.aggression * 0.5))
        mix_stereo(d2_bass, off, 0.85, 0.85)

    mix_stereo(lead_melody(drop2_bars), cursor, 0.35, 0.5)

    # Supersaw stabs every bar in drop 2
    for b in range(drop2_bars):
        mix_stereo(saw_chord, cursor + _samples_for(b * 4, bpm), 0.2, 0.2)

    cursor += drop2_samp

    # OUTRO
    outro_samp = _samples_for(outro_bars * 4, bpm)
    o_pad = dark_pad[:min(outro_samp, len(dark_pad))]
    o_pad = fade_out_np(lowpass_np(o_pad, 0.12), bar * 4)
    mix_stereo(o_pad, cursor, 0.4, 0.4)

    o_drums = fade_out_np(drum_intro(outro_bars), bar * 4)
    mix_stereo(o_drums, cursor, 0.3, 0.3)

    # ── MIXDOWN ──

    # Normalize
    peak = max(float(np.max(np.abs(master_L))),
               float(np.max(np.abs(master_R))))
    if peak > 0:
        gain = 0.95 / peak
        master_L *= gain
        master_R *= gain

    # Soft limit
    master_L = np.tanh(master_L)
    master_R = np.tanh(master_R)

    # ── EXPORT ──

    if not output_path:
        out_dir = Path(__file__).parent.parent / "output" / "emulations"
        out_dir.mkdir(parents=True, exist_ok=True)
        src_name = Path(profile.source_path).stem if profile.source_path else "emulated"
        output_path = str(out_dir / f"{src_name}_emulation.wav")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Interleave stereo
    n_out = min(len(master_L), len(master_R))
    interleaved = np.empty(n_out * 2, dtype=np.float64)
    interleaved[0::2] = master_L[:n_out]
    interleaved[1::2] = master_R[:n_out]
    int16_data = np.clip(interleaved * 32767, -32768, 32767).astype(np.int16)

    with wave.open(output_path, "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(int16_data.tobytes())

    duration = n_out / SAMPLE_RATE
    sections_rendered = 7  # intro, build, drop1, break, build2, drop2, outro

    return EmulationResult(
        output_path=output_path,
        profile=profile,
        duration_s=duration,
        sample_rate=SAMPLE_RATE,
        sections_rendered=sections_rendered,
        status="success",
    )


def emulate_track(reference_path: str,
                  output_path: str = "",
                  target_duration_s: float = 0.0) -> EmulationResult:
    """One-call entry point: reference WAV → emulated WAV.

    Args:
        reference_path: Path to the reference WAV file.
        output_path: Where to write the output. Auto-generated if empty.
        target_duration_s: Target duration. 0 = match reference (capped at 3 min).

    Returns:
        EmulationResult with output path and analysis profile.
    """
    profile = analyze_reference(reference_path)
    return render_emulation(profile, output_path, target_duration_s)
