#!/usr/bin/env python3
"""DUBFORGE -- "Wild Ones" (Electro House Remix)

A DUBFORGE electro house remix built around the studio acapella of
"Wild Ones" by Flo Rida feat. Sia.  The original isolated vocal
is loaded from MP3, normalised, time-aligned at 127 BPM, and sliced
bar-by-bar into every section of the arrangement.

    Song DNA (from Wikipedia — public factual data):
        Key:        Ab major
        BPM:        127
        Time:       4/4
        Chords:     Ab - Cm - Fm - Db  (I - iii - vi - IV)
        Vocal Range: Eb4 to C5
        Genre:      Dance-pop / electro house
        Duration:   ~3:53

    Acapella source:
        Flo-Rida-ft-Sia-Wild-Ones-Studio-Acapella.mp3
        44 100 Hz · stereo (down-mixed to mono) · ~246 s · ~130 bars

    Features:
        * REAL studio acapella — Sia & Flo Rida isolated vocals
        * Original hook melody in Ab major tracing Eb4-C5 range
        * 4-on-the-floor electro house drums (GALATCIA samples)
        * Supersaw chord walls cycling Ab-Cm-Fm-Db
        * Full stem export, MIDI, ALS, Serum presets

    Structure (128 bars at 127 BPM ≈ 4:02):
        Intro          8 bars  — Filtered pad + vocal whispers
        Verse 1       16 bars  — 4otf kick + bass + vocal chops
        Pre-Chorus 1   8 bars  — Build: riser + hook preview
        Chorus 1      16 bars  — Full drop: supersaw + hook lead
        Break          8 bars  — Acapella: vocal + pad only
        Verse 2        8 bars  — Kick + bass + vocal energy
        Pre-Chorus 2   8 bars  — Bigger build: all risers
        Chorus 2      16 bars  — Max energy: all layers + hook
        Bridge         8 bars  — Breakdown: vocal + pad (emotional)
        Final Chorus  16 bars  — Climax: everything layered
        Outro         16 bars  — Fade: pad + vocal dissolving

    Golden Section Point: bar ~79 (128/phi) → inside Final Chorus

Output:
    output/stems/wild_ones_*.wav       — 10 individual stem WAVs
    output/wild_ones.wav               — stereo mastered mixdown
    output/midi/wild_ones.mid          — MIDI for all melodic parts
    output/serum2/wild_ones_patches.json — Serum 2 patch reference
    output/ableton/Wild_Ones.als       — ALS with AudioClip refs
"""

import json
import math
import os
import subprocess
import wave

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import librosa
import numpy as np

# -- DUBFORGE engine -- Synthesizers --
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
from engine.chord_pad import ChordPadPreset, synthesize_chord_pad
from engine.arp_synth import ArpSynthPreset, synthesize_arp
from engine.transition_fx import TransitionPreset, synthesize_transition
from engine.vocal_chop import VocalChop, synthesize_chop

# -- DUBFORGE engine -- DSP pipeline --
from engine.sidechain import apply_sidechain, SidechainPreset
from engine.reverb_delay import apply_hall, apply_room, ReverbDelayPreset
from engine.stereo_imager import apply_mid_side, StereoPreset
from engine.mastering_chain import master, MasterSettings

# -- DUBFORGE engine -- DAW integration --
from engine.als_generator import ALSProject, ALSTrack, ALSScene, write_als
from engine.midi_export import NoteEvent, write_midi_file
from engine.serum2 import build_dubstep_patches
from engine.fxp_writer import (FXPPreset, FXPBank, VSTParam,
                               write_fxp, write_fxb, write_preset_manifest)

# -- DUBFORGE engine -- GALATCIA sample library --
from engine.galatcia import read_wav_samples

# -- Constants --
SR = 44100
BPM = 127
BEAT = 60.0 / BPM
BAR = BEAT * 4
PHI = 1.6180339887

GALATCIA_ROOT = r"C:\dev\DUBFORGE GALATCIA\Samples\Samples"
ACAPELLA_PATH = r"C:\dev\DUBFORGE GALATCIA\Flo-Rida-ft-Sia-Wild-Ones-Studio-Acapella.mp3"

# Acapella bar map — which bars of the source acapella feed each remix section
# (start_bar, end_bar) at 127 BPM against the original song structure
ACAP_MAP = {
    "INTRO":      (0, 8),       # Sia's opening hook
    "VERSE1":     (8, 24),      # Flo Rida verse 1
    "PRECHORUS1": (24, 32),     # Sia pre-chorus 1
    "CHORUS1":    (32, 48),     # Sia chorus 1
    "BREAK":      (0, 8),       # Reuse Sia's opening hook (stripped)
    "VERSE2":     (48, 56),     # Flo Rida verse 2 (first 8 bars)
    "PRECHORUS2": (64, 72),     # Sia pre-chorus 2
    "CHORUS2":    (72, 88),     # Sia chorus 2
    "BRIDGE":     (88, 96),     # Bridge
    "FINAL":      (96, 112),    # Final chorus
    "OUTRO":      (112, 122),   # Outro
}

# ====================================================================
#  KEY OF Ab MAJOR (440 Hz standard tuning)
# ====================================================================
A4 = 440.0
KEY_FREQS = {
    "Ab1": A4 * 2 ** (-36 / 12),
    "Bb1": A4 * 2 ** (-34 / 12),
    "C2":  A4 * 2 ** (-33 / 12),
    "Db2": A4 * 2 ** (-31 / 12),
    "Eb2": A4 * 2 ** (-29 / 12),
    "F2":  A4 * 2 ** (-28 / 12),
    "G2":  A4 * 2 ** (-26 / 12),
    "Ab2": A4 * 2 ** (-24 / 12),
    "Bb2": A4 * 2 ** (-22 / 12),
    "C3":  A4 * 2 ** (-21 / 12),
    "Db3": A4 * 2 ** (-19 / 12),
    "Eb3": A4 * 2 ** (-17 / 12),
    "F3":  A4 * 2 ** (-16 / 12),
    "G3":  A4 * 2 ** (-14 / 12),
    "Ab3": A4 * 2 ** (-12 / 12),
    "Bb3": A4 * 2 ** (-10 / 12),
    "C4":  A4 * 2 ** (-9 / 12),
    "Db4": A4 * 2 ** (-7 / 12),
    "Eb4": A4 * 2 ** (-5 / 12),
    "F4":  A4 * 2 ** (-4 / 12),
    "G4":  A4 * 2 ** (-2 / 12),
    "Ab4": A4,
    "Bb4": A4 * 2 ** (2 / 12),
    "C5":  A4 * 2 ** (3 / 12),
}

MIDI = {
    "Ab1": 32, "Bb1": 34, "C2": 36, "Db2": 37, "Eb2": 39,
    "F2": 41, "G2": 43, "Ab2": 44, "Bb2": 46, "C3": 48,
    "Db3": 49, "Eb3": 51, "F3": 53, "G3": 55, "Ab3": 56,
    "Bb3": 58, "C4": 60, "Db4": 61, "Eb4": 63, "F4": 65,
    "G4": 67, "Ab4": 68, "Bb4": 70, "C5": 72,
}

# Chord voicings (MIDI notes)
CHORD_Ab = [MIDI["Ab3"], MIDI["C4"], MIDI["Eb4"]]        # I
CHORD_Cm = [MIDI["C4"], MIDI["Eb4"], MIDI["G4"]]         # iii
CHORD_Fm = [MIDI["F3"], MIDI["Ab3"], MIDI["C4"]]         # vi
CHORD_Db = [MIDI["Db4"], MIDI["F4"], MIDI["Ab4"]]        # IV

# 4-chord cycle: Ab - Cm - Fm - Db (2 bars each = 8-bar cycle)
CHORD_CYCLE = [
    ("Ab", CHORD_Ab, KEY_FREQS["Ab3"]),
    ("Cm", CHORD_Cm, KEY_FREQS["C4"]),
    ("Fm", CHORD_Fm, KEY_FREQS["F3"]),
    ("Db", CHORD_Db, KEY_FREQS["Db4"]),
]

# DSP presets
SC_PUMP = SidechainPreset("WOPump", "pump", bpm=BPM, depth=0.70,
                          attack_ms=0.5, release_ms=180.0)
SC_HARD = SidechainPreset("WOHard", "pump", bpm=BPM, depth=0.85,
                          attack_ms=0.3, release_ms=150.0)
HALL_VERB = ReverbDelayPreset("WOHall", "hall", decay_time=3.5,
                              pre_delay_ms=35.0, damping=0.35, mix=0.30)
ROOM_VERB = ReverbDelayPreset("WORoom", "room", decay_time=0.7,
                              pre_delay_ms=10.0, room_size=0.3, mix=0.20)


# -- Helpers --

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


def peak_normalize(buf: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(buf))
    if peak > 1.0:
        buf /= peak
    return buf


# ====================================================================
#  SOUND DESIGN -- Pre-render all elements
# ====================================================================

print("=" * 60)
print('  DUBFORGE -- "Wild Ones" (Electro House Remix)')
print("=" * 60)
print(f"  BPM: {BPM}  |  Key: Ab major  |  Tuning: 440 Hz  |  SR: {SR}")
print(f"  Chords: Ab - Cm - Fm - Db  (I - iii - vi - IV)")
print(f"  Structure: 128 bars  |  3 choruses  |  real acapella + hook")
print()

# -- SERUM 2 PATCH DEFINITIONS + FXP PRESETS --
print("  [1/12] Loading Serum 2 patch definitions...")
serum_patches = build_dubstep_patches()
os.makedirs("output/serum2", exist_ok=True)
with open("output/serum2/wild_ones_patches.json", "w") as f:
    json.dump(serum_patches, f, indent=2, default=str)
print(f"         {len(serum_patches)} Serum 2 patches -> JSON")

# Convert to .fxp presets
os.makedirs("output/presets", exist_ok=True)


def _serum_dict_to_fxp(patch_dict: dict) -> FXPPreset:
    """Map a Serum2Patch dict into an FXPPreset with normalized params."""
    params = []
    idx = 0
    osc_a = patch_dict.get("osc_a", {})
    params.append(VSTParam(idx, "OscA_WtPos", float(osc_a.get("wt_position", 0.0)))); idx += 1
    params.append(VSTParam(idx, "OscA_Level", float(osc_a.get("level", 0.8)))); idx += 1
    params.append(VSTParam(idx, "OscA_Unison", min(1.0, float(osc_a.get("unison_voices", 1)) / 16.0))); idx += 1
    detune_val = osc_a.get("unison_detune", 0.0)
    if isinstance(detune_val, list):
        detune_val = detune_val[0] if detune_val else 0.0
    params.append(VSTParam(idx, "OscA_Detune", float(detune_val))); idx += 1
    params.append(VSTParam(idx, "OscA_Warp1", float(osc_a.get("warp_1_amount", 0.0)))); idx += 1
    params.append(VSTParam(idx, "OscA_Warp2", float(osc_a.get("warp_2_amount", 0.0)))); idx += 1
    osc_b = patch_dict.get("osc_b", {})
    params.append(VSTParam(idx, "OscB_WtPos", float(osc_b.get("wt_position", 0.0)))); idx += 1
    params.append(VSTParam(idx, "OscB_Level", float(osc_b.get("level", 0.0)))); idx += 1
    params.append(VSTParam(idx, "OscB_Semi", min(1.0, max(0.0, (float(osc_b.get("semi", 0)) + 24) / 48.0)))); idx += 1
    sub_osc = patch_dict.get("sub", {})
    params.append(VSTParam(idx, "Sub_Level", float(sub_osc.get("level", 0.0)))); idx += 1
    params.append(VSTParam(idx, "Sub_Enabled", 1.0 if sub_osc.get("enabled") else 0.0)); idx += 1
    filt = patch_dict.get("filter_1", {})
    params.append(VSTParam(idx, "Filt1_Cutoff", min(1.0, float(filt.get("cutoff", 1000.0)) / 22050.0))); idx += 1
    params.append(VSTParam(idx, "Filt1_Reso", float(filt.get("resonance", 0.0)))); idx += 1
    params.append(VSTParam(idx, "Filt1_Drive", float(filt.get("drive", 0.0)))); idx += 1
    env1 = patch_dict.get("env_1", {})
    params.append(VSTParam(idx, "Env1_Attack", min(1.0, float(env1.get("attack_ms", 1.0)) / 5000.0))); idx += 1
    params.append(VSTParam(idx, "Env1_Decay", min(1.0, float(env1.get("decay_ms", 200.0)) / 5000.0))); idx += 1
    params.append(VSTParam(idx, "Env1_Sustain", float(env1.get("sustain", 1.0)))); idx += 1
    params.append(VSTParam(idx, "Env1_Release", min(1.0, float(env1.get("release_ms", 200.0)) / 5000.0))); idx += 1
    for mi in range(1, 5):
        macro = patch_dict.get(f"macro_{mi}", {})
        params.append(VSTParam(idx, f"Macro{mi}", float(macro.get("value", 0.0)))); idx += 1
    params.append(VSTParam(idx, "Master_Volume", float(patch_dict.get("master_volume", 0.8)))); idx += 1
    params.append(VSTParam(idx, "Master_Tune", min(1.0, float(patch_dict.get("master_tune", 440.0)) / 880.0))); idx += 1
    voicing = patch_dict.get("voicing", {})
    params.append(VSTParam(idx, "Portamento", min(1.0, float(voicing.get("portamento_ms", 0.0)) / 500.0))); idx += 1
    return FXPPreset(name=patch_dict.get("name", "DUBFORGE")[:28], params=params)


fxp_presets = {}
for i, sp in enumerate(serum_patches):
    fxp = _serum_dict_to_fxp(sp)
    fxp_path = f"output/presets/{fxp.name.replace(' ', '_')}.fxp"
    write_fxp(fxp, fxp_path)
    fxp_presets[fxp.name] = fxp

bank = FXPBank(name="WILD_ONES_BANK", presets=list(fxp_presets.values()))
write_fxb(bank, "output/presets/WILD_ONES_BANK.fxb")
write_preset_manifest(fxp_presets, "output/presets")
print(f"         {len(fxp_presets)} .fxp presets + 1 .fxb bank written")

# -- GALATCIA REAL DRUMS --
print("  [2/12] Loading GALATCIA drum samples...")

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

# -- BASS --
print("  [3/12] Bass (sub + electro wobble)...")

sub_bass = to_np(synthesize_bass(BassPreset(
    name="WOSub", bass_type="sub_sine", frequency=KEY_FREQS["Ab1"],
    duration_s=BEAT * 2, attack_s=0.005, release_s=0.15, distortion=0.0
)))

wobble_bass = to_np(synthesize_bass(BassPreset(
    name="WOWobble", bass_type="wobble", frequency=KEY_FREQS["Ab2"],
    duration_s=BEAT * 2, attack_s=0.01, release_s=0.18,
    fm_ratio=2.0, fm_depth=2.5, distortion=0.20, filter_cutoff=0.55
)))

# Bass notes for each chord root
bass_Ab = to_np(synthesize_bass(BassPreset(
    name="WOBass_Ab", bass_type="sub_sine", frequency=KEY_FREQS["Ab1"],
    duration_s=BAR * 2, attack_s=0.005, release_s=0.2
)))
bass_C = to_np(synthesize_bass(BassPreset(
    name="WOBass_C", bass_type="sub_sine", frequency=KEY_FREQS["C2"],
    duration_s=BAR * 2, attack_s=0.005, release_s=0.2
)))
bass_F = to_np(synthesize_bass(BassPreset(
    name="WOBass_F", bass_type="sub_sine", frequency=KEY_FREQS["F2"],
    duration_s=BAR * 2, attack_s=0.005, release_s=0.2
)))
bass_Db = to_np(synthesize_bass(BassPreset(
    name="WOBass_Db", bass_type="sub_sine", frequency=KEY_FREQS["Db2"],
    duration_s=BAR * 2, attack_s=0.005, release_s=0.2
)))

BASS_ROOTS = [bass_Ab, bass_C, bass_F, bass_Db]
print("         sub + wobble + 4 chord root bass tones")

# -- SUPERSAW CHORDS (Ab - Cm - Fm - Db) --
print("  [4/12] Supersaw chords (Ab - Cm - Fm - Db)...")

saw_Ab = to_np(render_supersaw_mono(SupersawPatch(
    name="WOSaw_Ab", n_voices=13, detune_cents=42.0,
    mix=0.78, cutoff_hz=8000.0, resonance=0.35,
    attack=0.005, decay=0.2, sustain=0.7, release=0.25,
    master_gain=0.95
), freq=KEY_FREQS["Ab3"], duration=BAR * 2))

saw_Cm = to_np(render_supersaw_mono(SupersawPatch(
    name="WOSaw_Cm", n_voices=13, detune_cents=42.0,
    mix=0.78, cutoff_hz=8000.0, resonance=0.35,
    attack=0.005, decay=0.2, sustain=0.7, release=0.25,
    master_gain=0.95
), freq=KEY_FREQS["C4"], duration=BAR * 2))

saw_Fm = to_np(render_supersaw_mono(SupersawPatch(
    name="WOSaw_Fm", n_voices=13, detune_cents=42.0,
    mix=0.78, cutoff_hz=8000.0, resonance=0.35,
    attack=0.005, decay=0.2, sustain=0.7, release=0.25,
    master_gain=0.95
), freq=KEY_FREQS["F3"], duration=BAR * 2))

saw_Db = to_np(render_supersaw_mono(SupersawPatch(
    name="WOSaw_Db", n_voices=13, detune_cents=42.0,
    mix=0.78, cutoff_hz=8000.0, resonance=0.35,
    attack=0.005, decay=0.2, sustain=0.7, release=0.25,
    master_gain=0.95
), freq=KEY_FREQS["Db4"], duration=BAR * 2))

SAW_CHORDS = [saw_Ab, saw_Cm, saw_Fm, saw_Db]

# Stab versions (short)
stab_Ab = to_np(render_supersaw_mono(SupersawPatch(
    name="WOStab_Ab", n_voices=11, detune_cents=38.0,
    mix=0.75, cutoff_hz=9000.0, resonance=0.40,
    attack=0.002, decay=0.10, sustain=0.4, release=0.12,
    master_gain=0.90
), freq=KEY_FREQS["Ab3"], duration=BEAT * 0.5))

stab_Cm = to_np(render_supersaw_mono(SupersawPatch(
    name="WOStab_Cm", n_voices=11, detune_cents=38.0,
    mix=0.75, cutoff_hz=9000.0, resonance=0.40,
    attack=0.002, decay=0.10, sustain=0.4, release=0.12,
    master_gain=0.90
), freq=KEY_FREQS["C4"], duration=BEAT * 0.5))

stab_Fm = to_np(render_supersaw_mono(SupersawPatch(
    name="WOStab_Fm", n_voices=11, detune_cents=38.0,
    mix=0.75, cutoff_hz=9000.0, resonance=0.40,
    attack=0.002, decay=0.10, sustain=0.4, release=0.12,
    master_gain=0.90
), freq=KEY_FREQS["F3"], duration=BEAT * 0.5))

stab_Db = to_np(render_supersaw_mono(SupersawPatch(
    name="WOStab_Db", n_voices=11, detune_cents=38.0,
    mix=0.75, cutoff_hz=9000.0, resonance=0.40,
    attack=0.002, decay=0.10, sustain=0.4, release=0.12,
    master_gain=0.90
), freq=KEY_FREQS["Db4"], duration=BEAT * 0.5))

SAW_STABS = [stab_Ab, stab_Cm, stab_Fm, stab_Db]
print("         4 chord walls + 4 stabs (Ab/Cm/Fm/Db)")

# -- HOOK LEAD MELODY --
# Original hook melody tracing Eb4-C5 vocal range over the chord cycle
# Pattern: ascending call → descending answer (8-bar hook phrase)
print("  [5/12] Hook lead melody (pluck + FM)...")

# Pluck leads for crisp hook articulation
hook_notes_pluck = {}
for note_name in ["Eb4", "F4", "G4", "Ab4", "Bb4", "C5", "C4", "Db4"]:
    hook_notes_pluck[note_name] = to_np(synthesize_pluck_lead(LeadPreset(
        name=f"WOPluck_{note_name}", lead_type="pluck",
        frequency=KEY_FREQS[note_name],
        duration_s=BEAT * 0.75, attack_s=0.002, decay_s=0.12,
        sustain=0.35, release_s=0.15, filter_cutoff=0.82,
        resonance=0.40, distortion=0.05
    )))

# FM leads for warm sustained hook tone
hook_notes_fm = {}
for note_name in ["Eb4", "F4", "G4", "Ab4", "Bb4", "C5", "C4", "Db4"]:
    hook_notes_fm[note_name] = to_np(synthesize_fm_lead(LeadPreset(
        name=f"WOFM_{note_name}", lead_type="fm_lead",
        frequency=KEY_FREQS[note_name],
        duration_s=BEAT * 1.0, attack_s=0.008, decay_s=0.15,
        sustain=0.55, release_s=0.2, fm_ratio=2.0, fm_depth=1.8,
        filter_cutoff=0.78, resonance=0.32, distortion=0.08
    )))

# The hook melody sequence (8 bars = 32 beats)
# Bar 1-2 (Ab chord): Eb4 → F4 → Ab4 → Ab4 (ascending call)
# Bar 3-4 (Cm chord): G4 → Eb4 → C4 → C4 (descending answer)
# Bar 5-6 (Fm chord): F4 → Ab4 → C5 → Bb4 (ascending peak)
# Bar 7-8 (Db chord): Ab4 → F4 → Db4 → Eb4 (resolving)
HOOK_MELODY = [
    # (beat_offset, note_name, duration_beats)
    # Bars 1-2 (over Ab)
    (0.0, "Eb4", 1.0), (1.0, "Eb4", 0.5), (1.5, "F4", 0.5),
    (2.0, "Ab4", 1.5), (4.0, "Ab4", 1.0), (5.0, "F4", 0.5),
    (5.5, "Ab4", 0.5), (6.0, "Ab4", 2.0),
    # Bars 3-4 (over Cm)
    (8.0, "G4", 1.0), (9.0, "G4", 0.5), (9.5, "Eb4", 0.5),
    (10.0, "C4", 1.5), (12.0, "Eb4", 1.0), (13.0, "C4", 0.5),
    (13.5, "Eb4", 0.5), (14.0, "C4", 2.0),
    # Bars 5-6 (over Fm)
    (16.0, "F4", 1.0), (17.0, "F4", 0.5), (17.5, "Ab4", 0.5),
    (18.0, "C5", 1.5), (20.0, "C5", 1.0), (21.0, "Bb4", 0.5),
    (21.5, "Ab4", 0.5), (22.0, "Bb4", 2.0),
    # Bars 7-8 (over Db)
    (24.0, "Ab4", 1.0), (25.0, "Ab4", 0.5), (25.5, "F4", 0.5),
    (26.0, "Db4", 1.5), (28.0, "F4", 1.0), (29.0, "Db4", 0.5),
    (29.5, "Eb4", 0.5), (30.0, "Eb4", 2.0),
]

print(f"         {len(HOOK_MELODY)} hook melody notes (Eb4-C5 range)")

# -- REAL ACAPELLA LOADING --
print("  [6/12] Loading studio acapella...")

_acap_raw, _acap_sr = librosa.load(ACAPELLA_PATH, sr=SR, mono=True)
# Normalise — source peaks at ~1.46 (clipping)
_acap_peak = float(np.max(np.abs(_acap_raw)))
acapella_mono: np.ndarray = _acap_raw * (0.95 / _acap_peak) if _acap_peak > 0 else _acap_raw

acapella_total_bars = len(acapella_mono) / (BAR * SR)
print(f"         {len(acapella_mono)/SR:.1f}s  {acapella_total_bars:.1f} bars  "
      f"peak={_acap_peak:.3f} -> normalised to 0.95")


def slice_acapella(start_bar: int, num_bars: int) -> np.ndarray:
    """Extract *num_bars* from the acapella starting at *start_bar*."""
    s = int(start_bar * BAR * SR)
    e = int((start_bar + num_bars) * BAR * SR)
    target = int(num_bars * BAR * SR)
    raw = acapella_mono[s:min(e, len(acapella_mono))]
    if len(raw) >= target:
        return raw[:target]
    buf = np.zeros(target)
    buf[:len(raw)] = raw
    return buf


# Keep stutter + long-ah chops for FX/transition textures only
chop_stutter = to_np(synthesize_chop(VocalChop(
    name="WOChopStut", vowel="eh", note="E4",
    duration_s=BEAT * 1.0, attack_s=0.003, release_s=0.04,
    formant_shift=3.0, distortion=0.15,
    stutter_count=8, stutter_pitch_drift=0.3
)))
chop_long_ah = to_np(synthesize_chop(VocalChop(
    name="WOChopLongAh", vowel="ah", note="A3",
    duration_s=BEAT * 2.0, attack_s=0.03, release_s=0.4,
    formant_shift=-1.0, distortion=0.02
)))
chop_ee = to_np(synthesize_chop(VocalChop(
    name="WOChopEe", vowel="ee", note="C4",
    duration_s=BEAT * 0.3, attack_s=0.003, release_s=0.05,
    formant_shift=4.0, distortion=0.12
)))

print("         studio acapella loaded + 3 synth chops for FX")

# -- PADS --
print("  [7/12] Pads...")

lush_pad = to_np(synthesize_lush_pad(PadPreset(
    name="WOLushPad", pad_type="lush", frequency=KEY_FREQS["Ab3"],
    duration_s=BAR * 8, detune_cents=18.0, filter_cutoff=0.38,
    attack_s=1.5, release_s=2.5, reverb_amount=0.65, brightness=0.35
)))

dark_pad = to_np(synthesize_dark_pad(PadPreset(
    name="WODarkPad", pad_type="dark", frequency=KEY_FREQS["Ab3"],
    duration_s=BAR * 8, detune_cents=14.0, filter_cutoff=0.22,
    attack_s=2.0, release_s=3.0, reverb_amount=0.60, brightness=0.18
)))

chord_pad_major = to_np(synthesize_chord_pad(ChordPadPreset(
    name="WOChordPad", chord_type="major7",
    root_freq=KEY_FREQS["Ab3"], duration_s=BAR * 4,
    detune_cents=16.0, attack_s=1.0, release_s=2.0,
    brightness=0.40, warmth=0.6, reverb_amount=0.45
)))

# -- ARP --
print("  [8/12] Arp synth...")

arp_pluck = to_np(synthesize_arp(ArpSynthPreset(
    name="WOArpPluck", arp_type="pulse",
    base_freq=KEY_FREQS["Ab3"], duration_s=BAR * 4,
    step_count=16, filter_cutoff=0.50, resonance=0.35,
    octave_range=2
)))

arp_shimmer = to_np(synthesize_arp(ArpSynthPreset(
    name="WOArpShimmer", arp_type="acid",
    base_freq=KEY_FREQS["Ab3"], duration_s=BAR * 4,
    step_count=16, filter_cutoff=0.35, resonance=0.45,
    octave_range=2
)))

# -- RISERS + FX --
print("  [9/12] Risers, impacts & transitions...")

pitch_riser = to_np(synthesize_riser(RiserPreset(
    name="WOPitchRise", riser_type="pitch_rise",
    duration_s=BAR * 4,
    start_freq=80.0, end_freq=2500.0,
    brightness=0.55, intensity=0.70, distortion=0.03
)))

harmonic_riser = to_np(synthesize_riser(RiserPreset(
    name="WOHarmonicBuild", riser_type="harmonic_build",
    duration_s=BAR * 4,
    start_freq=60.0, end_freq=3000.0,
    brightness=0.50, intensity=0.75, distortion=0.05
)))

noise_riser = to_np(synthesize_riser(RiserPreset(
    name="WONoiseSweep", riser_type="noise_sweep",
    duration_s=BAR * 4,
    start_freq=100.0, end_freq=3500.0,
    brightness=0.40, intensity=0.55
)))

sub_boom = to_np(synthesize_sub_boom(ImpactPreset(
    name="WOBoom", impact_type="sub_boom", duration_s=2.5,
    frequency=KEY_FREQS["Ab1"], decay_s=2.0, intensity=0.9,
    reverb_amount=0.35
)))

cinema_hit = to_np(synthesize_cinematic_hit(ImpactPreset(
    name="WOCinemaHit", impact_type="cinematic_hit", duration_s=1.8,
    frequency=65.0, decay_s=1.2, brightness=0.55, intensity=0.85
)))

reverse_hit = to_np(synthesize_reverse_hit(ImpactPreset(
    name="WORevHit", impact_type="reverse_hit", duration_s=1.5,
    frequency=80.0, decay_s=1.0, intensity=0.75
)))

stutter_fx = to_np(synthesize_stutter(GlitchPreset(
    name="WOStutter", glitch_type="stutter",
    frequency=KEY_FREQS["Ab3"],
    duration_s=BEAT * 2, rate=16.0, depth=0.8, distortion=0.15
)))

tape_stop = to_np(synthesize_transition(TransitionPreset(
    name="WOTapeStop", fx_type="tape_stop",
    duration_s=BEAT * 2, start_freq=KEY_FREQS["Ab3"],
    brightness=0.35
)))

pitch_dive = to_np(synthesize_transition(TransitionPreset(
    name="WOPitchDive", fx_type="pitch_dive",
    duration_s=BEAT * 1.5, start_freq=KEY_FREQS["Ab4"],
    end_freq=KEY_FREQS["Ab1"], brightness=0.45
)))

# -- DRONE --
print("  [10/12] Drone...")

drone = to_np(synthesize_drone(DronePreset(
    name="WOAtmosDrone", drone_type="evolving",
    frequency=KEY_FREQS["Ab1"], duration_s=BAR * 8,
    num_voices=7, detune_cents=8.0, brightness=0.15,
    movement=0.45, attack_s=2.0, release_s=3.0,
    distortion=0.05, reverb_amount=0.50
)))

# -- FM HIT (for chord accents) --
print("  [11/12] FM hit...")

fm_hit = to_np(render_fm(FMPatch(
    name="WOFMAccent",
    operators=[
        FMOperator(freq_ratio=1.0, amplitude=1.0, mod_index=4.0,
                   envelope=(0.002, 0.08, 0.0, 0.15)),
        FMOperator(freq_ratio=2.0, amplitude=0.7, mod_index=2.5,
                   envelope=(0.002, 0.10, 0.0, 0.18)),
    ],
    algorithm=0, master_gain=0.60
), freq=KEY_FREQS["Ab3"], duration=0.3))

print("  [12/12] Sound design complete.")
print()


# ====================================================================
#  DRUM PATTERNS — 4-on-the-floor electro house
# ====================================================================

def drum_chorus(bars: int = 4) -> np.ndarray:
    """Full 4-on-the-floor chorus drums."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        # 4-on-the-floor kick
        for beat in range(4):
            mix_into(buf, kick, bo + samples_for(beat), gain=0.85)
        # Snare/clap on 2 and 4
        mix_into(buf, snare, bo + samples_for(1), gain=0.72)
        mix_into(buf, clap, bo + samples_for(1), gain=0.30)
        mix_into(buf, snare, bo + samples_for(3), gain=0.72)
        mix_into(buf, clap, bo + samples_for(3), gain=0.30)
        # Offbeat open hats (classic house)
        for eighth in range(8):
            if eighth % 2 == 1:  # offbeats
                mix_into(buf, hat_open, bo + samples_for(eighth * 0.5),
                         gain=0.22)
            else:
                mix_into(buf, hat_closed, bo + samples_for(eighth * 0.5),
                         gain=0.28)
    return peak_normalize(buf)


def drum_verse(bars: int = 4) -> np.ndarray:
    """Verse drums — kick + hats, lighter."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        for beat in range(4):
            mix_into(buf, kick, bo + samples_for(beat), gain=0.75)
        mix_into(buf, snare, bo + samples_for(1), gain=0.40)
        mix_into(buf, snare, bo + samples_for(3), gain=0.40)
        for eighth in range(8):
            if eighth % 2 == 1:
                mix_into(buf, hat_closed, bo + samples_for(eighth * 0.5),
                         gain=0.18)
            else:
                mix_into(buf, hat_closed, bo + samples_for(eighth * 0.5),
                         gain=0.22)
    return peak_normalize(buf)


def drum_build(bars: int = 4) -> np.ndarray:
    """Build-up drums — accelerating snare roll."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, kick, bo, gain=0.65)
        mix_into(buf, kick, bo + samples_for(2), gain=0.65)
        divisions = [4, 8, 16, 32][min(bar, 3)]
        step = 4.0 / divisions
        for hit in range(divisions):
            vel = 0.25 + 0.50 * (bar / bars) * (hit / divisions)
            mix_into(buf, snare, bo + samples_for(hit * step), gain=vel)
    return peak_normalize(buf)


def drum_intro(bars: int = 4) -> np.ndarray:
    """Minimal intro hats."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        for q in range(4):
            mix_into(buf, hat_closed, bo + samples_for(q),
                     gain=0.10 + 0.04 * (bar / max(bars - 1, 1)))
    return buf


# ====================================================================
#  CHORD PATTERN — Ab - Cm - Fm - Db cycling
# ====================================================================

def chord_progression_full(bars: int = 8) -> np.ndarray:
    """Full supersaw chord progression cycling through the 4 chords."""
    buf = render_section(bars)
    for bar in range(bars):
        chord_idx = (bar // 2) % 4  # 2 bars per chord
        bo = samples_for(bar * 4)
        saw = SAW_CHORDS[chord_idx]
        seg = saw[:min(len(saw), samples_for(4))]
        mix_into(buf, seg, bo, gain=1.40)
        # Stab accent on beat 1
        stab = SAW_STABS[chord_idx]
        mix_into(buf, stab, bo, gain=0.75)
    return buf


def chord_progression_filtered(bars: int = 8) -> np.ndarray:
    """Filtered chord pad (for intros/breaks)."""
    buf = chord_progression_full(bars)
    return lowpass(buf, cutoff=0.12)


# ====================================================================
#  HOOK MELODY PATTERN
# ====================================================================

def hook_melody_render(bars: int = 8, pluck_gain: float = 0.32,
                       fm_gain: float = 0.25) -> np.ndarray:
    """Render the 8-bar hook melody using pluck + FM leads."""
    buf = render_section(bars)
    for beat_off, note_name, dur in HOOK_MELODY:
        offset = samples_for(beat_off)
        if offset < len(buf):
            pluck = hook_notes_pluck[note_name]
            fm = hook_notes_fm[note_name]
            mix_into(buf, pluck, offset, gain=pluck_gain)
            mix_into(buf, fm, offset, gain=fm_gain)
    return buf


# ====================================================================
#  BASS PATTERN — following chord roots
# ====================================================================

def bass_pattern(bars: int = 8, gain: float = 0.55) -> np.ndarray:
    """Bass following the chord root progression."""
    buf = render_section(bars)
    for bar in range(bars):
        chord_idx = (bar // 2) % 4
        bo = samples_for(bar * 4)
        bass_root = BASS_ROOTS[chord_idx]
        seg = bass_root[:min(len(bass_root), samples_for(4))]
        mix_into(buf, seg, bo, gain=gain)
        # Wobble accent every other beat
        if bar % 2 == 0:
            mix_into(buf, wobble_bass, bo + samples_for(2), gain=gain * 0.4)
    return buf


# ====================================================================
#  ACAPELLA VOCAL PATTERN  (real vocal slicing)
# ====================================================================

# These wrapper functions are kept so existing arrangement code
# can call them, but they now just proxy to slice_acapella().

def acapella_section(bars: int = 8, acap_start: int = 0) -> np.ndarray:
    """Slice *bars* of real acapella starting at *acap_start*."""
    return slice_acapella(acap_start, bars)


def vocal_verse_pattern(bars: int = 4, acap_start: int = 0) -> np.ndarray:
    """Verse vocal — real acapella slice."""
    return slice_acapella(acap_start, bars)


def vocal_chorus_pattern(bars: int = 4, acap_start: int = 0) -> np.ndarray:
    """Chorus vocal — real acapella slice."""
    return slice_acapella(acap_start, bars)


# ====================================================================
#  STRUCTURE — 128 bars
# ====================================================================

INTRO_BARS = 8
VERSE1_BARS = 16
PRECHORUS1_BARS = 8
CHORUS1_BARS = 16
BREAK_BARS = 8
VERSE2_BARS = 8
PRECHORUS2_BARS = 8
CHORUS2_BARS = 16
BRIDGE_BARS = 8
FINAL_CHORUS_BARS = 16
OUTRO_BARS = 16

total_bars = (INTRO_BARS + VERSE1_BARS + PRECHORUS1_BARS + CHORUS1_BARS +
              BREAK_BARS + VERSE2_BARS + PRECHORUS2_BARS + CHORUS2_BARS +
              BRIDGE_BARS + FINAL_CHORUS_BARS + OUTRO_BARS)
total_samples = samples_for(total_bars * 4)
duration_s = total_samples / SR
golden_section_bar = int(total_bars / PHI)

print(f"  Structure: {total_bars} bars = {duration_s:.1f}s "
      f"({int(duration_s // 60)}:{int(duration_s % 60):02d})")
print(f"  Sections: {INTRO_BARS}/{VERSE1_BARS}/{PRECHORUS1_BARS}/"
      f"{CHORUS1_BARS}/{BREAK_BARS}/{VERSE2_BARS}/{PRECHORUS2_BARS}/"
      f"{CHORUS2_BARS}/{BRIDGE_BARS}/{FINAL_CHORUS_BARS}/{OUTRO_BARS}")
print(f"  Golden Section Point: bar ~{golden_section_bar}")
print()


# ====================================================================
#  STEM BUFFERS
# ====================================================================

STEM_NAMES = [
    "DRUMS", "BASS", "CHORDS", "HOOK", "PAD",
    "VOCAL", "ARP", "RISER", "FX", "DRONE",
]

STEM_PAN = {
    "DRUMS": 0.0, "BASS": 0.0, "CHORDS": 0.10, "HOOK": -0.08,
    "PAD": 0.0, "VOCAL": 0.0, "ARP": -0.18, "RISER": 0.0,
    "FX": 0.0, "DRONE": 0.0,
}

stems: dict[str, np.ndarray] = {
    name: np.zeros(total_samples) for name in STEM_NAMES
}

cursor = 0


def build_gain(bar_index: int, total_build_bars: int,
               start: float = 0.15, end: float = 0.85) -> float:
    """Phi acceleration curve for builds."""
    t = bar_index / max(total_build_bars - 1, 1)
    return start + (end - start) * (t ** PHI)


# ── INTRO (8 bars) ─────────────────────────────────────────────────
print("  Rendering Intro (8 bars)...")
intro_start = cursor

# Filtered pad
intro_pad = lush_pad[:samples_for(INTRO_BARS * 4)]
intro_pad = fade_in(intro_pad, duration_s=BAR * 3)
intro_pad = lowpass(intro_pad, cutoff=0.08)
mix_into(stems["PAD"], intro_pad, intro_start, gain=0.30)

# Atmospheric drone
intro_drone = drone[:samples_for(INTRO_BARS * 4)]
intro_drone = fade_in(intro_drone, duration_s=BAR * 4)
mix_into(stems["DRONE"], intro_drone, intro_start, gain=0.25)

# Whispered vocal — Sia's intro hook, filtered tease
_a = ACAP_MAP["INTRO"]
intro_vox = slice_acapella(_a[0], INTRO_BARS)
intro_vox = lowpass(intro_vox, cutoff=0.18)
intro_vox = fade_in(intro_vox, duration_s=BAR * 2)
mix_into(stems["VOCAL"], intro_vox, intro_start, gain=0.30)

# Light hats fading in
intro_drums = drum_intro(INTRO_BARS)
intro_drums = fade_in(intro_drums, duration_s=BAR * 4)
mix_into(stems["DRUMS"], intro_drums, intro_start, gain=0.20)

# Filtered chord preview (last 4 bars)
chord_filt = chord_progression_filtered(4)
chord_filt = fade_in(chord_filt, duration_s=BAR * 2)
mix_into(stems["CHORDS"], chord_filt, intro_start + samples_for(16), gain=0.30)

# Reverse hit into verse
rev_off = intro_start + samples_for(INTRO_BARS * 4) - len(reverse_hit)
if rev_off > intro_start:
    mix_into(stems["FX"], reverse_hit, rev_off, gain=0.25)

cursor += samples_for(INTRO_BARS * 4)

# ── VERSE 1 (16 bars) ─── "4otf kick + bass + vocal chops" ────────
print("  Rendering Verse 1 (16 bars)...")
verse1_start = cursor

# Drums — verse pattern
for rep in range(VERSE1_BARS // 4):
    offset = verse1_start + samples_for(rep * 16)
    d = drum_verse(4)
    mix_into(stems["DRUMS"], d, offset, gain=0.52)

# Bass following chord roots
v1_bass = apply_sidechain(bass_pattern(VERSE1_BARS, gain=0.50), SC_PUMP, SR)
mix_into(stems["BASS"], v1_bass, verse1_start, gain=0.48)

# Real acapella — Flo Rida verse 1
_a = ACAP_MAP["VERSE1"]
v1_vox = slice_acapella(_a[0], VERSE1_BARS)
v1_vox = fade_in(v1_vox, duration_s=BAR)
mix_into(stems["VOCAL"], v1_vox, verse1_start, gain=0.55)

# Light pad
verse_pad = lush_pad[:samples_for(VERSE1_BARS * 4)]
verse_pad = lowpass(verse_pad, cutoff=0.15)
mix_into(stems["PAD"], verse_pad, verse1_start, gain=0.22)

# Arp (subtle)
for rep in range(VERSE1_BARS // 4):
    offset = verse1_start + samples_for(rep * 16)
    seg = arp_pluck[:min(len(arp_pluck), samples_for(16))]
    mix_into(stems["ARP"], seg, offset, gain=0.12)

# Drone bed
for rep in range(VERSE1_BARS // 8 + 1):
    offset = verse1_start + samples_for(rep * 32)
    seg = drone[:min(len(drone), samples_for(32))]
    mix_into(stems["DRONE"], seg, offset, gain=0.12)

cursor += samples_for(VERSE1_BARS * 4)

# ── PRE-CHORUS 1 (8 bars) ─── "Build: riser + hook preview" ───────
print("  Rendering Pre-Chorus 1 (8 bars)...")
pc1_start = cursor

# Build drums
pc1_drums = drum_build(PRECHORUS1_BARS)
mix_into(stems["DRUMS"], pc1_drums, pc1_start, gain=0.45)

# Risers
riser_seg = pitch_riser[:samples_for(PRECHORUS1_BARS * 4)]
mix_into(stems["RISER"], riser_seg, pc1_start, gain=0.22)
noise_seg = noise_riser[:samples_for(PRECHORUS1_BARS * 4)]
mix_into(stems["RISER"], noise_seg, pc1_start, gain=0.13)

# Hook melody preview (filtered, quieter — tease)
hook_preview = hook_melody_render(8, pluck_gain=0.18, fm_gain=0.12)
hook_preview = lowpass(hook_preview, cutoff=0.25)
mix_into(stems["HOOK"], hook_preview, pc1_start, gain=0.28)

# Real acapella — Sia pre-chorus building
_a = ACAP_MAP["PRECHORUS1"]
pc1_vox = slice_acapella(_a[0], PRECHORUS1_BARS)
mix_into(stems["VOCAL"], pc1_vox, pc1_start, gain=0.50)

# Building pad
for bar in range(PRECHORUS1_BARS):
    bo = pc1_start + samples_for(bar * 4)
    g = build_gain(bar, PRECHORUS1_BARS, start=0.10, end=0.28)
    seg = chord_pad_major[:samples_for(4)]
    mix_into(stems["PAD"], seg, bo, gain=g)

# Vocal stutter layer building underneath for FX energy
for bar in range(PRECHORUS1_BARS):
    bo = pc1_start + samples_for(bar * 4)
    g = build_gain(bar, PRECHORUS1_BARS, start=0.06, end=0.18)
    mix_into(stems["VOCAL"], chop_stutter, bo, gain=g)

# Vocal "ee" scream at the top
ee_off = pc1_start + samples_for(PRECHORUS1_BARS * 4) - len(chop_ee) - SR // 4
if ee_off > pc1_start:
    mix_into(stems["VOCAL"], chop_ee, ee_off, gain=0.25)

# Reverse hit into drop
rev_pc1 = pc1_start + samples_for(PRECHORUS1_BARS * 4) - len(reverse_hit)
if rev_pc1 > pc1_start:
    mix_into(stems["FX"], reverse_hit, rev_pc1, gain=0.35)

cursor += samples_for(PRECHORUS1_BARS * 4)

# ── CHORUS 1 (16 bars) ─── "Full drop: supersaw + hook lead" ──────
print("  Rendering Chorus 1 (16 bars — full drop)...")
ch1_start = cursor

# Impact at top
mix_into(stems["FX"], sub_boom, ch1_start, gain=0.28)
mix_into(stems["FX"], cinema_hit, ch1_start, gain=0.18)
mix_into(stems["FX"], to_np(impact_boom), ch1_start, gain=0.12)

# Full chorus drums
for rep in range(CHORUS1_BARS // 4):
    offset = ch1_start + samples_for(rep * 16)
    d = drum_chorus(4)
    mix_into(stems["DRUMS"], d, offset, gain=0.55)

# Supersaw chord progression
for rep in range(CHORUS1_BARS // 8):
    offset = ch1_start + samples_for(rep * 32)
    chords = chord_progression_full(8)
    chords = apply_sidechain(chords, SC_PUMP, SR)
    mix_into(stems["CHORDS"], chords, offset, gain=0.95)

# Bass
ch1_bass = apply_sidechain(bass_pattern(CHORUS1_BARS, gain=0.58), SC_HARD, SR)
mix_into(stems["BASS"], ch1_bass, ch1_start, gain=0.50)

# HOOK MELODY — full energy
for rep in range(CHORUS1_BARS // 8):
    offset = ch1_start + samples_for(rep * 32)
    hook = hook_melody_render(8, pluck_gain=0.32, fm_gain=0.26)
    mix_into(stems["HOOK"], hook, offset, gain=0.40)

# Real acapella — Sia's chorus 1
_a = ACAP_MAP["CHORUS1"]
ch1_vox = slice_acapella(_a[0], CHORUS1_BARS)
mix_into(stems["VOCAL"], ch1_vox, ch1_start, gain=0.60)

# Pad underneath
ch1_pad = lush_pad[:samples_for(CHORUS1_BARS * 4)]
mix_into(stems["PAD"], ch1_pad, ch1_start, gain=0.18)

# Arp shimmer
for rep in range(CHORUS1_BARS // 4):
    offset = ch1_start + samples_for(rep * 16)
    seg = arp_shimmer[:min(len(arp_shimmer), samples_for(16))]
    mix_into(stems["ARP"], seg, offset, gain=0.14)

# FM hit accents
for bar in range(0, CHORUS1_BARS, 2):
    mix_into(stems["FX"], fm_hit,
             ch1_start + samples_for(bar * 4), gain=0.13)

# Stutter transition in last 2 bars
stut_off = ch1_start + samples_for((CHORUS1_BARS - 2) * 4)
mix_into(stems["FX"], stutter_fx, stut_off, gain=0.16)

# Tape stop exiting
tape_ch1 = ch1_start + samples_for(CHORUS1_BARS * 4) - len(tape_stop)
if tape_ch1 > ch1_start:
    mix_into(stems["FX"], tape_stop, tape_ch1, gain=0.20)

cursor += samples_for(CHORUS1_BARS * 4)

# ── BREAK (8 bars) ─── "Acapella: vocal + pad only" ───────────────
print("  Rendering Break (8 bars — ACAPELLA section)...")
break_start = cursor

# REAL ACAPELLA — Sia's hook stripped bare (iconic section)
_a = ACAP_MAP["BREAK"]
acapella = slice_acapella(_a[0], BREAK_BARS)
mix_into(stems["VOCAL"], acapella, break_start, gain=0.65)

# Soft pad bed
break_pad = dark_pad[:samples_for(BREAK_BARS * 4)]
break_pad = fade_in(break_pad, duration_s=BAR)
break_pad = fade_out(break_pad, duration_s=BAR * 2)
mix_into(stems["PAD"], break_pad, break_start, gain=0.25)

# Very subtle hats
for bar in range(BREAK_BARS):
    bo = break_start + samples_for(bar * 4)
    for q in range(4):
        mix_into(stems["DRUMS"], hat_closed, bo + samples_for(q), gain=0.06)

# Drone bed
break_drone = drone[:samples_for(BREAK_BARS * 4)]
break_drone = lowpass(break_drone, cutoff=0.08)
mix_into(stems["DRONE"], break_drone, break_start, gain=0.10)

cursor += samples_for(BREAK_BARS * 4)

# ── VERSE 2 (8 bars) ─── "More energy" ────────────────────────────
print("  Rendering Verse 2 (8 bars)...")
verse2_start = cursor

# Drums — verse but slightly heavier
for rep in range(VERSE2_BARS // 4):
    offset = verse2_start + samples_for(rep * 16)
    d = drum_verse(4)
    mix_into(stems["DRUMS"], d, offset, gain=0.55)

# Bass
v2_bass = apply_sidechain(bass_pattern(VERSE2_BARS, gain=0.52), SC_PUMP, SR)
mix_into(stems["BASS"], v2_bass, verse2_start, gain=0.50)

# Real acapella — Flo Rida verse 2
_a = ACAP_MAP["VERSE2"]
v2_vox = slice_acapella(_a[0], VERSE2_BARS)
mix_into(stems["VOCAL"], v2_vox, verse2_start, gain=0.55)

# Pad + arp
v2_pad = lush_pad[:samples_for(VERSE2_BARS * 4)]
v2_pad = lowpass(v2_pad, cutoff=0.18)
mix_into(stems["PAD"], v2_pad, verse2_start, gain=0.24)

for rep in range(VERSE2_BARS // 4):
    offset = verse2_start + samples_for(rep * 16)
    seg = arp_pluck[:min(len(arp_pluck), samples_for(16))]
    mix_into(stems["ARP"], seg, offset, gain=0.15)

cursor += samples_for(VERSE2_BARS * 4)

# ── PRE-CHORUS 2 (8 bars) ─── "Bigger build" ─────────────────────
print("  Rendering Pre-Chorus 2 (8 bars — bigger build)...")
pc2_start = cursor

# Build drums
pc2_drums = drum_build(PRECHORUS2_BARS)
mix_into(stems["DRUMS"], pc2_drums, pc2_start, gain=0.48)

# ALL risers stacked
riser2_pitch = pitch_riser[:samples_for(PRECHORUS2_BARS * 4)]
riser2_harm = harmonic_riser[:samples_for(PRECHORUS2_BARS * 4)]
riser2_noise = noise_riser[:samples_for(PRECHORUS2_BARS * 4)]
mix_into(stems["RISER"], riser2_pitch, pc2_start, gain=0.24)
mix_into(stems["RISER"], riser2_harm, pc2_start, gain=0.20)
mix_into(stems["RISER"], riser2_noise, pc2_start, gain=0.15)

# Hook melody preview (full energy tease)
hook_pre2 = hook_melody_render(8, pluck_gain=0.22, fm_gain=0.16)
mix_into(stems["HOOK"], hook_pre2, pc2_start, gain=0.32)

# Building chords
for bar in range(PRECHORUS2_BARS):
    bo = pc2_start + samples_for(bar * 4)
    g = build_gain(bar, PRECHORUS2_BARS, start=0.08, end=0.30)
    chord_idx = (bar // 2) % 4
    stab = SAW_STABS[chord_idx]
    mix_into(stems["CHORDS"], stab, bo, gain=g)

# Real acapella — Sia pre-chorus 2
_a = ACAP_MAP["PRECHORUS2"]
pc2_vox = slice_acapella(_a[0], PRECHORUS2_BARS)
mix_into(stems["VOCAL"], pc2_vox, pc2_start, gain=0.52)

# Vocal stutters building (FX texture under real vocal)
for bar in range(PRECHORUS2_BARS):
    bo = pc2_start + samples_for(bar * 4)
    g = build_gain(bar, PRECHORUS2_BARS, start=0.06, end=0.20)
    mix_into(stems["VOCAL"], chop_stutter, bo, gain=g)

# FX: reverse hit + pitch dive at end
rev_pc2 = pc2_start + samples_for(PRECHORUS2_BARS * 4) - len(reverse_hit)
if rev_pc2 > pc2_start:
    mix_into(stems["FX"], reverse_hit, rev_pc2, gain=0.30)
dive_pc2 = pc2_start + samples_for((PRECHORUS2_BARS - 1) * 4)
mix_into(stems["FX"], pitch_dive, dive_pc2, gain=0.22)

# Vocal "ee" scream at top
ee_off2 = pc2_start + samples_for(PRECHORUS2_BARS * 4) - len(chop_ee) - SR // 6
if ee_off2 > pc2_start:
    mix_into(stems["VOCAL"], chop_ee, ee_off2, gain=0.28)

cursor += samples_for(PRECHORUS2_BARS * 4)

# ── CHORUS 2 (16 bars) ─── "Max energy: all layers + hook" ────────
print("  Rendering Chorus 2 (16 bars — maximum energy)...")
ch2_start = cursor

# Maximum impact
mix_into(stems["FX"], sub_boom, ch2_start, gain=0.30)
mix_into(stems["FX"], cinema_hit, ch2_start, gain=0.20)
mix_into(stems["FX"], to_np(impact_boom), ch2_start, gain=0.14)
mix_into(stems["DRUMS"], clap, ch2_start, gain=0.35)

# Full drums
for rep in range(CHORUS2_BARS // 4):
    offset = ch2_start + samples_for(rep * 16)
    d = drum_chorus(4)
    mix_into(stems["DRUMS"], d, offset, gain=0.58)

# Supersaw chord progression — wider
for rep in range(CHORUS2_BARS // 8):
    offset = ch2_start + samples_for(rep * 32)
    chords = chord_progression_full(8)
    chords = apply_sidechain(chords, SC_HARD, SR)
    mix_into(stems["CHORDS"], chords, offset, gain=0.98)

# Bass — harder sidechain
ch2_bass = apply_sidechain(bass_pattern(CHORUS2_BARS, gain=0.60), SC_HARD, SR)
mix_into(stems["BASS"], ch2_bass, ch2_start, gain=0.52)

# HOOK MELODY — full energy with slightly higher gains
for rep in range(CHORUS2_BARS // 8):
    offset = ch2_start + samples_for(rep * 32)
    hook = hook_melody_render(8, pluck_gain=0.35, fm_gain=0.28)
    mix_into(stems["HOOK"], hook, offset, gain=0.42)

# Real acapella — Sia's chorus 2
_a = ACAP_MAP["CHORUS2"]
ch2_vox = slice_acapella(_a[0], CHORUS2_BARS)
mix_into(stems["VOCAL"], ch2_vox, ch2_start, gain=0.62)

# Pad
ch2_pad = lush_pad[:samples_for(CHORUS2_BARS * 4)]
mix_into(stems["PAD"], ch2_pad, ch2_start, gain=0.20)

# Arp shimmer full
for rep in range(CHORUS2_BARS // 4):
    offset = ch2_start + samples_for(rep * 16)
    seg = arp_shimmer[:min(len(arp_shimmer), samples_for(16))]
    mix_into(stems["ARP"], seg, offset, gain=0.16)

# FM accents
for bar in range(0, CHORUS2_BARS, 2):
    mix_into(stems["FX"], fm_hit,
             ch2_start + samples_for(bar * 4), gain=0.15)

# Stutter transitions
for trans_bar in [6, 14]:
    stut_ch2 = ch2_start + samples_for(trans_bar * 4)
    mix_into(stems["FX"], stutter_fx, stut_ch2, gain=0.18)

# Tape stop at end
tape_ch2 = ch2_start + samples_for(CHORUS2_BARS * 4) - len(tape_stop)
if tape_ch2 > ch2_start:
    mix_into(stems["FX"], tape_stop, tape_ch2, gain=0.22)

cursor += samples_for(CHORUS2_BARS * 4)

# ── BRIDGE (8 bars) ─── "Breakdown: vocal + pad (emotional)" ──────
print("  Rendering Bridge (8 bars — emotional breakdown)...")
bridge_start = cursor

# REAL ACAPELLA — emotional bridge vocal
_a = ACAP_MAP["BRIDGE"]
bridge_acapella = slice_acapella(_a[0], BRIDGE_BARS)
mix_into(stems["VOCAL"], bridge_acapella, bridge_start, gain=0.62)

# Lush pad
bridge_pad = lush_pad[:samples_for(BRIDGE_BARS * 4)]
bridge_pad = fade_in(bridge_pad, duration_s=BAR)
mix_into(stems["PAD"], bridge_pad, bridge_start, gain=0.30)

# Arp (reflective)
for rep in range(BRIDGE_BARS // 4):
    offset = bridge_start + samples_for(rep * 16)
    seg = arp_pluck[:min(len(arp_pluck), samples_for(16))]
    seg = lowpass(seg, cutoff=0.20)
    mix_into(stems["ARP"], seg, offset, gain=0.16)

# Drone
bridge_drone = drone[:samples_for(BRIDGE_BARS * 4)]
mix_into(stems["DRONE"], bridge_drone, bridge_start, gain=0.15)

# Light hats
for bar in range(BRIDGE_BARS):
    bo = bridge_start + samples_for(bar * 4)
    for q in range(4):
        mix_into(stems["DRUMS"], hat_closed, bo + samples_for(q), gain=0.07)

# Riser starting in last 4 bars (building into final chorus)
riser_bridge = pitch_riser[:samples_for(4 * 4)]
mix_into(stems["RISER"], riser_bridge,
         bridge_start + samples_for(4 * 4), gain=0.25)

# Reverse hit at very end
rev_bridge = bridge_start + samples_for(BRIDGE_BARS * 4) - len(reverse_hit)
if rev_bridge > bridge_start:
    mix_into(stems["FX"], reverse_hit, rev_bridge, gain=0.28)

cursor += samples_for(BRIDGE_BARS * 4)

# ── FINAL CHORUS (16 bars) ─── "Climax: everything layered" ───────
# Golden section point (~bar 79) falls here — this is the emotional peak
print("  Rendering Final Chorus (16 bars — CLIMAX, Golden Section)...")
fc_start = cursor

# MAXIMUM IMPACT
mix_into(stems["FX"], sub_boom, fc_start, gain=0.32)
mix_into(stems["FX"], cinema_hit, fc_start, gain=0.22)
mix_into(stems["FX"], to_np(impact_boom), fc_start, gain=0.15)
mix_into(stems["DRUMS"], clap, fc_start, gain=0.38)
mix_into(stems["VOCAL"], chop_ee, fc_start, gain=0.25)

# Full drums — slightly louder
for rep in range(FINAL_CHORUS_BARS // 4):
    offset = fc_start + samples_for(rep * 16)
    d = drum_chorus(4)
    mix_into(stems["DRUMS"], d, offset, gain=0.60)

# Supersaw chord progression — maximum presence
for rep in range(FINAL_CHORUS_BARS // 8):
    offset = fc_start + samples_for(rep * 32)
    chords = chord_progression_full(8)
    chords = apply_sidechain(chords, SC_HARD, SR)
    mix_into(stems["CHORDS"], chords, offset, gain=1.00)

# Bass — fullest
fc_bass = apply_sidechain(bass_pattern(FINAL_CHORUS_BARS, gain=0.62), SC_HARD, SR)
mix_into(stems["BASS"], fc_bass, fc_start, gain=0.55)

# HOOK MELODY — maximum energy, doubled
for rep in range(FINAL_CHORUS_BARS // 8):
    offset = fc_start + samples_for(rep * 32)
    hook = hook_melody_render(8, pluck_gain=0.38, fm_gain=0.30)
    mix_into(stems["HOOK"], hook, offset, gain=0.45)

# REAL ACAPELLA — Sia's final chorus (CLIMAX vocal)
_a = ACAP_MAP["FINAL"]
fc_vox = slice_acapella(_a[0], FINAL_CHORUS_BARS)
mix_into(stems["VOCAL"], fc_vox, fc_start, gain=0.65)

# Pad
fc_pad = lush_pad[:samples_for(FINAL_CHORUS_BARS * 4)]
mix_into(stems["PAD"], fc_pad, fc_start, gain=0.22)

# Arp — maximum shimmer
for rep in range(FINAL_CHORUS_BARS // 4):
    offset = fc_start + samples_for(rep * 16)
    seg = arp_shimmer[:min(len(arp_shimmer), samples_for(16))]
    mix_into(stems["ARP"], seg, offset, gain=0.18)

# Drone underneath
for rep in range(FINAL_CHORUS_BARS // 8 + 1):
    offset = fc_start + samples_for(rep * 32)
    seg = drone[:min(len(drone), samples_for(32))]
    mix_into(stems["DRONE"], seg, offset, gain=0.10)

# FM accents
for bar in range(0, FINAL_CHORUS_BARS, 2):
    mix_into(stems["FX"], fm_hit,
             fc_start + samples_for(bar * 4), gain=0.16)

# Stutter transitions in final bars
stut_fc1 = fc_start + samples_for(6 * 4)
stut_fc2 = fc_start + samples_for(14 * 4)
mix_into(stems["FX"], stutter_fx, stut_fc1, gain=0.16)
mix_into(stems["FX"], stutter_fx, stut_fc2, gain=0.19)

# Tape stop transitioning to outro
tape_fc = fc_start + samples_for(FINAL_CHORUS_BARS * 4) - len(tape_stop)
if tape_fc > fc_start:
    mix_into(stems["FX"], tape_stop, tape_fc, gain=0.22)

cursor += samples_for(FINAL_CHORUS_BARS * 4)

# ── OUTRO (16 bars) ─── "Fade: pad + vocal dissolving" ────────────
print("  Rendering Outro (16 bars — dissolving)...")
outro_start = cursor

# Pad fading out
outro_pad = lush_pad[:samples_for(OUTRO_BARS * 4)]
outro_pad = fade_out(outro_pad, duration_s=BAR * 10)
mix_into(stems["PAD"], outro_pad, outro_start, gain=0.28)

# Real acapella — outro vocals fading
_a = ACAP_MAP["OUTRO"]
_outro_len = _a[1] - _a[0]  # may be <16 bars, pad with silence
outro_acapella = slice_acapella(_a[0], min(_outro_len, OUTRO_BARS))
outro_acapella = fade_out(outro_acapella, duration_s=BAR * 6)
mix_into(stems["VOCAL"], outro_acapella, outro_start, gain=0.45)

# Drone fading
outro_drone = drone[:samples_for(OUTRO_BARS * 4)]
outro_drone = fade_out(outro_drone, duration_s=BAR * 12)
mix_into(stems["DRONE"], outro_drone, outro_start, gain=0.20)

# Light drums fading
outro_drums = drum_intro(OUTRO_BARS)
outro_drums = fade_out(outro_drums, duration_s=BAR * 10)
mix_into(stems["DRUMS"], outro_drums, outro_start, gain=0.12)

# Sub bass fading
outro_sub = to_np(synthesize_bass(BassPreset(
    name="WOOutroSub", bass_type="sub_sine", frequency=KEY_FREQS["Ab1"],
    duration_s=OUTRO_BARS * BAR, attack_s=0.01,
    release_s=OUTRO_BARS * BAR * 0.8
)))
outro_sub = fade_out(outro_sub, duration_s=BAR * 12)
mix_into(stems["BASS"], outro_sub, outro_start, gain=0.14)

# Arp — reflective, dissolving
for rep in range(OUTRO_BARS // 4):
    offset = outro_start + samples_for(rep * 16)
    seg = arp_pluck[:min(len(arp_pluck), samples_for(16))]
    seg = lowpass(seg, cutoff=0.10)
    seg = fade_out(seg, duration_s=BAR * 3)
    mix_into(stems["ARP"], seg, offset, gain=0.10)

# Final pitch dive
mix_into(stems["FX"], pitch_dive,
         outro_start + samples_for(10 * 4), gain=0.20)

# Filtered chord ghost
chord_ghost = chord_progression_filtered(4)
chord_ghost = fade_out(chord_ghost, duration_s=BAR * 3)
mix_into(stems["CHORDS"], chord_ghost, outro_start, gain=0.20)


# ====================================================================
#  DSP POST-PROCESSING
# ====================================================================
print()
print("  Applying DSP processing...")

stems["PAD"] = apply_sidechain(stems["PAD"], SC_PUMP, SR)

stems["PAD"] = apply_hall(stems["PAD"], HALL_VERB, SR)
stems["VOCAL"] = apply_hall(stems["VOCAL"], HALL_VERB, SR)
stems["ARP"] = apply_room(stems["ARP"], ROOM_VERB, SR)
stems["HOOK"] = apply_room(stems["HOOK"], ROOM_VERB, SR)
stems["CHORDS"] = apply_hall(stems["CHORDS"], HALL_VERB, SR)
stems["DRONE"] = apply_hall(stems["DRONE"], HALL_VERB, SR)

print("    PAD     -> apply_hall (decay=3.5s, mix=0.30)")
print("    VOCAL   -> apply_hall (decay=3.5s, mix=0.30)")
print("    ARP     -> apply_room (decay=0.7s, mix=0.20)")
print("    HOOK    -> apply_room (decay=0.7s, mix=0.20)")
print("    CHORDS  -> apply_hall (decay=3.5s, mix=0.30)")
print("    DRONE   -> apply_hall (decay=3.5s, mix=0.30)")


# ====================================================================
#  EXPORT STEMS + MASTERED MIXDOWN + MIDI + ALS
# ====================================================================
print()
print("  Bouncing stems...")

os.makedirs("output/stems", exist_ok=True)
stem_paths: list[str] = []

for name in STEM_NAMES:
    buf = stems[name]
    path = f"output/stems/wild_ones_{name}.wav"

    peak = float(np.max(np.abs(buf))) if len(buf) > 0 else 1.0
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
    print(f"    {name:16s}  {len(buf)/SR:.1f}s  {peak_db:.1f}dB  "
          f"{fsize/1024/1024:.1f}MB")

# -- Stereo mixdown with constant-power pan law --
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

# -- Master via mastering_chain (electro house settings) --
print("  Mastering (electro house preset)...")

master_settings = MasterSettings(
    target_lufs=-11.0,
    ceiling_db=-0.5,
    eq_low_shelf_db=1.5,
    eq_low_shelf_freq=90.0,
    eq_high_shelf_db=2.0,        # Bright air for dance-pop
    eq_high_shelf_freq=9000.0,
    eq_mid_boost_db=0.5,         # Slight presence boost
    eq_mid_freq=3000.0,
    eq_mid_q=1.0,
    compression_threshold_db=-10.0,
    compression_ratio=3.5,
    compression_attack_ms=8.0,
    compression_release_ms=80.0,
    stereo_width=1.0 + 1.0 / PHI,
    limiter_enabled=True,
)

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

os.makedirs("output", exist_ok=True)
output_path = "output/wild_ones.wav"

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

# -- MIDI export --
print("  Exporting MIDI...")
os.makedirs("output/midi", exist_ok=True)

# Bass MIDI — chord root notes
bass_events: list[NoteEvent] = []
for bar in range(total_bars):
    chord_idx = (bar // 2) % 4
    root_midi = [MIDI["Ab1"], MIDI["C2"], MIDI["F2"], MIDI["Db2"]][chord_idx]
    bass_events.append(NoteEvent(pitch=root_midi, start_beat=bar * 4,
                                 duration_beats=2.0, velocity=100))

# Hook melody MIDI
hook_events: list[NoteEvent] = []
# Section bar offsets
chorus1_bar = INTRO_BARS + VERSE1_BARS + PRECHORUS1_BARS
chorus2_bar = (chorus1_bar + CHORUS1_BARS + BREAK_BARS +
               VERSE2_BARS + PRECHORUS2_BARS)
final_bar = chorus2_bar + CHORUS2_BARS + BRIDGE_BARS

for section_start, section_len in [(chorus1_bar, CHORUS1_BARS),
                                    (chorus2_bar, CHORUS2_BARS),
                                    (final_bar, FINAL_CHORUS_BARS)]:
    for rep in range(section_len // 8):
        base_beat = (section_start + rep * 8) * 4
        for beat_off, note_name, dur in HOOK_MELODY:
            hook_events.append(NoteEvent(
                pitch=MIDI[note_name],
                start_beat=base_beat + beat_off,
                duration_beats=dur,
                velocity=90,
            ))

# Chord MIDI
chord_events: list[NoteEvent] = []
for section_start, section_len in [(chorus1_bar, CHORUS1_BARS),
                                    (chorus2_bar, CHORUS2_BARS),
                                    (final_bar, FINAL_CHORUS_BARS)]:
    for bar in range(section_len):
        chord_idx = (bar // 2) % 4
        b = (section_start + bar) * 4
        chord_notes = [CHORD_Ab, CHORD_Cm, CHORD_Fm, CHORD_Db][chord_idx]
        for pitch in chord_notes:
            chord_events.append(NoteEvent(
                pitch=pitch, start_beat=b,
                duration_beats=2.0, velocity=82))

# Vocal MIDI (simplified — key vocal chop triggers)
vocal_events: list[NoteEvent] = []
break_bar = chorus1_bar + CHORUS1_BARS
bridge_bar = chorus2_bar + CHORUS2_BARS
for section_start, section_len in [(break_bar, BREAK_BARS),
                                    (bridge_bar, BRIDGE_BARS)]:
    for bar in range(section_len):
        chord_idx = (bar // 2) % 4
        root_midi = [MIDI["Ab4"], MIDI["C5"], MIDI["F4"], MIDI["Db4"]][chord_idx]
        b = (section_start + bar) * 4
        vocal_events.append(NoteEvent(
            pitch=root_midi, start_beat=b,
            duration_beats=2.0, velocity=75))

midi_tracks = [
    ("Bass", bass_events),
    ("Hook", hook_events),
    ("Chords", chord_events),
    ("Vocal", vocal_events),
]

midi_path = "output/midi/wild_ones.mid"
write_midi_file(midi_tracks, midi_path, bpm=BPM)
total_notes = sum(len(evts) for _, evts in midi_tracks)
print(f"    {midi_path}  ({total_notes} notes)")

# -- Ableton Live Set --
print("  Generating Ableton Live project...")

stem_colors = {
    "DRUMS": 1, "BASS": 3, "CHORDS": 12, "HOOK": 20,
    "PAD": 24, "VOCAL": 36, "ARP": 16, "RISER": 32,
    "FX": 40, "DRONE": 28,
}

als_tracks = []

# Audio tracks
for idx, name in enumerate(STEM_NAMES):
    stem_abs = os.path.abspath(f"output/stems/wild_ones_{name}.wav")
    als_tracks.append(ALSTrack(
        name=name,
        track_type="audio",
        color=stem_colors.get(name, 0),
        volume_db=0.0,
        pan=STEM_PAN.get(name, 0.0),
        clip_names=[name],
        clip_paths=[stem_abs],
    ))

# MIDI tracks
midi_abs = os.path.abspath("output/midi/wild_ones.mid")
for track_name in ["Bass_MIDI", "Hook_MIDI", "Chords_MIDI", "Vocal_MIDI"]:
    als_tracks.append(ALSTrack(
        name=track_name,
        track_type="midi",
        color=stem_colors.get(track_name.split("_")[0].upper(), 0),
        volume_db=-6.0,
        mute=True,
        device_names=["Serum 2"],
        clip_names=[track_name],
    ))

# Return tracks
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
    ALSScene(name="VERSE_1", tempo=float(BPM)),
    ALSScene(name="PRE_CHORUS_1", tempo=float(BPM)),
    ALSScene(name="CHORUS_1", tempo=float(BPM)),
    ALSScene(name="BREAK_ACAPELLA", tempo=float(BPM)),
    ALSScene(name="VERSE_2", tempo=float(BPM)),
    ALSScene(name="PRE_CHORUS_2", tempo=float(BPM)),
    ALSScene(name="CHORUS_2", tempo=float(BPM)),
    ALSScene(name="BRIDGE", tempo=float(BPM)),
    ALSScene(name="FINAL_CHORUS", tempo=float(BPM)),
    ALSScene(name="OUTRO", tempo=float(BPM)),
]

project = ALSProject(
    name="Wild_Ones",
    bpm=float(BPM),
    tracks=als_tracks,
    scenes=als_scenes,
    notes="Wild Ones (Electro House Remix) | "
          "Ab major | 127 BPM | 440 Hz | 128 bars | "
          "Chords: Ab-Cm-Fm-Db | Real Acapella + Hook",
)

os.makedirs("output/ableton", exist_ok=True)
als_path = "output/ableton/Wild_Ones.als"
write_als(project, als_path)

# -- Summary --
duration = total_samples / SR
file_size = os.path.getsize(output_path)
stem_dir_size = sum(
    os.path.getsize(os.path.join("output/stems", f))
    for f in os.listdir("output/stems")
    if f.startswith("wild_ones_") and f.endswith(".wav")
)

print()
print("=" * 60)
print('  DUBFORGE -- "Wild Ones" (Electro House Remix)')
print("=" * 60)
print(f"  Format:   16-bit WAV @ {SR} Hz")
print(f"  BPM:      {BPM}  |  Key: Ab major  |  Tuning: 440 Hz")
print(f"  Chords:   Ab - Cm - Fm - Db  (I - iii - vi - IV)")
print(f"  Duration: {duration:.1f}s "
      f"({int(duration // 60)}:{int(duration % 60):02d})")
print(f"  Bars:     {total_bars}  "
      f"(Golden Section Point: bar ~{golden_section_bar})")
print()
print("  Features:")
print("    * REAL studio acapella (Sia & Flo Rida isolated vocals)")
print("    * Original hook melody: Eb4-C5 range over Ab-Cm-Fm-Db")
print("    * 4-on-the-floor electro house drums (GALATCIA samples)")
print("    * Supersaw chord walls (13-voice, 42ct detune)")
print("    * Electro house mastering (-11 LUFS, phi-wide stereo)")
print()
print(f"  Stems:    {len(STEM_NAMES)} tracks in output/stems/")
for name in STEM_NAMES:
    print(f"            - {name}")
print(f"  Stems:    {stem_dir_size / 1024 / 1024:.1f} MB total")
print(f"  Mixdown:  {output_path} ({file_size / 1024 / 1024:.1f} MB)")
print(f"  MIDI:     {midi_path} ({total_notes} notes)")
print(f"  Serum 2:  output/serum2/wild_ones_patches.json")
print(f"  Presets:  output/presets/ ({len(fxp_presets)} .fxp + 1 .fxb bank)")
print(f"  Ableton:  {als_path}")
print()
print("  Structure:")
print(f"    Intro          {INTRO_BARS:3d} bars")
print(f"    Verse 1        {VERSE1_BARS:3d} bars")
print(f"    Pre-Chorus 1   {PRECHORUS1_BARS:3d} bars")
print(f"    Chorus 1       {CHORUS1_BARS:3d} bars  (hook + full drop)")
print(f"    Break          {BREAK_BARS:3d} bars  (ACAPELLA section)")
print(f"    Verse 2        {VERSE2_BARS:3d} bars")
print(f"    Pre-Chorus 2   {PRECHORUS2_BARS:3d} bars")
print(f"    Chorus 2       {CHORUS2_BARS:3d} bars  (max energy)")
print(f"    Bridge         {BRIDGE_BARS:3d} bars  (emotional breakdown)")
print(f"    Final Chorus   {FINAL_CHORUS_BARS:3d} bars  (CLIMAX)")
print(f"    Outro          {OUTRO_BARS:3d} bars")
print(f"    TOTAL         {total_bars:3d} bars")
print()
print("  Song DNA Reference: Wild Ones (Flo Rida feat. Sia)")
print("    Ab major | 127 BPM | Ab-Cm-Fm-Db | Vocal range Eb4-C5")
print("    Vocals: studio acapella (Sia & Flo Rida)")
print("    Instrumental: 100% synthesized by DUBFORGE engines")
print("=" * 60)

# -- Install to Ableton User Library --
print()
print("  Installing to Ableton User Library...")
import shutil
from pathlib import Path

_user_lib = None
for _candidate in [
    Path.home() / "Documents" / "Ableton" / "User Library",
    Path.home() / "Music" / "Ableton" / "User Library",
    Path(os.environ.get("ABLETON_USER_LIBRARY", "")) if os.environ.get("ABLETON_USER_LIBRARY") else None,
]:
    if _candidate and _candidate.exists():
        _user_lib = _candidate
        break

if _user_lib:
    _installed = 0

    _stems_dst = _user_lib / "Samples" / "DUBFORGE" / "Wild_Ones" / "Stems"
    _stems_dst.mkdir(parents=True, exist_ok=True)
    for _f in Path("output/stems").glob("wild_ones_*.wav"):
        shutil.copy2(_f, _stems_dst / _f.name)
        _installed += 1
    print(f"    Stems:   {_installed} -> {_stems_dst}")

    _midi_dst = _user_lib / "Samples" / "DUBFORGE" / "Wild_Ones" / "MIDI"
    _midi_dst.mkdir(parents=True, exist_ok=True)
    for _f in Path("output/midi").glob("wild_ones*.mid"):
        shutil.copy2(_f, _midi_dst / _f.name)
    _installed += 1
    print(f"    MIDI:    1 -> {_midi_dst}")

    _preset_dst = _user_lib / "Presets" / "Instruments" / "DUBFORGE"
    _preset_dst.mkdir(parents=True, exist_ok=True)
    _pr_count = 0
    for _f in Path("output/presets").glob("*.fxp"):
        shutil.copy2(_f, _preset_dst / _f.name)
        _pr_count += 1
    for _f in Path("output/presets").glob("*.fxb"):
        shutil.copy2(_f, _preset_dst / _f.name)
        _pr_count += 1
    _installed += _pr_count
    print(f"    Presets: {_pr_count} -> {_preset_dst}")

    print(f"    TOTAL:   {_installed} files installed")
else:
    print("    Ableton User Library not found (set ABLETON_USER_LIBRARY env var)")

# -- Open in Ableton Live --
print()
_ableton_running = False
_ableton_exe = None

# Check if Ableton is running as a process
try:
    _tasklist = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq Ableton Live*", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, timeout=5
    )
    if "Ableton Live" in _tasklist.stdout:
        _ableton_running = True
except Exception:
    pass

# Check if Ableton is installed on disk
if not _ableton_running:
    _ableton_roots = [
        Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "Ableton",
        Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Ableton",
    ]
    for _abl_root in _ableton_roots:
        if _abl_root.is_dir():
            for _exe in _abl_root.rglob("Ableton Live*.exe"):
                _ableton_exe = _exe
                break
        if _ableton_exe:
            break

_als_abs = os.path.abspath(als_path)
if _ableton_running:
    print("  Ableton Live is running — opening project...")
    subprocess.Popen(["cmd", "/c", "start", "", _als_abs],
                     creationflags=0x08000000)
elif _ableton_exe:
    print(f"  Ableton Live installed ({_ableton_exe.stem}) but not running.")
    print(f"  Launching Ableton with project...")
    subprocess.Popen([str(_ableton_exe), _als_abs],
                     creationflags=0x08000000)
else:
    print("  WARNING: Ableton Live not detected — skipping auto-open.")
    print(f"  Install Ableton, then open: {_als_abs}")

print("  Done. Wild Ones Remix pipeline complete — acapella + hook + stems + presets + MIDI.")
print()
