#!/usr/bin/env python3
"""DUBFORGE — Dubstep Track Generator.

Renders a full dubstep track using the DUBFORGE engine:
  BPM: 140  |  Key: F minor  |  Duration: ~3 min
  Sections: Intro → Build → Drop 1 → Breakdown → Drop 2 → Outro

Output: output/dubstep_track.wav (16-bit stereo, 44100 Hz)
"""

import math
import os
import struct
import wave

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

# ── Constants ────────────────────────────────────────────────────────
SR = 48000
BPM = 140
BEAT = 60.0 / BPM                    # seconds per beat
BAR = BEAT * 4                       # seconds per bar
from engine.config_loader import PHI
# Key of F minor — F G Ab Bb C Db Eb
# MIDI: F2=41, F3=53, F4=65
KEY_FREQS = {
    "F1": 43.65, "Ab1": 51.91, "Bb1": 58.27, "C2": 65.41,
    "Db2": 69.30, "Eb2": 77.78, "F2": 87.31, "G2": 98.00,
    "Ab2": 103.83, "Bb2": 116.54, "C3": 130.81, "Db3": 138.59,
    "Eb3": 155.56, "F3": 174.61, "G3": 196.00, "Ab3": 207.65,
    "Bb3": 233.08, "C4": 261.63, "Db4": 277.18, "Eb4": 311.13,
    "F4": 349.23, "G4": 392.00, "Ab4": 415.30,
}


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


def mix_into(target: list[float], source: list[float], offset: int, gain: float = 1.0):
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
    alpha = cutoff
    out[0] = signal[0] * alpha
    for i in range(1, len(signal)):
        out[i] = out[i - 1] + alpha * (signal[i] - out[i - 1])
    return out


def distort(signal: list[float], drive: float = 2.0) -> list[float]:
    """Soft-clip distortion."""
    return [math.tanh(s * drive) for s in signal]


def sidechain_pump(signal: list[float], beats: int, depth: float = 0.7) -> list[float]:
    """Apply sidechain-style pumping envelope synced to quarter notes."""
    out = list(signal)
    beat_samples = samples_for(1)
    for i in range(len(out)):
        pos_in_beat = (i % beat_samples) / beat_samples
        # Quick duck then release
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

print("🔊 DUBFORGE — Rendering dubstep track...")
print(f"   BPM: {BPM}  |  Key: F minor  |  SR: {SR}")
print()

# ── DRUMS ────────────────────────────────────────────────────────────
print("  [1/8] Drums...")

kick = to_list(synthesize_kick(PercPreset(
    name="DubKick", perc_type="kick", duration_s=0.4,
    pitch=55.0, decay_s=0.3, tone_mix=0.8, brightness=0.4,
    distortion=0.2, attack_s=0.001
)))

snare = to_list(synthesize_snare(PercPreset(
    name="DubSnare", perc_type="snare", duration_s=0.25,
    pitch=180.0, decay_s=0.15, tone_mix=0.4, brightness=0.8,
    distortion=0.1, attack_s=0.001
)))

clap = to_list(synthesize_clap(PercPreset(
    name="Clap", perc_type="clap", duration_s=0.2,
    pitch=200.0, decay_s=0.12, tone_mix=0.2, brightness=0.9,
    distortion=0.0, attack_s=0.002
)))

hat_closed = to_list(synthesize_hat(PercPreset(
    name="HatClosed", perc_type="hat", duration_s=0.06,
    pitch=8000.0, decay_s=0.04, tone_mix=0.1, brightness=0.95,
    distortion=0.0, attack_s=0.001
)))

hat_open = to_list(synthesize_hat(PercPreset(
    name="HatOpen", perc_type="hat", duration_s=0.25,
    pitch=7500.0, decay_s=0.2, tone_mix=0.1, brightness=0.9,
    distortion=0.0, attack_s=0.001
)))

# ── BASS ─────────────────────────────────────────────────────────────
print("  [2/8] Bass...")

sub_bass = to_list(synthesize_bass(BassPreset(
    name="Sub", bass_type="sub_sine", frequency=KEY_FREQS["F1"],
    duration_s=BEAT * 2, attack_s=0.005, release_s=0.15, distortion=0.0
)))

wobble_bass = to_list(synthesize_bass(BassPreset(
    name="Wobble", bass_type="wobble", frequency=KEY_FREQS["F2"],
    duration_s=BEAT * 2, attack_s=0.01, release_s=0.2,
    fm_ratio=PHI, fm_depth=3.0, distortion=0.3, filter_cutoff=0.6
)))

growl_bass = to_list(synthesize_bass(BassPreset(
    name="Growl", bass_type="growl", frequency=KEY_FREQS["F2"],
    duration_s=BEAT, attack_s=0.005, release_s=0.1,
    fm_ratio=2.0, fm_depth=5.0, distortion=0.5, filter_cutoff=0.7
)))

neuro_bass = to_list(synthesize_bass(BassPreset(
    name="Neuro", bass_type="neuro", frequency=KEY_FREQS["F2"],
    duration_s=BEAT, attack_s=0.003, release_s=0.08,
    fm_ratio=3.0, fm_depth=4.0, distortion=0.6, filter_cutoff=0.5
)))

reese_bass = to_list(synthesize_bass(BassPreset(
    name="Reese", bass_type="reese", frequency=KEY_FREQS["F2"],
    duration_s=BAR, attack_s=0.3, release_s=0.5,
    detune_cents=15.0, filter_cutoff=0.4
)))

# ── LEADS & SYNTHS ───────────────────────────────────────────────────
print("  [3/8] Leads & synths...")

screech_f = to_list(synthesize_screech_lead(LeadPreset(
    name="ScreechF", lead_type="screech", frequency=KEY_FREQS["F4"],
    duration_s=BEAT * 0.5, attack_s=0.005, decay_s=0.05,
    sustain=0.6, release_s=0.08, filter_cutoff=0.9,
    resonance=0.5, distortion=0.4
)))

screech_eb = to_list(synthesize_screech_lead(LeadPreset(
    name="ScreechEb", lead_type="screech", frequency=KEY_FREQS["Eb4"],
    duration_s=BEAT * 0.5, attack_s=0.005, decay_s=0.05,
    sustain=0.6, release_s=0.08, filter_cutoff=0.9,
    resonance=0.5, distortion=0.4
)))

screech_c = to_list(synthesize_screech_lead(LeadPreset(
    name="ScreechC", lead_type="screech", frequency=KEY_FREQS["C4"],
    duration_s=BEAT * 0.75, attack_s=0.005, decay_s=0.05,
    sustain=0.6, release_s=0.1, filter_cutoff=0.85,
    resonance=0.4, distortion=0.3
)))

pluck_melody = to_list(synthesize_pluck_lead(LeadPreset(
    name="Pluck", lead_type="pluck", frequency=KEY_FREQS["Ab3"],
    duration_s=BEAT, attack_s=0.002, decay_s=0.15,
    sustain=0.3, release_s=0.2, filter_cutoff=0.7, resonance=0.2
)))

# Supersaw chord stab
saw_chord = render_supersaw_mono(SupersawPatch(
    name="ChordStab", n_voices=7, detune_cents=30.0,
    mix=0.7, cutoff_hz=6000.0, resonance=0.2,
    attack=0.005, decay=0.15, sustain=0.6, release=0.2, master_gain=0.7
), freq=KEY_FREQS["F3"], duration=BEAT * 0.75)

# FM metallic hit for transitions
fm_hit = render_fm(FMPatch(
    name="FMHit",
    operators=[
        FMOperator(freq_ratio=1.0, amplitude=1.0, mod_index=5.0, envelope=(0.001, 0.05, 0.0, 0.1)),
        FMOperator(freq_ratio=PHI, amplitude=0.8, mod_index=3.0, envelope=(0.001, 0.08, 0.0, 0.15)),
    ],
    algorithm=0, master_gain=0.7
), freq=KEY_FREQS["F3"], duration=0.3)

# ── PADS ─────────────────────────────────────────────────────────────
print("  [4/8] Pads...")

dark_pad = to_list(synthesize_dark_pad(PadPreset(
    name="DarkPad", pad_type="dark", frequency=KEY_FREQS["F3"],
    duration_s=BAR * 4, detune_cents=12.0, filter_cutoff=0.35,
    attack_s=1.0, release_s=2.0, reverb_amount=0.5, brightness=0.3
)))

lush_pad = to_list(synthesize_lush_pad(PadPreset(
    name="LushPad", pad_type="lush", frequency=KEY_FREQS["Ab3"],
    duration_s=BAR * 4, detune_cents=15.0, filter_cutoff=0.5,
    attack_s=0.8, release_s=1.5, reverb_amount=0.6, brightness=0.5
)))

# ── FX & RISERS ──────────────────────────────────────────────────────
print("  [5/8] FX & risers...")

noise_riser = to_list(synthesize_noise(NoisePreset(
    name="Riser", noise_type="white", duration_s=BAR * 4,
    brightness=0.3, density=0.5, modulation=0.8, mod_rate=0.5,
    attack_s=0.0, release_s=0.1, gain=0.5
)))
# Make it rise by applying a volume ramp
for i in range(len(noise_riser)):
    noise_riser[i] *= (i / len(noise_riser)) ** 2

sub_boom = to_list(synthesize_sub_boom(ImpactPreset(
    name="SubBoom", impact_type="sub_boom", duration_s=2.0,
    frequency=KEY_FREQS["F1"], decay_s=1.5, intensity=0.95, reverb_amount=0.3
)))

cinema_hit = to_list(synthesize_cinematic_hit(ImpactPreset(
    name="CinemaHit", impact_type="cinematic_hit", duration_s=1.5,
    frequency=80.0, decay_s=1.0, brightness=0.6, intensity=0.9
)))

reverse_hit = to_list(synthesize_reverse_hit(ImpactPreset(
    name="RevHit", impact_type="reverse_hit", duration_s=1.0,
    frequency=100.0, decay_s=0.8, intensity=0.7
)))

# Glitch stutter fill
stutter = to_list(synthesize_stutter(GlitchPreset(
    name="StutterFill", glitch_type="stutter", frequency=KEY_FREQS["F3"],
    duration_s=BEAT * 2, rate=16.0, depth=0.9, distortion=0.2
)))


# ════════════════════════════════════════════════════════════════════
#  DRUM PATTERN SEQUENCING
# ════════════════════════════════════════════════════════════════════
print("  [6/8] Sequencing patterns...")


def drum_pattern_drop(bars: int = 4) -> list[float]:
    """Dubstep halftime drop pattern: kick on 1, snare on 3."""
    buf = render_section(bars)
    for bar in range(bars):
        bar_offset = samples_for(bar * 4)
        # Kick on beat 1
        mix_into(buf, kick, bar_offset, gain=1.0)
        # Snare on beat 3
        mix_into(buf, snare, bar_offset + samples_for(2), gain=0.85)
        # Closed hats on 8ths
        for eighth in range(8):
            mix_into(buf, hat_closed, bar_offset + samples_for(eighth * 0.5), gain=0.35)
        # Open hat on upbeat of 2 and 4
        mix_into(buf, hat_open, bar_offset + samples_for(1.5), gain=0.3)
        mix_into(buf, hat_open, bar_offset + samples_for(3.5), gain=0.3)
    return buf


def drum_pattern_build(bars: int = 4) -> list[float]:
    """Buildup pattern — accelerating snare rolls."""
    buf = render_section(bars)
    for bar in range(bars):
        bar_offset = samples_for(bar * 4)
        # Kick on 1 and 3
        mix_into(buf, kick, bar_offset, gain=0.7)
        mix_into(buf, kick, bar_offset + samples_for(2), gain=0.7)
        # Snare roll — gets faster each bar
        divisions = [4, 8, 16, 32][min(bar, 3)]
        step = 4.0 / divisions
        for hit in range(divisions):
            vel = 0.4 + 0.4 * (bar / bars) * (hit / divisions)
            mix_into(buf, snare, bar_offset + samples_for(hit * step), gain=vel)
    return buf


def drum_pattern_intro(bars: int = 4) -> list[float]:
    """Sparse intro pattern — just hats and soft kicks."""
    buf = render_section(bars)
    for bar in range(bars):
        bar_offset = samples_for(bar * 4)
        # Soft kick on 1
        mix_into(buf, kick, bar_offset, gain=0.4)
        # Hats on quarters
        for q in range(4):
            mix_into(buf, hat_closed, bar_offset + samples_for(q), gain=0.25)
    return buf


# ════════════════════════════════════════════════════════════════════
#  BASS PATTERN SEQUENCING
# ════════════════════════════════════════════════════════════════════

def bass_drop_pattern(bars: int = 4) -> list[float]:
    """Drop bass — wobble + growl rhythmic pattern."""
    buf = render_section(bars)
    for bar in range(bars):
        bar_offset = samples_for(bar * 4)
        # Sub on beat 1
        mix_into(buf, sub_bass, bar_offset, gain=0.9)
        # Wobble on beat 1.5
        mix_into(buf, wobble_bass, bar_offset + samples_for(0.5), gain=0.6)
        # Growl on beats 2, 2.5
        mix_into(buf, growl_bass, bar_offset + samples_for(1), gain=0.5)
        mix_into(buf, neuro_bass, bar_offset + samples_for(1.5), gain=0.45)
        # Sub on beat 3
        mix_into(buf, sub_bass, bar_offset + samples_for(2), gain=0.8)
        # Wobble stab on 3.5
        mix_into(buf, wobble_bass, bar_offset + samples_for(2.5), gain=0.55)
        # Growl fill
        mix_into(buf, growl_bass, bar_offset + samples_for(3), gain=0.5)
        mix_into(buf, neuro_bass, bar_offset + samples_for(3.5), gain=0.4)
    return buf


def bass_drop2_pattern(bars: int = 4) -> list[float]:
    """Second drop — more aggressive, faster rhythm."""
    buf = render_section(bars)
    for bar in range(bars):
        bar_offset = samples_for(bar * 4)
        # Sub hits
        mix_into(buf, sub_bass, bar_offset, gain=1.0)
        mix_into(buf, sub_bass, bar_offset + samples_for(2), gain=0.9)
        # Fast neuro/growl 16th pattern
        for sixteenth in range(16):
            if sixteenth % 2 == 0:
                mix_into(buf, neuro_bass, bar_offset + samples_for(sixteenth * 0.25), gain=0.35)
            else:
                mix_into(buf, growl_bass, bar_offset + samples_for(sixteenth * 0.25), gain=0.35)
        # Wobble accent
        mix_into(buf, wobble_bass, bar_offset + samples_for(1), gain=0.5)
        mix_into(buf, wobble_bass, bar_offset + samples_for(3), gain=0.5)
    return buf


# ════════════════════════════════════════════════════════════════════
#  LEAD MELODY
# ════════════════════════════════════════════════════════════════════

def lead_melody_drop(bars: int = 4) -> list[float]:
    """Screech lead melody over the drop — F minor motif."""
    buf = render_section(bars)
    # Motif: F4 - Eb4 - C4 - Eb4 (repeated)
    melody = [
        (screech_f, 0.0, 0.5),    # F on beat 1
        (screech_eb, 1.0, 0.45),   # Eb on beat 2
        (screech_c, 2.0, 0.5),    # C on beat 3
        (screech_eb, 3.0, 0.45),   # Eb on beat 4
    ]
    for bar in range(bars):
        bar_offset = samples_for(bar * 4)
        for sound, beat, gain in melody:
            mix_into(buf, sound, bar_offset + samples_for(beat), gain=gain)
    return buf


def lead_fill(bars: int = 1) -> list[float]:
    """Quick lead fill — stutter effect."""
    buf = render_section(bars)
    bar_offset = 0
    for sixteenth in range(16):
        note = [screech_f, screech_eb, screech_c, screech_f][sixteenth % 4]
        gain = 0.3 + 0.2 * (sixteenth / 16)
        mix_into(buf, note, bar_offset + samples_for(sixteenth * 0.25), gain=gain)
    return buf


# ════════════════════════════════════════════════════════════════════
#  ARRANGE THE FULL TRACK
# ════════════════════════════════════════════════════════════════════
print("  [7/8] Arranging sections...")

# Structure (in bars):
# Intro:     8 bars  — pad + sparse drums
# Build:     4 bars  — riser + snare rolls + reverse FX
# Drop 1:   16 bars  — full drums + bass + lead
# Breakdown: 8 bars  — pad + pluck melody
# Build 2:   4 bars  — riser + snare rolls
# Drop 2:   16 bars  — heavier bass + drums + lead
# Outro:     8 bars  — decay

INTRO_BARS = 8
BUILD_BARS = 4
DROP1_BARS = 16
BREAK_BARS = 8
BUILD2_BARS = 4
DROP2_BARS = 16
OUTRO_BARS = 8

total_bars = INTRO_BARS + BUILD_BARS + DROP1_BARS + BREAK_BARS + BUILD2_BARS + DROP2_BARS + OUTRO_BARS
total_samples = samples_for(total_bars * 4)
print(f"   Total: {total_bars} bars = {total_bars * BAR:.1f}s")

# Master stereo buffers
master_L = [0.0] * total_samples
master_R = [0.0] * total_samples


def mix_stereo(mono: list[float], offset: int, gain_l: float = 0.7, gain_r: float = 0.7):
    """Mix mono signal into stereo master at offset."""
    mix_into(master_L, mono, offset, gain=gain_l)
    mix_into(master_R, mono, offset, gain=gain_r)


cursor = 0  # sample position

# ── INTRO (8 bars) ──────────────────────────────────────────────────
intro_start = cursor

# Dark pad (filtered, slow fade in)
intro_pad = dark_pad[:samples_for(INTRO_BARS * 4)]
intro_pad = fade_in(intro_pad, duration_s=BAR * 2)
intro_pad = lowpass(intro_pad, cutoff=0.15)
mix_stereo(intro_pad, intro_start, 0.5, 0.5)

# Sparse drums
intro_drums = drum_pattern_intro(INTRO_BARS)
mix_stereo(intro_drums, intro_start, 0.4, 0.4)

# Reese bass (filtered, quiet)
intro_reese = reese_bass[:samples_for(INTRO_BARS * 4)]
intro_reese = lowpass(intro_reese, cutoff=0.1)
intro_reese = fade_in(intro_reese, duration_s=BAR * 4)
mix_stereo(intro_reese, intro_start, 0.3, 0.3)

cursor += samples_for(INTRO_BARS * 4)

# ── BUILD (4 bars) ──────────────────────────────────────────────────
build_start = cursor

# Build drums (snare roll)
build_drums = drum_pattern_build(BUILD_BARS)
mix_stereo(build_drums, build_start, 0.6, 0.6)

# Noise riser
riser_seg = noise_riser[:samples_for(BUILD_BARS * 4)]
mix_stereo(riser_seg, build_start, 0.4, 0.4)

# Reverse hit before drop
rev_offset = build_start + samples_for(BUILD_BARS * 4) - len(reverse_hit)
if rev_offset > 0:
    mix_stereo(reverse_hit, rev_offset, 0.6, 0.6)

# Rising pad
build_pad = lush_pad[:samples_for(BUILD_BARS * 4)]
build_pad = fade_in(build_pad, duration_s=0.5)
mix_stereo(build_pad, build_start, 0.3, 0.3)

cursor += samples_for(BUILD_BARS * 4)

# ── DROP 1 (16 bars) ────────────────────────────────────────────────
drop1_start = cursor

# Impact at drop start
mix_stereo(sub_boom, drop1_start, 0.8, 0.8)
mix_stereo(cinema_hit, drop1_start, 0.5, 0.5)

# Drums — full halftime loop, 4-bar patterns repeated
for rep in range(DROP1_BARS // 4):
    offset = drop1_start + samples_for(rep * 16)
    drop_drums = sidechain_pump(drum_pattern_drop(4), 16, depth=0.0)
    mix_stereo(drop_drums, offset, 0.7, 0.7)

# Bass — with sidechain pumping
for rep in range(DROP1_BARS // 4):
    offset = drop1_start + samples_for(rep * 16)
    drop_bass = sidechain_pump(bass_drop_pattern(4), 16, depth=0.5)
    mix_stereo(drop_bass, offset, 0.8, 0.8)

# Lead melody
for rep in range(DROP1_BARS // 4):
    offset = drop1_start + samples_for(rep * 16)
    melody = lead_melody_drop(4)
    # Pan lead slightly right
    mix_into(master_L, melody, offset, gain=0.3)
    mix_into(master_R, melody, offset, gain=0.45)

# FM stabs every 2 bars
for bar in range(0, DROP1_BARS, 2):
    stab_offset = drop1_start + samples_for(bar * 4)
    mix_stereo(fm_hit, stab_offset, 0.25, 0.25)

# Lead fill before breakdown
fill_offset = drop1_start + samples_for((DROP1_BARS - 1) * 4)
mix_stereo(lead_fill(1), fill_offset, 0.35, 0.35)

# Stutter transition in last bar
stutter_offset = drop1_start + samples_for((DROP1_BARS - 1) * 4 + 2)
mix_stereo(stutter, stutter_offset, 0.4, 0.4)

cursor += samples_for(DROP1_BARS * 4)

# ── BREAKDOWN (8 bars) ──────────────────────────────────────────────
break_start = cursor

# Lush pad
break_pad = lush_pad[:samples_for(BREAK_BARS * 4)]
break_pad = fade_in(break_pad, duration_s=BAR)
break_pad = fade_out(break_pad, duration_s=BAR)
mix_stereo(break_pad, break_start, 0.45, 0.45)

# Pluck melody — arpeggiated feel
pluck_notes_freqs = [KEY_FREQS["F3"], KEY_FREQS["Ab3"], KEY_FREQS["C4"], KEY_FREQS["Eb4"]]
for bar in range(BREAK_BARS):
    bar_offset = break_start + samples_for(bar * 4)
    for q in range(4):
        # Render a pluck at the right frequency
        freq = pluck_notes_freqs[(bar + q) % len(pluck_notes_freqs)]
        pluck = to_list(synthesize_pluck_lead(LeadPreset(
            name="BreakPluck", lead_type="pluck", frequency=freq,
            duration_s=BEAT * 0.8, attack_s=0.002, decay_s=0.2,
            sustain=0.2, release_s=0.3, filter_cutoff=0.6
        )))
        # Pan plucks L/R alternating
        pan = -0.4 if q % 2 == 0 else 0.4
        gain_l = 0.35 * (1.0 - pan * 0.5)
        gain_r = 0.35 * (1.0 + pan * 0.5)
        mix_into(master_L, pluck, bar_offset + samples_for(q), gain=gain_l)
        mix_into(master_R, pluck, bar_offset + samples_for(q), gain=gain_r)

# Light hats
for bar in range(BREAK_BARS):
    bar_offset = break_start + samples_for(bar * 4)
    for q in range(4):
        mix_stereo(hat_closed, bar_offset + samples_for(q), 0.15, 0.15)

# Sub drone
sub_drone = to_list(synthesize_bass(BassPreset(
    name="SubDrone", bass_type="sub_sine", frequency=KEY_FREQS["F1"],
    duration_s=BREAK_BARS * BAR, attack_s=1.0, release_s=2.0
)))
mix_stereo(sub_drone, break_start, 0.35, 0.35)

cursor += samples_for(BREAK_BARS * 4)

# ── BUILD 2 (4 bars) ────────────────────────────────────────────────
build2_start = cursor

build2_drums = drum_pattern_build(BUILD2_BARS)
mix_stereo(build2_drums, build2_start, 0.65, 0.65)

riser2 = noise_riser[:samples_for(BUILD2_BARS * 4)]
mix_stereo(riser2, build2_start, 0.45, 0.45)

# Reverse hit before drop 2
rev2_offset = build2_start + samples_for(BUILD2_BARS * 4) - len(reverse_hit)
if rev2_offset > 0:
    mix_stereo(reverse_hit, rev2_offset, 0.7, 0.7)

cursor += samples_for(BUILD2_BARS * 4)

# ── DROP 2 (16 bars) — HEAVIER ──────────────────────────────────────
drop2_start = cursor

# Bigger impact
mix_stereo(sub_boom, drop2_start, 1.0, 1.0)
mix_stereo(cinema_hit, drop2_start, 0.6, 0.6)
# Clap layer on downbeat
mix_stereo(clap, drop2_start, 0.5, 0.5)

# Drums — same pattern but louder
for rep in range(DROP2_BARS // 4):
    offset = drop2_start + samples_for(rep * 16)
    drop2_drums = sidechain_pump(drum_pattern_drop(4), 16, depth=0.0)
    mix_stereo(drop2_drums, offset, 0.75, 0.75)
    # Extra clap layer on beat 3
    for bar in range(4):
        clap_off = offset + samples_for(bar * 4 + 2)
        mix_stereo(clap, clap_off, 0.3, 0.3)

# Heavier bass — drop2 pattern
for rep in range(DROP2_BARS // 4):
    offset = drop2_start + samples_for(rep * 16)
    d2_bass = sidechain_pump(bass_drop2_pattern(4), 16, depth=0.45)
    # Distort the bass more
    d2_bass = distort(d2_bass, drive=1.5)
    mix_stereo(d2_bass, offset, 0.85, 0.85)

# Lead — same motif but with more presence
for rep in range(DROP2_BARS // 4):
    offset = drop2_start + samples_for(rep * 16)
    melody2 = lead_melody_drop(4)
    mix_into(master_L, melody2, offset, gain=0.35)
    mix_into(master_R, melody2, offset, gain=0.5)

# Supersaw chord stabs every bar
for bar in range(DROP2_BARS):
    stab_offset = drop2_start + samples_for(bar * 4)
    mix_stereo(saw_chord, stab_offset, 0.2, 0.2)

# Stutter in last 2 bars
stutter_offset = drop2_start + samples_for((DROP2_BARS - 2) * 4)
mix_stereo(stutter, stutter_offset, 0.35, 0.35)
mix_stereo(stutter, stutter_offset + samples_for(4), 0.4, 0.4)

cursor += samples_for(DROP2_BARS * 4)

# ── OUTRO (8 bars) ──────────────────────────────────────────────────
outro_start = cursor

# Dark pad fading out
outro_pad = dark_pad[:samples_for(OUTRO_BARS * 4)]
outro_pad = fade_out(outro_pad, duration_s=BAR * 4)
outro_pad = lowpass(outro_pad, cutoff=0.12)
mix_stereo(outro_pad, outro_start, 0.4, 0.4)

# Sparse drums fading
outro_drums = drum_pattern_intro(OUTRO_BARS)
outro_drums = fade_out(outro_drums, duration_s=BAR * 4)
mix_stereo(outro_drums, outro_start, 0.3, 0.3)

# Sub decaying
outro_sub = to_list(synthesize_bass(BassPreset(
    name="OutroSub", bass_type="sub_sine", frequency=KEY_FREQS["F1"],
    duration_s=OUTRO_BARS * BAR, attack_s=0.01, release_s=OUTRO_BARS * BAR * 0.8
)))
outro_sub = fade_out(outro_sub, duration_s=BAR * 6)
mix_stereo(outro_sub, outro_start, 0.3, 0.3)


# ════════════════════════════════════════════════════════════════════
#  MIXDOWN & EXPORT
# ════════════════════════════════════════════════════════════════════
print("  [8/8] Mixdown & export...")

# Find peak for normalization
peak = 0.0
for i in range(total_samples):
    peak = max(peak, abs(master_L[i]), abs(master_R[i]))

if peak > 0:
    target = 0.95
    gain = target / peak
    for i in range(total_samples):
        master_L[i] *= gain
        master_R[i] *= gain

# Apply final soft limiting
for i in range(total_samples):
    master_L[i] = math.tanh(master_L[i])
    master_R[i] = math.tanh(master_R[i])

# Write stereo WAV
os.makedirs("output", exist_ok=True)
output_path = "output/dubstep_track.wav"

with wave.open(output_path, "w") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)  # 16-bit
    wf.setframerate(SR)

    # Write in chunks to manage memory
    chunk_size = SR  # 1 second at a time
    for start in range(0, total_samples, chunk_size):
        end = min(start + chunk_size, total_samples)
        frames = b""
        for i in range(start, end):
            l_sample = max(-32768, min(32767, int(master_L[i] * 32767)))
            r_sample = max(-32768, min(32767, int(master_R[i] * 32767)))
            frames += struct.pack("<hh", l_sample, r_sample)
        wf.writeframes(frames)

duration = total_samples / SR
file_size = os.path.getsize(output_path)

print()
print("═" * 56)
print("  DUBFORGE — Track Rendered Successfully!")
print("═" * 56)
print(f"  File:     {output_path}")
print(f"  Format:   16-bit stereo WAV @ {SR} Hz")
print(f"  BPM:      {BPM}")
print(f"  Key:      F minor")
print(f"  Duration: {duration:.1f}s ({int(duration // 60)}:{int(duration % 60):02d})")
print(f"  Bars:     {total_bars}")
print(f"  Size:     {file_size / 1024 / 1024:.1f} MB")
print(f"  Sections: Intro({INTRO_BARS}) → Build({BUILD_BARS}) → "
      f"Drop({DROP1_BARS}) → Break({BREAK_BARS}) → "
      f"Build({BUILD2_BARS}) → Drop({DROP2_BARS}) → Outro({OUTRO_BARS})")
print("═" * 56)
