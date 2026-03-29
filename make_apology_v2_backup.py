#!/usr/bin/env python3
"""DUBFORGE — "Can You See The Apology That Never Came"

Renders the full track using DUBFORGE engine modules.

    Title:    Can You See The Apology That Never Came
    BPM:      140 (halftime dubstep)
    Key:      D minor
    Tuning:   432 Hz
    Duration: ~4 min (72 bars)
    Mood:     Melancholy × Epic (55/45 blend)

    Structure:
        Intro      8 bars  — Evolving drone + reversed pad + space texture
        Verse 1    8 bars  — Pluck arp + sub + "ah" vocal chops
        Build 1    4 bars  — Pitch riser + snare roll + "eh" stutter chops
        Drop 1    16 bars  — Full halftime + wobble/neuro bass + screech lead
        Break      8 bars  — Lush pad + pluck melody + "oo" whisper chop
        Build 2    4 bars  — Harmonic build riser + darker stutter vocal
        Drop 2    16 bars  — Heavier bass + distortion + supersaw stabs
        Outro      8 bars  — Dark drone decay + final "ah" chop fading

    Lyrics placement (for later vocal tracking):
        Verse 1:   "In the hollow of midnight..." over bars 9-16
        Build 1:   "The apology that never came" vocal chop trigger
        Drop 1:    Screech lead carries the chorus melody
        Break:     "Phantoms of us whisper..." over bars 45-52
        Bridge:    "Perhaps the agony lingers..." woven into Build 2
        Drop 2:    "Forged my defiance" — the triumphant final chorus
        Outro:     "The apology that never came" — last whisper

Output:
    output/stems/apology_*.wav   — 11 individual stem WAVs (mono, normalized)
    output/apology_never_came.wav — stereo mixdown (16-bit, 44100 Hz)
    output/ableton/Apology_Never_Came_STEMS.als — Ableton Live set with stems
"""

import math
import os
import struct
import subprocess
import wave

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import numpy as np

# ── DUBFORGE engine imports ─────────────────────────────────────────
from engine.bass_oneshot import BassPreset, synthesize_bass
from engine.lead_synth import LeadPreset, synthesize_screech_lead, synthesize_pluck_lead
from engine.pad_synth import PadPreset, synthesize_dark_pad, synthesize_lush_pad
from engine.perc_synth import PercPreset, synthesize_kick, synthesize_snare, synthesize_hat, synthesize_clap
from engine.noise_generator import NoisePreset, synthesize_noise
from engine.impact_hit import ImpactPreset, synthesize_sub_boom, synthesize_cinematic_hit, synthesize_reverse_hit
from engine.fm_synth import FMPatch, FMOperator, render_fm
from engine.supersaw import SupersawPatch, render_supersaw_mono
from engine.glitch_engine import GlitchPreset, synthesize_stutter, synthesize_bitcrush
from engine.drone_synth import DronePreset, synthesize_drone
from engine.riser_synth import RiserPreset, synthesize_riser
from engine.vocal_chop import VocalChop, synthesize_chop
from engine.ambient_texture import TexturePreset, synthesize_texture
from engine.als_generator import ALSProject, ALSTrack, ALSScene, write_als

# ── Constants ────────────────────────────────────────────────────────
SR = 44100
BPM = 140
BEAT = 60.0 / BPM                    # seconds per beat
BAR = BEAT * 4                       # seconds per bar
PHI = 1.6180339887

# Key of D minor — D E F G A Bb C (432 Hz tuning)
# D2 = 72.08 Hz (432 tuning), D3 = 144.16, D4 = 288.33
A4 = 432.0
KEY_FREQS = {
    "D1": A4 * 2 ** (-31 / 12),  # ~36.04
    "F1": A4 * 2 ** (-28 / 12),  # ~42.86
    "A1": A4 * 2 ** (-24 / 12),  # ~54.00
    "Bb1": A4 * 2 ** (-23 / 12), # ~57.21
    "C2": A4 * 2 ** (-21 / 12),  # ~64.22
    "D2": A4 * 2 ** (-19 / 12),  # ~72.08
    "E2": A4 * 2 ** (-17 / 12),  # ~80.91
    "F2": A4 * 2 ** (-16 / 12),  # ~85.72
    "G2": A4 * 2 ** (-14 / 12),  # ~96.22
    "A2": A4 * 2 ** (-12 / 12),  # ~108.00
    "Bb2": A4 * 2 ** (-11 / 12), # ~114.42
    "C3": A4 * 2 ** (-9 / 12),   # ~128.43
    "D3": A4 * 2 ** (-7 / 12),   # ~144.16
    "E3": A4 * 2 ** (-5 / 12),   # ~161.82
    "F3": A4 * 2 ** (-4 / 12),   # ~171.44
    "G3": A4 * 2 ** (-2 / 12),   # ~192.43
    "A3": A4 * 2 ** (0 / 12),    # 216.00 (octave below A4)
    "Bb3": A4 * 2 ** (1 / 12),   # ~228.84  — wait, A3 should be 216
    "C4": A4 * 2 ** (3 / 12),    # ~256.87
    "D4": A4 * 2 ** (5 / 12),    # ~288.33
    "E4": A4 * 2 ** (7 / 12),    # ~323.63
    "F4": A4 * 2 ** (8 / 12),    # ~342.88
    "G4": A4 * 2 ** (10 / 12),   # ~384.87
    "A4": A4,                      # 432.00
    "Bb4": A4 * 2 ** (1 / 12),   # ~457.69
}
# Fix: A3 is one octave below A4
KEY_FREQS["A3"] = A4 / 2  # 216.0
KEY_FREQS["Bb3"] = A4 * 2 ** (-11 / 12)  # ~228.84


def samples_for(beats: float) -> int:
    """Number of samples for given beat count."""
    return int(beats * BEAT * SR)


def silence(beats: float) -> list[float]:
    """Generate silence for given beat count."""
    return [0.0] * samples_for(beats)


def to_list(arr) -> list[float]:
    """Convert np.ndarray or list to list[float]."""
    if isinstance(arr, np.ndarray):
        return arr.tolist()
    return list(arr)


def mix_into(target: list[float], source: list[float], offset: int,
             gain: float = 1.0):
    """Mix source into target at sample offset (in-place)."""
    for i, s in enumerate(source):
        pos = offset + i
        if pos < len(target):
            target[pos] += s * gain


def render_section(bars: int) -> list[float]:
    """Create a silent buffer for N bars."""
    return [0.0] * samples_for(bars * 4)


def fade_in(signal: list[float], duration_s: float = 0.5) -> list[float]:
    """Apply linear fade in."""
    n = int(duration_s * SR)
    out = list(signal)
    for i in range(min(n, len(out))):
        out[i] *= i / n
    return out


def fade_out(signal: list[float], duration_s: float = 0.5) -> list[float]:
    """Apply linear fade out."""
    n = int(duration_s * SR)
    out = list(signal)
    length = len(out)
    for i in range(min(n, length)):
        out[length - 1 - i] *= i / n
    return out


def lowpass(signal: list[float], cutoff: float = 0.3) -> list[float]:
    """Simple one-pole lowpass filter."""
    out = [0.0] * len(signal)
    out[0] = signal[0] * cutoff
    for i in range(1, len(signal)):
        out[i] = out[i - 1] + cutoff * (signal[i] - out[i - 1])
    return out


def distort(signal: list[float], drive: float = 2.0) -> list[float]:
    """Soft-clip distortion."""
    return [math.tanh(s * drive) for s in signal]


def sidechain_pump(signal: list[float], beats: int,
                   depth: float = 0.7) -> list[float]:
    """Apply sidechain-style pumping envelope synced to quarter notes."""
    out = list(signal)
    beat_samples = samples_for(1)
    for i in range(len(out)):
        pos_in_beat = (i % beat_samples) / beat_samples
        if pos_in_beat < 0.05:
            env = 1.0 - depth
        elif pos_in_beat < 0.3:
            env = (1.0 - depth) + depth * ((pos_in_beat - 0.05) / 0.25)
        else:
            env = 1.0
        out[i] *= env
    return out


# ════════════════════════════════════════════════════════════════════
#  SOUND DESIGN — Pre-render all elements
# ════════════════════════════════════════════════════════════════════

print("=" * 60)
print('  DUBFORGE — "Can You See The Apology That Never Came"')
print("=" * 60)
print(f"  BPM: {BPM}  |  Key: D minor  |  Tuning: 432 Hz  |  SR: {SR}")
print()

# ── DRUMS ────────────────────────────────────────────────────────────
print("  [1/10] Drums...")

kick = to_list(synthesize_kick(PercPreset(
    name="ApologyKick", perc_type="kick", duration_s=0.45,
    pitch=50.0, decay_s=0.35, tone_mix=0.85, brightness=0.35,
    distortion=0.15, attack_s=0.001
)))

snare = to_list(synthesize_snare(PercPreset(
    name="ApologySnare", perc_type="snare", duration_s=0.28,
    pitch=175.0, decay_s=0.18, tone_mix=0.45, brightness=0.75,
    distortion=0.08, attack_s=0.001
)))

clap = to_list(synthesize_clap(PercPreset(
    name="Clap", perc_type="clap", duration_s=0.22,
    pitch=200.0, decay_s=0.14, tone_mix=0.2, brightness=0.85,
    distortion=0.0, attack_s=0.002
)))

hat_closed = to_list(synthesize_hat(PercPreset(
    name="HatClosed", perc_type="hat", duration_s=0.06,
    pitch=8000.0, decay_s=0.04, tone_mix=0.1, brightness=0.9,
    distortion=0.0, attack_s=0.001
)))

hat_open = to_list(synthesize_hat(PercPreset(
    name="HatOpen", perc_type="hat", duration_s=0.28,
    pitch=7200.0, decay_s=0.22, tone_mix=0.1, brightness=0.85,
    distortion=0.0, attack_s=0.001
)))

# ── BASS ─────────────────────────────────────────────────────────────
print("  [2/10] Bass...")

sub_bass = to_list(synthesize_bass(BassPreset(
    name="Sub", bass_type="sub_sine", frequency=KEY_FREQS["D1"],
    duration_s=BEAT * 2, attack_s=0.005, release_s=0.15, distortion=0.0
)))

wobble_bass = to_list(synthesize_bass(BassPreset(
    name="Wobble", bass_type="wobble", frequency=KEY_FREQS["D2"],
    duration_s=BEAT * 2, attack_s=0.01, release_s=0.2,
    fm_ratio=PHI, fm_depth=3.5, distortion=0.3, filter_cutoff=0.55
)))

growl_bass = to_list(synthesize_bass(BassPreset(
    name="Growl", bass_type="growl", frequency=KEY_FREQS["D2"],
    duration_s=BEAT, attack_s=0.005, release_s=0.1,
    fm_ratio=2.0, fm_depth=5.5, distortion=0.5, filter_cutoff=0.65
)))

neuro_bass = to_list(synthesize_bass(BassPreset(
    name="Neuro", bass_type="neuro", frequency=KEY_FREQS["D2"],
    duration_s=BEAT, attack_s=0.003, release_s=0.08,
    fm_ratio=3.0, fm_depth=4.5, distortion=0.55, filter_cutoff=0.45
)))

reese_bass = to_list(synthesize_bass(BassPreset(
    name="Reese", bass_type="reese", frequency=KEY_FREQS["D2"],
    duration_s=BAR, attack_s=0.4, release_s=0.6,
    detune_cents=18.0, filter_cutoff=0.35
)))

# ── LEADS ────────────────────────────────────────────────────────────
print("  [3/10] Leads...")

# D minor motif: D4 - C4 - Bb3 - A3 (descending — falling, like hope)
screech_d = to_list(synthesize_screech_lead(LeadPreset(
    name="ScreechD", lead_type="screech", frequency=KEY_FREQS["D4"],
    duration_s=BEAT * 0.5, attack_s=0.005, decay_s=0.05,
    sustain=0.6, release_s=0.08, filter_cutoff=0.88,
    resonance=0.5, distortion=0.35
)))

screech_c = to_list(synthesize_screech_lead(LeadPreset(
    name="ScreechC", lead_type="screech", frequency=KEY_FREQS["C4"],
    duration_s=BEAT * 0.5, attack_s=0.005, decay_s=0.05,
    sustain=0.6, release_s=0.08, filter_cutoff=0.85,
    resonance=0.45, distortion=0.3
)))

screech_bb = to_list(synthesize_screech_lead(LeadPreset(
    name="ScreechBb", lead_type="screech", frequency=KEY_FREQS["Bb3"],
    duration_s=BEAT * 0.75, attack_s=0.005, decay_s=0.06,
    sustain=0.55, release_s=0.1, filter_cutoff=0.82,
    resonance=0.4, distortion=0.3
)))

screech_a = to_list(synthesize_screech_lead(LeadPreset(
    name="ScreechA", lead_type="screech", frequency=KEY_FREQS["A3"],
    duration_s=BEAT * 0.75, attack_s=0.005, decay_s=0.06,
    sustain=0.5, release_s=0.12, filter_cutoff=0.8,
    resonance=0.4, distortion=0.25
)))

# Pluck melody notes for verse/break arpeggio
pluck_notes = {}
for note_name in ["D3", "F3", "A3", "C4", "D4", "Bb3", "G3", "E3"]:
    pluck_notes[note_name] = to_list(synthesize_pluck_lead(LeadPreset(
        name=f"Pluck_{note_name}", lead_type="pluck",
        frequency=KEY_FREQS[note_name],
        duration_s=BEAT * 0.9, attack_s=0.002, decay_s=0.2,
        sustain=0.25, release_s=0.3, filter_cutoff=0.6, resonance=0.2
    )))

# Supersaw chord stab (Dm — D, F, A)
saw_chord = render_supersaw_mono(SupersawPatch(
    name="DmChordStab", n_voices=7, detune_cents=28.0,
    mix=0.7, cutoff_hz=5500.0, resonance=0.25,
    attack=0.005, decay=0.18, sustain=0.55, release=0.25,
    master_gain=0.65
), freq=KEY_FREQS["D3"], duration=BEAT * 0.75)

# FM metallic — sharp edge of betrayal
fm_hit = render_fm(FMPatch(
    name="FMBetrayal",
    operators=[
        FMOperator(freq_ratio=1.0, amplitude=1.0, mod_index=6.0,
                   envelope=(0.001, 0.06, 0.0, 0.12)),
        FMOperator(freq_ratio=PHI, amplitude=0.85, mod_index=3.5,
                   envelope=(0.001, 0.09, 0.0, 0.18)),
    ],
    algorithm=0, master_gain=0.65
), freq=KEY_FREQS["D3"], duration=0.35)

# ── PADS ─────────────────────────────────────────────────────────────
print("  [4/10] Pads...")

dark_pad = to_list(synthesize_dark_pad(PadPreset(
    name="GriefPad", pad_type="dark", frequency=KEY_FREQS["D3"],
    duration_s=BAR * 8, detune_cents=14.0, filter_cutoff=0.3,
    attack_s=1.5, release_s=2.5, reverb_amount=0.6, brightness=0.25
)))

lush_pad = to_list(synthesize_lush_pad(PadPreset(
    name="YearningPad", pad_type="lush", frequency=KEY_FREQS["F3"],
    duration_s=BAR * 8, detune_cents=16.0, filter_cutoff=0.45,
    attack_s=1.0, release_s=2.0, reverb_amount=0.65, brightness=0.4
)))

# ── DRONE ────────────────────────────────────────────────────────────
print("  [5/10] Drone...")

# Evolving drone — the void underneath
drone = to_list(synthesize_drone(DronePreset(
    name="VoidDrone", drone_type="evolving",
    frequency=KEY_FREQS["D1"], duration_s=BAR * 8,
    num_voices=7, detune_cents=8.0, brightness=0.2,
    movement=0.4, attack_s=2.0, release_s=3.0,
    distortion=0.05, reverb_amount=0.5
)))

# Dark drone for drops
dark_drone = to_list(synthesize_drone(DronePreset(
    name="DarkUndertow", drone_type="dark",
    frequency=KEY_FREQS["D1"], duration_s=BAR * 4,
    num_voices=5, brightness=0.15, movement=0.2,
    attack_s=0.5, release_s=1.0, distortion=0.1
)))

# ── RISERS ───────────────────────────────────────────────────────────
print("  [6/10] Risers...")

# Build 1: pitch rise — tension before first drop
pitch_riser = to_list(synthesize_riser(RiserPreset(
    name="PitchRise1", riser_type="pitch_rise",
    duration_s=BAR * 4,
    start_freq=80.0, end_freq=3000.0,
    brightness=0.7, intensity=0.85, distortion=0.05
)))

# Build 2: harmonic build — darker, more intense
harmonic_riser = to_list(synthesize_riser(RiserPreset(
    name="HarmonicBuild", riser_type="harmonic_build",
    duration_s=BAR * 4,
    start_freq=60.0, end_freq=4000.0,
    brightness=0.6, intensity=0.9, distortion=0.1
)))

# Noise sweep for texture risers
noise_riser = to_list(synthesize_riser(RiserPreset(
    name="NoiseSweep", riser_type="noise_sweep",
    duration_s=BAR * 4,
    start_freq=100.0, end_freq=5000.0,
    brightness=0.5, intensity=0.7
)))

# ── FX & IMPACTS ─────────────────────────────────────────────────────
print("  [7/10] FX & impacts...")

sub_boom = to_list(synthesize_sub_boom(ImpactPreset(
    name="DropBoom", impact_type="sub_boom", duration_s=2.5,
    frequency=KEY_FREQS["D1"], decay_s=2.0, intensity=0.95,
    reverb_amount=0.35
)))

cinema_hit = to_list(synthesize_cinematic_hit(ImpactPreset(
    name="CinemaHit", impact_type="cinematic_hit", duration_s=1.8,
    frequency=75.0, decay_s=1.2, brightness=0.55, intensity=0.9
)))

reverse_hit = to_list(synthesize_reverse_hit(ImpactPreset(
    name="RevHit", impact_type="reverse_hit", duration_s=1.2,
    frequency=90.0, decay_s=0.9, intensity=0.75
)))

stutter = to_list(synthesize_stutter(GlitchPreset(
    name="GriefStutter", glitch_type="stutter",
    frequency=KEY_FREQS["D3"],
    duration_s=BEAT * 2, rate=16.0, depth=0.85, distortion=0.2
)))

# ── VOCAL CHOPS ──────────────────────────────────────────────────────
print("  [8/10] Vocal chops...")

# "ah" — the cry, used in verse and outro
chop_ah = to_list(synthesize_chop(VocalChop(
    name="CryAh", vowel="ah", note="D3",
    duration_s=BEAT * 0.5, attack_s=0.01, release_s=0.1,
    formant_shift=0.0, distortion=0.1
)))

# "oh" — the hollow, used in breaks
chop_oh = to_list(synthesize_chop(VocalChop(
    name="HollowOh", vowel="oh", note="A3",
    duration_s=BEAT * 0.75, attack_s=0.02, release_s=0.15,
    formant_shift=-2.0, distortion=0.05
)))

# "eh" — the anguish, used in builds (stuttered)
chop_eh_stutter = to_list(synthesize_chop(VocalChop(
    name="AnguishEh", vowel="eh", note="F3",
    duration_s=BEAT * 1.0, attack_s=0.003, release_s=0.04,
    formant_shift=3.0, distortion=0.2,
    stutter_count=8, stutter_pitch_drift=0.5
)))

# "ee" — the scream, used at drop impacts
chop_ee = to_list(synthesize_chop(VocalChop(
    name="ScreamEe", vowel="ee", note="D4",
    duration_s=BEAT * 0.3, attack_s=0.002, release_s=0.05,
    formant_shift=5.0, distortion=0.4
)))

# "oo" — the whisper, used in break and outro
chop_oo = to_list(synthesize_chop(VocalChop(
    name="WhisperOo", vowel="oo", note="D3",
    duration_s=BEAT * 1.0, attack_s=0.05, release_s=0.3,
    formant_shift=-3.0, distortion=0.0
)))

# "ah" long — the apology that never came (final)
chop_ah_long = to_list(synthesize_chop(VocalChop(
    name="ApologyAh", vowel="ah", note="A3",
    duration_s=BEAT * 2.0, attack_s=0.03, release_s=0.5,
    formant_shift=-1.0, distortion=0.05
)))

# ── AMBIENT TEXTURE ──────────────────────────────────────────────────
print("  [9/10] Ambient textures...")

# Space texture for intro and break
space_texture = to_list(synthesize_texture(TexturePreset(
    name="VoidSpace", texture_type="space",
    duration_s=BAR * 8, brightness=0.3, density=0.3,
    depth=0.8, modulation_rate=0.1
)))

# Cave texture for drops (dark resonance)
cave_texture = to_list(synthesize_texture(TexturePreset(
    name="CaveDrop", texture_type="cave",
    duration_s=BAR * 4, brightness=0.2, density=0.5,
    depth=0.6, distortion=0.1
)))


# ════════════════════════════════════════════════════════════════════
#  DRUM PATTERNS
# ════════════════════════════════════════════════════════════════════
print("  [10/10] Sequencing & arranging...")


def drum_pattern_drop(bars: int = 4) -> list[float]:
    """Halftime drop pattern: kick on 1, snare on 3."""
    buf = render_section(bars)
    for bar in range(bars):
        bar_offset = samples_for(bar * 4)
        mix_into(buf, kick, bar_offset, gain=1.0)
        mix_into(buf, snare, bar_offset + samples_for(2), gain=0.85)
        for eighth in range(8):
            mix_into(buf, hat_closed, bar_offset + samples_for(eighth * 0.5),
                     gain=0.32)
        mix_into(buf, hat_open, bar_offset + samples_for(1.5), gain=0.28)
        mix_into(buf, hat_open, bar_offset + samples_for(3.5), gain=0.28)
    return buf


def drum_pattern_build(bars: int = 4) -> list[float]:
    """Buildup — accelerating snare rolls."""
    buf = render_section(bars)
    for bar in range(bars):
        bar_offset = samples_for(bar * 4)
        mix_into(buf, kick, bar_offset, gain=0.65)
        mix_into(buf, kick, bar_offset + samples_for(2), gain=0.65)
        divisions = [4, 8, 16, 32][min(bar, 3)]
        step = 4.0 / divisions
        for hit in range(divisions):
            vel = 0.35 + 0.45 * (bar / bars) * (hit / divisions)
            mix_into(buf, snare, bar_offset + samples_for(hit * step),
                     gain=vel)
    return buf


def drum_pattern_verse(bars: int = 4) -> list[float]:
    """Sparse verse pattern — soft kick + hats, intimate."""
    buf = render_section(bars)
    for bar in range(bars):
        bar_offset = samples_for(bar * 4)
        mix_into(buf, kick, bar_offset, gain=0.4)
        mix_into(buf, kick, bar_offset + samples_for(2), gain=0.3)
        for q in range(4):
            mix_into(buf, hat_closed, bar_offset + samples_for(q),
                     gain=0.2)
        mix_into(buf, hat_open, bar_offset + samples_for(3.5), gain=0.15)
    return buf


def drum_pattern_intro(bars: int = 4) -> list[float]:
    """Minimal intro — just light hats breathing."""
    buf = render_section(bars)
    for bar in range(bars):
        bar_offset = samples_for(bar * 4)
        for q in range(4):
            mix_into(buf, hat_closed, bar_offset + samples_for(q),
                     gain=0.12 + 0.03 * (bar / bars))
    return buf


# ════════════════════════════════════════════════════════════════════
#  BASS PATTERNS
# ════════════════════════════════════════════════════════════════════

def bass_drop_pattern(bars: int = 4) -> list[float]:
    """Drop 1 bass — melancholic wobble pattern."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, sub_bass, bo, gain=0.9)
        mix_into(buf, wobble_bass, bo + samples_for(0.5), gain=0.55)
        mix_into(buf, growl_bass, bo + samples_for(1), gain=0.45)
        mix_into(buf, neuro_bass, bo + samples_for(1.5), gain=0.4)
        mix_into(buf, sub_bass, bo + samples_for(2), gain=0.8)
        mix_into(buf, wobble_bass, bo + samples_for(2.5), gain=0.5)
        mix_into(buf, growl_bass, bo + samples_for(3), gain=0.45)
        mix_into(buf, neuro_bass, bo + samples_for(3.5), gain=0.35)
    return buf


def bass_drop2_pattern(bars: int = 4) -> list[float]:
    """Drop 2 bass — heavier, defiant. 'Forged my defiance.'"""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, sub_bass, bo, gain=1.0)
        mix_into(buf, sub_bass, bo + samples_for(2), gain=0.9)
        for sixteenth in range(16):
            if sixteenth % 2 == 0:
                mix_into(buf, neuro_bass,
                         bo + samples_for(sixteenth * 0.25), gain=0.38)
            else:
                mix_into(buf, growl_bass,
                         bo + samples_for(sixteenth * 0.25), gain=0.38)
        mix_into(buf, wobble_bass, bo + samples_for(1), gain=0.5)
        mix_into(buf, wobble_bass, bo + samples_for(3), gain=0.5)
    return buf


# ════════════════════════════════════════════════════════════════════
#  LEAD MELODY
# ════════════════════════════════════════════════════════════════════

def lead_melody_drop(bars: int = 4) -> list[float]:
    """Screech lead — D minor descending motif (falling hope).
    D4 → C4 → Bb3 → A3"""
    buf = render_section(bars)
    melody = [
        (screech_d, 0.0, 0.48),
        (screech_c, 1.0, 0.44),
        (screech_bb, 2.0, 0.48),
        (screech_a, 3.0, 0.44),
    ]
    for bar in range(bars):
        bo = samples_for(bar * 4)
        for sound, beat, gain in melody:
            mix_into(buf, sound, bo + samples_for(beat), gain=gain)
    return buf


def pluck_arpeggio(bars: int = 4) -> list[float]:
    """Verse pluck arpeggio — D minor broken chord, ascending.
    D3 → F3 → A3 → D4 (repeating, each bar shifts starting note)."""
    buf = render_section(bars)
    arp_sequence = ["D3", "F3", "A3", "D4", "C4", "A3", "G3", "F3"]
    for bar in range(bars):
        bo = samples_for(bar * 4)
        for q in range(4):
            note = arp_sequence[(bar * 2 + q) % len(arp_sequence)]
            pluck = pluck_notes[note]
            mix_into(buf, pluck, bo + samples_for(q), gain=0.32)
    return buf


def lead_fill(bars: int = 1) -> list[float]:
    """Quick lead fill — stutter through the motif."""
    buf = render_section(bars)
    notes = [screech_d, screech_c, screech_bb, screech_a]
    for sixteenth in range(16):
        note = notes[sixteenth % 4]
        gain = 0.25 + 0.2 * (sixteenth / 16)
        mix_into(buf, note, samples_for(sixteenth * 0.25), gain=gain)
    return buf


# ════════════════════════════════════════════════════════════════════
#  ARRANGE THE FULL TRACK
# ════════════════════════════════════════════════════════════════════

# Structure (bars):
INTRO_BARS = 8      # Void + drone + space
VERSE_BARS = 8      # "In the hollow of midnight..."
BUILD1_BARS = 4     # Pitch riser + "eh" stutter vocal
DROP1_BARS = 16     # "The apology that never came" — full force
BREAK_BARS = 8      # "Phantoms of us whisper..."
BUILD2_BARS = 4     # Harmonic riser + darker build
DROP2_BARS = 16     # "Forged my defiance" — triumphant
OUTRO_BARS = 8      # Decay into silence

total_bars = (INTRO_BARS + VERSE_BARS + BUILD1_BARS + DROP1_BARS +
              BREAK_BARS + BUILD2_BARS + DROP2_BARS + OUTRO_BARS)
total_samples = samples_for(total_bars * 4)
duration_s = total_samples / SR

print()
print(f"  Structure: {total_bars} bars = {duration_s:.1f}s "
      f"({int(duration_s // 60)}:{int(duration_s % 60):02d})")
print(f"  Intro({INTRO_BARS}) -> Verse({VERSE_BARS}) -> "
      f"Build({BUILD1_BARS}) -> Drop1({DROP1_BARS}) -> "
      f"Break({BREAK_BARS}) -> Build({BUILD2_BARS}) -> "
      f"Drop2({DROP2_BARS}) -> Outro({OUTRO_BARS})")
print()

# ════════════════════════════════════════════════════════════════════
#  STEM BUFFERS — one full-length mono buffer per stem
# ════════════════════════════════════════════════════════════════════

STEM_NAMES = [
    "DRUMS", "BASS", "LEAD", "PLUCK", "CHORDS",
    "PAD", "DRONE", "RISER", "VOCAL", "FX", "AMBIENT",
]

# Pan positions for stereo mixdown (L=-1, C=0, R=+1)
STEM_PAN = {
    "DRUMS": 0.0, "BASS": 0.0, "LEAD": 0.15, "PLUCK": -0.2,
    "CHORDS": 0.1, "PAD": 0.0, "DRONE": 0.0, "RISER": 0.0,
    "VOCAL": -0.05, "FX": 0.0, "AMBIENT": 0.0,
}

stems: dict[str, list[float]] = {
    name: [0.0] * total_samples for name in STEM_NAMES
}

cursor = 0

# ── INTRO (8 bars) — "The void before the words" ────────────────────
print("  Rendering Intro...")
intro_start = cursor

# Evolving drone — slow fade in from silence
intro_drone = drone[:samples_for(INTRO_BARS * 4)]
intro_drone = fade_in(intro_drone, duration_s=BAR * 4)
intro_drone = lowpass(intro_drone, cutoff=0.12)
mix_into(stems["DRONE"], intro_drone, intro_start, gain=0.4)

# Space texture — wide
space_seg = space_texture[:samples_for(INTRO_BARS * 4)]
space_seg = fade_in(space_seg, duration_s=BAR * 2)
mix_into(stems["AMBIENT"], space_seg, intro_start, gain=0.22)

# Dark pad — barely there, filtered
intro_pad = dark_pad[:samples_for(INTRO_BARS * 4)]
intro_pad = fade_in(intro_pad, duration_s=BAR * 3)
intro_pad = lowpass(intro_pad, cutoff=0.1)
mix_into(stems["PAD"], intro_pad, intro_start, gain=0.3)

# Reverse hit at bar 7 — something is coming
rev_offset = intro_start + samples_for(6 * 4)
mix_into(stems["FX"], reverse_hit, rev_offset, gain=0.4)

# Minimal hats fading in
intro_drums = drum_pattern_intro(INTRO_BARS)
intro_drums = fade_in(intro_drums, duration_s=BAR * 4)
mix_into(stems["DRUMS"], intro_drums, intro_start, gain=0.25)

# Vocal whisper "oo" at bar 4 and 8
mix_into(stems["VOCAL"], chop_oo, intro_start + samples_for(3 * 4), gain=0.16)
mix_into(stems["VOCAL"], chop_oo, intro_start + samples_for(7 * 4), gain=0.16)

cursor += samples_for(INTRO_BARS * 4)

# ── VERSE 1 (8 bars) — "In the hollow of midnight..." ───────────────
print("  Rendering Verse 1...")
verse_start = cursor

# Pluck arpeggio — the memory
for rep in range(VERSE_BARS // 4):
    arp = pluck_arpeggio(4)
    offset = verse_start + samples_for(rep * 16)
    mix_into(stems["PLUCK"], arp, offset, gain=0.32)

# Sub bass — heartbeat
for bar in range(VERSE_BARS):
    bo = verse_start + samples_for(bar * 4)
    mix_into(stems["BASS"], sub_bass, bo, gain=0.4)

# Verse drums — intimate
verse_drums = drum_pattern_verse(VERSE_BARS)
mix_into(stems["DRUMS"], verse_drums, verse_start, gain=0.45)

# Reese bass — low filtered texture
verse_reese = reese_bass[:samples_for(VERSE_BARS * 4)]
verse_reese = lowpass(verse_reese, cutoff=0.15)
mix_into(stems["BASS"], verse_reese, verse_start, gain=0.25)

# Dark pad — still present, slightly more open
verse_pad = dark_pad[:samples_for(VERSE_BARS * 4)]
verse_pad = lowpass(verse_pad, cutoff=0.18)
mix_into(stems["PAD"], verse_pad, verse_start, gain=0.3)

# Vocal "ah" cry — scattered, the raw heart
for bar in [0, 2, 4, 6]:
    mix_into(stems["VOCAL"], chop_ah, verse_start + samples_for(bar * 4 + 2),
             gain=0.21)
# "oh" on bar 4 — the hollow
mix_into(stems["VOCAL"], chop_oh, verse_start + samples_for(3 * 4 + 3),
         gain=0.19)

cursor += samples_for(VERSE_BARS * 4)

# ── BUILD 1 (4 bars) — "heart raw and exposed" ──────────────────────
print("  Rendering Build 1...")
build1_start = cursor

# Pitch riser — tension
mix_into(stems["RISER"], pitch_riser, build1_start, gain=0.5)

# Noise riser layered
noise_seg = noise_riser[:samples_for(BUILD1_BARS * 4)]
mix_into(stems["RISER"], noise_seg, build1_start, gain=0.3)

# Snare roll
build1_drums = drum_pattern_build(BUILD1_BARS)
mix_into(stems["DRUMS"], build1_drums, build1_start, gain=0.6)

# "eh" stutter chops — anguish accelerating
for bar in range(BUILD1_BARS):
    bo = build1_start + samples_for(bar * 4)
    gain = 0.15 + 0.15 * (bar / BUILD1_BARS)
    mix_into(stems["VOCAL"], chop_eh_stutter, bo, gain=gain)

# "ee" scream right before the drop
ee_offset = build1_start + samples_for(BUILD1_BARS * 4) - len(chop_ee) - SR // 4
if ee_offset > build1_start:
    mix_into(stems["VOCAL"], chop_ee, ee_offset, gain=0.4)

# Reverse hit before drop
rev_offset = build1_start + samples_for(BUILD1_BARS * 4) - len(reverse_hit)
if rev_offset > build1_start:
    mix_into(stems["FX"], reverse_hit, rev_offset, gain=0.6)

# Pad rising
build_pad = lush_pad[:samples_for(BUILD1_BARS * 4)]
build_pad = fade_in(build_pad, duration_s=0.5)
mix_into(stems["PAD"], build_pad, build1_start, gain=0.3)

cursor += samples_for(BUILD1_BARS * 4)

# ── DROP 1 (16 bars) — "The apology that never came" ────────────────
print("  Rendering Drop 1...")
drop1_start = cursor

# IMPACT — the silence breaks
mix_into(stems["FX"], sub_boom, drop1_start, gain=0.85)
mix_into(stems["FX"], cinema_hit, drop1_start, gain=0.55)
mix_into(stems["VOCAL"], chop_ee, drop1_start, gain=0.3)

# Drums — halftime
for rep in range(DROP1_BARS // 4):
    offset = drop1_start + samples_for(rep * 16)
    drop_drums = sidechain_pump(drum_pattern_drop(4), 16, depth=0.0)
    mix_into(stems["DRUMS"], drop_drums, offset, gain=0.7)

# Bass — wobble/neuro pattern with sidechain
for rep in range(DROP1_BARS // 4):
    offset = drop1_start + samples_for(rep * 16)
    drop_bass = sidechain_pump(bass_drop_pattern(4), 16, depth=0.45)
    mix_into(stems["BASS"], drop_bass, offset, gain=0.8)

# Lead melody — D4→C4→Bb3→A3 descending (hope falling)
for rep in range(DROP1_BARS // 4):
    offset = drop1_start + samples_for(rep * 16)
    melody = lead_melody_drop(4)
    mix_into(stems["LEAD"], melody, offset, gain=0.36)

# FM metallic stabs every 2 bars
for bar in range(0, DROP1_BARS, 2):
    stab_offset = drop1_start + samples_for(bar * 4)
    mix_into(stems["CHORDS"], fm_hit, stab_offset, gain=0.22)

# Dark drone underneath
for rep in range(DROP1_BARS // 4):
    offset = drop1_start + samples_for(rep * 16)
    seg = dark_drone[:samples_for(4 * 4)]
    mix_into(stems["DRONE"], seg, offset, gain=0.2)

# Cave texture for atmosphere in drops
for rep in range(DROP1_BARS // 4):
    offset = drop1_start + samples_for(rep * 16)
    cave_seg = cave_texture[:samples_for(4 * 4)]
    mix_into(stems["AMBIENT"], cave_seg, offset, gain=0.11)

# "ah" vocal chop accents in the drop
for bar in range(0, DROP1_BARS, 4):
    mix_into(stems["VOCAL"], chop_ah,
             drop1_start + samples_for(bar * 4 + 1.5), gain=0.19)

# Lead fill + stutter before breakdown
fill_offset = drop1_start + samples_for((DROP1_BARS - 1) * 4)
mix_into(stems["LEAD"], lead_fill(1), fill_offset, gain=0.3)
stutter_offset = drop1_start + samples_for((DROP1_BARS - 1) * 4 + 2)
mix_into(stems["FX"], stutter, stutter_offset, gain=0.35)

cursor += samples_for(DROP1_BARS * 4)

# ── BREAK (8 bars) — "Phantoms of us whisper..." ────────────────────
print("  Rendering Break...")
break_start = cursor

# Lush pad — the yearning
break_pad = lush_pad[:samples_for(BREAK_BARS * 4)]
break_pad = fade_in(break_pad, duration_s=BAR)
break_pad = fade_out(break_pad, duration_s=BAR * 2)
mix_into(stems["PAD"], break_pad, break_start, gain=0.45)

# Pluck melody — D minor arpeggio, wider and sadder
break_notes = ["D3", "A3", "F3", "D4", "Bb3", "G3", "A3", "E3"]
for bar in range(BREAK_BARS):
    bo = break_start + samples_for(bar * 4)
    for q in range(4):
        note = break_notes[(bar + q) % len(break_notes)]
        pluck = pluck_notes[note]
        mix_into(stems["PLUCK"], pluck, bo + samples_for(q), gain=0.3)

# Light hats
for bar in range(BREAK_BARS):
    bo = break_start + samples_for(bar * 4)
    for q in range(4):
        mix_into(stems["DRUMS"], hat_closed, bo + samples_for(q), gain=0.12)

# Sub drone
sub_break_drone = to_list(synthesize_bass(BassPreset(
    name="SubDrone", bass_type="sub_sine", frequency=KEY_FREQS["D1"],
    duration_s=BREAK_BARS * BAR, attack_s=1.0, release_s=2.0
)))
mix_into(stems["BASS"], sub_break_drone, break_start, gain=0.3)

# "oo" whisper chops — "Phantoms of us whisper"
for bar in [0, 2, 4, 6]:
    mix_into(stems["VOCAL"], chop_oo,
             break_start + samples_for(bar * 4 + 1), gain=0.21)

# "oh" — hollow between the whispers
for bar in [1, 3, 5]:
    mix_into(stems["VOCAL"], chop_oh,
             break_start + samples_for(bar * 4 + 3), gain=0.16)

# Space texture in break
break_space = space_texture[:samples_for(BREAK_BARS * 4)]
mix_into(stems["AMBIENT"], break_space, break_start, gain=0.13)

cursor += samples_for(BREAK_BARS * 4)

# ── BUILD 2 (4 bars) — "Perhaps the agony lingers..." ───────────────
print("  Rendering Build 2...")
build2_start = cursor

# Harmonic riser — darker, the rage building
mix_into(stems["RISER"], harmonic_riser, build2_start, gain=0.55)

# Noise riser layer
noise_seg2 = noise_riser[:samples_for(BUILD2_BARS * 4)]
mix_into(stems["RISER"], noise_seg2, build2_start, gain=0.35)

# Snare roll
build2_drums = drum_pattern_build(BUILD2_BARS)
mix_into(stems["DRUMS"], build2_drums, build2_start, gain=0.65)

# "eh" stutter — getting more intense
for bar in range(BUILD2_BARS):
    bo = build2_start + samples_for(bar * 4)
    gain = 0.2 + 0.2 * (bar / BUILD2_BARS)
    mix_into(stems["VOCAL"], chop_eh_stutter, bo, gain=gain)

# Reverse hit
rev2_offset = build2_start + samples_for(BUILD2_BARS * 4) - len(reverse_hit)
if rev2_offset > build2_start:
    mix_into(stems["FX"], reverse_hit, rev2_offset, gain=0.7)

# "ee" scream right before drop 2
ee2_offset = build2_start + samples_for(BUILD2_BARS * 4) - len(chop_ee) - SR // 4
if ee2_offset > build2_start:
    mix_into(stems["VOCAL"], chop_ee, ee2_offset, gain=0.45)

cursor += samples_for(BUILD2_BARS * 4)

# ── DROP 2 (16 bars) — "Forged my defiance" ─────────────────────────
print("  Rendering Drop 2...")
drop2_start = cursor

# BIGGER impact — defiance
mix_into(stems["FX"], sub_boom, drop2_start, gain=1.0)
mix_into(stems["FX"], cinema_hit, drop2_start, gain=0.65)
mix_into(stems["DRUMS"], clap, drop2_start, gain=0.5)
mix_into(stems["VOCAL"], chop_ee, drop2_start, gain=0.35)

# Drums — louder, with clap layers
for rep in range(DROP2_BARS // 4):
    offset = drop2_start + samples_for(rep * 16)
    d2_drums = sidechain_pump(drum_pattern_drop(4), 16, depth=0.0)
    mix_into(stems["DRUMS"], d2_drums, offset, gain=0.75)
    for bar in range(4):
        clap_off = offset + samples_for(bar * 4 + 2)
        mix_into(stems["DRUMS"], clap, clap_off, gain=0.3)

# Heavier bass — the defiance itself
for rep in range(DROP2_BARS // 4):
    offset = drop2_start + samples_for(rep * 16)
    d2_bass = sidechain_pump(bass_drop2_pattern(4), 16, depth=0.4)
    d2_bass = distort(d2_bass, drive=1.4)
    mix_into(stems["BASS"], d2_bass, offset, gain=0.85)

# Lead — same motif but more presence
for rep in range(DROP2_BARS // 4):
    offset = drop2_start + samples_for(rep * 16)
    melody2 = lead_melody_drop(4)
    mix_into(stems["LEAD"], melody2, offset, gain=0.42)

# Supersaw stabs every bar — emotional release
for bar in range(DROP2_BARS):
    stab_offset = drop2_start + samples_for(bar * 4)
    mix_into(stems["CHORDS"], saw_chord, stab_offset, gain=0.22)

# FM stabs every 2 bars
for bar in range(0, DROP2_BARS, 2):
    stab_offset = drop2_start + samples_for(bar * 4)
    mix_into(stems["CHORDS"], fm_hit, stab_offset, gain=0.2)

# Dark drone underneath drop 2
for rep in range(DROP2_BARS // 4):
    offset = drop2_start + samples_for(rep * 16)
    seg = dark_drone[:samples_for(4 * 4)]
    mix_into(stems["DRONE"], seg, offset, gain=0.22)

# "ah" vocal — defiance
for bar in range(0, DROP2_BARS, 2):
    mix_into(stems["VOCAL"], chop_ah,
             drop2_start + samples_for(bar * 4 + 1), gain=0.21)

# Stutter in last 2 bars — time fracturing
stutter_off = drop2_start + samples_for((DROP2_BARS - 2) * 4)
mix_into(stems["FX"], stutter, stutter_off, gain=0.35)
mix_into(stems["FX"], stutter, stutter_off + samples_for(4), gain=0.4)

cursor += samples_for(DROP2_BARS * 4)

# ── OUTRO (8 bars) — "The apology that never came" — final ──────────
print("  Rendering Outro...")
outro_start = cursor

# Dark pad — slowly dissolving
outro_pad = dark_pad[:samples_for(OUTRO_BARS * 4)]
outro_pad = fade_out(outro_pad, duration_s=BAR * 5)
outro_pad = lowpass(outro_pad, cutoff=0.1)
mix_into(stems["PAD"], outro_pad, outro_start, gain=0.35)

# Evolving drone — decaying
outro_drone = drone[:samples_for(OUTRO_BARS * 4)]
outro_drone = fade_out(outro_drone, duration_s=BAR * 6)
mix_into(stems["DRONE"], outro_drone, outro_start, gain=0.3)

# Space texture — widening as everything else fades
outro_space = space_texture[:samples_for(OUTRO_BARS * 4)]
outro_space = fade_out(outro_space, duration_s=BAR * 3)
mix_into(stems["AMBIENT"], outro_space, outro_start, gain=0.16)

# Sparse hats fading
outro_drums = drum_pattern_intro(OUTRO_BARS)
outro_drums = fade_out(outro_drums, duration_s=BAR * 4)
mix_into(stems["DRUMS"], outro_drums, outro_start, gain=0.2)

# Sub decaying
outro_sub = to_list(synthesize_bass(BassPreset(
    name="OutroSub", bass_type="sub_sine", frequency=KEY_FREQS["D1"],
    duration_s=OUTRO_BARS * BAR, attack_s=0.01,
    release_s=OUTRO_BARS * BAR * 0.8
)))
outro_sub = fade_out(outro_sub, duration_s=BAR * 6)
mix_into(stems["BASS"], outro_sub, outro_start, gain=0.25)

# Final vocal — "ah" long — the apology that never came
mix_into(stems["VOCAL"], chop_ah_long,
         outro_start + samples_for(1 * 4), gain=0.26)
mix_into(stems["VOCAL"], chop_ah_long,
         outro_start + samples_for(3 * 4), gain=0.21)
final_chop = chop_ah_long[:len(chop_ah_long)]
final_chop = fade_out(final_chop, duration_s=BEAT * 3)
mix_into(stems["VOCAL"], final_chop,
         outro_start + samples_for(5 * 4), gain=0.16)


# ════════════════════════════════════════════════════════════════════
#  EXPORT STEMS + STEREO MIXDOWN + ALS PROJECT
# ════════════════════════════════════════════════════════════════════
print()
print("  Bouncing stems...")

# ── 1. Individual stem WAVs — fast bulk writer ──────────────────────
os.makedirs("output/stems", exist_ok=True)
stem_paths: list[str] = []

for name in STEM_NAMES:
    buf = stems[name]
    path = f"output/stems/apology_{name}.wav"

    # Normalize per-stem
    peak = max(abs(s) for s in buf) if buf else 1.0
    gain = 0.95 / peak if peak > 0 else 1.0

    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        chunk_size = SR
        for start in range(0, len(buf), chunk_size):
            end = min(start + chunk_size, len(buf))
            frames = struct.pack(
                f"<{end - start}h",
                *(max(-32768, min(32767, int(buf[i] * gain * 32767)))
                  for i in range(start, end))
            )
            wf.writeframes(frames)

    fsize = os.path.getsize(path)
    peak_db = 20 * math.log10(peak) if peak > 0 else -120.0
    stem_paths.append(path)
    print(f"    {name:24s}  {len(buf)/SR:.1f}s  {peak_db:.1f}dB  "
          f"{fsize/1024/1024:.1f}MB")

# ── 2. Stereo mixdown with constant-power pan law ───────────────────
print()
print("  Stereo mixdown...")

master_L = [0.0] * total_samples
master_R = [0.0] * total_samples

for name, buf in stems.items():
    pan = STEM_PAN.get(name, 0.0)
    # Constant-power pan: L = cos(theta), R = sin(theta)
    theta = (pan + 1.0) * 0.5 * (math.pi / 2.0)
    gain_l = math.cos(theta)
    gain_r = math.sin(theta)
    for i in range(min(len(buf), total_samples)):
        master_L[i] += buf[i] * gain_l
        master_R[i] += buf[i] * gain_r

# Peak normalization
peak = 0.0
for i in range(total_samples):
    peak = max(peak, abs(master_L[i]), abs(master_R[i]))

if peak > 0:
    target = 0.95
    gain = target / peak
    for i in range(total_samples):
        master_L[i] *= gain
        master_R[i] *= gain

# Soft limiting
for i in range(total_samples):
    master_L[i] = math.tanh(master_L[i])
    master_R[i] = math.tanh(master_R[i])

# Write stereo WAV
os.makedirs("output", exist_ok=True)
output_path = "output/apology_never_came.wav"

with wave.open(output_path, "w") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)

    chunk_size = SR
    for start in range(0, total_samples, chunk_size):
        end = min(start + chunk_size, total_samples)
        frames = b""
        for i in range(start, end):
            l_sample = max(-32768, min(32767, int(master_L[i] * 32767)))
            r_sample = max(-32768, min(32767, int(master_R[i] * 32767)))
            frames += struct.pack("<hh", l_sample, r_sample)
        wf.writeframes(frames)

# ── 3. Ableton Live Set with stem references ────────────────────────
print("  Generating Ableton Live project...")

# Color palette for stems (Ableton color indices)
stem_colors = {
    "DRUMS": 1, "BASS": 3, "LEAD": 12, "PLUCK": 16,
    "CHORDS": 20, "PAD": 24, "DRONE": 28, "RISER": 32,
    "VOCAL": 36, "FX": 40, "AMBIENT": 44,
}

als_tracks = []
for name in STEM_NAMES:
    als_tracks.append(ALSTrack(
        name=name,
        track_type="audio",
        color=stem_colors.get(name, 0),
        volume_db=0.0,
        pan=STEM_PAN.get(name, 0.0),
        clip_names=[name],  # references stem WAV by name
    ))

# Add return tracks for reverb and delay
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
    ALSScene(name="VERSE", tempo=float(BPM)),
    ALSScene(name="BUILD_1", tempo=float(BPM)),
    ALSScene(name="DROP_1", tempo=float(BPM)),
    ALSScene(name="BREAK", tempo=float(BPM)),
    ALSScene(name="BUILD_2", tempo=float(BPM)),
    ALSScene(name="DROP_2", tempo=float(BPM)),
    ALSScene(name="OUTRO", tempo=float(BPM)),
]

project = ALSProject(
    name="Apology_Never_Came",
    bpm=float(BPM),
    tracks=als_tracks,
    scenes=als_scenes,
    notes="Can You See The Apology That Never Came | D minor | 140 BPM | 432 Hz",
)

os.makedirs("output/ableton", exist_ok=True)
als_path = "output/ableton/Apology_Never_Came_STEMS.als"
write_als(project, als_path)

# ── 4. Summary ──────────────────────────────────────────────────────
duration = total_samples / SR
file_size = os.path.getsize(output_path)
stem_dir_size = sum(
    os.path.getsize(os.path.join("output/stems", f))
    for f in os.listdir("output/stems") if f.endswith(".wav")
)

print()
print("=" * 60)
print('  "Can You See The Apology That Never Came"')
print("=" * 60)
print(f"  Format:   16-bit WAV @ {SR} Hz")
print(f"  BPM:      {BPM}  |  Key: D minor  |  Tuning: 432 Hz")
print(f"  Duration: {duration:.1f}s "
      f"({int(duration // 60)}:{int(duration % 60):02d})")
print(f"  Bars:     {total_bars}")
print(f"  Sections: Intro({INTRO_BARS}) -> Verse({VERSE_BARS}) -> "
      f"Build({BUILD1_BARS}) -> Drop1({DROP1_BARS}) -> "
      f"Break({BREAK_BARS}) -> Build({BUILD2_BARS}) -> "
      f"Drop2({DROP2_BARS}) -> Outro({OUTRO_BARS})")
print()
print(f"  Stems:    {len(STEM_NAMES)} tracks in output/stems/")
for name in STEM_NAMES:
    print(f"            - {name}")
print(f"  Stems:    {stem_dir_size / 1024 / 1024:.1f} MB total")
print(f"  Mixdown:  {output_path} ({file_size / 1024 / 1024:.1f} MB)")
print(f"  Ableton:  {als_path}")
print()
print("  Mood:     Melancholy x Epic (55/45)")
print("  Darkness: ~78%  |  Energy: ~55%  |  Reverb: ~75%")
print("  Modules:  11 engine + BounceEngine + ALSGenerator")
print("=" * 60)

# ── 5. Open in Ableton Live ─────────────────────────────────────────
print()
print("  Opening Ableton Live 12...")
subprocess.Popen(["cmd", "/c", "start", "", os.path.abspath(als_path)],
                 creationflags=0x08000000)  # CREATE_NO_WINDOW
print("  Done. Stems are in output/stems/ — drag into Live tracks.")
print()
