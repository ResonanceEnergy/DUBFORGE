#!/usr/bin/env python3
"""DUBFORGE — "Can You See The Apology That Never Came"  (v2 — DOJO REWORK)

Rewritten through Producer Dojo methodology + Subtronics SB10 signature analysis.

Lessons applied:
    DOJO — The Approach: Sound design SEPARATE from arrangement from mixing.
           Resampling chains for evolved bass (Mudpie → golden moments).
           VIP System: 61.8%% new, 38.2%% retained (golden ratio of novelty).
           Color coding + 128 Rack philosophy for organized palette.

    SUBTRONICS SB10 — PACK_WEAPON profile from Fibonacci Pt1+Pt2 analysis:
           89 bars (FIBONACCI) total, 3 drops, Fibonacci bar counts.
           Bass rotation: 5 distinct sounds cycling per drop.
           Growl resampler: multi-pass processed bass (not single-pass synth).
           FM depth INCREASES per drop (evolution across track).
           fibonacci_step energy curve in drops (1.0→0.88, not flat).
           Clean mono sine sub, FM/wavetable heavy mid, wide high.
           Beat repeat / stutter for mid-drop variation.

    PSBS MIX — Phase-Separated Bass System gain staging:
           Sub: clean -3dB, Mid: -6dB, High: -9dB.
           Drums -1.5dB, Leads -8dB, FX -4dB, Vocals -8dB.
           No stem clips. Period.

    Title:    Can You See The Apology That Never Came (Dojo Rework)
    BPM:      150 (Subtronics sweet spot)
    Key:      D minor (SB10 favored key center)
    Tuning:   432 Hz
    Duration: ~2:22 (89 bars — FIBONACCI)
    Mood:     Defiance × Fracture × Evolution (3-drop arc)

    Structure (PACK_WEAPON — Fibonacci bar counts):
        Intro      8 bars  — Granular dust + drone + formant whisper + vocal oo
        Build 1    5 bars  — Arp accelerating + riser + vocal stutter (phi curve 0.2→0.9)
        Drop 1    13 bars  — Riddim + growl A rotation + formant lead (energy 1.0→0.88)
        Break 1    5 bars  — Chord sus4 + granular shimmer + vocal oh (ceiling 0.35)
        Build 2    8 bars  — Darker arp + harmonic riser + beat repeat (exponential 0.15→0.95)
        Drop 2    21 bars  — Max aggression + growl tear/FM + deeper FM (energy 1.0→0.85)
        Break 2    3 bars  — Near-silence drone + freeze + single vocal (floor 0.08)
        Build 3    5 bars  — Final push + all risers + 64th snare + scream (phi 0.08→1.0)
        Drop 3    13 bars  — CLIMAX: all layers, deepest FM, growl yell (energy 1.0→0.75)
        Outro      8 bars  — Granular freeze + drone decay + ah_long apology

    Golden Section Point: bar ~55 (89/phi) — middle of Drop 2 (CLIMAX)

Output:
    output/stems/apology_v2_*.wav   — 13 individual stem WAVs (incl. vocals)
    output/apology_never_came_v2.wav — stereo mastered mixdown
    output/midi/apology_v2_*.mid     — MIDI for all melodic parts
    output/serum2/apology_v2_patches.json — Serum 2 patch reference
    output/ableton/Apology_Never_Came_V2.als — ALS with AudioClip refs
"""

import json
import math
import os
import subprocess
import wave

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import numpy as np

# ── DUBFORGE engine — Synthesizers ──────────────────────────────────
from engine.bass_oneshot import BassPreset, synthesize_bass
from engine.lead_synth import (LeadPreset, synthesize_screech_lead,
                               synthesize_pluck_lead, synthesize_fm_lead,
                               synthesize_wavetable_lead)
from engine.pad_synth import PadPreset, synthesize_dark_pad, synthesize_lush_pad
from engine.impact_hit import (ImpactPreset, synthesize_sub_boom,
                               synthesize_cinematic_hit, synthesize_reverse_hit)
from engine.fm_synth import FMPatch, FMOperator, render_fm
from engine.supersaw import SupersawPatch, render_supersaw_mono
from engine.glitch_engine import GlitchPreset, synthesize_stutter
from engine.drone_synth import DronePreset, synthesize_drone
from engine.riser_synth import RiserPreset, synthesize_riser
from engine.ambient_texture import TexturePreset, synthesize_texture

# ── DUBFORGE engine — NEW for v2 ───────────────────────────────────
from engine.granular_synth import GranularPreset, synthesize_granular
from engine.chord_pad import ChordPadPreset, synthesize_chord_pad
from engine.formant_synth import FormantPreset, synthesize_formant
from engine.riddim_engine import RiddimPreset, generate_riddim
from engine.arp_synth import ArpSynthPreset, synthesize_arp
from engine.karplus_strong import KarplusStrongPatch, render_ks
from engine.transition_fx import TransitionPreset, synthesize_transition

from engine.vocal_chop import VocalChop, synthesize_chop

# ── DUBFORGE engine — DOJO REWORK: Resampling + Stutter ────────────
from engine.growl_resampler import (waveshape_distortion, frequency_shift,
                                    formant_filter, comb_filter, bit_reduce,
                                    generate_saw_source, generate_fm_source,
                                    growl_resample_pipeline)
from engine.beat_repeat import BeatRepeatPatch, apply_beat_repeat

# ── DUBFORGE engine — GALATCIA sample library ──────────────────────
from engine.galatcia import read_wav_samples

# ── DUBFORGE engine — DSP pipeline ─────────────────────────────────
from engine.sidechain import apply_sidechain, SidechainPreset
from engine.reverb_delay import apply_hall, apply_room, ReverbDelayPreset
from engine.stereo_imager import apply_mid_side, StereoPreset
from engine.mastering_chain import master, dubstep_master_settings

# ── DUBFORGE engine — DAW integration ──────────────────────────────
from engine.als_generator import ALSProject, ALSTrack, ALSScene, write_als
from engine.midi_export import NoteEvent, write_midi_file
from engine.serum2 import build_dubstep_patches

# ── Constants ────────────────────────────────────────────────────────
SR = 44100
BPM = 150
BEAT = 60.0 / BPM                    # seconds per beat
BAR = BEAT * 4                       # seconds per bar
PHI = 1.6180339887

# GALATCIA sample library root
GALATCIA_ROOT = r"C:\dev\DUBFORGE GALATCIA\Samples\Samples"

# Key of D minor — D E F G A Bb C (432 Hz tuning)
A4 = 432.0
KEY_FREQS = {
    "D1": A4 * 2 ** (-31 / 12),
    "F1": A4 * 2 ** (-28 / 12),
    "A1": A4 * 2 ** (-24 / 12),
    "Bb1": A4 * 2 ** (-23 / 12),
    "C2": A4 * 2 ** (-21 / 12),
    "D2": A4 * 2 ** (-19 / 12),
    "E2": A4 * 2 ** (-17 / 12),
    "F2": A4 * 2 ** (-16 / 12),
    "G2": A4 * 2 ** (-14 / 12),
    "A2": A4 * 2 ** (-12 / 12),
    "Bb2": A4 * 2 ** (-11 / 12),
    "C3": A4 * 2 ** (-9 / 12),
    "D3": A4 * 2 ** (-7 / 12),
    "E3": A4 * 2 ** (-5 / 12),
    "F3": A4 * 2 ** (-4 / 12),
    "G3": A4 * 2 ** (-2 / 12),
    "A3": A4 / 2,
    "Bb3": A4 * 2 ** (-1 / 12),
    "C4": A4 * 2 ** (3 / 12),
    "D4": A4 * 2 ** (5 / 12),
    "E4": A4 * 2 ** (7 / 12),
    "F4": A4 * 2 ** (8 / 12),
    "G4": A4 * 2 ** (10 / 12),
    "A4": A4,
}

# MIDI note mapping
MIDI = {
    "D1": 26, "F1": 29, "A1": 33, "Bb1": 34, "C2": 36,
    "D2": 38, "E2": 40, "F2": 41, "G2": 43, "A2": 45, "Bb2": 46,
    "C3": 48, "D3": 50, "E3": 52, "F3": 53, "G3": 55,
    "A3": 57, "Bb3": 58, "C4": 60, "D4": 62, "E4": 64,
    "F4": 65, "G4": 67, "A4": 69,
}

# DSP presets — more aggressive for v2
SC_PUMP = SidechainPreset("V2Pump", "pump", bpm=BPM, depth=0.75,
                          attack_ms=0.3, release_ms=160.0)
SC_HARD = SidechainPreset("V2Hard", "pump", bpm=BPM, depth=0.9,
                          attack_ms=0.5, release_ms=200.0)
HALL_VERB = ReverbDelayPreset("V2Hall", "hall", decay_time=3.2,
                              pre_delay_ms=30.0, damping=0.4, mix=0.28)
ROOM_VERB = ReverbDelayPreset("V2Room", "room", decay_time=0.6,
                              pre_delay_ms=8.0, room_size=0.25, mix=0.18)
MS_WIDE = StereoPreset("V2Wide", "mid_side", width=1.4)


# ── Helpers ──────────────────────────────────────────────────────────

def samples_for(beats: float) -> int:
    return int(beats * BEAT * SR)


def to_np(arr) -> np.ndarray:
    if isinstance(arr, np.ndarray):
        return arr.astype(np.float64)
    return np.array(arr, dtype=np.float64)


def mix_into(target: np.ndarray, source: np.ndarray, offset: int,
             gain: float = 1.0):
    end = min(offset + len(source), len(target))
    n = end - offset
    if n > 0:
        target[offset:end] += source[:n] * gain


def render_section(bars: int) -> np.ndarray:
    return np.zeros(samples_for(bars * 4), dtype=np.float64)


def fade_in(signal: np.ndarray, duration_s: float = 0.5) -> np.ndarray:
    n = min(int(duration_s * SR), len(signal))
    out = signal.copy()
    out[:n] *= np.linspace(0.0, 1.0, n)
    return out


def fade_out(signal: np.ndarray, duration_s: float = 0.5) -> np.ndarray:
    n = min(int(duration_s * SR), len(signal))
    out = signal.copy()
    out[-n:] *= np.linspace(1.0, 0.0, n)
    return out


def lowpass(signal: np.ndarray, cutoff: float = 0.3) -> np.ndarray:
    out = np.zeros_like(signal)
    out[0] = signal[0] * cutoff
    for i in range(1, len(signal)):
        out[i] = out[i - 1] + cutoff * (signal[i] - out[i - 1])
    return out


def distort(signal: np.ndarray, drive: float = 2.0) -> np.ndarray:
    return np.tanh(signal * drive)


# ════════════════════════════════════════════════════════════════════
#  SOUND DESIGN — Pre-render all elements
# ════════════════════════════════════════════════════════════════════

print("=" * 60)
print('  DUBFORGE — "Can You See The Apology That Never Came"')
print("  v2 — DOJO REWORK (PACK_WEAPON × SB10)")
print("=" * 60)
print(f"  BPM: {BPM}  |  Key: D minor  |  Tuning: 432 Hz  |  SR: {SR}")
print(f"  Structure: PACK_WEAPON — 89 bars (FIBONACCI)  |  3 drops")
print()

# ── SERUM 2 PATCH DEFINITIONS ───────────────────────────────────────
print("  [1/14] Loading Serum 2 patch definitions...")
serum_patches = build_dubstep_patches()
os.makedirs("output/serum2", exist_ok=True)
with open("output/serum2/apology_v2_patches.json", "w") as f:
    json.dump(serum_patches, f, indent=2, default=str)
print(f"         {len(serum_patches)} Serum 2 patches exported")

# ── GALATCIA REAL DRUMS ──────────────────────────────────────────────
print("  [2/14] Loading GALATCIA drum samples...")

kick = read_wav_samples(os.path.join(
    GALATCIA_ROOT, "Drum One Shots", "KICKS", "BODP_Kick_3.wav"))
snare = read_wav_samples(os.path.join(
    GALATCIA_ROOT, "Drum One Shots", "Snares", "BODP_Snare_5.wav"))
clap = read_wav_samples(os.path.join(
    GALATCIA_ROOT, "Drum One Shots", "Claps", "BODP_Clap_2.wav"))
hat_closed = read_wav_samples(os.path.join(
    GALATCIA_ROOT, "Drum One Shots", "Hihats", "Closed", "BODP_Closed_7.wav"))
hat_open = read_wav_samples(os.path.join(
    GALATCIA_ROOT, "Drum One Shots", "Hihats", "Open", "BODP_Open_3.wav"))

impact_boom = read_wav_samples(os.path.join(
    GALATCIA_ROOT, "FX", "Impacts", "Booms", "BODP_Impact_3.wav"))

print(f"         kick={len(kick)} snare={len(snare)} clap={len(clap)} "
      f"hh_c={len(hat_closed)} hh_o={len(hat_open)} impact={len(impact_boom)}")

# ── BASS — Sub + Riddim Engine ───────────────────────────────────────
print("  [3/14] Bass (sub + riddim)...")

sub_bass = to_np(synthesize_bass(BassPreset(
    name="V2Sub", bass_type="sub_sine", frequency=KEY_FREQS["D1"],
    duration_s=BEAT * 2, attack_s=0.003, release_s=0.12, distortion=0.0
)))

wobble_bass = to_np(synthesize_bass(BassPreset(
    name="V2Wobble", bass_type="wobble", frequency=KEY_FREQS["D2"],
    duration_s=BEAT * 2, attack_s=0.008, release_s=0.15,
    fm_ratio=PHI, fm_depth=4.0, distortion=0.35, filter_cutoff=0.5
)))

neuro_bass = to_np(synthesize_bass(BassPreset(
    name="V2Neuro", bass_type="neuro", frequency=KEY_FREQS["D2"],
    duration_s=BEAT, attack_s=0.002, release_s=0.06,
    fm_ratio=3.0, fm_depth=5.0, distortion=0.6, filter_cutoff=0.4
)))

# Riddim engine — the v2 signature
riddim_heavy = to_np(generate_riddim(RiddimPreset(
    name="V2RiddimHeavy", riddim_type="heavy",
    frequency=KEY_FREQS["D2"], bpm=BPM,
    gap_ratio=0.3, attack_s=0.003, release_s=0.08,
    distortion=0.45, subdivisions=4
)))

riddim_stutter = to_np(generate_riddim(RiddimPreset(
    name="V2RiddimStutter", riddim_type="stutter",
    frequency=KEY_FREQS["D2"], bpm=BPM,
    gap_ratio=0.2, attack_s=0.002, release_s=0.05,
    distortion=0.55, subdivisions=8
)))

riddim_triplet = to_np(generate_riddim(RiddimPreset(
    name="V2RiddimTrip", riddim_type="triplet",
    frequency=KEY_FREQS["D2"], bpm=BPM,
    gap_ratio=0.25, attack_s=0.003, release_s=0.06,
    distortion=0.4, subdivisions=3
)))

# ── LEADS — Screech + Formant ────────────────────────────────────────
print("  [4/14] Leads (screech + formant)...")

screech_d = to_np(synthesize_screech_lead(LeadPreset(
    name="V2ScreechD", lead_type="screech", frequency=KEY_FREQS["D4"],
    duration_s=BEAT * 0.5, attack_s=0.003, decay_s=0.04,
    sustain=0.65, release_s=0.06, filter_cutoff=0.92,
    resonance=0.72, distortion=0.48
)))

screech_f = to_np(synthesize_screech_lead(LeadPreset(
    name="V2ScreechF", lead_type="screech", frequency=KEY_FREQS["F4"],
    duration_s=BEAT * 0.5, attack_s=0.003, decay_s=0.04,
    sustain=0.6, release_s=0.07, filter_cutoff=0.90,
    resonance=0.68, distortion=0.44
)))

screech_a = to_np(synthesize_screech_lead(LeadPreset(
    name="V2ScreechA", lead_type="screech", frequency=KEY_FREQS["A3"],
    duration_s=BEAT * 0.75, attack_s=0.005, decay_s=0.05,
    sustain=0.55, release_s=0.1, filter_cutoff=0.85,
    resonance=0.65, distortion=0.38
)))

screech_c = to_np(synthesize_screech_lead(LeadPreset(
    name="V2ScreechC", lead_type="screech", frequency=KEY_FREQS["C4"],
    duration_s=BEAT * 0.5, attack_s=0.004, decay_s=0.04,
    sustain=0.6, release_s=0.08, filter_cutoff=0.88,
    resonance=0.70, distortion=0.42
)))

# Formant synth — vocal-like lead (NEW for v2)
formant_ah = to_np(synthesize_formant(FormantPreset(
    name="V2FormantAh", formant_type="ah",
    frequency=KEY_FREQS["D4"], duration_s=BEAT * 1.0,
    brightness=0.72, vibrato_rate=5.5
)))

formant_ee = to_np(synthesize_formant(FormantPreset(
    name="V2FormantEe", formant_type="ee",
    frequency=KEY_FREQS["F4"], duration_s=BEAT * 0.75,
    brightness=0.8, vibrato_rate=6.0
)))

formant_morph = to_np(synthesize_formant(FormantPreset(
    name="V2FormantMorph", formant_type="morph",
    frequency=KEY_FREQS["A3"], duration_s=BEAT * 2.0,
    brightness=0.6, vibrato_rate=4.0
)))

# ── KARPLUS-STRONG STRINGS (NEW for v2) ─────────────────────────────
print("  [5/14] Karplus-Strong strings...")

ks_notes = {}
for note_name in ["D3", "F3", "A3", "C4", "D4", "Bb3", "G3", "E3"]:
    ks_notes[note_name] = to_np(render_ks(KarplusStrongPatch(
        frequency=KEY_FREQS[note_name],
        duration=BEAT * 1.2,
        damping=0.35,
        brightness=0.6,
        stretch=1.0,
        pluck_position=0.3,
        feedback=0.98,
        noise_mix=0.15,
    ), sample_rate=SR))

# ── CHORD PADS (NEW for v2) ─────────────────────────────────────────
print("  [6/14] Chord pads...")

chord_minor7 = to_np(synthesize_chord_pad(ChordPadPreset(
    name="V2DmChordPad", chord_type="minor7",
    root_freq=KEY_FREQS["D3"], duration_s=BAR * 4,
    detune_cents=18.0, attack_s=1.2, release_s=2.0,
    brightness=0.42, warmth=0.6, reverb_amount=0.5
)))

chord_sus4 = to_np(synthesize_chord_pad(ChordPadPreset(
    name="V2SusPad", chord_type="sus4",
    root_freq=KEY_FREQS["G3"], duration_s=BAR * 4,
    detune_cents=10.0, attack_s=1.5, release_s=2.5,
    brightness=0.3, warmth=0.65, reverb_amount=0.55
)))

chord_power = to_np(synthesize_chord_pad(ChordPadPreset(
    name="V2PowerPad", chord_type="power",
    root_freq=KEY_FREQS["D3"], duration_s=BAR * 2,
    detune_cents=20.0, attack_s=0.8, release_s=1.0,
    brightness=0.52, warmth=0.5, reverb_amount=0.3
)))

# ── ARP SYNTH (NEW for v2) ──────────────────────────────────────────
print("  [7/14] Arp synth...")

arp_pulse = to_np(synthesize_arp(ArpSynthPreset(
    name="V2ArpPulse", arp_type="pulse",
    base_freq=KEY_FREQS["D3"], duration_s=BAR * 4,
    step_count=16, filter_cutoff=0.55, resonance=0.3,
    octave_range=2
)))

arp_acid = to_np(synthesize_arp(ArpSynthPreset(
    name="V2ArpAcid", arp_type="acid",
    base_freq=KEY_FREQS["D3"], duration_s=BAR * 4,
    step_count=16, filter_cutoff=0.4, resonance=0.5,
    octave_range=2
)))

# ── SUPERSAW STABS ──────────────────────────────────────────────────
print("  [8/14] Supersaw...")

saw_chord = to_np(render_supersaw_mono(SupersawPatch(
    name="V2DmStab", n_voices=13, detune_cents=48.0,
    mix=0.78, cutoff_hz=7500.0, resonance=0.42,
    attack=0.003, decay=0.15, sustain=0.6, release=0.2,
    master_gain=0.75
), freq=KEY_FREQS["D3"], duration=BEAT * 0.5))

saw_wall = to_np(render_supersaw_mono(SupersawPatch(
    name="V2SawWall", n_voices=15, detune_cents=55.0,
    mix=0.82, cutoff_hz=9000.0, resonance=0.35,
    attack=0.01, decay=0.3, sustain=0.7, release=0.4,
    master_gain=0.65
), freq=KEY_FREQS["D3"], duration=BAR))

fm_hit = to_np(render_fm(FMPatch(
    name="V2FMFractal",
    operators=[
        FMOperator(freq_ratio=1.0, amplitude=1.0, mod_index=9.0,
                   envelope=(0.001, 0.05, 0.0, 0.1)),
        FMOperator(freq_ratio=PHI, amplitude=0.95, mod_index=5.5,
                   envelope=(0.001, 0.08, 0.0, 0.15)),
        FMOperator(freq_ratio=PHI ** 2, amplitude=0.6, mod_index=3.0,
                   envelope=(0.001, 0.12, 0.0, 0.2)),
    ],
    algorithm=0, master_gain=0.65
), freq=KEY_FREQS["D3"], duration=0.3))

# ── PADS ─────────────────────────────────────────────────────────────
print("  [9/14] Pads...")

dark_pad = to_np(synthesize_dark_pad(PadPreset(
    name="V2VoidPad", pad_type="dark", frequency=KEY_FREQS["D3"],
    duration_s=BAR * 8, detune_cents=16.0, filter_cutoff=0.25,
    attack_s=2.0, release_s=3.0, reverb_amount=0.65, brightness=0.2
)))

lush_pad = to_np(synthesize_lush_pad(PadPreset(
    name="V2LushPad", pad_type="lush", frequency=KEY_FREQS["F3"],
    duration_s=BAR * 8, detune_cents=18.0, filter_cutoff=0.4,
    attack_s=1.5, release_s=2.5, reverb_amount=0.7, brightness=0.35
)))

# ── DRONE ────────────────────────────────────────────────────────────
print("  [10/14] Drone...")

drone = to_np(synthesize_drone(DronePreset(
    name="V2AbyssDrone", drone_type="evolving",
    frequency=KEY_FREQS["D1"], duration_s=BAR * 8,
    num_voices=9, detune_cents=10.0, brightness=0.18,
    movement=0.5, attack_s=2.5, release_s=3.5,
    distortion=0.08, reverb_amount=0.55
)))

dark_drone = to_np(synthesize_drone(DronePreset(
    name="V2DarkUndertow", drone_type="dark",
    frequency=KEY_FREQS["D1"], duration_s=BAR * 4,
    num_voices=7, brightness=0.12, movement=0.25,
    attack_s=0.5, release_s=1.5, distortion=0.15
)))

# ── GRANULAR SYNTH (NEW for v2) ─────────────────────────────────────
print("  [11/14] Granular synth...")

granular_dust = to_np(synthesize_granular(GranularPreset(
    name="V2GranDust", grain_type="scatter",
    frequency=KEY_FREQS["D3"], duration_s=BAR * 8,
    grain_size_ms=35.0, grain_density=0.4,
    pitch_spread=0.3, brightness=0.2, reverb_amount=0.6,
    scatter_amount=0.6
)))

granular_shimmer = to_np(synthesize_granular(GranularPreset(
    name="V2GranShimmer", grain_type="shimmer",
    frequency=KEY_FREQS["A3"], duration_s=BAR * 4,
    grain_size_ms=60.0, grain_density=0.7,
    pitch_spread=0.5, brightness=0.55, reverb_amount=0.7
)))

granular_cloud = to_np(synthesize_granular(GranularPreset(
    name="V2GranCloud", grain_type="cloud",
    frequency=KEY_FREQS["D4"], duration_s=BAR * 4,
    grain_size_ms=80.0, grain_density=0.8,
    pitch_spread=0.4, brightness=0.45, reverb_amount=0.5
)))

granular_freeze = to_np(synthesize_granular(GranularPreset(
    name="V2GranFreeze", grain_type="freeze",
    frequency=KEY_FREQS["D3"], duration_s=BAR * 4,
    grain_size_ms=120.0, grain_density=0.6,
    pitch_spread=0.1, brightness=0.25, reverb_amount=0.8
)))

# ── RISERS ───────────────────────────────────────────────────────────
print("  [12/14] Risers...")

pitch_riser = to_np(synthesize_riser(RiserPreset(
    name="V2PitchRise", riser_type="pitch_rise",
    duration_s=BAR * 4,
    start_freq=80.0, end_freq=3000.0,
    brightness=0.6, intensity=0.75, distortion=0.05
)))

harmonic_riser = to_np(synthesize_riser(RiserPreset(
    name="V2HarmonicBuild", riser_type="harmonic_build",
    duration_s=BAR * 4,
    start_freq=60.0, end_freq=3500.0,
    brightness=0.55, intensity=0.8, distortion=0.08
)))

noise_riser = to_np(synthesize_riser(RiserPreset(
    name="V2NoiseSweep", riser_type="noise_sweep",
    duration_s=BAR * 4,
    start_freq=100.0, end_freq=4000.0,
    brightness=0.4, intensity=0.6
)))

# ── FX & IMPACTS + TRANSITIONS (NEW for v2) ─────────────────────────
print("  [13/14] FX, impacts & transitions...")

sub_boom = to_np(synthesize_sub_boom(ImpactPreset(
    name="V2DropBoom", impact_type="sub_boom", duration_s=3.0,
    frequency=KEY_FREQS["D1"], decay_s=2.5, intensity=1.0,
    reverb_amount=0.4
)))

cinema_hit = to_np(synthesize_cinematic_hit(ImpactPreset(
    name="V2CinemaHit", impact_type="cinematic_hit", duration_s=2.0,
    frequency=70.0, decay_s=1.5, brightness=0.6, intensity=0.95
)))

reverse_hit = to_np(synthesize_reverse_hit(ImpactPreset(
    name="V2RevHit", impact_type="reverse_hit", duration_s=1.5,
    frequency=85.0, decay_s=1.0, intensity=0.8
)))

stutter = to_np(synthesize_stutter(GlitchPreset(
    name="V2Stutter", glitch_type="stutter",
    frequency=KEY_FREQS["D3"],
    duration_s=BEAT * 2, rate=16.0, depth=0.9, distortion=0.25
)))

# Transition FX — tape stop, pitch dive, glitch stutter
tape_stop = to_np(synthesize_transition(TransitionPreset(
    name="V2TapeStop", fx_type="tape_stop",
    duration_s=BEAT * 2, start_freq=KEY_FREQS["D3"],
    brightness=0.4
)))

pitch_dive = to_np(synthesize_transition(TransitionPreset(
    name="V2PitchDive", fx_type="pitch_dive",
    duration_s=BEAT * 1.5, start_freq=KEY_FREQS["D4"],
    end_freq=KEY_FREQS["D1"], brightness=0.5
)))

glitch_trans = to_np(synthesize_transition(TransitionPreset(
    name="V2GlitchTrans", fx_type="glitch_stutter",
    duration_s=BEAT * 2, start_freq=KEY_FREQS["D3"],
    brightness=0.6
)))

# ── VOCAL CHOPS ──────────────────────────────────────────────────────
print("  [14/14] Vocal chops...")

chop_ah = to_np(synthesize_chop(VocalChop(
    name="V2CryAh", vowel="ah", note="D3",
    duration_s=BEAT * 0.5, attack_s=0.01, release_s=0.1,
    formant_shift=0.0, distortion=0.1
)))

chop_oh = to_np(synthesize_chop(VocalChop(
    name="V2HollowOh", vowel="oh", note="A3",
    duration_s=BEAT * 0.75, attack_s=0.02, release_s=0.15,
    formant_shift=-2.0, distortion=0.05
)))

chop_eh_stutter = to_np(synthesize_chop(VocalChop(
    name="V2AnguishEh", vowel="eh", note="F3",
    duration_s=BEAT * 1.0, attack_s=0.003, release_s=0.04,
    formant_shift=3.0, distortion=0.2,
    stutter_count=8, stutter_pitch_drift=0.5
)))

chop_ee = to_np(synthesize_chop(VocalChop(
    name="V2ScreamEe", vowel="ee", note="D4",
    duration_s=BEAT * 0.3, attack_s=0.002, release_s=0.05,
    formant_shift=5.0, distortion=0.4
)))

chop_oo = to_np(synthesize_chop(VocalChop(
    name="V2WhisperOo", vowel="oo", note="D3",
    duration_s=BEAT * 1.0, attack_s=0.05, release_s=0.3,
    formant_shift=-3.0, distortion=0.0
)))

chop_ah_long = to_np(synthesize_chop(VocalChop(
    name="V2ApologyAh", vowel="ah", note="A3",
    duration_s=BEAT * 2.0, attack_s=0.03, release_s=0.5,
    formant_shift=-1.0, distortion=0.05
)))

# ── FM + WAVETABLE LEADS (richer than screech alone) ─────────────────
fm_lead_d = to_np(synthesize_fm_lead(LeadPreset(
    name="V2FMLead_D", lead_type="fm_lead", frequency=KEY_FREQS["D4"],
    duration_s=BEAT * 0.5, attack_s=0.003, decay_s=0.06,
    sustain=0.5, release_s=0.08, fm_ratio=PHI, fm_depth=3.0,
    filter_cutoff=0.88, resonance=0.45, distortion=0.25
)))

fm_lead_f = to_np(synthesize_fm_lead(LeadPreset(
    name="V2FMLead_F", lead_type="fm_lead", frequency=KEY_FREQS["F4"],
    duration_s=BEAT * 0.5, attack_s=0.003, decay_s=0.06,
    sustain=0.45, release_s=0.09, fm_ratio=PHI, fm_depth=2.5,
    filter_cutoff=0.85, resonance=0.42, distortion=0.22
)))

fm_lead_a = to_np(synthesize_fm_lead(LeadPreset(
    name="V2FMLead_A", lead_type="fm_lead", frequency=KEY_FREQS["A3"],
    duration_s=BEAT * 0.75, attack_s=0.005, decay_s=0.07,
    sustain=0.45, release_s=0.1, fm_ratio=PHI, fm_depth=2.0,
    filter_cutoff=0.82, resonance=0.38, distortion=0.2
)))

fm_lead_c = to_np(synthesize_fm_lead(LeadPreset(
    name="V2FMLead_C", lead_type="fm_lead", frequency=KEY_FREQS["C4"],
    duration_s=BEAT * 0.5, attack_s=0.004, decay_s=0.06,
    sustain=0.48, release_s=0.08, fm_ratio=PHI, fm_depth=2.8,
    filter_cutoff=0.86, resonance=0.4, distortion=0.23
)))

# ── DOJO: FM LEADS PER DROP — increasing FM depth (SB10 insight) ────
# Drop 2 leads: deeper FM for evolution across the track
fm_lead_d_d2 = to_np(synthesize_fm_lead(LeadPreset(
    name="V2FMLead_D_D2", lead_type="fm_lead", frequency=KEY_FREQS["D4"],
    duration_s=BEAT * 0.5, attack_s=0.003, decay_s=0.06,
    sustain=0.5, release_s=0.08, fm_ratio=PHI, fm_depth=5.0,
    filter_cutoff=0.90, resonance=0.5, distortion=0.30
)))
fm_lead_f_d2 = to_np(synthesize_fm_lead(LeadPreset(
    name="V2FMLead_F_D2", lead_type="fm_lead", frequency=KEY_FREQS["F4"],
    duration_s=BEAT * 0.5, attack_s=0.003, decay_s=0.06,
    sustain=0.45, release_s=0.09, fm_ratio=PHI, fm_depth=4.5,
    filter_cutoff=0.88, resonance=0.48, distortion=0.28
)))
fm_lead_a_d2 = to_np(synthesize_fm_lead(LeadPreset(
    name="V2FMLead_A_D2", lead_type="fm_lead", frequency=KEY_FREQS["A3"],
    duration_s=BEAT * 0.75, attack_s=0.005, decay_s=0.07,
    sustain=0.45, release_s=0.1, fm_ratio=PHI, fm_depth=4.0,
    filter_cutoff=0.86, resonance=0.44, distortion=0.26
)))
fm_lead_c_d2 = to_np(synthesize_fm_lead(LeadPreset(
    name="V2FMLead_C_D2", lead_type="fm_lead", frequency=KEY_FREQS["C4"],
    duration_s=BEAT * 0.5, attack_s=0.004, decay_s=0.06,
    sustain=0.48, release_s=0.08, fm_ratio=PHI, fm_depth=4.8,
    filter_cutoff=0.89, resonance=0.46, distortion=0.28
)))

# Drop 3 leads: DEEPEST FM — Subtronics fm_index_trend="increasing_per_album"
fm_lead_d_d3 = to_np(synthesize_fm_lead(LeadPreset(
    name="V2FMLead_D_D3", lead_type="fm_lead", frequency=KEY_FREQS["D4"],
    duration_s=BEAT * 0.5, attack_s=0.002, decay_s=0.05,
    sustain=0.55, release_s=0.07, fm_ratio=PHI, fm_depth=7.0,
    filter_cutoff=0.92, resonance=0.55, distortion=0.35
)))
fm_lead_f_d3 = to_np(synthesize_fm_lead(LeadPreset(
    name="V2FMLead_F_D3", lead_type="fm_lead", frequency=KEY_FREQS["F4"],
    duration_s=BEAT * 0.5, attack_s=0.002, decay_s=0.05,
    sustain=0.5, release_s=0.08, fm_ratio=PHI, fm_depth=6.5,
    filter_cutoff=0.91, resonance=0.53, distortion=0.33
)))
fm_lead_a_d3 = to_np(synthesize_fm_lead(LeadPreset(
    name="V2FMLead_A_D3", lead_type="fm_lead", frequency=KEY_FREQS["A3"],
    duration_s=BEAT * 0.75, attack_s=0.003, decay_s=0.06,
    sustain=0.5, release_s=0.09, fm_ratio=PHI, fm_depth=6.0,
    filter_cutoff=0.89, resonance=0.50, distortion=0.30
)))
fm_lead_c_d3 = to_np(synthesize_fm_lead(LeadPreset(
    name="V2FMLead_C_D3", lead_type="fm_lead", frequency=KEY_FREQS["C4"],
    duration_s=BEAT * 0.5, attack_s=0.002, decay_s=0.05,
    sustain=0.52, release_s=0.07, fm_ratio=PHI, fm_depth=6.8,
    filter_cutoff=0.91, resonance=0.52, distortion=0.33
)))

# ── DOJO: GROWL RESAMPLED BASS (Mudpie → golden moments) ────────────
# Subtronics signature: multi-pass resampled bass, not single-pass synth.
# Each variant is existing bass → growl_resampler DSP chain.
print("  [DOJO] Growl resampler: generating evolved bass variants...")

growl_saw = waveshape_distortion(wobble_bass, drive=1.0, mix=0.8)
growl_saw = formant_filter(growl_saw, vowel="A", depth=0.7, mix=0.6)

growl_fm = frequency_shift(neuro_bass, hz=55.0, mix=0.5)
growl_fm = formant_filter(growl_fm, vowel="E", depth=0.6, mix=0.6)

growl_tear = waveshape_distortion(wobble_bass, drive=2.0, mix=0.9)
growl_tear = bit_reduce(growl_tear, bits=6, sample_rate_reduce=0.3, mix=0.4)
growl_tear = formant_filter(growl_tear, vowel="I", depth=0.8, mix=0.7)

growl_yell = formant_filter(neuro_bass, vowel="O", depth=0.9, mix=0.7)
growl_yell = waveshape_distortion(growl_yell, drive=1.5, mix=0.8)

growl_screech = comb_filter(wobble_bass, delay_ms=2.618, feedback=0.6, mix=0.5)
growl_screech = frequency_shift(growl_screech, hz=89.0, mix=0.4)
growl_screech = formant_filter(growl_screech, vowel="U", depth=0.7, mix=0.6)

# Growl palette for bass rotation within drops (Subtronics cycles 3-5 sounds)
GROWL_PALETTE = [growl_saw, growl_fm, growl_tear, growl_yell, growl_screech]

# ── DOJO: BEAT REPEAT PRESETS (phi-grid stutter) ─────────────────────
print("  [DOJO] Beat repeat presets (phi-grid stutter)...")

BR_PHI = BeatRepeatPatch(
    grid="phi", repeats=4, decay=0.15, pitch_shift=0.0,
    reverse_probability=0.1, gate=0.8, mix=0.7, probability=0.6
)
BR_SIXTEENTH = BeatRepeatPatch(
    grid="1/16", repeats=8, decay=0.2, pitch_shift=-2.0,
    reverse_probability=0.0, gate=0.9, mix=0.6, probability=0.8
)
BR_AGGRESSIVE = BeatRepeatPatch(
    grid="1/32", repeats=16, decay=0.3, pitch_shift=-5.0,
    reverse_probability=0.2, gate=0.7, mix=0.8, probability=0.9
)


# ════════════════════════════════════════════════════════════════════
#  DRUM PATTERNS
# ════════════════════════════════════════════════════════════════════


def drum_pattern_drop(bars: int = 4) -> np.ndarray:
    """Halftime drop — kick on 1, snare on 3, tight hats."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, kick, bo, gain=1.0)
        mix_into(buf, snare, bo + samples_for(2), gain=0.88)
        for eighth in range(8):
            mix_into(buf, hat_closed, bo + samples_for(eighth * 0.5),
                     gain=0.3)
        mix_into(buf, hat_open, bo + samples_for(1.5), gain=0.25)
        mix_into(buf, hat_open, bo + samples_for(3.5), gain=0.25)
    peak = np.max(np.abs(buf))
    if peak > 1.0:
        buf /= peak
    return buf


def drum_pattern_drop2(bars: int = 4) -> np.ndarray:
    """Drop 2 — heavier, sixteenth hats, clap layer."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, kick, bo, gain=1.0)
        mix_into(buf, snare, bo + samples_for(2), gain=0.9)
        mix_into(buf, clap, bo + samples_for(2), gain=0.35)
        # Sixteenth note hats — drive it
        for sixteenth in range(16):
            vel = 0.22 + 0.08 * (sixteenth % 4 == 0)
            mix_into(buf, hat_closed,
                     bo + samples_for(sixteenth * 0.25), gain=vel)
        mix_into(buf, hat_open, bo + samples_for(1.5), gain=0.28)
        mix_into(buf, hat_open, bo + samples_for(3.5), gain=0.28)
        # Ghost snare fills
        if bar % 2 == 1:
            mix_into(buf, snare, bo + samples_for(3.75), gain=0.3)
    peak = np.max(np.abs(buf))
    if peak > 1.0:
        buf /= peak
    return buf


def drum_pattern_build(bars: int = 4) -> np.ndarray:
    """Buildup — accelerating snare rolls."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, kick, bo, gain=0.6)
        mix_into(buf, kick, bo + samples_for(2), gain=0.6)
        divisions = [4, 8, 16, 32, 64][min(bar, 4)]
        step = 4.0 / divisions
        for hit in range(divisions):
            vel = 0.3 + 0.5 * (bar / bars) * (hit / divisions)
            mix_into(buf, snare, bo + samples_for(hit * step),
                     gain=vel)
    peak = np.max(np.abs(buf))
    if peak > 1.0:
        buf /= peak
    return buf


def drum_pattern_drop3(bars: int = 4) -> np.ndarray:
    """Drop 3 — CLIMAX: double kick, clap layers, 32nd hat cascades."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        # Double kick pattern (tamed to avoid clipping)
        mix_into(buf, kick, bo, gain=0.78)
        mix_into(buf, kick, bo + samples_for(1), gain=0.55)
        mix_into(buf, snare, bo + samples_for(2), gain=0.72)
        mix_into(buf, clap, bo + samples_for(2), gain=0.30)
        # 32nd-note hat cascade — relentless energy
        for thirtysecond in range(32):
            vel = 0.12 + 0.08 * (thirtysecond % 8 == 0)
            mix_into(buf, hat_closed,
                     bo + samples_for(thirtysecond * 0.125), gain=vel)
        mix_into(buf, hat_open, bo + samples_for(1.5), gain=0.22)
        mix_into(buf, hat_open, bo + samples_for(3.5), gain=0.22)
        # Ghost snare cascades
        if bar % 2 == 1:
            mix_into(buf, snare, bo + samples_for(3.5), gain=0.25)
            mix_into(buf, snare, bo + samples_for(3.75), gain=0.30)
    peak = np.max(np.abs(buf))
    if peak > 1.0:
        buf /= peak
    return buf


def drum_pattern_verse(bars: int = 4) -> np.ndarray:
    """Sparse verse — soft kick + hats, intimate."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, kick, bo, gain=0.35)
        mix_into(buf, kick, bo + samples_for(2), gain=0.25)
        for q in range(4):
            mix_into(buf, hat_closed, bo + samples_for(q), gain=0.18)
        mix_into(buf, hat_open, bo + samples_for(3.5), gain=0.12)
    return buf


def drum_pattern_intro(bars: int = 4) -> np.ndarray:
    """Minimal intro — light hats breathing."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        for q in range(4):
            mix_into(buf, hat_closed, bo + samples_for(q),
                     gain=0.1 + 0.04 * (bar / bars))
    return buf


# ════════════════════════════════════════════════════════════════════
#  BASS PATTERNS — DOJO: Bass rotation (Subtronics cycles 3-5 sounds)
# ════════════════════════════════════════════════════════════════════

def bass_drop_pattern(bars: int = 4) -> np.ndarray:
    """Drop 1 bass — riddim + growl_saw/growl_fm rotation (2 sounds)."""
    buf = render_section(bars)
    bar_samps = samples_for(4)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        # Clean mono sine sub (SB10: sub_treatment="clean_mono_sine")
        mix_into(buf, sub_bass, bo, gain=0.70)
        mix_into(buf, sub_bass, bo + samples_for(2), gain=0.60)
        # Rotate mid-bass: riddim_heavy vs growl variants
        if bar % 3 == 0:
            seg = riddim_heavy[:min(len(riddim_heavy), bar_samps)]
            mix_into(buf, seg, bo, gain=0.40)
        elif bar % 3 == 1:
            seg = growl_saw[:min(len(growl_saw), bar_samps)]
            mix_into(buf, seg, bo, gain=0.35)
        else:
            seg = growl_fm[:min(len(growl_fm), bar_samps)]
            mix_into(buf, seg, bo, gain=0.35)
    return buf


def bass_drop2_pattern(bars: int = 4) -> np.ndarray:
    """Drop 2 bass — maximum aggression, 4-sound rotation with growl."""
    buf = render_section(bars)
    bar_samps = samples_for(4)
    rotation = [
        (riddim_heavy, 0.38),
        (growl_tear, 0.35),
        (riddim_stutter, 0.38),
        (growl_yell, 0.35),
    ]
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, sub_bass, bo, gain=0.80)
        mix_into(buf, sub_bass, bo + samples_for(2), gain=0.70)
        # Rotate through 4 mid-bass sounds
        src, g = rotation[bar % len(rotation)]
        seg = src[:min(len(src), bar_samps)]
        mix_into(buf, seg, bo, gain=g)
        # Neuro fills on offbeats
        for sixteenth in range(0, 16, 3):
            mix_into(buf, neuro_bass,
                     bo + samples_for(sixteenth * 0.25), gain=0.22)
    return buf


def bass_drop3_pattern(bars: int = 4) -> np.ndarray:
    """Drop 3 bass — CLIMAX: 5-sound rotation, full growl palette."""
    buf = render_section(bars)
    bar_samps = samples_for(4)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        # Sub foundation
        mix_into(buf, sub_bass, bo, gain=0.85)
        mix_into(buf, sub_bass, bo + samples_for(2), gain=0.75)
        # Full 5-sound growl rotation
        growl = GROWL_PALETTE[bar % len(GROWL_PALETTE)]
        seg = growl[:min(len(growl), bar_samps)]
        mix_into(buf, seg, bo, gain=0.38)
        # Riddim triplet layer for extra density
        trip_seg = riddim_triplet[:min(len(riddim_triplet), bar_samps)]
        mix_into(buf, trip_seg, bo, gain=0.20)
    return buf


# ════════════════════════════════════════════════════════════════════
#  LEAD MELODY — Ascending motif (defiance rising)
# ════════════════════════════════════════════════════════════════════

def lead_melody_drop(bars: int = 4) -> np.ndarray:
    """Drop 1 lead — screech + FM (base depth). A3→C4→D4→F4."""
    buf = render_section(bars)
    melody = [
        (screech_a, fm_lead_a, 0.0, 0.28, 0.22),
        (screech_c, fm_lead_c, 1.0, 0.30, 0.24),
        (screech_d, fm_lead_d, 2.0, 0.32, 0.26),
        (screech_f, fm_lead_f, 3.0, 0.30, 0.24),
    ]
    for bar in range(bars):
        bo = samples_for(bar * 4)
        for scr, fm, beat, g_scr, g_fm in melody:
            mix_into(buf, scr, bo + samples_for(beat), gain=g_scr)
            mix_into(buf, fm, bo + samples_for(beat), gain=g_fm)
    return buf


def lead_melody_drop2(bars: int = 4) -> np.ndarray:
    """Drop 2 lead — deeper FM (SB10: fm_index_trend increasing)."""
    buf = render_section(bars)
    melody = [
        (screech_a, fm_lead_a_d2, 0.0, 0.30, 0.26),
        (screech_c, fm_lead_c_d2, 1.0, 0.32, 0.28),
        (screech_d, fm_lead_d_d2, 2.0, 0.34, 0.30),
        (screech_f, fm_lead_f_d2, 3.0, 0.32, 0.28),
    ]
    for bar in range(bars):
        bo = samples_for(bar * 4)
        for scr, fm, beat, g_scr, g_fm in melody:
            mix_into(buf, scr, bo + samples_for(beat), gain=g_scr)
            mix_into(buf, fm, bo + samples_for(beat), gain=g_fm)
    return buf


def lead_melody_drop3(bars: int = 4) -> np.ndarray:
    """Drop 3 lead — DEEPEST FM: climax intensity. SB10 evolution."""
    buf = render_section(bars)
    melody = [
        (screech_a, fm_lead_a_d3, 0.0, 0.32, 0.30),
        (screech_c, fm_lead_c_d3, 1.0, 0.34, 0.32),
        (screech_d, fm_lead_d_d3, 2.0, 0.36, 0.34),
        (screech_f, fm_lead_f_d3, 3.0, 0.34, 0.32),
    ]
    for bar in range(bars):
        bo = samples_for(bar * 4)
        for scr, fm, beat, g_scr, g_fm in melody:
            mix_into(buf, scr, bo + samples_for(beat), gain=g_scr)
            mix_into(buf, fm, bo + samples_for(beat), gain=g_fm)
    return buf


def formant_melody(bars: int = 4) -> np.ndarray:
    """Formant synth lead — vocal-like texture over the drops."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, formant_ah, bo, gain=0.28)
        mix_into(buf, formant_ee, bo + samples_for(2), gain=0.25)
        if bar % 2 == 1:
            mix_into(buf, formant_morph, bo + samples_for(1), gain=0.2)
    return buf


def ks_arpeggio(bars: int = 4) -> np.ndarray:
    """Karplus-Strong string arpeggio — D minor broken chord."""
    buf = render_section(bars)
    arp_seq = ["D3", "F3", "A3", "D4", "C4", "Bb3", "G3", "E3"]
    for bar in range(bars):
        bo = samples_for(bar * 4)
        for q in range(4):
            note = arp_seq[(bar * 2 + q) % len(arp_seq)]
            ks = ks_notes[note]
            mix_into(buf, ks, bo + samples_for(q), gain=0.3)
    return buf


def lead_fill(bars: int = 1) -> np.ndarray:
    """Quick lead fill — through the ascending motif."""
    buf = render_section(bars)
    notes = [screech_a, screech_c, screech_d, screech_f]
    for sixteenth in range(16):
        note = notes[sixteenth % 4]
        gain = 0.2 + 0.25 * (sixteenth / 16)
        mix_into(buf, note, samples_for(sixteenth * 0.25), gain=gain)
    return buf


# ════════════════════════════════════════════════════════════════════
#  ARRANGE — PACK_WEAPON profile (89 bars = Fibonacci)
#  Dojo: Fibonacci bar counts. SB10: 3 drops, bass rotation.
# ════════════════════════════════════════════════════════════════════

INTRO_BARS = 8       # Granular dust + drone + formant whisper + vocal oo
BUILD1_BARS = 5      # Arp accelerating + riser + vocal stutter (phi curve)
DROP1_BARS = 13      # Riddim + growl A/B rotation + formant lead
BREAK1_BARS = 5      # Chord sus4 + granular shimmer + vocal oh (ceiling 0.35)
BUILD2_BARS = 8      # Darker arp + harmonic riser + beat repeat
DROP2_BARS = 21      # Max aggression + growl tear/FM + deeper FM
BREAK2_BARS = 3      # Near-silence drone + freeze + single vocal (floor 0.08)
BUILD3_BARS = 5      # Final push + all risers + 64th snare + scream
DROP3_BARS = 13      # CLIMAX: all layers, deepest FM, growl yell
OUTRO_BARS = 8       # Granular freeze + drone decay + ah_long apology

total_bars = (INTRO_BARS + BUILD1_BARS + DROP1_BARS + BREAK1_BARS +
              BUILD2_BARS + DROP2_BARS + BREAK2_BARS + BUILD3_BARS +
              DROP3_BARS + OUTRO_BARS)
total_samples = samples_for(total_bars * 4)
duration_s = total_samples / SR
golden_section_bar = int(total_bars / PHI)

print()
print(f"  Structure: {total_bars} bars = {duration_s:.1f}s "
      f"({int(duration_s // 60)}:{int(duration_s % 60):02d})")
print(f"  PACK_WEAPON (Fibonacci): {INTRO_BARS}/{BUILD1_BARS}/{DROP1_BARS}/"
      f"{BREAK1_BARS}/{BUILD2_BARS}/{DROP2_BARS}/{BREAK2_BARS}/"
      f"{BUILD3_BARS}/{DROP3_BARS}/{OUTRO_BARS}")
print(f"  Golden Section Point: bar ~{golden_section_bar}")
print(f"  Intro({INTRO_BARS}) -> Build1({BUILD1_BARS}) -> "
      f"Drop1({DROP1_BARS}) -> Break1({BREAK1_BARS}) -> "
      f"Build2({BUILD2_BARS}) -> Drop2({DROP2_BARS}) -> "
      f"Break2({BREAK2_BARS}) -> Build3({BUILD3_BARS}) -> "
      f"Drop3({DROP3_BARS}) -> Outro({OUTRO_BARS})")
print()


# ════════════════════════════════════════════════════════════════════
#  STEM BUFFERS
# ════════════════════════════════════════════════════════════════════

STEM_NAMES = [
    "DRUMS", "BASS", "RIDDIM", "LEAD", "FORMANT", "KS_STRINGS",
    "CHORDS", "PAD", "DRONE", "RISER", "VOCAL", "FX", "GRANULAR",
]

# Dojo color coding: Drums=Gray(1), Bass=Red(3), Chords=Blue(20)
STEM_PAN = {
    "DRUMS": 0.0, "BASS": 0.0, "RIDDIM": 0.05, "LEAD": 0.18,
    "FORMANT": -0.15, "KS_STRINGS": -0.22, "CHORDS": 0.12,
    "PAD": 0.0, "DRONE": 0.0, "RISER": 0.0, "VOCAL": -0.05,
    "FX": 0.0, "GRANULAR": 0.0,
}

stems: dict[str, np.ndarray] = {
    name: np.zeros(total_samples) for name in STEM_NAMES
}

cursor = 0

# ── fibonacci_step energy: drops maintain energy with slight decay ───
def fib_step_gain(bar_index: int, total_drop_bars: int,
                  start: float = 1.0, end: float = 0.88) -> float:
    """Fibonacci-step energy curve: high energy with slight decay."""
    t = bar_index / max(total_drop_bars - 1, 1)
    return start - (start - end) * t


def phi_build_gain(bar_index: int, total_build_bars: int,
                   start: float = 0.2, end: float = 0.9) -> float:
    """Phi acceleration curve for builds."""
    t = bar_index / max(total_build_bars - 1, 1)
    return start + (end - start) * (t ** PHI)


# ── INTRO (8 bars) — "Fractal dust rising from the void" ────────────
print("  Rendering Intro...")
intro_start = cursor

# Granular dust — the v2 signature sound
gran_dust_seg = granular_dust[:samples_for(INTRO_BARS * 4)]
gran_dust_seg = fade_in(gran_dust_seg, duration_s=BAR * 3)
mix_into(stems["GRANULAR"], gran_dust_seg, intro_start, gain=0.22)

# Evolving drone — slow rise
intro_drone = drone[:samples_for(INTRO_BARS * 4)]
intro_drone = fade_in(intro_drone, duration_s=BAR * 5)
intro_drone = lowpass(intro_drone, cutoff=0.1)
mix_into(stems["DRONE"], intro_drone, intro_start, gain=0.38)

# Dark pad — barely audible
intro_pad = dark_pad[:samples_for(INTRO_BARS * 4)]
intro_pad = fade_in(intro_pad, duration_s=BAR * 4)
intro_pad = lowpass(intro_pad, cutoff=0.08)
mix_into(stems["PAD"], intro_pad, intro_start, gain=0.25)

# Formant whisper at bars 4 and 7
mix_into(stems["FORMANT"], formant_morph,
         intro_start + samples_for(3 * 4), gain=0.12)
mix_into(stems["FORMANT"], formant_morph,
         intro_start + samples_for(6 * 4), gain=0.15)

# Reverse hit at bar 7
rev_offset = intro_start + samples_for(6 * 4)
mix_into(stems["FX"], reverse_hit, rev_offset, gain=0.30)

# Minimal hats
intro_drums = drum_pattern_intro(INTRO_BARS)
intro_drums = fade_in(intro_drums, duration_s=BAR * 5)
mix_into(stems["DRUMS"], intro_drums, intro_start, gain=0.22)

# KS arpeggio — metallic whispers in the intro (retained from v1: VIP 38.2%)
for rep in range(INTRO_BARS // 4):
    offset = intro_start + samples_for(rep * 16 + 16)  # start at bar 4
    arp = ks_arpeggio(4)
    arp = lowpass(arp, cutoff=0.15)
    mix_into(stems["KS_STRINGS"], arp, offset, gain=0.18)

# Vocal whisper "oo" at bar 4 and bar 7
mix_into(stems["VOCAL"], chop_oo, intro_start + samples_for(3 * 4), gain=0.16)
mix_into(stems["VOCAL"], chop_oo, intro_start + samples_for(6 * 4), gain=0.16)

cursor += samples_for(INTRO_BARS * 4)

# ── BUILD 1 (5 bars) — "The fracture splits open" ─────────────────────
print("  Rendering Build 1...")
build1_start = cursor

# Arp synth accelerating — phi curve energy
for bar in range(BUILD1_BARS):
    bo = build1_start + samples_for(bar * 4)
    g = phi_build_gain(bar, BUILD1_BARS, start=0.15, end=0.32)
    seg = arp_pulse[:samples_for(4)]
    mix_into(stems["KS_STRINGS"], seg, bo, gain=g)

# Pitch riser — tamed
riser_seg = pitch_riser[:samples_for(BUILD1_BARS * 4)]
mix_into(stems["RISER"], riser_seg, build1_start, gain=0.30)

# Noise riser — subtle layer
noise_seg = noise_riser[:samples_for(BUILD1_BARS * 4)]
mix_into(stems["RISER"], noise_seg, build1_start, gain=0.18)

# Snare roll — accelerating
build1_drums = drum_pattern_build(BUILD1_BARS)
mix_into(stems["DRUMS"], build1_drums, build1_start, gain=0.48)

# Glitch transition FX at end
glitch_off = build1_start + samples_for((BUILD1_BARS - 1) * 4)
mix_into(stems["FX"], glitch_trans, glitch_off, gain=0.30)

# Reverse hit
rev_off = build1_start + samples_for(BUILD1_BARS * 4) - len(reverse_hit)
if rev_off > build1_start:
    mix_into(stems["FX"], reverse_hit, rev_off, gain=0.45)

# Chord pad rising with phi curve
for bar in range(BUILD1_BARS):
    bo = build1_start + samples_for(bar * 4)
    g = phi_build_gain(bar, BUILD1_BARS, start=0.10, end=0.28)
    seg = chord_minor7[:samples_for(4)]
    mix_into(stems["PAD"], seg, bo, gain=g)

# Vocal "eh" stutter — anguish accelerating with phi curve
for bar in range(BUILD1_BARS):
    bo = build1_start + samples_for(bar * 4)
    g = phi_build_gain(bar, BUILD1_BARS, start=0.12, end=0.35)
    mix_into(stems["VOCAL"], chop_eh_stutter, bo, gain=g)

# "ee" scream right before the drop
ee_offset = build1_start + samples_for(BUILD1_BARS * 4) - len(chop_ee) - SR // 4
if ee_offset > build1_start:
    mix_into(stems["VOCAL"], chop_ee, ee_offset, gain=0.38)

cursor += samples_for(BUILD1_BARS * 4)

# ── DROP 1 (13 bars) — "The apology fractures" ────────────────────────
print("  Rendering Drop 1 (13 bars — Fibonacci)...")
drop1_start = cursor

# IMPACT — PSBS-aware gains (no clipping!)
mix_into(stems["FX"], sub_boom, drop1_start, gain=0.55)
mix_into(stems["FX"], cinema_hit, drop1_start, gain=0.35)
mix_into(stems["FX"], to_np(impact_boom), drop1_start, gain=0.28)
mix_into(stems["VOCAL"], chop_ee, drop1_start, gain=0.28)

# Drums — halftime with fibonacci_step energy
for rep in range(DROP1_BARS // 4 + 1):
    offset = drop1_start + samples_for(rep * 16)
    bars_left = min(4, DROP1_BARS - rep * 4)
    if bars_left > 0:
        g = fib_step_gain(rep * 4, DROP1_BARS, start=0.58, end=0.52)
        d1d = drum_pattern_drop(bars_left)
        mix_into(stems["DRUMS"], d1d, offset, gain=g)

# Bass — riddim + growl rotation with sidechain (PSBS: sub -3dB, mid -6dB)
for rep in range(DROP1_BARS // 4 + 1):
    offset = drop1_start + samples_for(rep * 16)
    bars_left = min(4, DROP1_BARS - rep * 4)
    if bars_left > 0:
        d1b = apply_sidechain(bass_drop_pattern(bars_left), SC_PUMP, SR)
        g = fib_step_gain(rep * 4, DROP1_BARS, start=0.52, end=0.46)
        mix_into(stems["BASS"], d1b, offset, gain=g)

# Riddim stem — growl-processed riddim
for rep in range(DROP1_BARS // 4 + 1):
    offset = drop1_start + samples_for(rep * 16)
    bars_left = min(4, DROP1_BARS - rep * 4)
    if bars_left > 0:
        bar_samps = samples_for(bars_left * 4)
        r_seg = riddim_heavy[:min(len(riddim_heavy), bar_samps)]
        r_seg = apply_sidechain(r_seg, SC_PUMP, SR)
        mix_into(stems["RIDDIM"], r_seg, offset, gain=0.30)

# Lead — ascending motif (Drop 1: base FM depth)
for rep in range(DROP1_BARS // 4 + 1):
    offset = drop1_start + samples_for(rep * 16)
    bars_left = min(4, DROP1_BARS - rep * 4)
    if bars_left > 0:
        melody = lead_melody_drop(bars_left)
        mix_into(stems["LEAD"], melody, offset, gain=0.30)

# Formant melody — vocal-like texture
for rep in range(DROP1_BARS // 4 + 1):
    offset = drop1_start + samples_for(rep * 16)
    bars_left = min(4, DROP1_BARS - rep * 4)
    if bars_left > 0:
        fmt = formant_melody(bars_left)
        mix_into(stems["FORMANT"], fmt, offset, gain=0.22)

# FM stabs every 2 bars
for bar in range(0, DROP1_BARS, 2):
    stab_off = drop1_start + samples_for(bar * 4)
    mix_into(stems["CHORDS"], fm_hit, stab_off, gain=0.22)

# Granular cloud over the drop
gran_cloud_drop = granular_cloud[:min(len(granular_cloud),
                                      samples_for(DROP1_BARS * 4))]
mix_into(stems["GRANULAR"], gran_cloud_drop, drop1_start, gain=0.08)

# Dark drone underneath
for rep in range(DROP1_BARS // 4 + 1):
    offset = drop1_start + samples_for(rep * 16)
    bars_left = min(4, DROP1_BARS - rep * 4)
    if bars_left > 0:
        seg = dark_drone[:samples_for(bars_left * 4)]
        mix_into(stems["DRONE"], seg, offset, gain=0.15)

# Lead fill + stutter before break
fill_off = drop1_start + samples_for((DROP1_BARS - 1) * 4)
mix_into(stems["LEAD"], lead_fill(1), fill_off, gain=0.30)
stutter_off = drop1_start + samples_for((DROP1_BARS - 1) * 4 + 2)
mix_into(stems["FX"], stutter, stutter_off, gain=0.28)

# Tape stop transition into break
tape_off = drop1_start + samples_for(DROP1_BARS * 4) - len(tape_stop)
if tape_off > drop1_start:
    mix_into(stems["FX"], tape_stop, tape_off, gain=0.30)

# "ah" vocal chop accents in the drop
for bar in range(0, DROP1_BARS, 3):
    mix_into(stems["VOCAL"], chop_ah,
             drop1_start + samples_for(bar * 4 + 1.5), gain=0.18)

cursor += samples_for(DROP1_BARS * 4)

# ── BREAK 1 (5 bars) — "Silence between the fractures" ──────────────
# SB10: break_energy_ceiling = 0.35 — minimal elements only
print("  Rendering Break 1 (5 bars — energy ceiling 0.35)...")
break1_start = cursor

# Chord pad sus4 — suspended, unresolved
chord_sus_seg = chord_sus4[:samples_for(BREAK1_BARS * 4)]
chord_sus_seg = fade_in(chord_sus_seg, duration_s=BAR)
chord_sus_seg = fade_out(chord_sus_seg, duration_s=BAR * 2)
mix_into(stems["PAD"], chord_sus_seg, break1_start, gain=0.32)

# Granular shimmer — ethereal
gran_shim_seg = granular_shimmer[:samples_for(BREAK1_BARS * 4)]
gran_shim_seg = fade_in(gran_shim_seg, duration_s=BAR * 0.5)
mix_into(stems["GRANULAR"], gran_shim_seg, break1_start, gain=0.18)

# KS string melody — wider, more yearning
break_notes = ["D3", "A3", "F3", "D4", "Bb3", "G3", "A3", "E3"]
for bar in range(BREAK1_BARS):
    bo = break1_start + samples_for(bar * 4)
    for q in range(4):
        note = break_notes[(bar + q) % len(break_notes)]
        ks = ks_notes[note]
        mix_into(stems["KS_STRINGS"], ks, bo + samples_for(q), gain=0.22)

# Light hats only — energy ceiling!
for bar in range(BREAK1_BARS):
    bo = break1_start + samples_for(bar * 4)
    for q in range(4):
        mix_into(stems["DRUMS"], hat_closed, bo + samples_for(q), gain=0.08)

# Sub drone — minimal bass presence
sub_break = to_np(synthesize_bass(BassPreset(
    name="V2SubDrone", bass_type="sub_sine", frequency=KEY_FREQS["D1"],
    duration_s=BREAK1_BARS * BAR, attack_s=1.0, release_s=2.0
)))
mix_into(stems["BASS"], sub_break, break1_start, gain=0.20)

# Formant morph — ghost voice
mix_into(stems["FORMANT"], formant_morph,
         break1_start + samples_for(2 * 4), gain=0.12)

# "oo" whisper chops + "oh" — phantom vocals
for bar in [0, 2, 4]:
    mix_into(stems["VOCAL"], chop_oo,
             break1_start + samples_for(bar * 4 + 1), gain=0.19)
for bar in [1, 3]:
    mix_into(stems["VOCAL"], chop_oh,
             break1_start + samples_for(bar * 4 + 3), gain=0.14)

cursor += samples_for(BREAK1_BARS * 4)

# ── BUILD 2 (8 bars) — "The rage crystallizes" ────────────────────────
# SB10: build_bars_mode = 8. Beat repeat integration.
print("  Rendering Build 2 (8 bars — with beat repeat)...")
build2_start = cursor

# Arp acid — darker, more aggressive, with phi acceleration
for bar in range(BUILD2_BARS):
    bo = build2_start + samples_for(bar * 4)
    g = phi_build_gain(bar, BUILD2_BARS, start=0.12, end=0.35)
    seg = arp_acid[:samples_for(4)]
    mix_into(stems["KS_STRINGS"], seg, bo, gain=g)

# Harmonic riser — darker
harmonic_seg = harmonic_riser[:samples_for(BUILD2_BARS * 4)]
mix_into(stems["RISER"], harmonic_seg, build2_start, gain=0.35)

# Noise riser
noise_seg2 = noise_riser[:samples_for(BUILD2_BARS * 4)]
mix_into(stems["RISER"], noise_seg2, build2_start, gain=0.22)

# Snare roll — longer build = more dramatic acceleration
build2_drums = drum_pattern_build(BUILD2_BARS)
mix_into(stems["DRUMS"], build2_drums, build2_start, gain=0.45)

# Beat repeat on the build drums — phi grid stutter for texture
build2_br = np.array(apply_beat_repeat(build2_drums.tolist(), BR_PHI, BPM, SR))
mix_into(stems["DRUMS"], build2_br, build2_start, gain=0.15)

# Tape stop FX mid-build for drama
tape_mid = build2_start + samples_for(4 * 4)
mix_into(stems["FX"], tape_stop, tape_mid, gain=0.25)

# Pitch dive before drop 2
dive_off = build2_start + samples_for((BUILD2_BARS - 1) * 4)
mix_into(stems["FX"], pitch_dive, dive_off, gain=0.40)

# Reverse hit
rev2_off = build2_start + samples_for(BUILD2_BARS * 4) - len(reverse_hit)
if rev2_off > build2_start:
    mix_into(stems["FX"], reverse_hit, rev2_off, gain=0.55)

# Power chord pad with phi acceleration
for bar in range(BUILD2_BARS):
    bo = build2_start + samples_for(bar * 4)
    g = phi_build_gain(bar, BUILD2_BARS, start=0.08, end=0.25)
    seg = chord_power[:samples_for(4)]
    mix_into(stems["PAD"], seg, bo, gain=g)

# Vocal stutter — accelerating desperation (exponential 0.15→0.95)
for i, beat in enumerate([0, 4, 8, 12, 16, 20, 24, 26, 28, 30, 31]):
    g = 0.15 + (i / 10) * 0.30
    if beat < BUILD2_BARS * 4:
        mix_into(stems["VOCAL"], chop_eh_stutter,
                 build2_start + samples_for(beat), gain=g)
# "ee" scream — rip before drop 2
mix_into(stems["VOCAL"], chop_ee,
         build2_start + samples_for(BUILD2_BARS * 4 - 1), gain=0.42)

cursor += samples_for(BUILD2_BARS * 4)

# ── DROP 2 (21 bars) — "DEFIANCE ABSOLUTE — GOLDEN SECTION" ──────────
# This is the LONGEST drop (Fibonacci 21). Golden Section Point (bar ~55) falls HERE.
# SB10: max aggression, growl tear/FM rotation, deeper FM index.
print("  Rendering Drop 2 (21 bars — Golden Section, deepest aggression)...")
drop2_start = cursor

# MASSIVE impact — PSBS-aware (no clipping)
mix_into(stems["FX"], sub_boom, drop2_start, gain=0.60)
mix_into(stems["FX"], cinema_hit, drop2_start, gain=0.40)
mix_into(stems["FX"], to_np(impact_boom), drop2_start, gain=0.32)
mix_into(stems["DRUMS"], clap, drop2_start, gain=0.40)

# Vocal "ee" — drop 2 entry scream
mix_into(stems["VOCAL"], chop_ee, drop2_start, gain=0.32)

# Drums — heavier pattern with fibonacci_step energy
for rep in range(DROP2_BARS // 4 + 1):
    offset = drop2_start + samples_for(rep * 16)
    bars_left = min(4, DROP2_BARS - rep * 4)
    if bars_left > 0:
        g = fib_step_gain(rep * 4, DROP2_BARS, start=0.55, end=0.48)
        d2d = drum_pattern_drop2(bars_left)
        mix_into(stems["DRUMS"], d2d, offset, gain=g)

# Bass — maximum aggression with growl tear/yell rotation
for rep in range(DROP2_BARS // 4 + 1):
    offset = drop2_start + samples_for(rep * 16)
    bars_left = min(4, DROP2_BARS - rep * 4)
    if bars_left > 0:
        d2b = apply_sidechain(bass_drop2_pattern(bars_left), SC_HARD, SR)
        d2b = distort(d2b, drive=1.4)
        g = fib_step_gain(rep * 4, DROP2_BARS, start=0.55, end=0.48)
        mix_into(stems["BASS"], d2b, offset, gain=g)

# Layered riddim — growl-processed with rotation
for rep in range(DROP2_BARS // 4 + 1):
    offset = drop2_start + samples_for(rep * 16)
    bars_left = min(4, DROP2_BARS - rep * 4)
    if bars_left > 0:
        bar_samps = samples_for(bars_left * 4)
        r_heavy = riddim_heavy[:min(len(riddim_heavy), bar_samps)]
        r_stutter = riddim_stutter[:min(len(riddim_stutter), bar_samps)]
        r_heavy = apply_sidechain(r_heavy, SC_HARD, SR)
        r_stutter = apply_sidechain(r_stutter, SC_HARD, SR)
        mix_into(stems["RIDDIM"], r_heavy, offset, gain=0.28)
        mix_into(stems["RIDDIM"], r_stutter, offset, gain=0.20)

# Lead — ascending motif with DEEPER FM (Drop 2 variant)
for rep in range(DROP2_BARS // 4 + 1):
    offset = drop2_start + samples_for(rep * 16)
    bars_left = min(4, DROP2_BARS - rep * 4)
    if bars_left > 0:
        melody2 = lead_melody_drop2(bars_left)
        mix_into(stems["LEAD"], melody2, offset, gain=0.35)

# Formant melody — bigger in drop 2
for rep in range(DROP2_BARS // 4 + 1):
    offset = drop2_start + samples_for(rep * 16)
    bars_left = min(4, DROP2_BARS - rep * 4)
    if bars_left > 0:
        fmt2 = formant_melody(bars_left)
        mix_into(stems["FORMANT"], fmt2, offset, gain=0.26)

# Supersaw walls every bar — FM stab + saw chord
for bar in range(DROP2_BARS):
    stab_off = drop2_start + samples_for(bar * 4)
    mix_into(stems["CHORDS"], saw_chord, stab_off, gain=0.22)
    if bar % 2 == 0:
        wall_seg = saw_wall[:samples_for(4)]
        mix_into(stems["CHORDS"], wall_seg, stab_off, gain=0.18)

# FM stabs every 2 bars
for bar in range(0, DROP2_BARS, 2):
    stab_off = drop2_start + samples_for(bar * 4)
    mix_into(stems["CHORDS"], fm_hit, stab_off, gain=0.20)

# Dark drone underneath
for rep in range(DROP2_BARS // 4 + 1):
    offset = drop2_start + samples_for(rep * 16)
    bars_left = min(4, DROP2_BARS - rep * 4)
    if bars_left > 0:
        seg = dark_drone[:samples_for(bars_left * 4)]
        mix_into(stems["DRONE"], seg, offset, gain=0.16)

# Granular cloud — fractal texture in drop 2
gran_d2 = granular_cloud[:min(len(granular_cloud),
                               samples_for(DROP2_BARS * 4))]
mix_into(stems["GRANULAR"], gran_d2, drop2_start, gain=0.06)

# Beat repeat stutters within Drop 2 (Dojo: Resampling Chain philosophy)
for trans_bar in [5, 10, 15]:
    if trans_bar < DROP2_BARS:
        trans_off = drop2_start + samples_for(trans_bar * 4)
        # Apply phi-grid beat repeat to a bass chunk
        chunk_len = min(samples_for(4), len(stems["BASS"]) - trans_off)
        if chunk_len > 0:
            chunk = stems["BASS"][trans_off:trans_off + chunk_len].copy()
            br_chunk = np.array(apply_beat_repeat(chunk.tolist(), BR_SIXTEENTH, BPM, SR))
            mix_into(stems["FX"], br_chunk, trans_off, gain=0.20)

# Glitch transitions within drop 2
for trans_bar in [7, 14, 20]:
    if trans_bar < DROP2_BARS:
        mix_into(stems["FX"], glitch_trans,
                 drop2_start + samples_for(trans_bar * 4), gain=0.22)

# Stutter in last 2 bars
stutter_off2 = drop2_start + samples_for((DROP2_BARS - 2) * 4)
mix_into(stems["FX"], stutter, stutter_off2, gain=0.30)
mix_into(stems["FX"], stutter, stutter_off2 + samples_for(4), gain=0.34)

# Vocal "ah" chops — every 3 bars through the drop
for bar in range(0, DROP2_BARS, 3):
    mix_into(stems["VOCAL"], chop_ah,
             drop2_start + samples_for(bar * 4 + 2), gain=0.19)

cursor += samples_for(DROP2_BARS * 4)

# ── BREAK 2 (3 bars) — "The void between worlds" ─────────────────────
# SB10: floor 0.08 — near silence. Dojo: contrast makes drops hit harder.
print("  Rendering Break 2 (3 bars — near-silence floor 0.08)...")
break2_start = cursor

# Drone only — barely there
break2_drone = drone[:samples_for(BREAK2_BARS * 4)]
break2_drone = fade_in(break2_drone, duration_s=BAR * 0.5)
break2_drone = fade_out(break2_drone, duration_s=BAR * 2)
mix_into(stems["DRONE"], break2_drone, break2_start, gain=0.12)

# Granular freeze — time stops
gran_freeze_b2 = granular_freeze[:samples_for(BREAK2_BARS * 4)]
gran_freeze_b2 = lowpass(gran_freeze_b2, cutoff=0.06)
mix_into(stems["GRANULAR"], gran_freeze_b2, break2_start, gain=0.10)

# Single vocal — the apology moment
mix_into(stems["VOCAL"], chop_ah_long,
         break2_start + samples_for(1 * 4), gain=0.22)

cursor += samples_for(BREAK2_BARS * 4)

# ── BUILD 3 (5 bars) — "Final ascension" ──────────────────────────────
# The last push into the climax drop. All risers. 64th snare.
print("  Rendering Build 3 (5 bars — final push to climax)...")
build3_start = cursor

# ALL THREE RISERS stacked — pitch + harmonic + noise
riser3_pitch = pitch_riser[:samples_for(BUILD3_BARS * 4)]
riser3_harm = harmonic_riser[:samples_for(BUILD3_BARS * 4)]
riser3_noise = noise_riser[:samples_for(BUILD3_BARS * 4)]
mix_into(stems["RISER"], riser3_pitch, build3_start, gain=0.30)
mix_into(stems["RISER"], riser3_harm, build3_start, gain=0.28)
mix_into(stems["RISER"], riser3_noise, build3_start, gain=0.22)

# Snare roll — 64th notes in final bar (maximum tension)
build3_drums = drum_pattern_build(BUILD3_BARS)
mix_into(stems["DRUMS"], build3_drums, build3_start, gain=0.42)

# Beat repeat — aggressive 1/32 grid on the build
build3_br = np.array(apply_beat_repeat(build3_drums.tolist(), BR_AGGRESSIVE, BPM, SR))
mix_into(stems["DRUMS"], build3_br, build3_start, gain=0.12)

# Arp synth — fastest, most frantic
for bar in range(BUILD3_BARS):
    bo = build3_start + samples_for(bar * 4)
    g = phi_build_gain(bar, BUILD3_BARS, start=0.08, end=0.38)
    seg = arp_acid[:samples_for(4)]
    mix_into(stems["KS_STRINGS"], seg, bo, gain=g)

# Chord pad — power chord escalating
for bar in range(BUILD3_BARS):
    bo = build3_start + samples_for(bar * 4)
    g = phi_build_gain(bar, BUILD3_BARS, start=0.06, end=0.28)
    seg = chord_power[:samples_for(4)]
    mix_into(stems["PAD"], seg, bo, gain=g)

# Reverse hit + pitch dive before the final drop
rev3_off = build3_start + samples_for(BUILD3_BARS * 4) - len(reverse_hit)
if rev3_off > build3_start:
    mix_into(stems["FX"], reverse_hit, rev3_off, gain=0.60)
dive3_off = build3_start + samples_for((BUILD3_BARS - 1) * 4)
mix_into(stems["FX"], pitch_dive, dive3_off, gain=0.45)

# Vocal scream — raw desperation
for bar in range(BUILD3_BARS):
    g = phi_build_gain(bar, BUILD3_BARS, start=0.10, end=0.38)
    mix_into(stems["VOCAL"], chop_eh_stutter,
             build3_start + samples_for(bar * 4), gain=g)
# Final "ee" SCREAM
ee3_off = build3_start + samples_for(BUILD3_BARS * 4) - len(chop_ee) - SR // 8
if ee3_off > build3_start:
    mix_into(stems["VOCAL"], chop_ee, ee3_off, gain=0.48)

cursor += samples_for(BUILD3_BARS * 4)

# ── DROP 3 (13 bars) — "CLIMAX: THE APOLOGY THAT NEVER CAME" ─────────
# SB10: deepest FM, full growl palette rotation, maximum density.
# Dojo: 3rd drop IS the destination. Everything converges here.
print("  Rendering Drop 3 (13 bars — CLIMAX: deepest FM, full growl)...")
drop3_start = cursor

# MASSIVE climax impact
mix_into(stems["FX"], sub_boom, drop3_start, gain=0.65)
mix_into(stems["FX"], cinema_hit, drop3_start, gain=0.45)
mix_into(stems["FX"], to_np(impact_boom), drop3_start, gain=0.35)
mix_into(stems["DRUMS"], clap, drop3_start, gain=0.32)
mix_into(stems["VOCAL"], chop_ee, drop3_start, gain=0.35)

# Drums — DROP 3 pattern: double kick + 32nd cascades + fibonacci_step
for rep in range(DROP3_BARS // 4 + 1):
    offset = drop3_start + samples_for(rep * 16)
    bars_left = min(4, DROP3_BARS - rep * 4)
    if bars_left > 0:
        g = fib_step_gain(rep * 4, DROP3_BARS, start=0.48, end=0.40)
        d3d = drum_pattern_drop3(bars_left)
        mix_into(stems["DRUMS"], d3d, offset, gain=g)

# Bass — FULL 5-SOUND growl palette rotation (Subtronics signature)
for rep in range(DROP3_BARS // 4 + 1):
    offset = drop3_start + samples_for(rep * 16)
    bars_left = min(4, DROP3_BARS - rep * 4)
    if bars_left > 0:
        d3b = apply_sidechain(bass_drop3_pattern(bars_left), SC_HARD, SR)
        d3b = distort(d3b, drive=1.8)
        g = fib_step_gain(rep * 4, DROP3_BARS, start=0.58, end=0.50)
        mix_into(stems["BASS"], d3b, offset, gain=g)

# Riddim — all three patterns layered for maximum density
for rep in range(DROP3_BARS // 4 + 1):
    offset = drop3_start + samples_for(rep * 16)
    bars_left = min(4, DROP3_BARS - rep * 4)
    if bars_left > 0:
        bar_samps = samples_for(bars_left * 4)
        r_heavy = riddim_heavy[:min(len(riddim_heavy), bar_samps)]
        r_stutter = riddim_stutter[:min(len(riddim_stutter), bar_samps)]
        r_triplet = riddim_triplet[:min(len(riddim_triplet), bar_samps)]
        r_heavy = apply_sidechain(r_heavy, SC_HARD, SR)
        r_stutter = apply_sidechain(r_stutter, SC_HARD, SR)
        r_triplet = apply_sidechain(r_triplet, SC_HARD, SR)
        mix_into(stems["RIDDIM"], r_heavy, offset, gain=0.25)
        mix_into(stems["RIDDIM"], r_stutter, offset, gain=0.18)
        mix_into(stems["RIDDIM"], r_triplet, offset, gain=0.15)

# Lead — DEEPEST FM (Drop 3 variant: fm_depth=7.0!)
for rep in range(DROP3_BARS // 4 + 1):
    offset = drop3_start + samples_for(rep * 16)
    bars_left = min(4, DROP3_BARS - rep * 4)
    if bars_left > 0:
        melody3 = lead_melody_drop3(bars_left)
        mix_into(stems["LEAD"], melody3, offset, gain=0.38)

# Formant melody — maximum presence in climax
for rep in range(DROP3_BARS // 4 + 1):
    offset = drop3_start + samples_for(rep * 16)
    bars_left = min(4, DROP3_BARS - rep * 4)
    if bars_left > 0:
        fmt3 = formant_melody(bars_left)
        mix_into(stems["FORMANT"], fmt3, offset, gain=0.28)

# Supersaw walls + FM stabs — maximum harmonic density
for bar in range(DROP3_BARS):
    stab_off = drop3_start + samples_for(bar * 4)
    mix_into(stems["CHORDS"], saw_chord, stab_off, gain=0.24)
    wall_seg = saw_wall[:samples_for(4)]
    mix_into(stems["CHORDS"], wall_seg, stab_off, gain=0.20)
    if bar % 2 == 0:
        mix_into(stems["CHORDS"], fm_hit, stab_off, gain=0.22)

# Dark drone
for rep in range(DROP3_BARS // 4 + 1):
    offset = drop3_start + samples_for(rep * 16)
    bars_left = min(4, DROP3_BARS - rep * 4)
    if bars_left > 0:
        seg = dark_drone[:samples_for(bars_left * 4)]
        mix_into(stems["DRONE"], seg, offset, gain=0.18)

# Granular texture
gran_d3 = granular_cloud[:min(len(granular_cloud),
                               samples_for(DROP3_BARS * 4))]
mix_into(stems["GRANULAR"], gran_d3, drop3_start, gain=0.06)

# Beat repeat stutters mid-drop (Dojo: Clip Launching philosophy)
for trans_bar in [4, 8]:
    if trans_bar < DROP3_BARS:
        trans_off = drop3_start + samples_for(trans_bar * 4)
        chunk_len = min(samples_for(4), len(stems["BASS"]) - trans_off)
        if chunk_len > 0:
            chunk = stems["BASS"][trans_off:trans_off + chunk_len].copy()
            br_chunk = np.array(apply_beat_repeat(chunk.tolist(), BR_PHI, BPM, SR))
            mix_into(stems["FX"], br_chunk, trans_off, gain=0.22)

# Glitch transitions
for trans_bar in [6, 12]:
    if trans_bar < DROP3_BARS:
        mix_into(stems["FX"], glitch_trans,
                 drop3_start + samples_for(trans_bar * 4), gain=0.24)

# Final stutter into outro
stutter_off3 = drop3_start + samples_for((DROP3_BARS - 1) * 4)
mix_into(stems["FX"], stutter, stutter_off3, gain=0.30)

# Tape stop on the very last beat — everything cuts
tape_final = drop3_start + samples_for(DROP3_BARS * 4) - len(tape_stop)
if tape_final > drop3_start:
    mix_into(stems["FX"], tape_stop, tape_final, gain=0.35)

# Vocal "ah" accents + climax moment
for bar in range(0, DROP3_BARS, 2):
    mix_into(stems["VOCAL"], chop_ah,
             drop3_start + samples_for(bar * 4 + 1.5), gain=0.20)
# The "apology" vocal at the golden section
mix_into(stems["VOCAL"], chop_ah_long,
         drop3_start + samples_for(6 * 4), gain=0.24)

cursor += samples_for(DROP3_BARS * 4)

# ── OUTRO (8 bars) — "The fracture closes" ────────────────────────
print("  Rendering Outro (8 bars — dissolution)...")
outro_start = cursor

# Granular freeze — time stops
gran_freeze_seg = granular_freeze[:samples_for(OUTRO_BARS * 4)]
gran_freeze_seg = fade_out(gran_freeze_seg, duration_s=BAR * 5)
mix_into(stems["GRANULAR"], gran_freeze_seg, outro_start, gain=0.22)

# Dark pad dissolving
outro_pad = dark_pad[:samples_for(OUTRO_BARS * 4)]
outro_pad = fade_out(outro_pad, duration_s=BAR * 6)
outro_pad = lowpass(outro_pad, cutoff=0.08)
mix_into(stems["PAD"], outro_pad, outro_start, gain=0.25)

# Drone decaying slowly
outro_drone = drone[:samples_for(OUTRO_BARS * 4)]
outro_drone = fade_out(outro_drone, duration_s=BAR * 7)
mix_into(stems["DRONE"], outro_drone, outro_start, gain=0.22)

# Sparse hats fading
outro_drums = drum_pattern_intro(OUTRO_BARS)
outro_drums = fade_out(outro_drums, duration_s=BAR * 5)
mix_into(stems["DRUMS"], outro_drums, outro_start, gain=0.12)

# Sub decaying
outro_sub = to_np(synthesize_bass(BassPreset(
    name="V2OutroSub", bass_type="sub_sine", frequency=KEY_FREQS["D1"],
    duration_s=OUTRO_BARS * BAR, attack_s=0.01,
    release_s=OUTRO_BARS * BAR * 0.85
)))
outro_sub = fade_out(outro_sub, duration_s=BAR * 6)
mix_into(stems["BASS"], outro_sub, outro_start, gain=0.16)

# KS arpeggio — final whispers (retained from v1: VIP 38.2%)
for rep in range(OUTRO_BARS // 4):
    offset = outro_start + samples_for(rep * 16)
    arp = ks_arpeggio(4)
    arp = lowpass(arp, cutoff=0.12)
    arp = fade_out(arp, duration_s=BAR * 3)
    mix_into(stems["KS_STRINGS"], arp, offset, gain=0.14)

# Pitch dive — final descent
mix_into(stems["FX"], pitch_dive,
         outro_start + samples_for(5 * 4), gain=0.25)

# "ah_long" — the apology that never came
mix_into(stems["VOCAL"], chop_ah_long,
         outro_start + samples_for(1 * 4), gain=0.24)
mix_into(stems["VOCAL"], chop_ah_long,
         outro_start + samples_for(4 * 4), gain=0.20)
# Final fading whisper
final_chop = chop_ah_long * 0.5  # quieter copy
final_chop = fade_out(final_chop, duration_s=BAR * 2)
mix_into(stems["VOCAL"], final_chop,
         outro_start + samples_for(6 * 4), gain=0.14)


# ════════════════════════════════════════════════════════════════════
#  DSP POST-PROCESSING — DOJO: Separate mixing pass
# ════════════════════════════════════════════════════════════════════
print()
print("  Applying DSP processing (DOJO: separate mixing pass)...")

# Sidechain on CHORDS and PAD in drops for kick clarity
stems["CHORDS"] = apply_sidechain(stems["CHORDS"], SC_PUMP, SR)
stems["PAD"] = apply_sidechain(stems["PAD"], SC_PUMP, SR)

# Reverb/delay — space and depth
stems["PAD"] = apply_hall(stems["PAD"], HALL_VERB, SR)
stems["GRANULAR"] = apply_hall(stems["GRANULAR"], HALL_VERB, SR)
stems["FORMANT"] = apply_room(stems["FORMANT"], ROOM_VERB, SR)
stems["KS_STRINGS"] = apply_room(stems["KS_STRINGS"], ROOM_VERB, SR)
stems["LEAD"] = apply_room(stems["LEAD"], ROOM_VERB, SR)
stems["VOCAL"] = apply_room(stems["VOCAL"], ROOM_VERB, SR)
stems["CHORDS"] = apply_hall(stems["CHORDS"], HALL_VERB, SR)

# Growl processing on RIDDIM stem — additional resampling character
stems["RIDDIM"] = waveshape_distortion(stems["RIDDIM"], drive=0.5, mix=0.3)

print("    PAD         -> apply_hall (decay=3.2s, mix=0.28)")
print("    GRANULAR    -> apply_hall (decay=3.2s, mix=0.28)")
print("    FORMANT     -> apply_room (decay=0.6s, mix=0.18)")
print("    KS_STRINGS  -> apply_room (decay=0.6s, mix=0.18)")
print("    LEAD        -> apply_room (decay=0.6s, mix=0.18)")
print("    VOCAL       -> apply_room (decay=0.6s, mix=0.18)")
print("    CHORDS      -> apply_hall (decay=3.2s, mix=0.28)")
print("    RIDDIM      -> growl waveshape (drive=0.5, mix=0.3)")


# ════════════════════════════════════════════════════════════════════
#  EXPORT STEMS + MASTERED MIXDOWN + MIDI + ALS
# ════════════════════════════════════════════════════════════════════
print()
print("  Bouncing stems...")

os.makedirs("output/stems", exist_ok=True)
stem_paths: list[str] = []

for name in STEM_NAMES:
    buf = stems[name]
    path = f"output/stems/apology_v2_{name}.wav"

    peak = float(np.max(np.abs(buf))) if len(buf) > 0 else 1.0
    # Only clip-protect, don't normalize each stem independently
    # This preserves relative mix balance between stems
    gain = min(1.0, 0.95 / peak) if peak > 0 else 1.0

    int_buf = np.clip(buf * gain * 32767.0, -32768, 32767).astype(np.int16)

    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(int_buf.tobytes())

    fsize = os.path.getsize(path)
    peak_db = 20.0 * math.log10(peak) if peak > 0 else -120.0
    stem_paths.append(os.path.abspath(path))
    print(f"    {name:24s}  {len(buf)/SR:.1f}s  {peak_db:.1f}dB  "
          f"{fsize/1024/1024:.1f}MB")

# ── Stereo mixdown with constant-power pan law ──────────────────────
print()
print("  Stereo mixdown...")

mix_L = np.zeros(total_samples)
mix_R = np.zeros(total_samples)

for name, buf in stems.items():
    pan = STEM_PAN.get(name, 0.0)
    theta = (pan + 1.0) * 0.5 * (math.pi / 2.0)
    gain_l = math.cos(theta)
    gain_r = math.sin(theta)
    n = min(len(buf), total_samples)
    mix_L[:n] += buf[:n] * gain_l
    mix_R[:n] += buf[:n] * gain_r

stereo = np.column_stack((mix_L, mix_R))

# ── Master via mastering_chain ──────────────────────────────────────
print("  Mastering via engine.mastering_chain...")

master_settings = dubstep_master_settings()
mastered, master_report = master(stereo, SR, master_settings)

if mastered.ndim == 2:
    master_L = mastered[:, 0]
    master_R = mastered[:, 1]
else:
    master_L = mastered
    master_R = mastered

print(f"    Target LUFS: {master_settings.target_lufs}")
print(f"    Ceiling:     {master_settings.ceiling_db} dB")
print(f"    Stereo:      {master_settings.stereo_width:.2f}")

# Write mastered stereo WAV
os.makedirs("output", exist_ok=True)
output_path = "output/apology_never_came_v2.wav"

stereo_int = np.empty(total_samples * 2, dtype=np.int16)
stereo_int[0::2] = np.clip(master_L[:total_samples] * 32767.0,
                            -32768, 32767).astype(np.int16)
stereo_int[1::2] = np.clip(master_R[:total_samples] * 32767.0,
                            -32768, 32767).astype(np.int16)

with wave.open(output_path, "w") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(stereo_int.tobytes())

# ── MIDI export ─────────────────────────────────────────────────────
print("  Exporting MIDI...")
os.makedirs("output/midi", exist_ok=True)

# Bass MIDI
bass_events: list[NoteEvent] = []
for bar in range(total_bars):
    bass_events.append(NoteEvent(pitch=MIDI["D1"], start_beat=bar * 4,
                                 duration_beats=2.0, velocity=100))

# Lead MIDI — ascending motif A3 → C4 → D4 → F4 (all 3 drops)
lead_events: list[NoteEvent] = []
drop1_bar_start = INTRO_BARS + BUILD1_BARS
drop2_bar_start = drop1_bar_start + DROP1_BARS + BREAK1_BARS + BUILD2_BARS
drop3_bar_start = (drop2_bar_start + DROP2_BARS + BREAK2_BARS + BUILD3_BARS)
for drop_start, drop_len in [(drop1_bar_start, DROP1_BARS),
                              (drop2_bar_start, DROP2_BARS),
                              (drop3_bar_start, DROP3_BARS)]:
    for bar in range(drop_len):
        b = (drop_start + bar) * 4
        lead_events.append(NoteEvent(pitch=MIDI["A3"], start_beat=b + 0.0,
                                     duration_beats=0.5, velocity=85))
        lead_events.append(NoteEvent(pitch=MIDI["C4"], start_beat=b + 1.0,
                                     duration_beats=0.5, velocity=88))
        lead_events.append(NoteEvent(pitch=MIDI["D4"], start_beat=b + 2.0,
                                     duration_beats=0.5, velocity=92))
        lead_events.append(NoteEvent(pitch=MIDI["F4"], start_beat=b + 3.0,
                                     duration_beats=0.5, velocity=90))

# KS String MIDI — arpeggio (intro + break1)
ks_events: list[NoteEvent] = []
arp_seq = ["D3", "F3", "A3", "D4", "C4", "Bb3", "G3", "E3"]
# Intro KS notes (bars 4-7)
for bar in range(4, INTRO_BARS):
    b = bar * 4
    for q in range(4):
        note_name = arp_seq[(bar * 2 + q) % len(arp_seq)]
        ks_events.append(NoteEvent(
            pitch=MIDI[note_name], start_beat=b + q,
            duration_beats=1.0, velocity=70))
# Break 1 KS notes
break1_bar_start = INTRO_BARS + BUILD1_BARS + DROP1_BARS
for bar in range(BREAK1_BARS):
    b = (break1_bar_start + bar) * 4
    for q in range(4):
        note_name = arp_seq[(bar + q) % len(arp_seq)]
        ks_events.append(NoteEvent(
            pitch=MIDI[note_name], start_beat=b + q,
            duration_beats=1.0, velocity=65))

# Chord MIDI — Dm stabs (all 3 drops)
chord_events: list[NoteEvent] = []
dm_chord = [MIDI["D3"], MIDI["F3"], MIDI["A3"]]
for drop_start, drop_len in [(drop1_bar_start, DROP1_BARS),
                              (drop2_bar_start, DROP2_BARS),
                              (drop3_bar_start, DROP3_BARS)]:
    for bar in range(drop_len):
        b = (drop_start + bar) * 4
        for pitch in dm_chord:
            chord_events.append(NoteEvent(
                pitch=pitch, start_beat=b,
                duration_beats=0.5, velocity=82))

midi_tracks = [
    ("Bass", bass_events),
    ("Lead", lead_events),
    ("KS_Strings", ks_events),
    ("Chords", chord_events),
]

midi_path = "output/midi/apology_never_came_v2.mid"
write_midi_file(midi_tracks, midi_path, bpm=BPM)
total_notes = sum(len(evts) for _, evts in midi_tracks)
print(f"    {midi_path}  ({total_notes} notes)")

# ── Ableton Live Set ────────────────────────────────────────────────
print("  Generating Ableton Live project...")

stem_colors = {
    "DRUMS": 1, "BASS": 3, "RIDDIM": 5, "LEAD": 12, "FORMANT": 14,
    "KS_STRINGS": 16, "CHORDS": 20, "PAD": 24, "DRONE": 28,
    "RISER": 32, "VOCAL": 36, "FX": 40, "GRANULAR": 44,
}

als_tracks = []
for idx, name in enumerate(STEM_NAMES):
    stem_abs = os.path.abspath(f"output/stems/apology_v2_{name}.wav")
    als_tracks.append(ALSTrack(
        name=name,
        track_type="audio",
        color=stem_colors.get(name, 0),
        volume_db=0.0,
        pan=STEM_PAN.get(name, 0.0),
        clip_names=[name],
        clip_paths=[stem_abs],
    ))

als_tracks.append(ALSTrack(
    name="REVERB", track_type="return", color=50,
    device_names=["Reverb"],
))
als_tracks.append(ALSTrack(
    name="DELAY", track_type="return", color=52,
    device_names=["Delay"],
))

als_scenes = [
    ALSScene(name="INTRO", tempo=float(BPM)),
    ALSScene(name="BUILD_1", tempo=float(BPM)),
    ALSScene(name="DROP_1", tempo=float(BPM)),
    ALSScene(name="BREAK_1", tempo=float(BPM)),
    ALSScene(name="BUILD_2", tempo=float(BPM)),
    ALSScene(name="DROP_2", tempo=float(BPM)),
    ALSScene(name="BREAK_2", tempo=float(BPM)),
    ALSScene(name="BUILD_3", tempo=float(BPM)),
    ALSScene(name="DROP_3", tempo=float(BPM)),
    ALSScene(name="OUTRO", tempo=float(BPM)),
]

project = ALSProject(
    name="Apology_Never_Came_V2",
    bpm=float(BPM),
    tracks=als_tracks,
    scenes=als_scenes,
    notes="Can You See The Apology That Never Came (Dojo Rework) | "
          "D minor | 150 BPM | 432 Hz | PACK_WEAPON 89 bars | v2",
)

os.makedirs("output/ableton", exist_ok=True)
als_path = "output/ableton/Apology_Never_Came_V2.als"
write_als(project, als_path)

# ── Summary ─────────────────────────────────────────────────────────
duration = total_samples / SR
file_size = os.path.getsize(output_path)
stem_dir_size = sum(
    os.path.getsize(os.path.join("output/stems", f))
    for f in os.listdir("output/stems")
    if f.startswith("apology_v2_") and f.endswith(".wav")
)

print()
print("=" * 60)
print('  "Can You See The Apology That Never Came"')
print("  v2 — DOJO REWORK (PACK_WEAPON × SB10)")
print("=" * 60)
print(f"  Format:   16-bit WAV @ {SR} Hz")
print(f"  BPM:      {BPM}  |  Key: D minor  |  Tuning: 432 Hz")
print(f"  Duration: {duration:.1f}s "
      f"({int(duration // 60)}:{int(duration % 60):02d})")
print(f"  Bars:     {total_bars}  "
      f"(Golden Section Point: bar ~{golden_section_bar})")
print(f"  Bar counts (PACK_WEAPON): {INTRO_BARS}/{BUILD1_BARS}/"
      f"{DROP1_BARS}/{BREAK1_BARS}/{BUILD2_BARS}/{DROP2_BARS}/"
      f"{BREAK2_BARS}/{BUILD3_BARS}/{DROP3_BARS}/{OUTRO_BARS}")
print()
print("  Dojo Rework — What Changed:")
print("    * PACK_WEAPON structure: 89 bars (Fibonacci)")
print("    * 3 drops (13/21/13) — was 2 drops (12/20)")
print("    * Growl resampler: 5 bass variants via multi-pass chains")
print("    * Bass rotation: 3/4/5 sounds cycling per drop")
print("    * FM depth increasing per drop (3.0 -> 5.0 -> 7.0)")
print("    * Beat repeat: phi grid + 1/16 + 1/32 aggressive")
print("    * Fibonacci-step energy in drops (1.0 -> 0.88 decay)")
print("    * Phi-curve acceleration in builds")
print("    * Break energy ceiling: 0.35 / 0.08 (near-silence)")
print("    * PSBS-aware gains (no clipping)")
print("    * Dojo: separate mixing pass, resampling chains, VIP 38.2%")
print("    * KS arpeggio whispers retained (VIP: 38.2% from v1)")
print("    * drum_pattern_drop3: double kick, 32nd hat cascades")
print()
print("  DOCTRINE Compliance:")
print("    + GALATCIA real drum samples (kick/snare/clap/hat/impact)")
print("    + Serum 2 patch definitions exported (JSON)")
print("    + Mastering chain: EQ -> Compress -> Stereo -> LUFS -> Limit")
print("    + Sidechain pump via engine.sidechain (phi-curve)")
print("    + Reverb via engine.reverb_delay (phi-spaced reflections)")
print("    + MIDI export for all melodic content (3 drops)")
print("    + ALS with AudioClip/SampleRef (not hollow)")
print(f"    + Golden Section Point at bar ~{golden_section_bar}")
print("    + 432 Hz tuning throughout")
print("    + PACK_WEAPON Fibonacci structure: 8/5/13/5/8/21/3/5/13/8")
print()
print(f"  Stems:    {len(STEM_NAMES)} tracks in output/stems/")
for name in STEM_NAMES:
    print(f"            - {name}")
print(f"  Stems:    {stem_dir_size / 1024 / 1024:.1f} MB total")
print(f"  Mixdown:  {output_path} ({file_size / 1024 / 1024:.1f} MB)")
print(f"  MIDI:     {midi_path}")
print(f"  Serum 2:  output/serum2/apology_v2_patches.json")
print(f"  Ableton:  {als_path}")
print()
print("  Mood:     Defiance x Fracture (60/40)")
print("  Modules:  GALATCIA + Serum2 + Granular + ChordPad + FormantSynth")
print("            + RiddimEngine + KarplusStrong + ArpSynth + TransitionFX")
print("            + GrowlResampler + BeatRepeat + MasteringChain")
print("            + Sidechain + Reverb + StereoImager")
print("            + MidiExport + ALSGenerator")
print("=" * 60)

# ── Open in Ableton Live ────────────────────────────────────────────
print()
print("  Opening Ableton Live 12...")
subprocess.Popen(["cmd", "/c", "start", "", os.path.abspath(als_path)],
                 creationflags=0x08000000)  # CREATE_NO_WINDOW
print("  Done. All stems + MIDI in output/ — load into Live.")
print()
