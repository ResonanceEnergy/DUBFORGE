#!/usr/bin/env python3
"""DUBFORGE — Full Production Pipeline.

One command to generate everything:
  1. Serum 2 wavetables (drag into Serum oscillators)
  2. Audio stems (kick, snare, hats, bass, leads, pads, FX)
  3. Ableton Live project (.als) with tracks pre-wired
  4. VST presets (.fxp)
  5. Full mixed track

Usage:
    python forge.py              # run everything
    python forge.py --stems      # stems only
    python forge.py --serum      # wavetables only
    python forge.py --ableton    # .als project only
    python forge.py --track      # mixed track only

Output tree:
    output/
    ├── dubstep_track_v5.wav          Full mixed track
    ├── wavetables/                   Serum 2 wavetables
    │   ├── DUBFORGE_GROWL_SAW.wav
    │   ├── DUBFORGE_GROWL_FM.wav
    │   ├── DUBFORGE_NEURO_A.wav
    │   ├── DUBFORGE_NEURO_B.wav
    │   ├── DUBFORGE_SCREECH.wav
    │   └── DUBFORGE_SUB_MORPH.wav
    ├── stems/                        Individual stems
    │   ├── drums_full.wav
    │   ├── bass_sub.wav
    │   ├── bass_mid.wav
    │   ├── lead.wav
    │   ├── pad.wav
    │   ├── fx_riser.wav
    │   └── fx_impacts.wav
    ├── presets/                       VST2 .fxp presets
    │   ├── DUBFORGE_SUB.fxp
    │   ├── DUBFORGE_GROWL.fxp
    │   ├── DUBFORGE_LEAD.fxp
    │   └── DUBFORGE_PAD.fxp
    └── ableton/                      Ableton projects
        ├── DUBFORGE_SESSION.als
        └── DUBFORGE_SESSION_structure.json
"""

import math
import os
import struct
import sys
import wave
from pathlib import Path

import numpy as np

# ── DUBFORGE engine imports ─────────────────────────────────────────
from engine.bass_oneshot import BassPreset, synthesize_bass
from engine.lead_synth import LeadPreset, synthesize_screech_lead, synthesize_pluck_lead
from engine.pad_synth import PadPreset, synthesize_dark_pad, synthesize_lush_pad
from engine.perc_synth import PercPreset, synthesize_kick, synthesize_snare, synthesize_hat, synthesize_clap
from engine.noise_generator import NoisePreset, synthesize_noise
from engine.impact_hit import ImpactPreset, synthesize_sub_boom, synthesize_cinematic_hit
from engine.fm_synth import FMPatch, FMOperator, render_fm, FM_PRESETS
from engine.glitch_engine import GlitchPreset, synthesize_stutter
from engine.growl_resampler import (
    generate_saw_source, generate_fm_source, growl_resample_pipeline
)
from engine.karplus_strong import KarplusStrongPatch, render_ks
from engine.additive_synth import (
    AdditivePatch, Partial, render_additive, harmonic_partials, phi_partials
)
from engine.phi_core import write_wav as write_serum_wav, WAVETABLE_SIZE
from engine.fxp_writer import main as fxp_main
from engine.als_generator import (
    ALSProject, ALSTrack, ALSScene, write_als, write_als_json
)
from engine.mastering_chain import master, MasterSettings, dubstep_master_settings
from engine.config_loader import PHI

# V4 processing imports — full engine
from engine.reverb_delay import apply_reverb_delay, ReverbDelayPreset
from engine.multiband_distortion import apply_multiband_distortion, MultibandDistPreset
from engine.stereo_imager import apply_stereo_imaging, StereoPreset
from engine.saturation import SaturationEngine, SatConfig
from engine.dynamics import compress, transient_shape, CompressorSettings
from engine.lfo_matrix import generate_lfo, LFOPreset
from engine.formant_synth import synthesize_morph_formant, FormantPreset
from engine.supersaw import render_supersaw, SupersawPatch
from engine.intelligent_eq import auto_eq, apply_eq_band
from engine.beat_repeat import apply_beat_repeat, BeatRepeatPatch
from engine.panning import PanningEngine
from engine.drone_synth import synthesize_dark_drone, DronePreset
from engine.granular_synth import synthesize_cloud, GranularPreset
from engine.vocal_chop import VocalChop, synthesize_chop
from engine.pitch_automation import PitchAutoPreset, apply_pitch_automation
from engine.transition_fx import TransitionPreset, synthesize_transition
from engine.riser_synth import RiserPreset, synthesize_noise_sweep
from engine.groove import GrooveEngine, GROOVE_TEMPLATES, NoteEvent
from engine.vocal_processor import VocalPreset, apply_vocal_processing
from engine.variation_engine import (
    VariationEngine, SongBlueprint, SongDNA, forge_song_dna, save_dna,
    DrumDNA, BassDNA, LeadDNA, AtmosphereDNA, FxDNA, MixDNA,
    ArrangementSection, SCALE_INTERVALS, NOTES,
)

# ── Constants ────────────────────────────────────────────────────────
SR = 48000
BPM = 140
BEAT = 60.0 / BPM
BAR = BEAT * 4
OUTPUT = Path("output")

# F minor scale frequencies
FREQ = {
    "F1": 43.65, "Ab1": 51.91, "Bb1": 58.27, "C2": 65.41,
    "Db2": 69.30, "Eb2": 77.78, "F2": 87.31, "G2": 98.00,
    "Ab2": 103.83, "Bb2": 116.54, "C3": 130.81, "Db3": 138.59,
    "Eb3": 155.56, "F3": 174.61, "G3": 196.00, "Ab3": 207.65,
    "Bb3": 233.08, "C4": 261.63, "Db4": 277.18, "Eb4": 311.13,
    "F4": 349.23, "G4": 392.00, "Ab4": 415.30,
}


# ═══════════════════════════════════════════
#  UTILITIES
# ═══════════════════════════════════════════

def samples(beats: float) -> int:
    return int(beats * BEAT * SR)


def silence(beats: float) -> list[float]:
    return [0.0] * samples(beats)


def to_list(arr) -> list[float]:
    if isinstance(arr, np.ndarray):
        return arr.tolist()
    return list(arr)


def to_np(signal) -> np.ndarray:
    if isinstance(signal, np.ndarray):
        return signal
    return np.array(signal, dtype=np.float64)


def mix_into(target: list[float], source: list[float], offset: int, gain: float = 1.0):
    for i, s in enumerate(source):
        pos = offset + i
        if pos < len(target):
            target[pos] += s * gain


def fade_in(sig: list[float], dur_s: float = 0.5) -> list[float]:
    n = int(dur_s * SR)
    out = list(sig)
    for i in range(min(n, len(out))):
        out[i] *= i / n
    return out


def fade_out(sig: list[float], dur_s: float = 0.5) -> list[float]:
    n = int(dur_s * SR)
    out = list(sig)
    length = len(out)
    for i in range(min(n, length)):
        out[length - 1 - i] *= i / n
    return out


def lowpass(sig: list[float], cutoff: float = 0.3) -> list[float]:
    """SVF lowpass filter (12 dB/oct) — cutoff is 0-1 mapped to Hz."""
    from engine.dsp_core import svf_lowpass
    arr = np.array(sig, dtype=np.float64)
    cutoff_hz = max(20, cutoff * 10000)
    filtered = svf_lowpass(arr, cutoff_hz, 0.1, SR)
    return filtered.tolist()


def highpass(sig: list[float], cutoff: float = 0.95) -> list[float]:
    out = [0.0] * len(sig)
    prev_in = sig[0]
    out[0] = sig[0]
    for i in range(1, len(sig)):
        out[i] = cutoff * (out[i - 1] + sig[i] - prev_in)
        prev_in = sig[i]
    return out


def distort(sig: list[float], drive: float = 2.0) -> list[float]:
    """Oversampled warm saturation via dsp_core."""
    from engine.dsp_core import saturate_warm
    arr = np.array(sig, dtype=np.float64)
    out = saturate_warm(arr, drive, SR)
    return out.tolist()


def wavefold(sig: list[float], threshold: float = 0.6) -> list[float]:
    """Wavefolder distortion — oversampled via dsp_core."""
    from engine.dsp_core import distort_foldback, oversample_2x, downsample_2x
    arr = np.array(sig, dtype=np.float64)
    up = oversample_2x(arr)
    up = distort_foldback(up, threshold)
    down = downsample_2x(up)
    return down.tolist()


def bitcrush(sig: list[float], bits: int = 8) -> list[float]:
    """Reduce bit depth for lo-fi grit."""
    levels = 2 ** bits
    return [round(s * levels) / levels for s in sig]


def sidechain(sig: list[float], depth: float = 0.7, attack: float = 0.005, release: float = 0.25, bpm: float = 0.0) -> list[float]:
    """Musical sidechain compression synced to kick (beat 1 and 3).

    Uses an exponential envelope for natural-sounding pump with longer release.
    When bpm > 0, uses that BPM for timing; otherwise falls back to module-level.
    """
    out = list(sig)
    _beat_s = int((60.0 / bpm) * SR) if bpm > 0 else samples(1)
    atk_s = max(1, int(attack * SR))
    rel_s = max(1, int(release * SR))

    for i in range(len(out)):
        beat_pos = i % (_beat_s * 2)  # trigger every 2 beats (halftime)
        if beat_pos < atk_s:
            # Fast attack — duck the signal
            t = beat_pos / atk_s
            env = 1.0 - depth * (1.0 - t * t)  # quadratic attack
        elif beat_pos < atk_s + rel_s:
            # Slow release — let it breathe back in
            t = (beat_pos - atk_s) / rel_s
            env = (1.0 - depth) + depth * (1.0 - (1.0 - t) ** 2)  # quadratic release
        else:
            env = 1.0
        out[i] *= env
    return out


def sidechain_bus(L: list[float], R: list[float], kick_positions: list[int],
                  depth: float = 0.8, attack: float = 0.003, release: float = 0.2) -> tuple[list[float], list[float]]:
    """Apply sidechain compression to stereo bus triggered by actual kick positions.

    This creates the signature dubstep pumping effect by ducking
    the bass/pad bus whenever a kick hits.
    """
    out_l = list(L)
    out_r = list(R)
    n = len(out_l)
    atk_s = max(1, int(attack * SR))
    rel_s = max(1, int(release * SR))

    # Build envelope from kick positions
    env = np.ones(n)
    for kick_pos in kick_positions:
        for i in range(atk_s + rel_s):
            pos = kick_pos + i
            if pos >= n:
                break
            if i < atk_s:
                t = i / atk_s
                val = 1.0 - depth * (1.0 - t * t)
            else:
                t = (i - atk_s) / rel_s
                val = (1.0 - depth) + depth * (1.0 - (1.0 - t) ** 2)
            env[pos] = min(env[pos], val)  # min to handle overlapping kicks

    for i in range(n):
        out_l[i] *= env[i]
        out_r[i] *= env[i]
    return out_l, out_r


def pitch_shift_bass(sig: list[float], semitones: float) -> list[float]:
    """Quick pitch shift via linear interpolation resampling.

    Shifts pitch by the given number of semitones while keeping
    the output the same length as the input (zero-pads if needed).
    """
    if abs(semitones) < 0.01:
        return sig
    ratio = 2.0 ** (semitones / 12.0)
    n_orig = len(sig)
    new_n = int(n_orig / ratio)
    if new_n < 2:
        return sig
    arr = np.array(sig, dtype=np.float64)
    indices = np.linspace(0, n_orig - 1, new_n)
    shifted = np.interp(indices, np.arange(n_orig), arr)
    # Pad or truncate to original length
    if len(shifted) < n_orig:
        shifted = np.pad(shifted, (0, n_orig - len(shifted)))
    else:
        shifted = shifted[:n_orig]
    return shifted.tolist()


def stereo_widen(mono: list[float], width: float = 0.5) -> tuple[list[float], list[float]]:
    """Stereo widening via Haas delay + slight pitch detune for rich spread."""
    delay = int(0.018 * SR)  # 18ms Haas delay (wider than before)
    left = list(mono)
    right = [0.0] * len(mono)
    for i in range(len(mono)):
        if i >= delay:
            right[i] = mono[i - delay] * width + mono[i] * (1 - width)
        else:
            right[i] = mono[i]
    return left, right


def write_mono_wav(path: str, sig: list[float]):
    """Write 24-bit mono WAV."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(3)  # 24-bit
        wf.setframerate(SR)
        frames = b""
        for s in sig:
            val = max(-8388608, min(8388607, int(s * 8388607)))
            frames += struct.pack("<i", val)[:3]  # 24-bit LE
        wf.writeframes(frames)


def write_stereo_wav(path: str, left: list[float], right: list[float]):
    """Write 24-bit stereo WAV."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    n = min(len(left), len(right))
    with wave.open(path, "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(3)  # 24-bit
        wf.setframerate(SR)
        chunk_size = SR
        for start in range(0, n, chunk_size):
            end = min(start + chunk_size, n)
            frames = b""
            for i in range(start, end):
                l_s = max(-8388608, min(8388607, int(left[i] * 8388607)))
                r_s = max(-8388608, min(8388607, int(right[i] * 8388607)))
                frames += struct.pack("<i", l_s)[:3]
                frames += struct.pack("<i", r_s)[:3]
            wf.writeframes(frames)


def normalize(sig: list[float], target: float = 0.95) -> list[float]:
    peak = max(abs(s) for s in sig) if sig else 1.0
    if peak > 0:
        g = target / peak
        return [s * g for s in sig]
    return sig


# ═══════════════════════════════════════════
#  1. SERUM WAVETABLE GENERATOR
# ═══════════════════════════════════════════

def generate_wavetables():
    """Generate Serum 2-ready wavetable .wav files."""
    print("\n═══ STEP 1: Serum 2 Wavetables ═══")
    wt_dir = OUTPUT / "wavetables"
    wt_dir.mkdir(parents=True, exist_ok=True)

    # Growl wavetables (from growl_resampler pipeline)
    print("  [1/6] GROWL_SAW — Saw → growl resampling pipeline...")
    saw = generate_saw_source()
    saw_frames = growl_resample_pipeline(saw, n_output_frames=256)
    write_serum_wav(str(wt_dir / "DUBFORGE_GROWL_SAW.wav"), saw_frames)

    print("  [2/6] GROWL_FM — FM → growl resampling pipeline...")
    fm = generate_fm_source(fm_ratio=PHI, fm_depth=3.0)
    fm_frames = growl_resample_pipeline(fm, n_output_frames=256)
    write_serum_wav(str(wt_dir / "DUBFORGE_GROWL_FM.wav"), fm_frames)

    # Neuro bass wavetables — custom spectral morphs
    print("  [3/6] NEURO_A — Harmonic stacking with waveshaping...")
    neuro_a_frames = _gen_neuro_wavetable(style="aggressive")
    write_serum_wav(str(wt_dir / "DUBFORGE_NEURO_A.wav"), neuro_a_frames)

    print("  [4/6] NEURO_B — Phase distortion morph...")
    neuro_b_frames = _gen_neuro_wavetable(style="phase")
    write_serum_wav(str(wt_dir / "DUBFORGE_NEURO_B.wav"), neuro_b_frames)

    print("  [5/6] SCREECH — Metallic screech lead...")
    screech_frames = _gen_screech_wavetable()
    write_serum_wav(str(wt_dir / "DUBFORGE_SCREECH.wav"), screech_frames)

    print("  [6/6] SUB_MORPH — Sub bass morphing sine→saw...")
    sub_frames = _gen_sub_morph_wavetable()
    write_serum_wav(str(wt_dir / "DUBFORGE_SUB_MORPH.wav"), sub_frames)

    # Copy wavetables to Serum's user folder if it exists
    serum_tables = Path.home() / "Documents" / "Xfer" / "Serum Presets" / "Tables" / "DUBFORGE"
    if (Path.home() / "Documents" / "Xfer").exists():
        serum_tables.mkdir(parents=True, exist_ok=True)
        import shutil
        for wt in wt_dir.glob("DUBFORGE_*.wav"):
            shutil.copy2(wt, serum_tables / wt.name)
        print(f"  → Copied to Serum: {serum_tables}")
    else:
        print(f"  → Serum user folder not found yet. Open Serum once in Ableton,")
        print(f"    then copy from: {wt_dir.resolve()}")
        print(f"    into: ~/Documents/Xfer/Serum Presets/Tables/")

    print(f"  ✓ 6 wavetables in {wt_dir.resolve()}")
    return wt_dir


def _gen_neuro_wavetable(style: str = "aggressive", n_frames: int = 256) -> list[np.ndarray]:
    """Generate neuro bass wavetable with harmonic stacking and distortion."""
    frames = []
    size = WAVETABLE_SIZE
    t = np.linspace(0, 2 * np.pi, size, endpoint=False)

    for i in range(n_frames):
        progress = i / (n_frames - 1)

        if style == "aggressive":
            # Start with saw, add FM + waveshaping
            n_harmonics = 3 + int(progress * 20)
            frame = np.zeros(size)
            for h in range(1, n_harmonics + 1):
                amp = 1.0 / (h ** (1.3 - progress * 0.5))
                frame += amp * np.sin(h * t + progress * PHI * h * 0.5)

            # Progressive waveshaping distortion
            drive = 1.0 + progress * 8.0
            frame = np.tanh(frame * drive)

            # FM modulation increasing with progress
            mod_depth = progress * 5.0
            mod = np.sin(PHI * t * (2 + progress * 3))
            frame = np.sin(np.cumsum(frame) * 0.1 + mod * mod_depth)

        else:  # phase distortion
            # Phase distortion synthesis
            phase = t.copy()
            dist_amount = progress * 0.9
            # Bend the phase
            mask = phase < np.pi * (1 - dist_amount)
            if np.any(mask):
                scale = np.pi / (np.pi * (1 - dist_amount)) if dist_amount < 1 else 1
                phase[mask] *= scale
            phase[~mask] = np.pi + (phase[~mask] - np.pi * (1 - dist_amount)) * (
                np.pi / (np.pi * dist_amount + 1e-10)
            )
            frame = np.sin(phase)
            # Add harmonics
            for h in [PHI, PHI * 2, PHI * 3]:
                frame += progress * 0.3 * np.sin(h * t)
            # Soft clip
            frame = np.tanh(frame * (1.5 + progress * 3))

        # Normalize
        peak = np.max(np.abs(frame))
        if peak > 0:
            frame /= peak
        frames.append(frame)

    return frames


def _gen_screech_wavetable(n_frames: int = 256) -> list[np.ndarray]:
    """Generate metallic screech lead wavetable."""
    frames = []
    size = WAVETABLE_SIZE
    t = np.linspace(0, 2 * np.pi, size, endpoint=False)

    for i in range(n_frames):
        progress = i / (n_frames - 1)

        # Base: detuned saw pair
        frame = np.sin(t) * 0.5 + np.sin(t * 1.01) * 0.5

        # Add metallic partials (non-integer ratios)
        for ratio in [PHI, math.sqrt(2), math.e, PHI * 2]:
            amp = 0.15 + progress * 0.35
            frame += amp * np.sin(ratio * t + progress * ratio)

        # Ring modulation
        ring_freq = 3 + progress * 8
        frame *= np.sin(ring_freq * t)

        # Hard clip for grit
        clip = 1.0 - progress * 0.4
        frame = np.clip(frame, -clip, clip)

        peak = np.max(np.abs(frame))
        if peak > 0:
            frame /= peak
        frames.append(frame)

    return frames


def _gen_sub_morph_wavetable(n_frames: int = 256) -> list[np.ndarray]:
    """Generate sub bass wavetable: sine → triangle → saw morph."""
    frames = []
    size = WAVETABLE_SIZE
    t = np.linspace(0, 2 * np.pi, size, endpoint=False)

    for i in range(n_frames):
        progress = i / (n_frames - 1)

        # Sine
        sine = np.sin(t)
        # Triangle (additive, odd harmonics)
        tri = np.zeros(size)
        for h in range(1, 12, 2):
            tri += ((-1) ** ((h - 1) // 2)) / (h * h) * np.sin(h * t)
        tri *= 8 / (np.pi ** 2)
        # Saw (additive)
        saw = np.zeros(size)
        for h in range(1, 24):
            saw += ((-1) ** (h + 1)) / h * np.sin(h * t)
        saw *= 2 / np.pi

        # Morph: sine(0) → tri(0.5) → saw(1.0)
        if progress < 0.5:
            p = progress * 2
            frame = sine * (1 - p) + tri * p
        else:
            p = (progress - 0.5) * 2
            frame = tri * (1 - p) + saw * p

        peak = np.max(np.abs(frame))
        if peak > 0:
            frame /= peak
        frames.append(frame)

    return frames


# ═══════════════════════════════════════════
#  2. AUDIO STEM RENDERER
# ═══════════════════════════════════════════

def render_stems():
    """Render individual audio stems for Ableton import."""
    print("\n═══ STEP 2: Audio Stems ═══")
    stem_dir = OUTPUT / "stems"
    stem_dir.mkdir(parents=True, exist_ok=True)

    total_beats = 32  # 8 bars of stems

    # ── DRUMS ────────────────────────────────────────
    print("  [1/7] drums_full.wav ...")
    kick = to_list(synthesize_kick(PercPreset(
        name="Kick", perc_type="kick", duration_s=0.4,
        pitch=55.0, decay_s=0.3, tone_mix=0.85, brightness=0.35,
        distortion=0.25, attack_s=0.001
    )))
    snare = to_list(synthesize_snare(PercPreset(
        name="Snare", perc_type="snare", duration_s=0.25,
        pitch=180.0, decay_s=0.15, tone_mix=0.4, brightness=0.8,
        distortion=0.15, attack_s=0.001
    )))
    hat_c = to_list(synthesize_hat(PercPreset(
        name="HatC", perc_type="hat", duration_s=0.06,
        pitch=8000.0, decay_s=0.04, tone_mix=0.1, brightness=0.95
    )))
    hat_o = to_list(synthesize_hat(PercPreset(
        name="HatO", perc_type="hat", duration_s=0.25,
        pitch=7500.0, decay_s=0.2, tone_mix=0.1, brightness=0.9
    )))
    clap = to_list(synthesize_clap(PercPreset(
        name="Clap", perc_type="clap", duration_s=0.2,
        pitch=200.0, decay_s=0.12, tone_mix=0.2, brightness=0.9
    )))

    drum_buf = silence(total_beats)
    for bar in range(8):
        off = samples(bar * 4)
        mix_into(drum_buf, kick, off, 1.0)           # kick on 1
        mix_into(drum_buf, snare, off + samples(2), 0.85)  # snare on 3
        mix_into(drum_buf, clap, off + samples(2), 0.3)    # clap layer
        for e in range(8):
            mix_into(drum_buf, hat_c, off + samples(e * 0.5), 0.35)
        mix_into(drum_buf, hat_o, off + samples(1.5), 0.3)
        mix_into(drum_buf, hat_o, off + samples(3.5), 0.3)

    drum_buf = normalize(drum_buf, 0.95)
    write_mono_wav(str(stem_dir / "drums_full.wav"), drum_buf)

    # ── SUB BASS ─────────────────────────────────────
    print("  [2/7] bass_sub.wav ...")
    sub = to_list(synthesize_bass(BassPreset(
        name="Sub", bass_type="sub_sine", frequency=FREQ["F1"],
        duration_s=BEAT * 2, attack_s=0.005, release_s=0.15
    )))
    sub_buf = silence(total_beats)
    for bar in range(8):
        off = samples(bar * 4)
        mix_into(sub_buf, sub, off, 0.9)
        mix_into(sub_buf, sub, off + samples(2), 0.8)
    sub_buf = normalize(sub_buf, 0.9)
    write_mono_wav(str(stem_dir / "bass_sub.wav"), sub_buf)

    # ── MID BASS ─────────────────────────────────────
    print("  [3/7] bass_mid.wav ...")
    wobble = to_list(synthesize_bass(BassPreset(
        name="Wobble", bass_type="wobble", frequency=FREQ["F2"],
        duration_s=BEAT * 2, attack_s=0.01, release_s=0.2,
        fm_ratio=PHI, fm_depth=3.0, distortion=0.4, filter_cutoff=0.6
    )))
    growl = to_list(synthesize_bass(BassPreset(
        name="Growl", bass_type="growl", frequency=FREQ["F2"],
        duration_s=BEAT, attack_s=0.005, release_s=0.1,
        fm_ratio=2.0, fm_depth=5.0, distortion=0.6, filter_cutoff=0.7
    )))
    neuro = to_list(synthesize_bass(BassPreset(
        name="Neuro", bass_type="neuro", frequency=FREQ["F2"],
        duration_s=BEAT, attack_s=0.003, release_s=0.08,
        fm_ratio=3.0, fm_depth=4.0, distortion=0.7, filter_cutoff=0.5
    )))

    mid_buf = silence(total_beats)
    for bar in range(8):
        off = samples(bar * 4)
        mix_into(mid_buf, wobble, off + samples(0.5), 0.6)
        mix_into(mid_buf, growl, off + samples(1), 0.55)
        mix_into(mid_buf, neuro, off + samples(1.5), 0.5)
        mix_into(mid_buf, wobble, off + samples(2.5), 0.55)
        mix_into(mid_buf, growl, off + samples(3), 0.5)
        mix_into(mid_buf, neuro, off + samples(3.5), 0.45)

    mid_buf = distort(mid_buf, drive=2.0)
    mid_buf = sidechain(mid_buf, depth=0.6)
    mid_buf = normalize(mid_buf, 0.9)
    write_mono_wav(str(stem_dir / "bass_mid.wav"), mid_buf)

    # ── LEAD ─────────────────────────────────────────
    print("  [4/7] lead.wav ...")
    lead_f = to_list(synthesize_screech_lead(LeadPreset(
        name="LeadF", lead_type="screech", frequency=FREQ["F4"],
        duration_s=BEAT * 0.5, attack_s=0.005, decay_s=0.05,
        sustain=0.6, release_s=0.08, filter_cutoff=0.9,
        resonance=0.5, distortion=0.4
    )))
    lead_eb = to_list(synthesize_screech_lead(LeadPreset(
        name="LeadEb", lead_type="screech", frequency=FREQ["Eb4"],
        duration_s=BEAT * 0.5, attack_s=0.005, decay_s=0.05,
        sustain=0.6, release_s=0.08, filter_cutoff=0.9,
        resonance=0.5, distortion=0.4
    )))
    lead_c = to_list(synthesize_screech_lead(LeadPreset(
        name="LeadC", lead_type="screech", frequency=FREQ["C4"],
        duration_s=BEAT * 0.75, attack_s=0.005, decay_s=0.05,
        sustain=0.6, release_s=0.1, filter_cutoff=0.85,
        resonance=0.4, distortion=0.3
    )))

    lead_buf = silence(total_beats)
    melody = [(lead_f, 0.0), (lead_eb, 1.0), (lead_c, 2.0), (lead_eb, 3.0)]
    for bar in range(8):
        off = samples(bar * 4)
        for sound, beat in melody:
            mix_into(lead_buf, sound, off + samples(beat), 0.5)
    lead_buf = normalize(lead_buf, 0.85)
    write_mono_wav(str(stem_dir / "lead.wav"), lead_buf)

    # ── PAD ──────────────────────────────────────────
    print("  [5/7] pad.wav ...")
    pad = to_list(synthesize_dark_pad(PadPreset(
        name="DarkPad", pad_type="dark", frequency=FREQ["F3"],
        duration_s=BAR * 8, detune_cents=12.0, filter_cutoff=0.4,
        attack_s=1.0, release_s=2.0, reverb_amount=0.5, brightness=0.35
    )))
    pad = pad[:samples(total_beats)]
    pad = fade_in(pad, BAR * 2)
    pad = fade_out(pad, BAR * 2)
    pad = normalize(pad, 0.6)
    write_mono_wav(str(stem_dir / "pad.wav"), pad)

    # ── RISER FX ─────────────────────────────────────
    print("  [6/7] fx_riser.wav ...")
    riser = to_list(synthesize_noise(NoisePreset(
        name="Riser", noise_type="white", duration_s=BAR * 4,
        brightness=0.3, density=0.5, attack_s=0.0, gain=0.6
    )))
    for i in range(len(riser)):
        riser[i] *= (i / len(riser)) ** 2.5  # exponential rise
    riser = highpass(riser, cutoff=0.98)
    riser = normalize(riser, 0.8)
    write_mono_wav(str(stem_dir / "fx_riser.wav"), riser)

    # ── IMPACT FX ────────────────────────────────────
    print("  [7/7] fx_impacts.wav ...")
    boom = to_list(synthesize_sub_boom(ImpactPreset(
        name="Boom", impact_type="sub_boom", duration_s=2.0,
        frequency=FREQ["F1"], decay_s=1.5, intensity=0.95
    )))
    hit = to_list(synthesize_cinematic_hit(ImpactPreset(
        name="Hit", impact_type="cinematic_hit", duration_s=1.5,
        frequency=80.0, decay_s=1.0, brightness=0.6, intensity=0.9
    )))
    impact_buf = silence(8)  # 2 bars of impacts
    mix_into(impact_buf, boom, 0, 0.9)
    mix_into(impact_buf, hit, 0, 0.6)
    impact_buf = normalize(impact_buf, 0.95)
    write_mono_wav(str(stem_dir / "fx_impacts.wav"), impact_buf)

    print(f"  ✓ 7 stems in {stem_dir.resolve()}")
    return stem_dir


# ═══════════════════════════════════════════
#  3. ABLETON PROJECT GENERATOR
# ═══════════════════════════════════════════

def generate_ableton_project():
    """Generate Ableton Live .als project file with Serum 2 on bass tracks."""
    print("\n═══ STEP 3: Ableton Live Project ═══")
    als_dir = OUTPUT / "ableton"
    als_dir.mkdir(parents=True, exist_ok=True)

    project = ALSProject(
        name="DUBFORGE_SESSION",
        bpm=BPM,
        tracks=[
            # Drum tracks (audio — import stems)
            ALSTrack(name="DRUMS", track_type="audio", color=0,
                     volume_db=0, clip_names=["drums_full"]),

            # Sub bass — Serum 2
            ALSTrack(name="SUB BASS", track_type="midi", color=5,
                     volume_db=-1, device_names=["Serum2"],
                     clip_names=["Sub_F_Pattern"]),

            # Mid bass — Serum 2 (load DUBFORGE wavetables)
            ALSTrack(name="MID BASS", track_type="midi", color=10,
                     volume_db=-2, device_names=["Serum2"],
                     clip_names=["MidBass_Wobble", "MidBass_Growl"]),

            # Neuro bass — Serum 2
            ALSTrack(name="NEURO", track_type="midi", color=15,
                     volume_db=-3, device_names=["Serum2"],
                     clip_names=["Neuro_Drop"]),

            # Lead — Serum 2
            ALSTrack(name="LEAD", track_type="midi", color=25,
                     volume_db=-4, device_names=["Serum2"],
                     clip_names=["Lead_Melody"]),

            # Pad
            ALSTrack(name="PAD", track_type="audio", color=30,
                     volume_db=-8, clip_names=["pad"]),

            # FX
            ALSTrack(name="FX RISER", track_type="audio", color=40,
                     volume_db=-6, clip_names=["fx_riser"]),
            ALSTrack(name="FX IMPACT", track_type="audio", color=45,
                     volume_db=-4, clip_names=["fx_impacts"]),

            # Audio backup stems
            ALSTrack(name="BASS SUB [stem]", track_type="audio", color=5,
                     volume_db=-100, mute=True,
                     clip_names=["bass_sub"]),
            ALSTrack(name="BASS MID [stem]", track_type="audio", color=10,
                     volume_db=-100, mute=True,
                     clip_names=["bass_mid"]),
            ALSTrack(name="LEAD [stem]", track_type="audio", color=25,
                     volume_db=-100, mute=True,
                     clip_names=["lead"]),
        ],
        scenes=[
            ALSScene(name="INTRO", tempo=BPM),
            ALSScene(name="BUILD", tempo=BPM),
            ALSScene(name="DROP 1", tempo=BPM),
            ALSScene(name="BREAKDOWN", tempo=BPM),
            ALSScene(name="BUILD 2", tempo=BPM),
            ALSScene(name="DROP 2", tempo=BPM),
            ALSScene(name="OUTRO", tempo=BPM),
        ],
        master_volume_db=0,
        notes=(
            "DUBFORGE Dubstep Session — F minor @ 140 BPM\n\n"
            "SETUP INSTRUCTIONS:\n"
            "1. Drag stems from output/stems/ into the audio tracks\n"
            "2. On SUB/MID/NEURO/LEAD tracks: load Serum 2\n"
            "3. In Serum Osc A: drag wavetables from output/wavetables/\n"
            "   - SUB: DUBFORGE_SUB_MORPH.wav\n"
            "   - MID: DUBFORGE_GROWL_SAW.wav or GROWL_FM.wav\n"
            "   - NEURO: DUBFORGE_NEURO_A.wav or NEURO_B.wav\n"
            "   - LEAD: DUBFORGE_SCREECH.wav\n"
            "4. Audio stem tracks are muted backups — unmute to compare\n"
            "5. Use scenes to trigger sections\n"
        ),
    )

    als_path = str(als_dir / "DUBFORGE_SESSION.als")
    write_als(project, als_path)
    write_als_json(project, str(als_dir / "DUBFORGE_SESSION_structure.json"))

    print(f"  ✓ {als_path}")
    print(f"  → Open in Ableton: File → Open Live Set → {als_path}")
    return als_path


# ═══════════════════════════════════════════
#  4. VST PRESETS
# ═══════════════════════════════════════════

def generate_presets():
    """Generate .fxp VST2 presets."""
    print("\n═══ STEP 4: VST Presets ═══")
    fxp_main()
    print(f"  ✓ Presets in {OUTPUT / 'presets'}")




def _scale_note(root_freq: float, scale: str, degree: int, octave: int) -> float:
    """Get Hz for scale degree at octave (1-based from root).

    Example: _scale_note(43.65, "minor", 0, 1) → F1 = 43.65
             _scale_note(43.65, "minor", 2, 3) → Ab3 = 207.65
             _scale_note(43.65, "minor", 4, 3) → C4 = 261.63
    """
    intervals = SCALE_INTERVALS.get(scale, [0, 2, 3, 5, 7, 8, 10])
    semi = intervals[degree % len(intervals)]
    return root_freq * (2.0 ** (octave - 1)) * (2.0 ** (semi / 12.0))


def _default_v5_dna() -> SongDNA:
    """Build a SongDNA that reproduces the V5 hardcoded defaults."""
    return SongDNA(
        name="Dubstep Track V5",
        style="dubstep",
        theme="aggressive dubstep",
        mood_name="aggressive",
        tags=["dubstep", "aggressive", "high_energy"],
        seed=0,
        key="F",
        scale="minor",
        bpm=140,
        root_freq=43.65,
        freq_table=dict(FREQ),
        arrangement=[
            ArrangementSection("intro", 16, 0.15, ["drone", "pad", "hats_sparse"]),
            ArrangementSection("build", 8, 0.5, ["kick", "snare_roll", "riser", "pad"]),
            ArrangementSection("drop1", 32, 1.0, ["kick", "snare", "hats", "sub", "bass", "lead", "chops"]),
            ArrangementSection("break", 16, 0.25, ["pad", "plucks", "sub_long"]),
            ArrangementSection("build2", 8, 0.55, ["kick", "snare_roll", "riser"]),
            ArrangementSection("drop2", 32, 1.0, ["kick", "snare", "hats", "sub", "bass", "lead", "chops", "extra_bass"]),
            ArrangementSection("outro", 16, 0.1, ["kick_fade", "pad_fade"]),
        ],
        total_bars=128,
        drums=DrumDNA(
            kick_pitch=42.0, kick_fm_depth=3.0, kick_drive=0.55,
            kick_sub_weight=0.65, kick_attack=3.0,
            snare_pitch=230.0, snare_noise_mix=0.5, snare_metallic=0.2,
            snare_compression=8.0, snare_ott=0.35,
            hat_frequency=8000.0, hat_metallic=0.15, hat_brightness=0.95,
            clap_brightness=0.95, clap_reverb=0.15, hat_density=16,
        ),
        bass=BassDNA(
            primary_type="dist_fm", secondary_type="sync", tertiary_type="neuro",
            fm_depth=10.0, fm_feedback=0.6, distortion=0.9,
            filter_cutoff=0.8, acid_resonance=0.0, growl_resampler=True,
            lfo_rate=2.5, lfo_depth=0.8, sub_weight=0.9, mid_drive=0.85,
            pitch_dive_semi=12.0, wavefold_thresh=0.0, bitcrush_bits=0,
            ott_amount=0.4, ring_mod_freq=0.0,
        ),
        lead=LeadDNA(
            use_additive=True, additive_partials=16, additive_rolloff="sawtooth",
            use_fm=True, fm_operators=2, fm_depth=3.0,
            brightness=0.7, reverb_decay=0.5, shimmer=0.0,
            supersaw_voices=7, supersaw_detune=35.0, supersaw_cutoff=5500.0,
            ott_amount=0.3,
        ),
        atmosphere=AtmosphereDNA(
            pad_type="dark", pad_attack=2.0, pad_brightness=0.25,
            reverb_decay=3.5, stereo_width=1.5, shimmer=0.0,
            granular_density=0.45, drone_voices=7, drone_movement=0.45,
            use_karplus_drone=True, noise_bed_type="pink", noise_bed_level=0.15,
        ),
        fx=FxDNA(
            riser_intensity=0.85, impact_intensity=0.95, glitch_amount=0.0,
            tape_degrade=0.0, stutter_rate=16.0, pitch_dive_range=12.0,
            vocal_chop_distortion=0.35, beat_repeat_probability=0.25,
            riser_start_freq=150.0, riser_end_freq=8000.0, boom_decay=2.0,
        ),
        mix=MixDNA(
            target_lufs=-7.5, stereo_width=1.5, master_drive=0.55,
            eq_low_boost=1.5, eq_high_boost=2.5, compression_ratio=4.0,
            sidechain_depth=0.8, ceiling_db=-0.1, eq_low_freq=80.0,
            eq_high_freq=8000.0, compression_threshold=-12.0,
            limiter_enabled=True,
        ),
        bass_rotation=["fm_growl", "growl_wt", "dist_fm", "sync", "acid", "neuro", "formant"],
        chop_vowels=["ah", "oh", "ee", "oo"],
    )


# ═══════════════════════════════════════════


# ═══════════════════════════════════════════
#  5. FULL MIXED TRACK (V6 — DNA-Driven Sound Design)
# ═══════════════════════════════════════════

def _ott_simulate(sig: list[float], amount: float = 0.4) -> list[float]:
    """Simulate OTT multiband upward compression."""
    sat = SaturationEngine(sample_rate=SR)
    compressed = compress(sig, CompressorSettings(
        threshold_db=-25.0, ratio=6.0, attack_ms=0.5,
        release_ms=20.0, knee_db=6.0, makeup_db=8.0, mix=amount
    ))
    excited = sat.harmonic_exciter(compressed, amount=amount * 0.5, frequency=2500)
    result = sat.saturate(excited, SatConfig(
        sat_type="tape", drive=0.2 * amount, mix=amount * 0.3
    ))
    return result


def _wavetable_to_audio(frames: list[np.ndarray], freq: float,
                        duration_s: float, sr: int = SR) -> np.ndarray:
    """Convert a list of single-cycle wavetable frames into audio.

    Reads through the wavetable frames while playing back at `freq`,
    morphing smoothly between frames over `duration_s`.
    """
    n_samples = int(duration_s * sr)
    n_frames = len(frames)
    frame_size = len(frames[0])
    out = np.zeros(n_samples)
    phase = 0.0
    phase_inc = freq * frame_size / sr

    for i in range(n_samples):
        # Which frame are we in? (morph across all frames over duration)
        frame_pos = (i / n_samples) * (n_frames - 1)
        frame_idx = int(frame_pos)
        frame_frac = frame_pos - frame_idx
        frame_idx = min(frame_idx, n_frames - 2)

        # Read from current frame
        pos = phase % frame_size
        idx0 = int(pos)
        frac = pos - idx0
        idx1 = (idx0 + 1) % frame_size

        # Bilinear interpolation: between samples in frame, between frames
        val_a = frames[frame_idx][idx0] * (1 - frac) + frames[frame_idx][idx1] * frac
        val_b = frames[frame_idx + 1][idx0] * (1 - frac) + frames[frame_idx + 1][idx1] * frac
        out[i] = val_a * (1 - frame_frac) + val_b * frame_frac

        phase += phase_inc

    return out


def render_full_track(dna: 'SongDNA | None' = None):
    """Render DNA-driven dubstep track — V6 full integration.

    When dna is None, falls back to V5 defaults (F minor, 140 BPM).
    When dna is provided, EVERY synthesis parameter is driven by SongDNA:
      - Key, scale, BPM from DNA
      - Drum layer params from DrumDNA
      - Bass types + processing from BassDNA
      - Lead synthesis from LeadDNA
      - Pad/atmosphere from AtmosphereDNA
      - Transition FX from FxDNA
      - Mix/master from MixDNA
      - Arrangement sections from DNA arrangement
      - Bass rotation order from DNA
      - Vocal chop vowels from DNA
    """
    # ═══ DNA SETUP ═══════════════════════════════════
    if dna is None:
        dna = _default_v5_dna()

    # Import DSP primitives needed throughout
    from engine.dsp_core import svf_highpass, svf_lowpass, multiband_compress

    # Shadow module-level timing constants with DNA values
    BEAT = 60.0 / dna.bpm
    BAR = BEAT * 4

    def samples(beats: float) -> int:
        return int(beats * BEAT * SR)

    # Scale-degree frequency helper
    intervals = SCALE_INTERVALS.get(dna.scale, [0, 2, 3, 5, 7, 8, 10])

    def n(degree: int, octave: int) -> float:
        """Scale degree → Hz. n(0,1)=root@oct1, n(2,3)=3rd@oct3."""
        semi = intervals[degree % len(intervals)]
        return dna.root_freq * (2.0 ** (octave - 1)) * (2.0 ** (semi / 12.0))

    # Build FREQ lookup from DNA (shadows module-level FREQ)
    # Maps same keys V5 code used → DNA-key frequencies
    FREQ = {
        "F1": n(0, 1), "F2": n(0, 2), "F3": n(0, 3), "F4": n(0, 4),
        "G2": n(1, 2), "G3": n(1, 3), "G4": n(1, 4),
        "Ab1": n(2, 1), "Ab2": n(2, 2), "Ab3": n(2, 3), "Ab4": n(2, 4),
        "Bb1": n(3, 1), "Bb2": n(3, 2), "Bb3": n(3, 3),
        "C2": n(4, 1), "C3": n(4, 2), "C4": n(4, 3),
        "Db2": n(5, 1), "Db3": n(5, 2), "Db4": n(5, 3),
        "Eb2": n(6, 1), "Eb3": n(6, 2), "Eb4": n(6, 3),
    }

    # Shorthand aliases for DNA sub-specifications
    dd = dna.drums
    bd = dna.bass
    ld = dna.lead
    ad = dna.atmosphere
    fd = dna.fx
    md = dna.mix

    # Derive note names for vocal chops from DNA key
    _root_idx = NOTES.index(dna.key) if dna.key in NOTES else 5
    _fifth_idx = (_root_idx + intervals[4 % len(intervals)]) % 12
    _root_note3 = f"{dna.key}3"
    _fifth_note3 = f"{NOTES[_fifth_idx]}3"

    # Extract arrangement section bars
    sec_map = {s.name: s.bars for s in dna.arrangement}
    INTRO = sec_map.get("intro", 8)
    BUILD = sec_map.get("build", 4)
    DROP1 = sec_map.get("drop1", sec_map.get("drop1b", 16))
    BREAK_ = sec_map.get("break", 8)
    BUILD2 = sec_map.get("build2", 4)
    DROP2 = sec_map.get("drop2", sec_map.get("drop2b", 16))
    OUTRO = sec_map.get("outro", 8)
    # Recalculate total_bars from ONLY rendered sections (excludes verse1/drop1b etc)
    total_bars = INTRO + BUILD + DROP1 + BREAK_ + BUILD2 + DROP2 + OUTRO
    total_s = samples(total_bars * 4)

    song_label = dna.name or "dubstep_track"
    safe_name = song_label.lower().replace(" ", "_").replace("'", "")

    print(f"\n═══ RENDERING: {dna.name} ═══")
    print(f"  {dna.key} {dna.scale} @ {dna.bpm} BPM | {total_bars} bars | Mood: {dna.mood_name}")
    print(f"  Bass: {' → '.join(dna.bass_rotation[:5])}")
    print(f"  Arrangement: {' → '.join(s.name for s in dna.arrangement)}")
    print(f"  Drums: kick@{dd.kick_pitch:.0f}Hz drive={dd.kick_drive:.2f} | snare@{dd.snare_pitch:.0f}Hz")
    print(f"  Bass: FM depth={bd.fm_depth:.1f} dist={bd.distortion:.2f} | Lead: {ld.additive_partials}p {ld.additive_rolloff}")
    print(f"  Mix: {md.target_lufs:.1f} LUFS target | ceiling={md.ceiling_db:.1f} dB")

    sat = SaturationEngine(sample_rate=SR)
    panner = PanningEngine(sample_rate=SR)
    groove_eng = GrooveEngine(bpm=dna.bpm, sample_rate=SR)

    # ═══════════════════════════════════════════
    #  SOUND DESIGN — Drums (LAYERED, MULTI-SOURCE)
    # ═══════════════════════════════════════════
    print("  [1/9] Drums — layered synthesis...")

    # ── KICK ──────────────────────────────────────────
    # Layer 1: Sub body — perc_synth kick with DNA-driven pitch sweep
    kick_sub = to_list(synthesize_kick(PercPreset(
        name="KSub", perc_type="kick", pitch=dd.kick_pitch, duration_s=0.6,
        decay_s=0.45, tone_mix=0.95, brightness=0.1 + (1 - dd.kick_sub_weight) * 0.15,
        distortion=dd.kick_drive * 0.36
    )))

    # Layer 2: FM body — DNA-driven mod_index and feedback
    kick_fm_patch = FMPatch(
        name="KickFM",
        operators=[
            FMOperator(freq_ratio=1.0, amplitude=1.0, mod_index=dd.kick_fm_depth,
                       feedback=dd.kick_drive * 0.36, envelope=(0.001, 0.08, 0.0, 0.05)),
            FMOperator(freq_ratio=2.0, amplitude=0.8, mod_index=dd.kick_fm_depth * 0.67,
                       feedback=0.0, envelope=(0.001, 0.04, 0.0, 0.02)),
        ],
        algorithm=0, master_gain=0.85,
    )
    kick_fm = render_fm(kick_fm_patch, freq=dd.kick_pitch * 1.3, duration=0.3)

    # Layer 3: Click transient — Karplus-Strong with very high freq, short
    kick_click = render_ks(KarplusStrongPatch(
        frequency=2500.0, duration=0.015, damping=0.8, brightness=0.95,
        stretch=0.0, feedback=0.5, noise_mix=1.0
    ))

    # Layer 4: Brown noise sub rumble
    kick_rumble = to_list(synthesize_noise(NoisePreset(
        name="KRumble", noise_type="brown", duration_s=0.25,
        brightness=0.1, gain=0.4, attack_s=0.001, release_s=0.2
    )))

    # Mix kick layers
    kick_len = max(len(kick_sub), len(kick_fm), len(kick_click), len(kick_rumble))
    kick = [0.0] * kick_len
    for i in range(len(kick_sub)):
        kick[i] += kick_sub[i] * 0.35
    for i in range(len(kick_fm)):
        kick[i] += kick_fm[i] * 0.35
    for i in range(len(kick_click)):
        kick[i] += kick_click[i] * 0.45
    for i in range(len(kick_rumble)):
        kick[i] += kick_rumble[i] * 0.2

    # Process kick — DNA-driven intensity
    kick = transient_shape(kick, attack_gain=dd.kick_attack, sustain_gain=0.6)
    kick = compress(kick, CompressorSettings(
        threshold_db=-4.0, ratio=10.0, attack_ms=0.2, release_ms=35.0, makeup_db=4.0
    ))
    kick = sat.saturate(kick, SatConfig(sat_type="tape", drive=dd.kick_drive, mix=0.5))
    kick = apply_eq_band(kick, center_hz=dd.kick_pitch * 1.3, gain_db=4.0, q=0.5)   # sub weight
    kick = apply_eq_band(kick, center_hz=3500.0, gain_db=4.0, q=1.2)  # click
    kick = apply_eq_band(kick, center_hz=300.0, gain_db=-3.0, q=1.0)  # scoop mud
    kick = normalize(kick, 0.98)

    # ── SNARE ─────────────────────────────────────────
    # Layer 1: Tonal body — DNA-driven pitch and mix
    snare_body = to_list(synthesize_snare(PercPreset(
        name="SBody", perc_type="snare", pitch=dd.snare_pitch, duration_s=0.3,
        decay_s=0.15, tone_mix=dd.snare_noise_mix, brightness=0.5,
        distortion=dd.snare_metallic * 0.67
    )))

    # Layer 2: Pink noise tail
    snare_noise = to_list(synthesize_noise(NoisePreset(
        name="SNoise", noise_type="pink", duration_s=0.25,
        brightness=0.5 + dd.snare_noise_mix * 0.4, gain=0.7,
        attack_s=0.001, release_s=0.18
    )))

    # Layer 3: Metallic Karplus ring — DNA metallic control
    snare_ring = render_ks(KarplusStrongPatch(
        frequency=dd.snare_pitch * 3.5, duration=0.12,
        damping=0.4, brightness=dd.hat_brightness,
        stretch=0.2 + dd.snare_metallic * 0.3,
        feedback=0.5 + dd.snare_metallic * 0.3, noise_mix=0.8
    ))

    # Layer 4: White noise top (transient)
    snare_top = to_list(synthesize_noise(NoisePreset(
        name="STop", noise_type="white", duration_s=0.05,
        brightness=0.95, gain=0.9, attack_s=0.0005, release_s=0.04
    )))

    # Mix snare layers
    snr_len = max(len(snare_body), len(snare_noise), len(snare_ring), len(snare_top))
    snare_dry = [0.0] * snr_len
    for i in range(len(snare_body)):
        snare_dry[i] += snare_body[i] * 0.45
    for i in range(len(snare_noise)):
        snare_dry[i] += snare_noise[i] * 0.35
    for i in range(len(snare_ring)):
        snare_dry[i] += snare_ring[i] * 0.2
    for i in range(len(snare_top)):
        snare_dry[i] += snare_top[i] * 0.3

    # Process snare — parallel compression
    snr_compressed = compress(snare_dry, CompressorSettings(
        threshold_db=-12.0, ratio=8.0, attack_ms=0.3, release_ms=30.0, makeup_db=6.0
    ))
    # Blend dry + compressed (parallel compression)
    snare_pc = [0.0] * len(snare_dry)
    for i in range(len(snare_dry)):
        snare_pc[i] = snare_dry[i] * 0.5 + (snr_compressed[i] if i < len(snr_compressed) else 0.0) * 0.5

    snare_pc = transient_shape(snare_pc, attack_gain=1.5 + dd.snare_compression * 0.1, sustain_gain=0.55)
    snare_pc = _ott_simulate(snare_pc, dd.snare_ott)
    snare_pc = sat.saturate(snare_pc, SatConfig(sat_type="transistor", drive=dd.snare_metallic + 0.2, mix=0.35))
    snare_pc = apply_eq_band(snare_pc, center_hz=dd.snare_pitch * 0.87, gain_db=2.5, q=1.0)  # body
    snare_pc = apply_eq_band(snare_pc, center_hz=5000.0, gain_db=3.0, q=0.8)  # crack
    # Plate reverb
    snr_np = apply_reverb_delay(to_np(snare_pc), ReverbDelayPreset(
        name="SnrPlate", effect_type="plate", decay_time=0.6,
        pre_delay_ms=8.0, diffusion=0.85, damping=0.55, mix=0.2
    ))
    snare = to_list(snr_np)
    snare = normalize(snare, 0.93)

    # ── HATS — DNA-driven Karplus-Strong metallic ─────
    hat_c_ks = render_ks(KarplusStrongPatch(
        frequency=dd.hat_frequency, duration=0.06,
        damping=0.85, brightness=dd.hat_brightness,
        stretch=0.1 + dd.hat_metallic * 0.3,
        feedback=0.2 + dd.hat_metallic * 0.3, noise_mix=0.9, pluck_position=0.3
    ))
    hat_c_perc = to_list(synthesize_hat(PercPreset(
        name="HC", perc_type="hat", pitch=dd.hat_frequency * 1.19,
        duration_s=0.04, decay_s=0.025, tone_mix=0.06,
        brightness=dd.hat_brightness
    )))
    # Mix
    hc_len = max(len(hat_c_ks), len(hat_c_perc))
    hat_c = [0.0] * hc_len
    for i in range(len(hat_c_ks)):
        hat_c[i] += hat_c_ks[i] * 0.5
    for i in range(len(hat_c_perc)):
        hat_c[i] += hat_c_perc[i] * 0.5
    hat_c = apply_eq_band(hat_c, center_hz=10000.0, gain_db=3.0, q=0.4)
    hat_c = sat.saturate(hat_c, SatConfig(sat_type="tape", drive=0.3, mix=0.25))
    hat_c = normalize(hat_c, 0.85)

    # Open hat: longer Karplus + noise — DNA-driven
    hat_o_ks = render_ks(KarplusStrongPatch(
        frequency=dd.hat_frequency * 0.81, duration=0.25,
        damping=0.3, brightness=dd.hat_brightness * 0.95,
        stretch=0.08 + dd.hat_metallic * 0.2,
        feedback=0.4 + dd.hat_metallic * 0.3, noise_mix=0.85
    ))
    hat_o_noise = to_list(synthesize_noise(NoisePreset(
        name="HO", noise_type="white", duration_s=0.2,
        brightness=dd.hat_brightness * 0.9, gain=0.5,
        attack_s=0.001, release_s=0.15
    )))
    ho_len = max(len(hat_o_ks), len(hat_o_noise))
    hat_o = [0.0] * ho_len
    for i in range(len(hat_o_ks)):
        hat_o[i] += hat_o_ks[i] * 0.55
    for i in range(len(hat_o_noise)):
        hat_o[i] += hat_o_noise[i] * 0.45
    hat_o = normalize(hat_o, 0.78)

    # ── CLAP — DNA-driven brightness + reverb ────────
    clap = to_list(synthesize_clap(PercPreset(
        name="CL", perc_type="clap", pitch=dd.snare_pitch * 1.09,
        duration_s=0.3, decay_s=0.18, tone_mix=0.1,
        brightness=dd.clap_brightness
    )))
    clap = compress(clap, CompressorSettings(
        threshold_db=-8.0, ratio=5.0, attack_ms=0.3, release_ms=25.0, makeup_db=3.5
    ))
    clap = sat.harmonic_exciter(clap, amount=0.3, frequency=4000)
    clap_np = apply_reverb_delay(to_np(clap), ReverbDelayPreset(
        name="ClapVerb", effect_type="plate", decay_time=0.3 + dd.clap_reverb,
        diffusion=0.7, damping=0.6, mix=dd.clap_reverb
    ))
    clap = to_list(clap_np)
    clap = normalize(clap, 0.82)

    # ═══════════════════════════════════════════
    #  SOUND DESIGN — Bass (DNA-DRIVEN, 7 types)
    # ═══════════════════════════════════════════
    print(f"  [2/9] Bass — {bd.primary_type}/{bd.secondary_type}/{bd.tertiary_type}...")

    # SUB — clean root sub with DNA sub_weight
    sub = to_list(synthesize_bass(BassPreset(
        name="Sub", bass_type="sub_sine", frequency=FREQ["F1"],
        duration_s=BEAT * 2, attack_s=0.002, release_s=0.1
    )))
    sub = apply_eq_band(sub, center_hz=FREQ["F1"] * 1.03, gain_db=bd.sub_weight * 1.5, q=0.6)
    sub = normalize(sub, 0.55)

    # BASS 1: FM Growl — DNA-driven mod_index, feedback, depth
    print(f"    FM Growl (depth={bd.fm_depth:.1f})...")
    fm_growl_patch = FMPatch(
        name="GrowlFM",
        operators=[
            FMOperator(freq_ratio=1.0, amplitude=1.0, mod_index=bd.fm_depth,
                       feedback=bd.fm_feedback, envelope=(0.005, 0.08, 0.85, 0.15)),
            FMOperator(freq_ratio=2.0, amplitude=0.9, mod_index=bd.fm_depth * 0.7,
                       feedback=bd.fm_feedback * 0.58, envelope=(0.003, 0.1, 0.75, 0.12)),
            FMOperator(freq_ratio=PHI, amplitude=0.5, mod_index=bd.fm_depth * 0.4,
                       feedback=0.0, envelope=(0.001, 0.06, 0.55, 0.08)),
        ],
        algorithm=0, master_gain=0.8,
    )
    fm_growl_raw = render_fm(fm_growl_patch, freq=FREQ["F2"], duration=BEAT * 2)
    fm_growl_np = to_np(fm_growl_raw)
    # LFO wobble — DNA rate and depth
    lfo_fg = generate_lfo(LFOPreset(
        name="FMLfo", lfo_type="sine", rate_hz=bd.lfo_rate,
        depth=bd.lfo_depth, polarity="unipolar", sync_bpm=float(dna.bpm),
        sync_division=2.0
    ), duration_s=BEAT * 2)
    fm_growl_np = fm_growl_np * (0.2 + 0.8 * lfo_fg[:len(fm_growl_np)])
    # Multiband distortion — DNA-driven mids
    fm_growl_np = apply_multiband_distortion(fm_growl_np, MultibandDistPreset(
        name="FMDist", dist_type="aggressive", low_drive=0.3,
        mid_drive=bd.mid_drive, high_drive=0.4,
        crossover_low=130.0, crossover_high=3000.0, output_gain=0.8
    ))
    fm_growl = to_list(fm_growl_np)
    fm_growl = _ott_simulate(fm_growl, bd.ott_amount)
    fm_growl = sat.saturate(fm_growl, SatConfig(
        sat_type="transistor", drive=bd.distortion * 0.78, mix=bd.distortion * 0.67))
    fm_growl = normalize(fm_growl, 0.88)

    # BASS 2: Growl Resampler — DNA fm_depth drives wavetable character
    print("    Growl Resampler wavetable...")
    growl_source = generate_fm_source(size=WAVETABLE_SIZE, fm_ratio=PHI,
                                       fm_depth=bd.fm_depth * 0.4)
    growl_frames = growl_resample_pipeline(growl_source, n_output_frames=256)
    growl_wt_np = _wavetable_to_audio(growl_frames, freq=FREQ["F2"],
                                       duration_s=BEAT * 2, sr=SR)
    growl_wt_np = apply_multiband_distortion(growl_wt_np, MultibandDistPreset(
        name="GrlWTDist", dist_type="tube", low_drive=0.4,
        mid_drive=bd.mid_drive, high_drive=0.3,
        crossover_low=120.0, crossover_high=2800.0, output_gain=0.82
    ))
    growl_wt = to_list(growl_wt_np)
    growl_wt = _ott_simulate(growl_wt, bd.ott_amount)
    growl_wt = sat.saturate(growl_wt, SatConfig(
        sat_type="tape", drive=bd.distortion * 0.67, mix=bd.distortion * 0.61))
    growl_wt = normalize(growl_wt, 0.87)

    # BASS 3: Dist FM — DNA distortion + filter
    print(f"    Dist FM (dist={bd.distortion:.2f})...")
    dist_fm = to_list(synthesize_bass(BassPreset(
        name="DistFM", bass_type="dist_fm", frequency=FREQ["F2"],
        duration_s=BEAT, fm_ratio=2.5, fm_depth=bd.fm_depth * 0.4,
        distortion=bd.distortion, filter_cutoff=bd.filter_cutoff
    )))
    dist_fm_np = to_np(dist_fm)
    dist_fm_np = apply_multiband_distortion(dist_fm_np, MultibandDistPreset(
        name="DFMDist", dist_type="aggressive", low_drive=0.25,
        mid_drive=bd.mid_drive, high_drive=0.4, output_gain=0.8
    ))
    dist_fm = to_list(dist_fm_np)
    dist_fm = _ott_simulate(dist_fm, bd.ott_amount)
    dist_fm = normalize(dist_fm, 0.86)

    # BASS 4: Sync bass — DNA lfo_rate drives sweep
    print("    Sync bass...")
    sync_bass = to_list(synthesize_bass(BassPreset(
        name="Sync", bass_type="sync", frequency=FREQ["F2"],
        duration_s=BEAT * 1.5, distortion=bd.distortion * 0.78,
        filter_cutoff=bd.filter_cutoff
    )))
    sync_np = to_np(sync_bass)
    lfo_sync = generate_lfo(LFOPreset(
        name="SyncLFO", lfo_type="triangle", rate_hz=bd.lfo_rate * 1.2,
        depth=bd.lfo_depth * 0.88, polarity="unipolar"
    ), duration_s=BEAT * 1.5)
    sync_np = sync_np * (0.3 + 0.7 * lfo_sync[:len(sync_np)])
    sync_np = apply_multiband_distortion(sync_np, MultibandDistPreset(
        name="SyncDist", dist_type="tube", low_drive=0.35,
        mid_drive=bd.mid_drive, high_drive=0.3, output_gain=0.82
    ))
    sync_bass = to_list(sync_np)
    sync_bass = _ott_simulate(sync_bass, bd.ott_amount * 0.88)
    sync_bass = sat.saturate(sync_bass, SatConfig(
        sat_type="transistor", drive=bd.distortion * 0.67, mix=0.5))
    sync_bass = normalize(sync_bass, 0.86)

    # BASS 5: Acid bass — DNA acid_resonance drives filter character
    print(f"    Acid bass (res={bd.acid_resonance:.2f})...")
    acid = to_list(synthesize_bass(BassPreset(
        name="Acid", bass_type="acid", frequency=FREQ["F2"],
        duration_s=BEAT * 2, distortion=bd.distortion * 0.72,
        filter_cutoff=bd.filter_cutoff * 1.12
    )))
    acid_np = to_np(acid)
    acid_np = apply_multiband_distortion(acid_np, MultibandDistPreset(
        name="AcidDist", dist_type="tube", low_drive=0.3,
        mid_drive=bd.mid_drive * 0.82, high_drive=0.2, output_gain=0.85
    ))
    acid = to_list(acid_np)
    acid = _ott_simulate(acid, bd.ott_amount * 0.75)
    acid = normalize(acid, 0.85)

    # BASS 6: Neuro — DNA fm_depth + lfo_rate for phase distortion chaos
    print(f"    Neuro bass (fm={bd.fm_depth:.1f})...")
    neuro = to_list(synthesize_bass(BassPreset(
        name="Neuro", bass_type="neuro", frequency=FREQ["F2"],
        duration_s=BEAT, fm_ratio=3.0, fm_depth=bd.fm_depth * 0.6,
        distortion=bd.distortion, filter_cutoff=bd.filter_cutoff * 0.88
    )))
    neuro_np = to_np(neuro)
    lfo_n = generate_lfo(LFOPreset(
        name="NroLFO", lfo_type="square", rate_hz=bd.lfo_rate * 1.6,
        depth=bd.lfo_depth * 0.94, polarity="unipolar", pulse_width=0.3
    ), duration_s=BEAT)
    neuro_np = neuro_np * (0.25 + 0.75 * lfo_n[:len(neuro_np)])
    neuro_np = apply_multiband_distortion(neuro_np, MultibandDistPreset(
        name="NroDist", dist_type="aggressive", low_drive=0.15,
        mid_drive=min(0.99, bd.mid_drive * 1.15),
        high_drive=0.5, crossover_low=100.0, crossover_high=3500.0,
        output_gain=0.75
    ))
    neuro = to_list(neuro_np)
    neuro = _ott_simulate(neuro, bd.ott_amount * 1.12)
    neuro = normalize(neuro, 0.86)

    # BASS 7: Formant "yoi" — DNA distortion + brightness
    print("    Formant bass...")
    formant_raw = synthesize_morph_formant(FormantPreset(
        name="Yoi", formant_type="morph", frequency=FREQ["F2"],
        duration_s=BEAT * 2, bandwidth=110.0,
        brightness=0.5 + bd.filter_cutoff * 0.38,
        distortion=bd.distortion * 0.44
    ))
    form_np = to_np(formant_raw)
    form_np = apply_multiband_distortion(form_np, MultibandDistPreset(
        name="FormDist", dist_type="tube", low_drive=0.4,
        mid_drive=bd.mid_drive * 0.88, high_drive=0.25, output_gain=0.82
    ))
    formant = to_list(form_np)
    formant = _ott_simulate(formant, bd.ott_amount * 0.88)
    formant = sat.saturate(formant, SatConfig(
        sat_type="tape", drive=bd.distortion * 0.56, mix=0.45))
    formant = normalize(formant, 0.84)

    # Pitch-dive variant — DNA pitch_dive_semi
    dive_raw = to_list(fm_growl)
    dive_np = to_np(dive_raw)
    dive_np = apply_pitch_automation(dive_np, PitchAutoPreset(
        name="BassDive", auto_type="dive", start_semitones=0.0,
        end_semitones=-bd.pitch_dive_semi, duration_s=BEAT * 2,
        curve_exp=3.0
    ), base_freq=FREQ["F2"])
    dive_bass = to_list(dive_np)
    dive_bass = normalize(dive_bass, 0.85)

    # Reese — detuned saws
    reese = to_list(synthesize_bass(BassPreset(
        name="Reese", bass_type="reese", frequency=FREQ["F2"],
        duration_s=BAR, detune_cents=25.0, filter_cutoff=0.35,
        attack_s=0.3, release_s=0.5
    )))
    reese = sat.warmth(reese, amount=0.5)
    reese = normalize(reese, 0.72)

    # Bass fills — DNA stutter_rate
    bass_repeat = apply_beat_repeat(dist_fm, BeatRepeatPatch(
        name="BassGlitch", grid="1/16", repeats=8, decay=0.15,
        pitch_shift=-3.0, reverse_probability=fd.beat_repeat_probability,
        gate=0.75
    ), bpm=float(dna.bpm))
    bass_repeat = normalize(bass_repeat, 0.7)

    # Arsenal for rotation
    bass_arsenal = [fm_growl, growl_wt, dist_fm, sync_bass, acid, neuro, formant]

    # ── Cutting-edge: wavefold + bitcrush if DNA demands it ──
    if bd.wavefold_thresh > 0.0 and bd.wavefold_thresh < 1.0:
        def _wavefold(sig, thresh):
            """Analog-style wavefolding — creates dense harmonics."""
            out = list(sig)
            inv_t = 1.0 / max(thresh, 0.01)
            for i in range(len(out)):
                x = out[i] * inv_t
                # Triangle-fold: keeps within [-1, 1] while adding harmonics
                x = 4 * abs((x / 4 + 0.25) % 1 - 0.5) - 1
                out[i] = x * thresh
            return out
        bass_arsenal = [_wavefold(b, bd.wavefold_thresh) for b in bass_arsenal]
        fm_growl = _wavefold(fm_growl, bd.wavefold_thresh)
        neuro = _wavefold(neuro, bd.wavefold_thresh)
        dist_fm = _wavefold(dist_fm, bd.wavefold_thresh)
        print(f"    wavefold @ {bd.wavefold_thresh:.2f} thresh")

    if bd.bitcrush_bits > 0:
        def _bitcrush(sig, bits):
            """Digital degradation — quantize to N bits."""
            levels = 2 ** bits
            out = list(sig)
            for i in range(len(out)):
                out[i] = round(out[i] * levels) / levels
            return out
        bass_arsenal = [_bitcrush(b, bd.bitcrush_bits) for b in bass_arsenal]
        fm_growl = _bitcrush(fm_growl, bd.bitcrush_bits)
        neuro = _bitcrush(neuro, bd.bitcrush_bits)
        dist_fm = _bitcrush(dist_fm, bd.bitcrush_bits)
        print(f"    bitcrush @ {bd.bitcrush_bits} bits")

    # ═══════════════════════════════════════════
    #  SOUND DESIGN — Leads (DNA-DRIVEN)
    # ═══════════════════════════════════════════
    print(f"  [3/9] Leads — {ld.additive_partials}p {ld.additive_rolloff} + FM...")

    # Lead maker — DNA-driven partial count, rolloff, FM depth
    def make_lead(freq, dur):
        ld_parts = []
        if ld.use_additive:
            add_patch = AdditivePatch(
                name="Lead",
                partials=harmonic_partials(ld.additive_partials, rolloff=ld.additive_rolloff),
                master_gain=0.7,
            )
            ld_parts.append(("add", render_additive(add_patch, freq=freq, duration=dur)))

        if ld.use_fm:
            fm_ops = [
                FMOperator(freq_ratio=1.0, amplitude=0.7, mod_index=ld.fm_depth,
                           feedback=0.15, envelope=(0.003, 0.1, 0.5, 0.15)),
                FMOperator(freq_ratio=PHI, amplitude=0.4, mod_index=ld.fm_depth * 0.67,
                           feedback=0.0, envelope=(0.005, 0.08, 0.3, 0.1)),
            ]
            if ld.fm_operators >= 3:
                fm_ops.append(FMOperator(
                    freq_ratio=PHI * 2, amplitude=0.2, mod_index=ld.fm_depth * 0.33,
                    feedback=0.05, envelope=(0.002, 0.06, 0.2, 0.08)))
            fm_ld = render_fm(FMPatch(
                name="LeadFM", operators=fm_ops,
                algorithm=0, master_gain=0.5,
            ), freq=freq, duration=dur)
            ld_parts.append(("fm", fm_ld))

        # Mix layers
        if len(ld_parts) == 2:
            mix_a, mix_b = 0.6, 0.4
        elif len(ld_parts) == 1:
            mix_a, mix_b = 1.0, 0.0
        else:
            mix_a, mix_b = 0.5, 0.5

        max_len = max(len(p[1]) for p in ld_parts) if ld_parts else 0
        ld_sig = [0.0] * max_len
        for idx_p, (_, sig) in enumerate(ld_parts):
            gain = mix_a if idx_p == 0 else mix_b
            for i in range(len(sig)):
                ld_sig[i] += sig[i] * gain

        # Process — DNA-driven OTT and brightness
        ld_sig = _ott_simulate(ld_sig, ld.ott_amount)
        ld_sig = sat.harmonic_exciter(ld_sig, amount=ld.brightness * 0.57, frequency=3500)
        ld_np = apply_reverb_delay(to_np(ld_sig), ReverbDelayPreset(
            name="LdVerb", effect_type="plate", decay_time=ld.reverb_decay,
            diffusion=0.75, damping=0.5, mix=0.18
        ))
        return to_list(ld_np)

    # Pre-render leads for ALL 7 scale degrees × 2 octaves (oct 3 & 4)
    # so DNA melody_patterns can reference any scale degree
    lead_notes = {}  # {(degree, octave): audio_list}
    for _deg in range(7):
        for _oct in [3, 4]:
            _freq = n(_deg, _oct)
            lead_notes[(_deg, _oct)] = make_lead(_freq, BEAT * 0.5)
    # Also pre-render longer variants for held notes
    lead_notes_long = {}
    for _deg in range(7):
        for _oct in [3, 4]:
            _freq = n(_deg, _oct)
            lead_notes_long[(_deg, _oct)] = make_lead(_freq, BEAT * 1.0)
    # Backwards-compat aliases
    lead_f = lead_notes[(0, 4)]
    lead_eb = lead_notes[(6, 3)]
    lead_c = lead_notes[(4, 3)]
    lead_ab = lead_notes[(2, 4)]

    # Pre-render chord stabs for all chord progression degrees
    chord_notes_l = {}
    chord_notes_r = {}

    # Supersaw chord stabs — DNA-driven voices + detune
    def make_chord(freq, dur=BEAT * 0.75):
        cl, cr = render_supersaw(SupersawPatch(
            name="Chord", n_voices=ld.supersaw_voices,
            detune_cents=ld.supersaw_detune, mix=0.8,
            stereo_width=0.9, cutoff_hz=ld.supersaw_cutoff,
            resonance=0.38, attack=0.003, decay=0.12,
            sustain=0.55, release=0.22, master_gain=0.72
        ), freq=freq, duration=dur)
        cl_np = apply_reverb_delay(to_np(cl), ReverbDelayPreset(
            name="ChVerb", effect_type="room", decay_time=ld.reverb_decay * 0.8,
            diffusion=0.6, damping=0.6, mix=0.12
        ))
        return to_list(cl_np), cr

    chord_f_l, chord_f_r = make_chord(FREQ["F3"])
    chord_ab_l, chord_ab_r = make_chord(FREQ["Ab3"])
    chord_c_l, chord_c_r = make_chord(FREQ["C3"])

    # Pre-render chords for all progression degrees
    _chord_prog = getattr(ld, 'chord_progression', [0, 5, 2, 4])
    for _cdeg in set(_chord_prog):
        _cfreq = n(_cdeg, 3)
        _cl, _cr = make_chord(_cfreq)
        chord_notes_l[_cdeg] = _cl
        chord_notes_r[_cdeg] = _cr

    # ═══════════════════════════════════════════
    #  SOUND DESIGN — Vocal chops (DNA-driven vowels)
    # ═══════════════════════════════════════════
    print(f"  [4/9] Vocal chops — {' '.join(dna.chop_vowels[:4])}...")

    # Map DNA vowels to chops
    _vowel_list = dna.chop_vowels if dna.chop_vowels else ["ah", "oh", "ee", "oo"]

    chop_ah = to_list(synthesize_chop(VocalChop(
        name=_vowel_list[0], vowel=_vowel_list[0], note=_root_note3,
        duration_s=0.2, distortion=fd.vocal_chop_distortion, stutter_count=0
    )))
    chop_ah = _ott_simulate(chop_ah, 0.3)
    chop_ah = normalize(chop_ah, 0.72)

    chop_oh = to_list(synthesize_chop(VocalChop(
        name=_vowel_list[1], vowel=_vowel_list[1], note=_fifth_note3,
        duration_s=0.15, distortion=fd.vocal_chop_distortion * 0.86,
        stutter_count=0
    )))
    chop_oh = normalize(chop_oh, 0.68)

    chop_ee_stut = to_list(synthesize_chop(VocalChop(
        name="stutter", vowel=_vowel_list[2] if len(_vowel_list) > 2 else "ee",
        note=_root_note3, duration_s=0.4,
        distortion=fd.vocal_chop_distortion * 1.14, stutter_count=4
    )))
    chop_ee_stut = normalize(chop_ee_stut, 0.72)

    _yoi_vowel = _vowel_list[3] if len(_vowel_list) > 3 else "oo"
    chop_yoi = to_list(synthesize_chop(VocalChop(
        name="yoi", vowel=_yoi_vowel, note=_root_note3,
        duration_s=0.3, formant_shift=3.0,
        distortion=fd.vocal_chop_distortion, stutter_count=2
    )))
    chop_yoi_np = apply_reverb_delay(to_np(chop_yoi), ReverbDelayPreset(
        name="ChopVerb", effect_type="plate", decay_time=0.3, mix=0.15
    ))
    chop_yoi = to_list(chop_yoi_np)
    chop_yoi = normalize(chop_yoi, 0.72)

    vocal_chops = [chop_ah, chop_oh, chop_ee_stut, chop_yoi]

    # ═══════════════════════════════════════════
    #  SOUND DESIGN — Pads & atmosphere (DNA-driven)
    # ═══════════════════════════════════════════
    print(f"  [5/9] Pads — {ad.pad_type} pad, verb={ad.reverb_decay:.1f}s...")

    # Pad — DNA-driven type, attack, brightness
    pad_add = render_additive(AdditivePatch(
        name="DarkPad", partials=phi_partials(12, base_amp=0.6),
        master_gain=0.5,
    ), freq=FREQ["F3"], duration=BAR * 8)

    _pad_synth = synthesize_dark_pad if ad.pad_type == "dark" else synthesize_lush_pad
    dark_pad_raw = to_list(_pad_synth(PadPreset(
        name="DP", pad_type=ad.pad_type, frequency=FREQ["F3"],
        duration_s=BAR * 8, detune_cents=18.0,
        filter_cutoff=ad.pad_brightness + 0.05,
        attack_s=ad.pad_attack, release_s=ad.pad_attack * 1.5,
        brightness=ad.pad_brightness
    )))

    gran_tex = to_list(synthesize_cloud(GranularPreset(
        name="Tex", grain_type="cloud", frequency=FREQ["F3"],
        duration_s=BAR * 8, grain_size_ms=90.0,
        grain_density=ad.granular_density,
        pitch_spread=5.0, brightness=ad.pad_brightness + 0.05,
        reverb_amount=0.5
    )))

    # Mix — DNA stereo_width drives the blend
    pad_len = min(len(dark_pad_raw), len(gran_tex), len(pad_add))
    dark_pad = [0.0] * pad_len
    for i in range(pad_len):
        dark_pad[i] = dark_pad_raw[i] * 0.4 + gran_tex[i] * 0.3 + pad_add[i] * 0.3

    _pad_verb_type = "shimmer" if ad.shimmer > 0.3 else "hall"
    pad_np = apply_reverb_delay(to_np(dark_pad), ReverbDelayPreset(
        name="PadShim", effect_type=_pad_verb_type,
        decay_time=ad.reverb_decay,
        pre_delay_ms=35.0, diffusion=0.9, damping=0.35,
        shimmer_pitch=12.0 if ad.shimmer > 0.3 else 0.0,
        shimmer_feedback=ad.shimmer if ad.shimmer > 0.3 else 0.0,
        mix=0.35
    ))
    dark_pad = to_list(pad_np)
    dark_pad = normalize(dark_pad, 0.6)

    # Drone — DNA voices + movement + Karplus-Strong option
    drone_parts = []
    if ad.use_karplus_drone:
        drone_ks = render_ks(KarplusStrongPatch(
            frequency=FREQ["F1"], duration=BAR * INTRO,
            damping=0.2, brightness=ad.pad_brightness + 0.05,
            stretch=0.05, feedback=0.999, noise_mix=0.7
        ))
        drone_parts.append((drone_ks, 0.35))

    drone_synth_sig = to_list(synthesize_dark_drone(DronePreset(
        name="Drone", drone_type="dark", frequency=FREQ["F1"],
        duration_s=BAR * INTRO, num_voices=ad.drone_voices,
        detune_cents=12.0, brightness=ad.pad_brightness,
        movement=ad.drone_movement, distortion=0.15,
        reverb_amount=0.55
    )))
    drone_parts.append((drone_synth_sig, 0.65 if ad.use_karplus_drone else 1.0))

    drone_len = min(len(p[0]) for p in drone_parts)
    drone = [0.0] * drone_len
    for sig, gain in drone_parts:
        for i in range(drone_len):
            drone[i] += sig[i] * gain if i < len(sig) else 0.0
    drone = normalize(drone, 0.45)

    # Breakdown pad — DNA atmosphere personality
    _break_type = "lush" if ad.pad_type == "dark" else "dark"
    _break_synth = synthesize_lush_pad if _break_type == "lush" else synthesize_dark_pad
    lush = to_list(_break_synth(PadPreset(
        name="LP", pad_type=_break_type, frequency=FREQ["Ab3"],
        duration_s=BAR * BREAK_, filter_cutoff=ad.pad_brightness + 0.3,
        brightness=ad.pad_brightness + 0.3,
        attack_s=ad.pad_attack * 0.25, release_s=ad.pad_attack
    )))
    lush_np = apply_reverb_delay(to_np(lush), ReverbDelayPreset(
        name="LushVerb", effect_type="hall",
        decay_time=ad.reverb_decay * 0.8,
        diffusion=0.88, damping=0.35, mix=0.3
    ))
    lush = to_list(lush_np)
    lush = normalize(lush, 0.55)

    # Noise bed — DNA type and level
    drop_noise_raw = to_list(synthesize_noise(NoisePreset(
        name="DropNoise", noise_type=ad.noise_bed_type,
        duration_s=BAR * 4, brightness=0.3,
        gain=ad.noise_bed_level * 2.33
    )))
    drop_noise = apply_eq_band(drop_noise_raw, center_hz=8000.0, gain_db=3.0, q=0.3)
    drop_noise = apply_eq_band(drop_noise, center_hz=200.0, gain_db=-6.0, q=0.5)
    drop_noise = normalize(drop_noise, 0.30)

    # ═══════════════════════════════════════════
    #  SOUND DESIGN — Transition FX (DNA-driven)
    # ═══════════════════════════════════════════
    print(f"  [6/9] Transition FX — riser {fd.riser_start_freq:.0f}→{fd.riser_end_freq:.0f}Hz...")

    _riser_bars = max(BUILD, BUILD2, 8)
    riser = to_list(synthesize_noise_sweep(RiserPreset(
        name="Riser", riser_type="noise_sweep", duration_s=BAR * _riser_bars,
        start_freq=fd.riser_start_freq, end_freq=fd.riser_end_freq,
        brightness=0.8, intensity=fd.riser_intensity, reverb_amount=0.3
    )))
    riser = normalize(riser, fd.riser_intensity * 0.88)

    boom = to_list(synthesize_sub_boom(ImpactPreset(
        name="Boom", impact_type="sub_boom", duration_s=fd.boom_decay + 0.5,
        frequency=FREQ["F1"], decay_s=fd.boom_decay,
        intensity=fd.impact_intensity
    )))
    boom = compress(boom, CompressorSettings(
        threshold_db=-4.0, ratio=10.0, attack_ms=0.3, release_ms=80.0, makeup_db=4.0
    ))
    boom = normalize(boom, fd.impact_intensity * 1.02)

    hit = to_list(synthesize_cinematic_hit(ImpactPreset(
        name="Hit", impact_type="cinematic_hit", duration_s=2.0,
        frequency=FREQ["F1"] * 2, decay_s=1.5,
        intensity=fd.impact_intensity
    )))
    hit_np = apply_reverb_delay(to_np(hit), ReverbDelayPreset(
        name="HitVerb", effect_type="plate", decay_time=1.2,
        diffusion=0.8, mix=0.22
    ))
    hit = to_list(hit_np)
    hit = normalize(hit, fd.impact_intensity * 0.92)

    tape_stop = to_list(synthesize_transition(TransitionPreset(
        name="TapeStop", fx_type="tape_stop", duration_s=0.8,
        start_freq=fd.riser_start_freq * 2, end_freq=30.0, brightness=0.6
    )))
    tape_stop = normalize(tape_stop, fd.impact_intensity * 0.68)

    pitch_dive = to_list(synthesize_transition(TransitionPreset(
        name="Dive", fx_type="pitch_dive", duration_s=1.5,
        start_freq=fd.riser_start_freq * 3.33, end_freq=25.0,
        brightness=0.5, reverb_amount=0.2
    )))
    pitch_dive = normalize(pitch_dive, fd.impact_intensity * 0.63)

    rev_crash = to_list(synthesize_transition(TransitionPreset(
        name="RevCrash", fx_type="reverse_crash", duration_s=2.0,
        brightness=fd.riser_intensity * 0.82, reverb_amount=0.3
    )))
    rev_crash = normalize(rev_crash, fd.riser_intensity * 0.65)

    stutter = to_list(synthesize_stutter(GlitchPreset(
        name="Stut", glitch_type="stutter", frequency=FREQ["F3"],
        duration_s=BEAT * 2, rate=fd.stutter_rate,
        depth=0.9, distortion=fd.vocal_chop_distortion * 0.8
    )))
    stutter = normalize(stutter, fd.impact_intensity * 0.68)

    gate_chop = to_list(synthesize_transition(TransitionPreset(
        name="GateChop", fx_type="gate_chop", duration_s=BAR * 2,
        gate_divisions=int(fd.stutter_rate), brightness=0.5
    )))
    gate_chop = normalize(gate_chop, fd.riser_intensity * 0.53)

    # ═══════════════════════════════════════════
    #  GROOVE — Grooved hat patterns
    # ═══════════════════════════════════════════
    print("  [7/9] Groove patterns...")

    def make_hat_events_bar():
        events = []
        _hat_steps = getattr(dd, 'hat_density', 16)
        for i in range(_hat_steps):
            vel = 0.6 + 0.3 * ((i % 4) == 0)
            if i % 4 == 2:
                vel *= 0.7
            events.append(NoteEvent(
                time=i * (BAR / _hat_steps),
                duration=0.03, pitch=42, velocity=vel
            ))
        grooved = groove_eng.apply_groove(
            events, GROOVE_TEMPLATES.get("dubstep_halftime")
        )
        grooved = groove_eng.humanize(grooved, timing_ms=5, velocity_pct=8)
        return grooved

    hat_pattern = make_hat_events_bar()

    # ═══════════════════════════════════════════
    #  ARRANGEMENT
    # ═══════════════════════════════════════════
    print("  [8/9] Arranging...")

    L = [0.0] * total_s
    R = [0.0] * total_s

    def mx(mono, offset, gl=0.7, gr=0.7):
        mix_into(L, mono, offset, gl)
        mix_into(R, mono, offset, gr)

    def mx_stereo(left, right, offset, gain=1.0):
        mix_into(L, left, offset, gain)
        mix_into(R, right, offset, gain)

    def mx_wide(mono, offset, gain=0.7, delay_ms=18.0):
        st = panner.haas_delay(mono, delay_ms=delay_ms, side="right")
        mix_into(L, st.left, offset, gain)
        mix_into(R, st.right, offset, gain * 0.92)

    def mx_panned(mono, offset, gain, pan):
        st = panner.pan_constant_power(mono, position=pan)
        mix_into(L, st.left, offset, gain)
        mix_into(R, st.right, offset, gain)

    cursor = 0

    # ══════════════════════════════════════════════════
    #  INTRO (8 bars)
    # ══════════════════════════════════════════════════
    print("  Intro...")

    drone_st = panner.haas_delay(drone[:samples(INTRO * 4)], delay_ms=18.0)
    mx_stereo(drone_st.left, drone_st.right, cursor, 0.20)

    ip = dark_pad[:samples(INTRO * 4)]
    ip = fade_in(ip, BAR * 5)
    ip = lowpass(ip, 0.12)
    mx(ip, cursor, 0.18, 0.18)

    # Track kick positions for post-arrangement sidechain (collect from ALL sections)
    kick_positions = []

    for bar in range(INTRO):
        off = cursor + samples(bar * 4)
        if bar >= 4:
            k_vol = 0.10 + (bar - 4) * 0.04
            mx(kick, off, k_vol, k_vol)
            kick_positions.append(off)
        if bar >= 6:
            for ev in hat_pattern:
                h_vol = 0.08 + (bar - 6) * 0.03
                mx_panned(hat_c, off + int(ev.time * SR), h_vol * ev.velocity, -0.15)
            # Open hat every 4 beats for groove (M9)
            if bar % 2 == 0:
                mx_panned(hat_o, off + samples(1.5), 0.06 + (bar - 6) * 0.01, 0.25)

    ir = reese[:samples(INTRO * 4)]
    ir = lowpass(ir, 0.05)
    ir = fade_in(ir, BAR * 5)
    mx(ir, cursor, 0.10, 0.10)

    mx_wide(rev_crash, cursor + samples((INTRO - 2) * 4), 0.25)

    cursor += samples(INTRO * 4)

    # ══════════════════════════════════════════════════
    #  BUILD (8 bars) — accelerating tension
    # ══════════════════════════════════════════════════
    print("  Build...")

    for bar in range(BUILD):
        off = cursor + samples(bar * 4)
        k_vol = 0.35 + 0.15 * (bar / max(BUILD - 1, 1))
        mx(kick, off, k_vol, k_vol)
        kick_positions.append(off)
        mx(kick, off + samples(2), k_vol, k_vol)
        kick_positions.append(off + samples(2))
        # Progressive snare roll: 2→4→4→8→8→16→16→32
        divs_seq = [2, 4, 4, 8, 8, 16, 16, 32]
        divs = divs_seq[min(bar, len(divs_seq) - 1)]
        step = 4.0 / divs
        for h in range(divs):
            vel = 0.12 + 0.55 * (bar / max(BUILD, 1)) * (h / max(divs, 1))
            pan = -0.25 + 0.5 * ((h % 6) / 6)
            mx_panned(snare, off + samples(h * step), vel, pan)

    r_seg = riser[:samples(BUILD * 4)]
    mx_wide(r_seg, cursor, 0.55)

    gc_seg = gate_chop[:samples(BUILD * 4)]
    mx(gc_seg, cursor, 0.2, 0.2)

    bp = dark_pad[:samples(BUILD * 4)]
    mx(bp, cursor, 0.30, 0.30)

    mx_wide(chop_ee_stut, cursor + samples(3 * 4), 0.35)

    cursor += samples(BUILD * 4)

    # ══════════════════════════════════════════════════
    #  DROP 1 (16 bars)
    # ══════════════════════════════════════════════════
    print("  Drop 1...")

    mx(boom, cursor, 0.85, 0.85)
    mx(hit, cursor, 0.7, 0.7)

    for bar in range(DROP1):
        off = cursor + samples(bar * 4)

        # Drums — balanced gains
        kick_positions.append(off)
        mx(kick, off, 0.88, 0.88)
        mx(snare, off + samples(2), 0.82, 0.82)
        mx(clap, off + samples(2), 0.38, 0.38)

        for ev in hat_pattern:
            h_vol = 0.45 * ev.velocity  # Hats UP for hi-freq presence
            h_pan = -0.4 + 0.8 * (ev.time / BAR)  # Wider panning
            mx_panned(hat_c, off + int(ev.time * SR), h_vol, h_pan)

        mx_panned(hat_o, off + samples(1.5), 0.35, 0.35)
        mx_panned(hat_o, off + samples(3.5), 0.35, -0.35)

        # Sub — proper dubstep level
        sub_sc = sidechain(sub, depth=0.85, release=0.2, bpm=dna.bpm)
        mx(sub_sc, off, 0.35, 0.35)
        mx(sub_sc, off + samples(2), 0.28, 0.28)

        # Noise bed — air and width
        dn = drop_noise[:min(samples(4), len(drop_noise))]
        mx_wide(dn, off, 0.40, 20.0)

        # Pad atmosphere in drops (sustained harmonic content)
        _pad_seg = dark_pad[: min(samples(4), len(dark_pad))]
        mx_wide(_pad_seg, off, 0.18)

        # Mid bass — DNA bass_riff drives pitch + timbre rotation
        _bass_riff = getattr(bd, 'bass_riff', None)
        bass_idx = bar % 7
        bass_snd = bass_arsenal[bass_idx]

        # Get pitch shift from bass_riff pattern
        _bass_semi = 0
        if _bass_riff and len(_bass_riff) > 0:
            _riff_pat = _bass_riff[bar % len(_bass_riff)]
            if _riff_pat:
                # Use first note's degree for the main bass pitch
                _bdeg = _riff_pat[0][0]  # scale degree
                _bass_semi = intervals[_bdeg % len(intervals)]

        if bass_idx in (0, 1):
            # FM growl or Wavetable growl — full 2-beat phrase
            _b = pitch_shift_bass(bass_snd, _bass_semi) if _bass_semi else bass_snd
            mx_wide(_b, off + samples(0.5), 0.88)
            _d = pitch_shift_bass(dist_fm, _bass_semi) if _bass_semi else dist_fm
            mx_wide(_d, off + samples(2.5), 0.82)
        elif bass_idx == 2:
            # Dist FM — staccato 8ths with pitch variation per note
            _riff_notes = _bass_riff[bar % len(_bass_riff)] if _bass_riff else [(0, i*0.5, 0.5) for i in range(8)]
            for s8 in range(min(8, len(_riff_notes))):
                _rdeg = _riff_notes[s8 % len(_riff_notes)][0]
                _rsemi = intervals[_rdeg % len(intervals)]
                _b = pitch_shift_bass(bass_snd, _rsemi) if _rsemi else bass_snd
                mx_panned(_b, off + samples(s8 * 0.5), 0.75, -0.2 + 0.4 * (s8 / 8))
        elif bass_idx == 3:
            # Sync bass — swept harmonics
            _b = pitch_shift_bass(bass_snd, _bass_semi) if _bass_semi else bass_snd
            mx_wide(_b, off + samples(0.5), 0.88, 15.0)
        elif bass_idx == 4:
            # Acid — filter sweep
            _b = pitch_shift_bass(bass_snd, _bass_semi) if _bass_semi else bass_snd
            mx_wide(_b, off + samples(0.5), 0.85)
            # Pitch dive on beat 3
            mx_wide(pitch_dive, off + samples(2), 0.48)
        elif bass_idx == 5:
            # Neuro — choppy with pitch variation
            _riff_notes = _bass_riff[bar % len(_bass_riff)] if _bass_riff else [(0, i*0.5, 0.5) for i in range(8)]
            for s16 in range(8):
                b = neuro if s16 % 2 == 0 else dist_fm
                _rdeg = _riff_notes[s16 % len(_riff_notes)][0]
                _rsemi = intervals[_rdeg % len(intervals)]
                b = pitch_shift_bass(b, _rsemi) if _rsemi else b
                mx_panned(b, off + samples(s16 * 0.5), 0.68, -0.25 + 0.5 * (s16 / 8))
        elif bass_idx == 6:
            # Formant — talking bass "yoi"
            mx_wide(bass_snd, off + samples(0.5), 0.88, 14.0)

        # Vocal chops (every 4 bars) — louder for mid presence
        if bar % 4 == 0:
            chop = vocal_chops[bar // 4 % len(vocal_chops)]
            mx_wide(chop, off, 0.75)
        if bar % 4 == 2:
            mx_panned(chop_oh, off + samples(2), 0.55, 0.35)

        # Lead — DNA-driven melody patterns (varied per bar, per song)
        _melody_pats = getattr(ld, 'melody_patterns', None)
        if _melody_pats and len(_melody_pats) > 0:
            _phrase_len = getattr(ld, 'phrase_length', 4)
            _pat_idx = (bar // _phrase_len) % len(_melody_pats)
            _pattern = _melody_pats[_pat_idx]
            for (deg, bt, dur, vel) in _pattern:
                _oct = 4 if deg >= 4 else 3
                _lnote = lead_notes_long if dur > 0.6 else lead_notes
                _key = (deg % 7, _oct)
                if _key in _lnote:
                    _pan = -0.35 + 0.20 * math.sin(bar * 0.5 + bt * 0.3)
                    mx_panned(_lnote[_key], off + samples(bt), 0.82 * vel, _pan)
        else:
            # Fallback to original 4-note pattern
            notes = [(lead_f, 0.0), (lead_eb, 1.0), (lead_c, 2.0), (lead_ab, 3.0)]
            for snd, bt in notes:
                mx_panned(snd, off + samples(bt), 0.82, 0.30 + 0.20 * math.sin(bar * 0.5))

        # Chords — DNA chord progression (rotates every 4 bars)
        if bar % 4 == 0:
            _cprog = getattr(ld, 'chord_progression', [0, 5, 2, 4])
            _cidx = (bar // 4) % len(_cprog)
            _cdeg = _cprog[_cidx]
            _cl = chord_notes_l.get(_cdeg, chord_f_l)
            _cr = chord_notes_r.get(_cdeg, chord_f_r)
            mx_stereo(_cl, _cr, off, 0.70)

        # Crash cymbal on phrase starts (every 4 bars)
        if bar % 4 == 0 and bar > 0:
            _crash = synthesize_noise(NoisePreset(
                name="Crash", noise_type="white", duration_s=BEAT * 3,
                attack_s=0.001, release_s=0.8, brightness=0.9, gain=0.7
            ))
            _crash_np = to_np(_crash)
            # HP filter at 6kHz to make it cymbal-like
            _crash_np = svf_highpass(_crash_np, 6000.0, 0.7, SR)
            _crash = normalize(to_list(_crash_np), 0.55)
            mx_wide(_crash, off, 0.48, 25.0)

        # Drum fill at phrase boundaries (bar 3, 7, 11, 15) — accelerating 16th-note rolls
        if bar % 4 == 3:
            _fill_positions = [2.0, 2.25, 2.5, 2.625, 2.75, 2.875, 3.0, 3.0625, 3.125, 3.25, 3.5]
            for _fi, _fp in enumerate(_fill_positions):
                _fv = 0.40 + 0.05 * _fi
                mx(snare, off + samples(_fp), _fv, _fv)
            for _fill_i in range(8):
                mx_panned(hat_c, off + samples(2 + _fill_i * 0.25), 0.35, -0.4 + 0.8 * (_fill_i / 8))

    mx(tape_stop, cursor + samples((DROP1 - 1) * 4 + 2), 0.5, 0.5)
    mx_wide(stutter, cursor + samples((DROP1 - 1) * 4 + 2), 0.35)
    mx(bass_repeat, cursor + samples((DROP1 - 1) * 4), 0.50, 0.50)

    cursor += samples(DROP1 * 4)

    # ══════════════════════════════════════════════════
    #  BREAKDOWN (8 bars) — stripped back
    # ══════════════════════════════════════════════════
    print("  Breakdown...")

    mx(pitch_dive, cursor - samples(1), 0.4, 0.4)

    bp = lush[:samples(BREAK_ * 4)]
    bp = fade_in(bp, BAR * 1.5)
    bp = fade_out(bp, BAR * 2)
    bp_st = panner.haas_delay(bp, delay_ms=14.0, side="right")
    mx_stereo(bp_st.left, bp_st.right, cursor, 0.25)

    # Karplus-Strong pluck arps — physical modeled
    pluck_freqs = [FREQ["F3"], FREQ["Ab3"], FREQ["C4"], FREQ["Eb4"]]
    for bar in range(BREAK_):
        off = cursor + samples(bar * 4)
        for q in range(4):
            freq = pluck_freqs[(bar + q) % 4]
            # Karplus-Strong pluck instead of basic lead_synth
            plk = render_ks(KarplusStrongPatch(
                frequency=freq, duration=BEAT * 0.8,
                damping=0.4, brightness=0.65, stretch=0.0,
                feedback=0.992, noise_mix=0.9, pluck_position=0.3
            ))
            plk_np = apply_reverb_delay(to_np(plk), ReverbDelayPreset(
                name="PlkDly", effect_type="delay", decay_time=0.5,
                bpm=float(dna.bpm), delay_feedback=0.35, num_taps=3, mix=0.22
            ))
            plk = to_list(plk_np)
            pan = -0.45 + 0.9 * (q / 3)
            mx_panned(plk, off + samples(q), 0.22, pan)

        for q in range(4):
            mx_panned(hat_c, off + samples(q), 0.04, -0.2 + 0.4 * (q / 3))

    sd = to_list(synthesize_bass(BassPreset(
        name="SD", bass_type="sub_sine", frequency=FREQ["F1"],
        duration_s=BREAK_ * BAR, attack_s=1.5, release_s=2.5
    )))
    sd = normalize(sd, 0.65)
    mx(sd, cursor, 0.18, 0.18)

    mx_wide(rev_crash, cursor + samples((BREAK_ - 2) * 4), 0.35)

    cursor += samples(BREAK_ * 4)

    # ══════════════════════════════════════════════════
    #  BUILD 2 (4 bars)
    # ══════════════════════════════════════════════════
    print("  Build 2...")

    for bar in range(BUILD2):
        off = cursor + samples(bar * 4)
        k_vol = 0.40 + 0.15 * (bar / max(BUILD2 - 1, 1))
        mx(kick, off, k_vol, k_vol)
        kick_positions.append(off)
        mx(kick, off + samples(2), k_vol, k_vol)
        kick_positions.append(off + samples(2))
        divs_seq = [2, 4, 4, 8, 8, 16, 16, 32]
        divs = divs_seq[min(bar, len(divs_seq) - 1)]
        step = 4.0 / divs
        for h in range(divs):
            vel = 0.15 + 0.55 * (bar / max(BUILD2, 1)) * (h / max(divs, 1))
            pan = -0.3 + 0.6 * ((h % 6) / 6)
            mx_panned(snare, off + samples(h * step), vel, pan)

    r2 = riser[:samples(BUILD2 * 4)]
    mx_wide(r2, cursor, 0.6)

    swell_l, swell_r = render_supersaw(SupersawPatch(
        name="Swell", n_voices=ld.supersaw_voices,
        detune_cents=ld.supersaw_detune, mix=0.8,
        stereo_width=md.stereo_width * 0.61,
        cutoff_hz=ld.supersaw_cutoff * 0.64, resonance=0.42,
        attack=2.5, decay=0.1, sustain=0.9, release=0.5,
        master_gain=0.5
    ), freq=FREQ["F3"], duration=BAR * BUILD2)
    seg_l = swell_l[:samples(BUILD2 * 4)]
    seg_r = swell_r[:samples(BUILD2 * 4)]
    mx_stereo(seg_l, seg_r, cursor, 0.42)

    gc2 = gate_chop[:samples(BUILD2 * 4)]
    mx(gc2, cursor, 0.22, 0.22)

    mx_wide(chop_ee_stut, cursor + samples(3 * 4), 0.4)

    cursor += samples(BUILD2 * 4)

    # ══════════════════════════════════════════════════
    #  DROP 2 (16 bars) — MAXIMUM ENERGY — DISTINCT from Drop 1
    # ══════════════════════════════════════════════════
    print("  Drop 2...")

    mx(boom, cursor, 0.90, 0.90)
    mx(hit, cursor, 0.75, 0.75)
    mx(clap, cursor, 0.50, 0.50)

    for bar in range(DROP2):
        off = cursor + samples(bar * 4)

        # Heavier drums — collect kick positions for sidechain
        kick_positions.append(off)
        mx(kick, off, 0.92, 0.92)
        mx(snare, off + samples(2), 0.88, 0.88)
        mx(clap, off + samples(2), 0.42, 0.42)

        for ev in hat_pattern:
            h_vol = 0.48 * ev.velocity  # Brighter hats
            h_pan = -0.45 + 0.9 * (ev.time / BAR)  # Even wider
            mx_panned(hat_c, off + int(ev.time * SR), h_vol, h_pan)

        mx_panned(hat_o, off + samples(1.5), 0.38, 0.38)
        mx_panned(hat_o, off + samples(3.5), 0.38, -0.38)

        # Sub — proper dubstep level (Drop 2 slightly hotter)
        sub_sc = sidechain(sub, depth=0.88, release=0.18, bpm=dna.bpm)
        mx(sub_sc, off, 0.38, 0.38)
        mx(sub_sc, off + samples(2), 0.30, 0.30)

        # Noise bed — wider
        dn = drop_noise[:min(samples(4), len(drop_noise))]
        mx_wide(dn, off, 0.42, 22.0)

        # Pad atmosphere in drops (sustained harmonic content)
        _pad_seg = dark_pad[: min(samples(4), len(dark_pad))]
        mx_wide(_pad_seg, off, 0.20)

        # Mid bass — 8 patterns, more aggressive, HIGHER gains, DNA pitch variation
        _bass_riff = getattr(bd, 'bass_riff', None)
        bass_idx = bar % 8
        _bass_semi = 0
        if _bass_riff and len(_bass_riff) > 0:
            _riff_pat = _bass_riff[bar % len(_bass_riff)]
            if _riff_pat:
                _bdeg = _riff_pat[0][0]
                _bass_semi = intervals[_bdeg % len(intervals)]

        if bass_idx in (0, 7):
            # Double-time mixed bass 16ths with pitch variation
            bass_pool = [neuro, dist_fm, fm_growl, growl_wt, sync_bass]
            _riff_notes = _bass_riff[bar % len(_bass_riff)] if _bass_riff else [(0, i*0.25, 0.25) for i in range(16)]
            for s16 in range(16):
                b = bass_pool[s16 % len(bass_pool)]
                _rdeg = _riff_notes[s16 % len(_riff_notes)][0]
                _rsemi = intervals[_rdeg % len(intervals)]
                b = pitch_shift_bass(b, _rsemi) if _rsemi else b
                mx_panned(b, off + samples(s16 * 0.25), 0.68, -0.3 + 0.6 * (s16 / 16))
        elif bass_idx == 1:
            _b = pitch_shift_bass(formant, _bass_semi) if _bass_semi else formant
            mx_wide(_b, off + samples(0.5), 0.92, 14.0)
            mx_wide(pitch_dive, off + samples(2.5), 0.48)
        elif bass_idx == 2:
            _riff_notes = _bass_riff[bar % len(_bass_riff)] if _bass_riff else [(0, i*0.5, 0.5) for i in range(8)]
            for s8 in range(8):
                _rdeg = _riff_notes[s8 % len(_riff_notes)][0]
                _rsemi = intervals[_rdeg % len(intervals)]
                _b = pitch_shift_bass(dist_fm, _rsemi) if _rsemi else dist_fm
                mx_panned(_b, off + samples(s8 * 0.5), 0.78, -0.25 + 0.5 * (s8 / 8))
        elif bass_idx == 3:
            _b = pitch_shift_bass(growl_wt, _bass_semi) if _bass_semi else growl_wt
            mx_wide(_b, off + samples(0.5), 0.90)
        elif bass_idx == 4:
            _b = pitch_shift_bass(dive_bass, _bass_semi) if _bass_semi else dive_bass
            mx_wide(_b, off + samples(0.5), 0.85)
        elif bass_idx == 5:
            _riff_notes = _bass_riff[bar % len(_bass_riff)] if _bass_riff else [(0, i*0.5, 0.5) for i in range(8)]
            for s16 in range(8):
                b = sync_bass if s16 % 2 == 0 else acid
                _rdeg = _riff_notes[s16 % len(_riff_notes)][0]
                _rsemi = intervals[_rdeg % len(intervals)]
                b = pitch_shift_bass(b, _rsemi) if _rsemi else b
                mx_panned(b, off + samples(s16 * 0.5), 0.72, -0.2 + 0.4 * (s16 / 8))
        elif bass_idx == 6:
            _b1 = pitch_shift_bass(fm_growl, _bass_semi) if _bass_semi else fm_growl
            mx_wide(_b1, off + samples(0.5), 0.82)
            _b2 = pitch_shift_bass(neuro, _bass_semi) if _bass_semi else neuro
            mx_wide(_b2, off + samples(2.5), 0.78)

        # Vocal chops (more frequent) — MAX
        if bar % 2 == 0:
            chop = vocal_chops[bar // 2 % len(vocal_chops)]
            mx_wide(chop, off, 0.60)
        if bar % 4 == 3:
            mx_panned(chop_yoi, off + samples(2), 0.52, -0.25)

        # Lead — DNA-driven melody (uses SECOND HALF of patterns for Drop 2)
        _melody_pats = getattr(ld, 'melody_patterns', None)
        if _melody_pats and len(_melody_pats) > 0:
            _phrase_len = getattr(ld, 'phrase_length', 4)
            # Offset pattern index so Drop 2 uses different patterns than Drop 1
            _n_pats = len(_melody_pats)
            _pat_idx = (_n_pats // 2 + (bar // _phrase_len)) % _n_pats
            _pattern = _melody_pats[_pat_idx]
            for (deg, bt, dur, vel) in _pattern:
                _oct = 4 if deg >= 4 else 3
                _lnote = lead_notes_long if dur > 0.6 else lead_notes
                _key = (deg % 7, _oct)
                if _key in _lnote:
                    _pan = -0.40 + 0.22 * math.sin(bar * 0.9 + bt * 0.4)
                    mx_panned(_lnote[_key], off + samples(bt), 0.85 * vel, _pan)
        else:
            notes_d2 = [(lead_ab, 0.0), (lead_c, 1.0), (lead_eb, 2.0), (lead_f, 3.0)]
            for snd, bt in notes_d2:
                mx_panned(snd, off + samples(bt), 0.85, -0.35 + 0.20 * math.sin(bar * 0.9))

        # Chords — DNA progression (rotates every 2 bars in Drop 2)
        if bar % 2 == 0:
            _cprog = getattr(ld, 'chord_progression', [0, 5, 2, 4])
            _cidx = (bar // 2) % len(_cprog)
            _cdeg = _cprog[_cidx]
            _cl = chord_notes_l.get(_cdeg, chord_f_l)
            _cr = chord_notes_r.get(_cdeg, chord_f_r)
            mx_stereo(_cl, _cr, off, 0.72)

        # Crash cymbal on phrase starts (every 4 bars)
        if bar % 4 == 0 and bar > 0:
            _crash = synthesize_noise(NoisePreset(
                name="Crash", noise_type="white", duration_s=BEAT * 3,
                attack_s=0.001, release_s=0.8, brightness=0.9, gain=0.7
            ))
            _crash_np = to_np(_crash)
            _crash_np = svf_highpass(_crash_np, 6000.0, 0.7, SR)
            _crash = normalize(to_list(_crash_np), 0.55)
            mx_wide(_crash, off, 0.50, 25.0)

        # Drum fill at phrase boundaries (bar 3, 7, 11, 15) — accelerating 16th-note rolls
        if bar % 4 == 3:
            _fill_positions = [2.0, 2.25, 2.5, 2.625, 2.75, 2.875, 3.0, 3.0625, 3.125, 3.25, 3.5]
            for _fi, _fp in enumerate(_fill_positions):
                _fv = 0.42 + 0.05 * _fi
                mx(snare, off + samples(_fp), _fv, _fv)
            for _fill_i in range(8):
                mx_panned(hat_c, off + samples(2 + _fill_i * 0.25), 0.38, -0.5 + 1.0 * (_fill_i / 8))

    mx(tape_stop, cursor + samples((DROP2 - 1) * 4 + 2), 0.55, 0.55)
    mx_wide(stutter, cursor + samples((DROP2 - 2) * 4), 0.35)
    mx_wide(stutter, cursor + samples((DROP2 - 1) * 4), 0.4)
    mx(bass_repeat, cursor + samples((DROP2 - 1) * 4 + 2), 0.50, 0.50)

    cursor += samples(DROP2 * 4)

    # ══════════════════════════════════════════════════
    #  OUTRO (8 bars)
    # ══════════════════════════════════════════════════
    print("  Outro...")

    mx(pitch_dive, cursor, 0.35, 0.35)

    op = dark_pad[:samples(OUTRO * 4)]
    op = fade_out(op, BAR * 7)
    mx_wide(op, cursor, 0.3)

    for bar in range(OUTRO):
        off = cursor + samples(bar * 4)
        vol = max(0.04, 0.65 - bar * 0.08)
        mx(kick, off, vol, vol)
        for ev in hat_pattern:
            h_vol = max(0.02, 0.12 - bar * 0.015) * ev.velocity
            mx_panned(hat_c, off + int(ev.time * SR), h_vol, 0.0)

    os_sub = to_list(synthesize_bass(BassPreset(
        name="OS", bass_type="sub_sine", frequency=FREQ["F1"],
        duration_s=OUTRO * BAR, release_s=OUTRO * BAR * 0.85
    )))
    os_sub = fade_out(os_sub, BAR * 7)
    mx(os_sub, cursor, 0.25, 0.25)

    # ══════════════════════════════════════════════════
    #  MIXDOWN + MASTERING
    # ══════════════════════════════════════════════════
    print("  [9/9] Mixing & mastering...")

    # ── Apply sidechain_bus using collected kick positions ──
    # This creates the signature dubstep pump on the full mix
    if kick_positions:
        L, R = sidechain_bus(L, R, kick_positions, depth=0.55, attack=0.003, release=0.18)

    # ── Bus compression on full mix before mastering ──
    # This glues the mix together like a console bus compressor
    L_np = np.array(L, dtype=np.float64)
    R_np = np.array(R, dtype=np.float64)

    # High-pass at 25Hz to remove inaudible sub rumble
    L_np = svf_highpass(L_np, 25.0, 0.7, SR)
    R_np = svf_highpass(R_np, 25.0, 0.7, SR)

    # Sub energy preserved — no pre-master 60Hz cut (let mastering chain handle it)
    L_list = L_np.tolist()
    R_list = R_np.tolist()

    # Mid presence boost at 1kHz (+2 dB — gentle, mastering adds more)
    L_list = apply_eq_band(L_list, center_hz=1000.0, gain_db=2.0, q=0.8)
    R_list = apply_eq_band(R_list, center_hz=1000.0, gain_db=2.0, q=0.8)

    # High presence boost at 5kHz (+1.5 dB — gentle, mastering adds DNA eq_high_boost)
    L_list = apply_eq_band(L_list, center_hz=5000.0, gain_db=1.5, q=0.7)
    R_list = apply_eq_band(R_list, center_hz=5000.0, gain_db=1.5, q=0.7)

    L_np = np.array(L_list, dtype=np.float64)
    R_np = np.array(R_list, dtype=np.float64)

    # Bus compress as linked stereo (sum L+R → derive gain → apply to both)
    M_np = (L_np + R_np) * 0.5  # Mid signal for gain detection
    M_compressed = multiband_compress(M_np, SR,
                               low_xover=120.0, high_xover=4000.0,
                               threshold_db=-10.0, ratio=2.5,
                               attack_ms=10.0, release_ms=80.0)
    # Derive gain envelope from mid compression (with safe threshold and smoothing)
    _gain_env = np.ones_like(M_np)
    _nonzero = np.abs(M_np) > 1e-4
    _gain_env[_nonzero] = M_compressed[_nonzero] / M_np[_nonzero]
    _gain_env = np.clip(_gain_env, 0.0, 2.0)
    # Smooth gain envelope to avoid zero-crossing artifacts (1ms window)
    _smooth_n = max(1, int(0.001 * SR))
    _kernel = np.ones(_smooth_n) / _smooth_n
    _gain_env = np.convolve(_gain_env, _kernel, mode='same')
    L_np = L_np * _gain_env
    R_np = R_np * _gain_env

    stereo = np.column_stack([L_np, R_np])

    stereo = apply_stereo_imaging(stereo, StereoPreset(
        name="MasterImg", image_type="frequency_split",
        width=md.stereo_width, crossover_hz=180.0, mix=0.85
    ))

    settings = dubstep_master_settings()
    settings.target_lufs = md.target_lufs
    settings.ceiling_db = md.ceiling_db
    settings.eq_low_shelf_db = md.eq_low_boost
    settings.eq_low_shelf_freq = md.eq_low_freq
    settings.eq_high_shelf_db = md.eq_high_boost
    settings.eq_high_shelf_freq = md.eq_high_freq
    settings.compression_ratio = md.compression_ratio
    settings.compression_threshold_db = md.compression_threshold
    settings.stereo_width = md.stereo_width
    settings.limiter_enabled = md.limiter_enabled

    mastered, report = master(stereo, sr=SR, settings=settings)

    master_L = mastered[:, 0].tolist()
    master_R = mastered[:, 1].tolist()

    # NOTE: Post-limiter saturation REMOVED — replaced by soft_clip
    # inside mastering_chain.master() which runs BEFORE the limiter,
    # avoiding aliased harmonics above the ceiling.

    out_path = str(OUTPUT / f"{safe_name}.wav")
    write_stereo_wav(out_path, master_L, master_R)

    duration = len(master_L) / SR
    fsize = os.path.getsize(out_path)
    print(f"\n  Output:   {out_path}")
    print(f"  Duration: {duration:.1f}s ({int(duration // 60)}:{int(duration % 60):02d})")
    print(f"  LUFS:     {report.output_lufs:.1f}")
    print(f"  Peak:     {report.output_peak_db:.1f} dB")
    print(f"  Size:     {fsize / 1024 / 1024:.1f} MB")
    return out_path
# ═══════════════════════════════════════════

def main():
    args = sys.argv[1:]

    # ── Song mode: --song "Song Name" [--style dubstep] [--mood dark] ──
    if "--song" in args:
        idx = args.index("--song")
        song_name = args[idx + 1] if idx + 1 < len(args) else "Untitled"

        # Optional flags
        style = "dubstep"
        mood = ""
        sound_style = ""
        if "--style" in args:
            si = args.index("--style")
            style = args[si + 1] if si + 1 < len(args) else style
        if "--mood" in args:
            mi = args.index("--mood")
            mood = args[mi + 1] if mi + 1 < len(args) else mood
        if "--sound" in args:
            sdi = args.index("--sound")
            sound_style = args[sdi + 1] if sdi + 1 < len(args) else sound_style

        bp = SongBlueprint(name=song_name, style=style, mood=mood,
                           sound_style=sound_style)
        engine = VariationEngine(artistic_variance=0.15)
        dna = engine.forge_dna(bp)

        print("╔══════════════════════════════════════════════╗")
        print(f"║  DUBFORGE — {dna.name:<33}║")
        print(f"║  BPM: {dna.bpm}  |  Key: {dna.key} {dna.scale:<8} | v6   ║")
        print("╚══════════════════════════════════════════════╝")
        print(dna.summary())

        # Save DNA
        dna_path = save_dna(dna)
        print(f"\n  DNA saved: {dna_path}")

        # Render track with full DNA→render integration
        render_full_track(dna=dna)
        return

    print("╔══════════════════════════════════════════════╗")
    print("║  DUBFORGE — Full Production Pipeline        ║")
    print("║  BPM: 140  |  Key: F minor  |  Engine: v6   ║")
    print("╚══════════════════════════════════════════════╝")

    run_all = not args or "--all" in args

    if run_all or "--serum" in args:
        generate_wavetables()

    if run_all or "--stems" in args:
        render_stems()

    if run_all or "--presets" in args:
        generate_presets()

    if run_all or "--ableton" in args:
        generate_ableton_project()

    if run_all or "--track" in args:
        render_full_track()

    print("\n╔══════════════════════════════════════════════╗")
    print("║  PIPELINE COMPLETE                          ║")
    print("╠══════════════════════════════════════════════╣")
    print("║                                              ║")
    print("║  WHAT TO DO NEXT:                            ║")
    print("║                                              ║")
    print("║  1. Open Ableton Live 10                     ║")
    print("║     File → Open → output/ableton/            ║")
    print("║       DUBFORGE_SESSION.als                   ║")
    print("║                                              ║")
    print("║  2. Load Serum 2 on MIDI tracks              ║")
    print("║     Drag wavetables from output/wavetables/  ║")
    print("║     into Serum's Osc A                       ║")
    print("║                                              ║")
    print("║  3. Drag stems from output/stems/            ║")
    print("║     into the audio tracks                    ║")
    print("║                                              ║")
    print("║  4. Listen to the full mix:                  ║")
    print("║     open output/dubstep_track_v5.wav         ║")
    print("║                                              ║")
    print("╚══════════════════════════════════════════════╝")


if __name__ == "__main__":
    main()
