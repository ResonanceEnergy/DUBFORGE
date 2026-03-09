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
    ├── dubstep_track_v2.wav          Full mixed track
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
from engine.fm_synth import FMPatch, FMOperator, render_fm
from engine.glitch_engine import GlitchPreset, synthesize_stutter
from engine.growl_resampler import (
    generate_saw_source, generate_fm_source, growl_resample_pipeline
)
from engine.phi_core import write_wav as write_serum_wav, WAVETABLE_SIZE
from engine.fxp_writer import main as fxp_main
from engine.als_generator import (
    ALSProject, ALSTrack, ALSScene, write_als, write_als_json
)
from engine.mastering_chain import master, MasterSettings, dubstep_master_settings
from engine.config_loader import PHI

# ── Constants ────────────────────────────────────────────────────────
SR = 44100
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
    out = [0.0] * len(sig)
    out[0] = sig[0] * cutoff
    for i in range(1, len(sig)):
        out[i] = out[i - 1] + cutoff * (sig[i] - out[i - 1])
    return out


def highpass(sig: list[float], cutoff: float = 0.95) -> list[float]:
    out = [0.0] * len(sig)
    prev_in = sig[0]
    out[0] = sig[0]
    for i in range(1, len(sig)):
        out[i] = cutoff * (out[i - 1] + sig[i] - prev_in)
        prev_in = sig[i]
    return out


def distort(sig: list[float], drive: float = 2.0) -> list[float]:
    return [math.tanh(s * drive) for s in sig]


def wavefold(sig: list[float], threshold: float = 0.6) -> list[float]:
    """Wavefolder distortion — folds signal back when exceeding threshold."""
    out = []
    for s in sig:
        while abs(s) > threshold:
            if s > threshold:
                s = 2 * threshold - s
            elif s < -threshold:
                s = -2 * threshold - s
        out.append(s)
    return out


def bitcrush(sig: list[float], bits: int = 8) -> list[float]:
    """Reduce bit depth for lo-fi grit."""
    levels = 2 ** bits
    return [round(s * levels) / levels for s in sig]


def sidechain(sig: list[float], depth: float = 0.7, attack: float = 0.01, release: float = 0.15) -> list[float]:
    """Musical sidechain compression synced to kick (beat 1 and 3)."""
    out = list(sig)
    beat_s = samples(1)
    atk_s = int(attack * SR)
    rel_s = int(release * SR)

    for i in range(len(out)):
        beat_pos = i % (beat_s * 2)  # trigger every 2 beats (halftime)
        if beat_pos < atk_s:
            env = 1.0 - depth * (1.0 - beat_pos / atk_s)
        elif beat_pos < atk_s + rel_s:
            env = (1.0 - depth) + depth * ((beat_pos - atk_s) / rel_s)
        else:
            env = 1.0
        out[i] *= env
    return out


def stereo_widen(mono: list[float], width: float = 0.3) -> tuple[list[float], list[float]]:
    """Simple stereo widening via comb-filter delay."""
    delay = int(0.012 * SR)  # 12ms Haas delay
    left = list(mono)
    right = [0.0] * len(mono)
    for i in range(len(mono)):
        if i >= delay:
            right[i] = mono[i - delay] * width + mono[i] * (1 - width)
        else:
            right[i] = mono[i]
    return left, right


def write_mono_wav(path: str, sig: list[float]):
    """Write 16-bit mono WAV."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        frames = b""
        for s in sig:
            frames += struct.pack("<h", max(-32768, min(32767, int(s * 32767))))
        wf.writeframes(frames)


def write_stereo_wav(path: str, left: list[float], right: list[float]):
    """Write 16-bit stereo WAV."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    n = min(len(left), len(right))
    with wave.open(path, "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        chunk_size = SR
        for start in range(0, n, chunk_size):
            end = min(start + chunk_size, n)
            frames = b""
            for i in range(start, end):
                l_s = max(-32768, min(32767, int(left[i] * 32767)))
                r_s = max(-32768, min(32767, int(right[i] * 32767)))
                frames += struct.pack("<hh", l_s, r_s)
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


# ═══════════════════════════════════════════
#  5. FULL MIXED TRACK (V2 — mastered)
# ═══════════════════════════════════════════

def render_full_track():
    """Render a full mastered dubstep track using all engine modules."""
    print("\n═══ STEP 5: Full Mastered Track ═══")

    # Section lengths (bars)
    INTRO = 8
    BUILD = 4
    DROP1 = 16
    BREAK_ = 8
    BUILD2 = 4
    DROP2 = 16
    OUTRO = 8
    total_bars = INTRO + BUILD + DROP1 + BREAK_ + BUILD2 + DROP2 + OUTRO
    total_s = samples(total_bars * 4)
    print(f"  {total_bars} bars = {total_bars * BAR:.0f}s at {BPM} BPM")

    # Pre-render sounds
    kick = to_list(synthesize_kick(PercPreset(
        name="K", perc_type="kick", pitch=55.0, duration_s=0.4,
        decay_s=0.3, tone_mix=0.85, brightness=0.35, distortion=0.25
    )))
    snare = to_list(synthesize_snare(PercPreset(
        name="S", perc_type="snare", pitch=180.0, duration_s=0.25,
        decay_s=0.15, tone_mix=0.4, brightness=0.8, distortion=0.15
    )))
    hat_c = to_list(synthesize_hat(PercPreset(
        name="HC", perc_type="hat", pitch=8000.0, duration_s=0.06,
        decay_s=0.04, tone_mix=0.1, brightness=0.95
    )))
    hat_o = to_list(synthesize_hat(PercPreset(
        name="HO", perc_type="hat", pitch=7500.0, duration_s=0.25,
        decay_s=0.2, tone_mix=0.1, brightness=0.9
    )))
    clap = to_list(synthesize_clap(PercPreset(
        name="CL", perc_type="clap", pitch=200.0, duration_s=0.2,
        decay_s=0.12, tone_mix=0.2, brightness=0.9
    )))
    sub = to_list(synthesize_bass(BassPreset(
        name="Sub", bass_type="sub_sine", frequency=FREQ["F1"],
        duration_s=BEAT * 2, attack_s=0.005, release_s=0.15
    )))
    wobble = to_list(synthesize_bass(BassPreset(
        name="Wob", bass_type="wobble", frequency=FREQ["F2"],
        duration_s=BEAT * 2, fm_ratio=PHI, fm_depth=3.0,
        distortion=0.4, filter_cutoff=0.6
    )))
    growl = to_list(synthesize_bass(BassPreset(
        name="Grl", bass_type="growl", frequency=FREQ["F2"],
        duration_s=BEAT, fm_ratio=2.0, fm_depth=5.0,
        distortion=0.6, filter_cutoff=0.7
    )))
    neuro = to_list(synthesize_bass(BassPreset(
        name="Nro", bass_type="neuro", frequency=FREQ["F2"],
        duration_s=BEAT, fm_ratio=3.0, fm_depth=4.0,
        distortion=0.7, filter_cutoff=0.5
    )))
    reese = to_list(synthesize_bass(BassPreset(
        name="Reese", bass_type="reese", frequency=FREQ["F2"],
        duration_s=BAR, detune_cents=15.0, filter_cutoff=0.4,
        attack_s=0.3, release_s=0.5
    )))
    lead_f = to_list(synthesize_screech_lead(LeadPreset(
        name="LF", lead_type="screech", frequency=FREQ["F4"],
        duration_s=BEAT * 0.5, filter_cutoff=0.9, resonance=0.5, distortion=0.4
    )))
    lead_eb = to_list(synthesize_screech_lead(LeadPreset(
        name="LE", lead_type="screech", frequency=FREQ["Eb4"],
        duration_s=BEAT * 0.5, filter_cutoff=0.9, resonance=0.5, distortion=0.4
    )))
    lead_c = to_list(synthesize_screech_lead(LeadPreset(
        name="LC", lead_type="screech", frequency=FREQ["C4"],
        duration_s=BEAT * 0.75, filter_cutoff=0.85, resonance=0.4, distortion=0.3
    )))
    dark_pad = to_list(synthesize_dark_pad(PadPreset(
        name="DP", pad_type="dark", frequency=FREQ["F3"],
        duration_s=BAR * 8, detune_cents=12.0, filter_cutoff=0.4,
        attack_s=1.0, release_s=2.0, brightness=0.35
    )))
    riser = to_list(synthesize_noise(NoisePreset(
        name="Rise", noise_type="white", duration_s=BAR * 4,
        brightness=0.3, gain=0.5
    )))
    for i in range(len(riser)):
        riser[i] *= (i / len(riser)) ** 2.5
    boom = to_list(synthesize_sub_boom(ImpactPreset(
        name="Boom", impact_type="sub_boom", duration_s=2.0,
        frequency=FREQ["F1"], decay_s=1.5, intensity=0.95
    )))
    hit = to_list(synthesize_cinematic_hit(ImpactPreset(
        name="Hit", impact_type="cinematic_hit", duration_s=1.5,
        frequency=80.0, decay_s=1.0, intensity=0.9
    )))
    stutter = to_list(synthesize_stutter(GlitchPreset(
        name="Stut", glitch_type="stutter", frequency=FREQ["F3"],
        duration_s=BEAT * 2, rate=16.0, depth=0.9, distortion=0.2
    )))

    # Master buffers
    L = [0.0] * total_s
    R = [0.0] * total_s

    def mx(mono, offset, gl=0.7, gr=0.7):
        mix_into(L, mono, offset, gl)
        mix_into(R, mono, offset, gr)

    cursor = 0

    # ── INTRO (8 bars) ──
    print("  Intro...")
    ip = dark_pad[:samples(INTRO * 4)]
    ip = fade_in(ip, BAR * 3)
    ip = lowpass(ip, 0.12)
    mx(ip, cursor, 0.45, 0.45)
    # Sparse hats
    for bar in range(INTRO):
        off = cursor + samples(bar * 4)
        mx(kick, off, 0.35, 0.35)
        for q in range(4):
            mx(hat_c, off + samples(q), 0.2, 0.2)
    # Filtered reese
    ir = reese[:samples(INTRO * 4)]
    ir = lowpass(ir, 0.08)
    ir = fade_in(ir, BAR * 4)
    mx(ir, cursor, 0.25, 0.25)
    cursor += samples(INTRO * 4)

    # ── BUILD (4 bars) ──
    print("  Build...")
    # Snare roll
    for bar in range(BUILD):
        off = cursor + samples(bar * 4)
        mx(kick, off, 0.6, 0.6)
        mx(kick, off + samples(2), 0.6, 0.6)
        divs = [4, 8, 16, 32][bar]
        step = 4.0 / divs
        for h in range(divs):
            vel = 0.3 + 0.5 * (bar / BUILD) * (h / divs)
            mx(snare, off + samples(h * step), vel, vel)
    # Riser
    r_seg = riser[:samples(BUILD * 4)]
    mx(r_seg, cursor, 0.4, 0.4)
    cursor += samples(BUILD * 4)

    # ── DROP 1 (16 bars) ──
    print("  Drop 1...")
    # Impact
    mx(boom, cursor, 0.9, 0.9)
    mx(hit, cursor, 0.5, 0.5)

    for bar in range(DROP1):
        off = cursor + samples(bar * 4)
        # Halftime drums
        mx(kick, off, 0.9, 0.9)
        mx(snare, off + samples(2), 0.8, 0.8)
        mx(clap, off + samples(2), 0.3, 0.3)
        for e in range(8):
            mx(hat_c, off + samples(e * 0.5), 0.3, 0.3)
        mx(hat_o, off + samples(1.5), 0.25, 0.25)
        mx(hat_o, off + samples(3.5), 0.25, 0.25)

        # Sub
        mx(sub, off, 0.85, 0.85)
        mx(sub, off + samples(2), 0.75, 0.75)

        # Mid bass (sidechained)
        sc_wob = sidechain(wobble, depth=0.55)
        sc_grl = sidechain(growl, depth=0.55)
        sc_nro = sidechain(neuro, depth=0.55)
        mx(sc_wob, off + samples(0.5), 0.55, 0.55)
        mx(sc_grl, off + samples(1), 0.5, 0.5)
        mx(sc_nro, off + samples(1.5), 0.45, 0.45)
        mx(sc_wob, off + samples(2.5), 0.5, 0.5)
        mx(sc_grl, off + samples(3), 0.45, 0.45)
        mx(sc_nro, off + samples(3.5), 0.4, 0.4)

        # Lead melody (panned slightly right)
        notes = [(lead_f, 0.0), (lead_eb, 1.0), (lead_c, 2.0), (lead_eb, 3.0)]
        for snd, bt in notes:
            mix_into(L, snd, off + samples(bt), 0.25)
            mix_into(R, snd, off + samples(bt), 0.38)

    # Stutter transition
    mx(stutter, cursor + samples((DROP1 - 1) * 4 + 2), 0.4, 0.4)
    cursor += samples(DROP1 * 4)

    # ── BREAKDOWN (8 bars) ──
    print("  Breakdown...")
    lush = to_list(synthesize_lush_pad(PadPreset(
        name="LP", pad_type="lush", frequency=FREQ["Ab3"],
        duration_s=BAR * BREAK_, filter_cutoff=0.5, brightness=0.5,
        attack_s=0.8, release_s=1.5
    )))
    bp = lush[:samples(BREAK_ * 4)]
    bp = fade_in(bp, BAR)
    bp = fade_out(bp, BAR)
    mx(bp, cursor, 0.4, 0.4)
    # Pluck arps
    pluck_freqs = [FREQ["F3"], FREQ["Ab3"], FREQ["C4"], FREQ["Eb4"]]
    for bar in range(BREAK_):
        off = cursor + samples(bar * 4)
        for q in range(4):
            freq = pluck_freqs[(bar + q) % 4]
            plk = to_list(synthesize_pluck_lead(LeadPreset(
                name="P", lead_type="pluck", frequency=freq,
                duration_s=BEAT * 0.8, filter_cutoff=0.6
            )))
            pan = -0.3 if q % 2 == 0 else 0.3
            mix_into(L, plk, off + samples(q), 0.3 * (1.0 - pan * 0.5))
            mix_into(R, plk, off + samples(q), 0.3 * (1.0 + pan * 0.5))
        mx(hat_c, off + samples(0), 0.12, 0.12)
        mx(hat_c, off + samples(1), 0.12, 0.12)
        mx(hat_c, off + samples(2), 0.12, 0.12)
        mx(hat_c, off + samples(3), 0.12, 0.12)
    # Sub drone
    sd = to_list(synthesize_bass(BassPreset(
        name="SD", bass_type="sub_sine", frequency=FREQ["F1"],
        duration_s=BREAK_ * BAR, attack_s=1.0, release_s=2.0
    )))
    mx(sd, cursor, 0.3, 0.3)
    cursor += samples(BREAK_ * 4)

    # ── BUILD 2 (4 bars) ──
    print("  Build 2...")
    for bar in range(BUILD2):
        off = cursor + samples(bar * 4)
        mx(kick, off, 0.6, 0.6)
        mx(kick, off + samples(2), 0.6, 0.6)
        divs = [4, 8, 16, 32][bar]
        step = 4.0 / divs
        for h in range(divs):
            vel = 0.35 + 0.5 * (bar / BUILD2) * (h / divs)
            mx(snare, off + samples(h * step), vel, vel)
    r2 = riser[:samples(BUILD2 * 4)]
    mx(r2, cursor, 0.5, 0.5)
    cursor += samples(BUILD2 * 4)

    # ── DROP 2 (16 bars) — HEAVIER ──
    print("  Drop 2...")
    mx(boom, cursor, 1.0, 1.0)
    mx(hit, cursor, 0.65, 0.65)
    mx(clap, cursor, 0.5, 0.5)

    for bar in range(DROP2):
        off = cursor + samples(bar * 4)
        mx(kick, off, 0.95, 0.95)
        mx(snare, off + samples(2), 0.85, 0.85)
        mx(clap, off + samples(2), 0.35, 0.35)
        for e in range(8):
            mx(hat_c, off + samples(e * 0.5), 0.32, 0.32)
        mx(hat_o, off + samples(1.5), 0.28, 0.28)
        mx(hat_o, off + samples(3.5), 0.28, 0.28)

        # Sub
        mx(sub, off, 0.95, 0.95)
        mx(sub, off + samples(2), 0.85, 0.85)

        # Heavier bass — 16ths with more drive
        for s16 in range(16):
            bass_snd = neuro if s16 % 3 == 0 else growl if s16 % 2 == 0 else wobble
            sc_b = sidechain(bass_snd, depth=0.5)
            sc_b = distort(sc_b, drive=1.8)
            mx(sc_b, off + samples(s16 * 0.25), 0.3, 0.3)

        # Lead
        for snd, bt in [(lead_f, 0.0), (lead_eb, 1.0), (lead_c, 2.0), (lead_eb, 3.0)]:
            mix_into(L, snd, off + samples(bt), 0.3)
            mix_into(R, snd, off + samples(bt), 0.45)

    # Stutter
    mx(stutter, cursor + samples((DROP2 - 2) * 4), 0.35, 0.35)
    mx(stutter, cursor + samples((DROP2 - 1) * 4), 0.4, 0.4)
    cursor += samples(DROP2 * 4)

    # ── OUTRO (8 bars) ──
    print("  Outro...")
    op = dark_pad[:samples(OUTRO * 4)]
    op = fade_out(op, BAR * 5)
    op = lowpass(op, 0.1)
    mx(op, cursor, 0.35, 0.35)
    for bar in range(OUTRO):
        off = cursor + samples(bar * 4)
        mx(kick, off, max(0.05, 0.35 - bar * 0.04), max(0.05, 0.35 - bar * 0.04))
        for q in range(4):
            mx(hat_c, off + samples(q), max(0.03, 0.2 - bar * 0.02), max(0.03, 0.2 - bar * 0.02))
    os_sub = to_list(synthesize_bass(BassPreset(
        name="OS", bass_type="sub_sine", frequency=FREQ["F1"],
        duration_s=OUTRO * BAR, release_s=OUTRO * BAR * 0.8
    )))
    os_sub = fade_out(os_sub, BAR * 6)
    mx(os_sub, cursor, 0.25, 0.25)

    # ── MASTER ──
    print("  Mastering...")
    # Convert to numpy stereo array for mastering chain
    stereo = np.column_stack([np.array(L), np.array(R)])

    settings = dubstep_master_settings()
    settings.target_lufs = -10.0
    settings.ceiling_db = -0.5
    settings.eq_low_shelf_db = 2.0       # sub boost
    settings.eq_low_shelf_freq = 80.0
    settings.eq_high_shelf_db = 1.0      # air
    settings.eq_high_shelf_freq = 10000.0
    settings.compression_ratio = 4.0
    settings.compression_threshold_db = -10.0
    settings.stereo_width = 1.1
    settings.limiter_enabled = True

    mastered, report = master(stereo, sr=SR, settings=settings)

    # Extract L/R back
    master_L = mastered[:, 0].tolist()
    master_R = mastered[:, 1].tolist()

    # Final soft clip
    for i in range(len(master_L)):
        master_L[i] = math.tanh(master_L[i] * 1.05)
        master_R[i] = math.tanh(master_R[i] * 1.05)

    # Write
    out_path = str(OUTPUT / "dubstep_track_v2.wav")
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
#  MAIN — RUN EVERYTHING
# ═══════════════════════════════════════════

def main():
    args = sys.argv[1:]

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
    print("║     open output/dubstep_track_v2.wav         ║")
    print("║                                              ║")
    print("╚══════════════════════════════════════════════╝")


if __name__ == "__main__":
    main()
