#!/usr/bin/env python3
"""DUBFORGE -- "Wild Ones" v6 (Electro House Remix — Studio Edition)

A DUBFORGE electro house remix built around the studio acapella of
"Wild Ones" by Flo Rida feat. Sia.  V6 extends V5 with:

    NEW IN V6:
    * 24-bit WAV export (16→24 bit, 144 dB dynamic range)
    * Granular shimmer texture (engine granular_synth)
    * Vinyl noise layer (intro/outro) + white noise air (drops)
    * Engine saturation (tape/console/phi) replacing inline saturator
    * DC offset removal on all stems before mastering
    * PHI-distributed dithering on final export
    * Tighter mastering target (-10.5 LUFS)
    * 16 sound design steps (was 14)

    V5 features retained:

    * 144 bars (Fibonacci!) — VIP Drop section added
    * 12 stems — GROWL + TEXTURE layers
    * Growl resampler bass, phi harmonics, beat repeat FX
    * Per-stem compression, transient shaping, de-essing
    * Phi crossfades between every section
    * Multi-technique stereo imaging (Haas, psychoacoustic, freq split)
    * Enhanced ALS: clip positioning, automation, cue points, sends
    * AbletonOSC bridge + Link sync integration ready

    Song DNA (from Wikipedia — public factual data):
        Key:        Ab major
        BPM:        127
        Time:       4/4
        Chords:     Ab - Cm - Fm - Db  (I - iii - vi - IV)
        Vocal Range: Eb4 to C5
        Genre:      Dance-pop / electro house
        Duration:   ~4:32

    Acapella source:
        Flo-Rida-ft-Sia-Wild-Ones-Studio-Acapella.mp3
        44 100 Hz · stereo (down-mixed to mono) · ~246 s · ~130 bars

    Features:
        * REAL studio acapella — Sia & Flo Rida isolated vocals
        * Original hook melody in Ab major tracing Eb4-C5 range
        * 4-on-the-floor electro house drums (GALATCIA samples)
        * Supersaw chord walls cycling Ab-Cm-Fm-Db
        * Growl resampler bass (phi-modulated mid-bass layer)
        * Phi-harmonic sub reinforcement
        * Beat repeat stutters in builds (phi grid)
        * Phi crossfades between all sections
        * Per-stem dynamics & transient shaping
        * Enhanced Ableton Live Set (automation, cue points, sends)
        * Full stem export, MIDI, ALS, Serum presets

    Structure (144 bars at 127 BPM ≈ 4:32):
        Intro          8 bars  — Filtered pad + vocal whispers
        Verse 1       16 bars  — 4otf kick + bass + vocal chops
        Pre-Chorus 1   8 bars  — Build: riser + hook preview
        Chorus 1      16 bars  — Full drop: supersaw + hook lead
        Break          8 bars  — Acapella: vocal + pad only
        Verse 2        8 bars  — Kick + bass + vocal energy
        Pre-Chorus 2   8 bars  — Bigger build: all risers
        Chorus 2      16 bars  — Max energy: all layers + hook
        Bridge         8 bars  — Breakdown: vocal + pad (emotional)
        VIP Drop      16 bars  — GROWL BASS VIP: resampled + glitch
        Final Chorus  16 bars  — Climax: everything layered
        Outro         16 bars  — Fade: pad + vocal dissolving

    Golden Section Point: bar ~89 (144/phi) → Bridge (emotional pivot)

Output:
    output/stems/wild_ones_v6_*.wav       — 12 individual stem WAVs (24-bit)
    output/wild_ones_v6.wav               — stereo reference preview (24-bit, NO master)
    output/midi/wild_ones_v6.mid          — MIDI for all melodic parts
    output/serum2/wild_ones_v6_patches.json — Serum 2 patch reference
    output/ableton/Wild_Ones_V6.als       — ALS with automation + cue pts
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

# -- DUBFORGE engine -- NEW in v5 --
from engine.growl_resampler import growl_resample_pipeline, waveshape_distortion
from engine.harmonic_gen import HarmonicGenerator, HarmonicSpectrum
from engine.beat_repeat import BeatRepeatPatch, apply_beat_repeat
from engine.crossfade import CrossfadeEngine, FadeConfig
from engine.dynamics import CompressorSettings, compress, limit, analyze_dynamics
from engine.dynamics_processor import (DynamicsProcessor, GateConfig,
                                       DeEsserConfig)

# -- DUBFORGE engine -- NEW in v6 --
from engine.granular_synth import GranularPreset, synthesize_granular
from engine.noise_generator import NoisePreset, synthesize_noise
from engine.dc_remover import DCRemover
from engine.dither import DitherEngine, DitherConfig
from engine.saturation import SaturationEngine, SatConfig

# -- DUBFORGE engine -- DSP pipeline --
from engine.sidechain import apply_sidechain, SidechainPreset
from engine.reverb_delay import apply_hall, apply_room, ReverbDelayPreset
from engine.stereo_imager import (apply_mid_side, apply_haas,
                                  apply_frequency_split, apply_psychoacoustic,
                                  StereoPreset)
from engine.auto_master import auto_master, MasterSettings, MasterResult

# -- DUBFORGE engine -- DAW integration --
from engine.als_generator import (ALSProject, ALSTrack, ALSScene,
                                  ALSClipInfo, ALSAutomation,
                                  ALSAutomationPoint, ALSCuePoint,
                                  ALSWarpMarker, build_als_xml, write_als,
                                  make_sine_automation,
                                  make_sawtooth_automation,
                                  make_ramp_automation,
                                  make_lp_sweep_automation,
                                  make_section_send_automation)
from engine.midi_export import NoteEvent, write_midi_file
from engine.serum2 import build_dubstep_patches
from engine.fxp_writer import (FXPPreset, FXPBank, VSTParam,
                               write_fxp, write_fxb, write_preset_manifest)

# -- DUBFORGE engine -- Ableton integration (Tier 2 + 5) --
from engine.ableton_bridge import AbletonBridge, get_bridge
from engine.link_sync import LinkSync, get_link

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
ACAP_MAP = {
    "INTRO":      (0, 8),
    "VERSE1":     (8, 24),
    "PRECHORUS1": (24, 32),
    "CHORUS1":    (32, 48),
    "BREAK":      (0, 8),       # Reuse Sia's opening hook
    "VERSE2":     (48, 56),
    "PRECHORUS2": (64, 72),
    "CHORUS2":    (72, 88),
    "BRIDGE":     (88, 96),
    "VIP":        (32, 48),     # Reuse chorus 1 vocal for VIP layer
    "FINAL":      (96, 112),
    "OUTRO":      (112, 122),
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

# v5: Per-stem compression settings
COMP_BASS = CompressorSettings(threshold_db=-12.0, ratio=4.0,
                               attack_ms=5.0, release_ms=60.0,
                               knee_db=3.0, makeup_db=2.0, mix=1.0)
COMP_DRUMS = CompressorSettings(threshold_db=-8.0, ratio=3.0,
                                attack_ms=1.0, release_ms=40.0,
                                knee_db=2.0, makeup_db=1.5, mix=0.7)
COMP_VOCAL = CompressorSettings(threshold_db=-14.0, ratio=3.5,
                                attack_ms=8.0, release_ms=80.0,
                                knee_db=4.0, makeup_db=3.0, mix=0.8)
DEESS = DeEsserConfig(frequency=6500.0, threshold_db=-18.0,
                      reduction_db=6.0, bandwidth=2000.0)

# v5: Stereo presets per stem
STEREO_PAD = StereoPreset(name="WOPadStereo", image_type="haas",
                          width=1.2, delay_ms=12.0, mix=0.8)
STEREO_CHORD = StereoPreset(name="WOChordStereo", image_type="psychoacoustic",
                            width=1.4, delay_ms=8.0, mix=0.7)
STEREO_ARP = StereoPreset(name="WOArpStereo", image_type="frequency_split",
                          width=1.1, crossover_hz=2000.0, mix=0.6)
STEREO_HOOK = StereoPreset(name="WOHookStereo", image_type="mid_side",
                           width=0.9, mix=0.5)

# v5: Crossfade engine
XFADE = CrossfadeEngine(SR)
XFADE_CONFIG = FadeConfig(fade_type="phi", duration_ms=BAR * 1000 * 0.5)
XFADE_SHORT = FadeConfig(fade_type="equal_power", duration_ms=100.0)

# v5: Beat repeat for builds
BEAT_REPEAT_BUILD = BeatRepeatPatch(
    name="WOBuildRepeat", grid="1/8", repeats=4,
    decay=0.618, pitch_shift=0, reverse_probability=0.0,
    gate=0.8, mix=0.35, probability=0.7)
BEAT_REPEAT_VIP = BeatRepeatPatch(
    name="WOVIPRepeat", grid="phi", repeats=8,
    decay=0.382, pitch_shift=2, reverse_probability=0.15,
    gate=0.6, mix=0.50, probability=0.85)

# v5: Dynamics processor
DYNPROC = DynamicsProcessor(SR)

# v5: Harmonic generator for phi sub reinforcement
HARMGEN = HarmonicGenerator(SR)

# v6: Engine saturation, DC remover, dithering
SAT_ENGINE = SaturationEngine(SR)
DC_ENGINE = DCRemover(SR)
DITHER_ENGINE = DitherEngine(seed=42)
DITHER_CFG = DitherConfig(dither_type="phi", target_bits=24,
                          noise_shaping=True, amplitude=0.8)


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


def phi_crossfade_sections(buf: np.ndarray, bar_boundary: int,
                           fade_bars: float = 0.5) -> np.ndarray:
    """Apply a phi-curve crossfade at a section boundary."""
    center = samples_for(bar_boundary * 4)
    half = int(samples_for(fade_bars * 4) / 2)
    start = max(0, center - half)
    end = min(len(buf), center + half)
    n = end - start
    if n < 4:
        return buf
    out = buf.copy()
    # Phi fade curve: t^PHI for out, 1-(1-t)^PHI for in
    t = np.linspace(0.0, 1.0, n)
    curve = 1.0 - (1.0 - t) ** PHI
    out[start:end] *= curve
    return out


def build_gain(bar_index: int, total_build_bars: int,
               start: float = 0.15, end: float = 0.85) -> float:
    """Phi acceleration curve for builds."""
    t = bar_index / max(total_build_bars - 1, 1)
    return start + (end - start) * (t ** PHI)


# ====================================================================
#  SOUND DESIGN -- Pre-render all elements
# ====================================================================

print("=" * 60)
print('  DUBFORGE -- "Wild Ones" V6 (Electro House Remix — Studio)')
print("=" * 60)
print(f"  BPM: {BPM}  |  Key: Ab major  |  Tuning: 440 Hz  |  SR: {SR}")
print(f"  Bit Depth: 24-bit  |  Dither: PHI")
print(f"  Chords: Ab - Cm - Fm - Db  (I - iii - vi - IV)")
print(f"  Structure: 144 bars (Fibonacci!)  |  3 drops + VIP  |  "
      f"real acapella + hook")
print()

# -- SERUM 2 PATCH DEFINITIONS + FXP PRESETS --
print("  [1/16] Loading Serum 2 patch definitions...")
serum_patches = build_dubstep_patches()
os.makedirs("output/serum2", exist_ok=True)
with open("output/serum2/wild_ones_v6_patches.json", "w") as f:
    json.dump(serum_patches, f, indent=2, default=str)
print(f"         {len(serum_patches)} Serum 2 patches -> JSON")

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

bank = FXPBank(name="WILD_ONES_V6_BANK", presets=list(fxp_presets.values()))
write_fxb(bank, "output/presets/WILD_ONES_V6_BANK.fxb")
write_preset_manifest(fxp_presets, "output/presets")
print(f"         {len(fxp_presets)} .fxp presets + 1 .fxb bank written")

# -- GALATCIA REAL DRUMS --
print("  [2/16] Loading GALATCIA drum samples...")

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
print("  [3/16] Bass (sub + electro wobble)...")

sub_bass = to_np(synthesize_bass(BassPreset(
    name="WOSub", bass_type="sub_sine", frequency=KEY_FREQS["Ab1"],
    duration_s=BEAT * 2, attack_s=0.005, release_s=0.15, distortion=0.0
)))

wobble_bass = to_np(synthesize_bass(BassPreset(
    name="WOWobble", bass_type="wobble", frequency=KEY_FREQS["Ab2"],
    duration_s=BEAT * 2, attack_s=0.01, release_s=0.18,
    fm_ratio=2.0, fm_depth=2.5, distortion=0.20, filter_cutoff=0.55
)))

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

# -- v5: PHI HARMONIC SUB REINFORCEMENT --
print("  [4/16] Phi-harmonic sub reinforcement...")

phi_spec = HARMGEN.phi_harmonics(KEY_FREQS["Ab1"], count=8)
phi_sub_raw = to_np(HARMGEN.render(phi_spec, duration_s=BAR * 2, amplitude=0.6))
print(f"         phi harmonics: {phi_spec.partial_count} partials")

# -- v5: GROWL RESAMPLER BASS --
print("  [5/16] Growl resampler bass (phi-modulated mid-bass)...")

# Generate a source frame from wobble bass for resampling
_growl_source = wobble_bass[:2048] if len(wobble_bass) >= 2048 else np.pad(
    wobble_bass, (0, 2048 - len(wobble_bass)))
_growl_frames = growl_resample_pipeline(_growl_source, n_output_frames=32)
# Stitch growl frames into a bass one-shot
growl_oneshot = np.concatenate([to_np(f) for f in _growl_frames])
growl_oneshot = to_np(waveshape_distortion(growl_oneshot, drive=0.45, mix=0.6))
# Make it long enough for 2 bars
_growl_target_len = samples_for(8)  # 2 bars
if len(growl_oneshot) < _growl_target_len:
    _reps = int(np.ceil(_growl_target_len / len(growl_oneshot)))
    growl_oneshot = np.tile(growl_oneshot, _reps)[:_growl_target_len]
else:
    growl_oneshot = growl_oneshot[:_growl_target_len]
# Envelope
_env_att = int(0.005 * SR)
_env_rel = int(0.15 * SR)
growl_oneshot[:_env_att] *= np.linspace(0, 1, _env_att)
growl_oneshot[-_env_rel:] *= np.linspace(1, 0, _env_rel)
print(f"         growl: {len(growl_oneshot)/SR:.2f}s one-shot from {len(_growl_frames)} frames")

# -- SUPERSAW CHORDS --
print("  [6/16] Supersaw chords (Ab - Cm - Fm - Db)...")

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
print("  [7/16] Hook lead melody (pluck + FM)...")

hook_notes_pluck = {}
for note_name in ["Eb4", "F4", "G4", "Ab4", "Bb4", "C5", "C4", "Db4"]:
    hook_notes_pluck[note_name] = to_np(synthesize_pluck_lead(LeadPreset(
        name=f"WOPluck_{note_name}", lead_type="pluck",
        frequency=KEY_FREQS[note_name],
        duration_s=BEAT * 0.75, attack_s=0.002, decay_s=0.12,
        sustain=0.35, release_s=0.15, filter_cutoff=0.82,
        resonance=0.40, distortion=0.05
    )))

hook_notes_fm = {}
for note_name in ["Eb4", "F4", "G4", "Ab4", "Bb4", "C5", "C4", "Db4"]:
    hook_notes_fm[note_name] = to_np(synthesize_fm_lead(LeadPreset(
        name=f"WOFM_{note_name}", lead_type="fm_lead",
        frequency=KEY_FREQS[note_name],
        duration_s=BEAT * 1.0, attack_s=0.008, decay_s=0.15,
        sustain=0.55, release_s=0.2, fm_ratio=2.0, fm_depth=1.8,
        filter_cutoff=0.78, resonance=0.32, distortion=0.08
    )))

HOOK_MELODY = [
    (0.0, "Eb4", 1.0), (1.0, "Eb4", 0.5), (1.5, "F4", 0.5),
    (2.0, "Ab4", 1.5), (4.0, "Ab4", 1.0), (5.0, "F4", 0.5),
    (5.5, "Ab4", 0.5), (6.0, "Ab4", 2.0),
    (8.0, "G4", 1.0), (9.0, "G4", 0.5), (9.5, "Eb4", 0.5),
    (10.0, "C4", 1.5), (12.0, "Eb4", 1.0), (13.0, "C4", 0.5),
    (13.5, "Eb4", 0.5), (14.0, "C4", 2.0),
    (16.0, "F4", 1.0), (17.0, "F4", 0.5), (17.5, "Ab4", 0.5),
    (18.0, "C5", 1.5), (20.0, "C5", 1.0), (21.0, "Bb4", 0.5),
    (21.5, "Ab4", 0.5), (22.0, "Bb4", 2.0),
    (24.0, "Ab4", 1.0), (25.0, "Ab4", 0.5), (25.5, "F4", 0.5),
    (26.0, "Db4", 1.5), (28.0, "F4", 1.0), (29.0, "Db4", 0.5),
    (29.5, "Eb4", 0.5), (30.0, "Eb4", 2.0),
]
print(f"         {len(HOOK_MELODY)} hook melody notes (Eb4-C5 range)")

# -- REAL ACAPELLA LOADING --
print("  [8/16] Loading studio acapella...")

_acap_raw, _acap_sr = librosa.load(ACAPELLA_PATH, sr=SR, mono=True)
_acap_peak = float(np.max(np.abs(_acap_raw)))
acapella_mono: np.ndarray = _acap_raw * (0.95 / _acap_peak) if _acap_peak > 0 else _acap_raw

acapella_total_bars = len(acapella_mono) / (BAR * SR)
print(f"         {len(acapella_mono)/SR:.1f}s  {acapella_total_bars:.1f} bars  "
      f"peak={_acap_peak:.3f} -> normalised to 0.95")


def slice_acapella(start_bar: int, num_bars: int) -> np.ndarray:
    s = int(start_bar * BAR * SR)
    e = int((start_bar + num_bars) * BAR * SR)
    target = int(num_bars * BAR * SR)
    raw = acapella_mono[s:min(e, len(acapella_mono))]
    if len(raw) >= target:
        return raw[:target]
    buf = np.zeros(target)
    buf[:len(raw)] = raw
    return buf


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
print("  [9/16] Pads...")

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

# -- v5: AMBIENT TEXTURE --
print("  [10/16] Ambient texture...")

atmos_texture = to_np(synthesize_texture(TexturePreset(
    name="WOAtmosTexture", texture_type="crystal",
    duration_s=BAR * 8,
    density=0.4, brightness=0.25, depth=0.7,
    modulation_rate=0.6
)))
print(f"         texture: {len(atmos_texture)/SR:.1f}s crystal texture")

# -- ARP --
print("  [11/16] Arp synth...")

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
print("  [12/16] Risers, impacts & transitions...")

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
print("  [13/16] Drone...")

drone = to_np(synthesize_drone(DronePreset(
    name="WOAtmosDrone", drone_type="evolving",
    frequency=KEY_FREQS["Ab1"], duration_s=BAR * 8,
    num_voices=7, detune_cents=8.0, brightness=0.15,
    movement=0.45, attack_s=2.0, release_s=3.0,
    distortion=0.05, reverb_amount=0.50
)))

# -- FM HIT --
print("  [14/16] FM hit...")

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

# -- v6: GRANULAR SHIMMER TEXTURE --
print("  [15/16] Granular shimmer texture (v6)...")

granular_shimmer = to_np(synthesize_granular(GranularPreset(
    name="WOGranShimmer", grain_type="shimmer",
    frequency=KEY_FREQS["Ab3"], duration_s=BAR * 8,
    grain_size_ms=35.0, grain_density=0.6, pitch_spread=7.0,
    attack_s=1.5, release_s=2.0, brightness=0.45,
    reverb_amount=0.55, scatter_amount=0.2
)))
print(f"         granular shimmer: {len(granular_shimmer)/SR:.1f}s")

granular_dust = to_np(synthesize_granular(GranularPreset(
    name="WOGranDust", grain_type="scatter",
    frequency=KEY_FREQS["Ab4"], duration_s=BAR * 4,
    grain_size_ms=15.0, grain_density=0.3, pitch_spread=12.0,
    attack_s=0.5, release_s=1.0, brightness=0.30,
    scatter_amount=0.6
)))
print(f"         granular dust:    {len(granular_dust)/SR:.1f}s")

# -- v6: NOISE TEXTURES --
print("  [16/16] Noise textures (vinyl + air) (v6)...")

vinyl_noise = to_np(synthesize_noise(NoisePreset(
    name="WOVinyl", noise_type="vinyl",
    duration_s=BAR * 8, brightness=0.25, density=0.4,
    modulation=0.15, mod_rate=0.08, attack_s=2.0, release_s=3.0,
    gain=0.6
)))
print(f"         vinyl crackle: {len(vinyl_noise)/SR:.1f}s")

white_air = to_np(synthesize_noise(NoisePreset(
    name="WOAir", noise_type="white",
    duration_s=BAR * 4, brightness=0.12, density=0.5,
    attack_s=0.01, release_s=0.5, gain=0.3
)))
print(f"         white noise air: {len(white_air)/SR:.1f}s")

print("  Sound design complete (16/16 steps).")
print()


# ====================================================================
#  DRUM PATTERNS — 4-on-the-floor electro house
# ====================================================================

def drum_chorus(bars: int = 4) -> np.ndarray:
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        for beat in range(4):
            mix_into(buf, kick, bo + samples_for(beat), gain=0.85)
        mix_into(buf, snare, bo + samples_for(1), gain=0.72)
        mix_into(buf, clap, bo + samples_for(1), gain=0.30)
        mix_into(buf, snare, bo + samples_for(3), gain=0.72)
        mix_into(buf, clap, bo + samples_for(3), gain=0.30)
        for eighth in range(8):
            if eighth % 2 == 1:
                mix_into(buf, hat_open, bo + samples_for(eighth * 0.5),
                         gain=0.22)
            else:
                mix_into(buf, hat_closed, bo + samples_for(eighth * 0.5),
                         gain=0.28)
    return peak_normalize(buf)


def drum_verse(bars: int = 4) -> np.ndarray:
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
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        for q in range(4):
            mix_into(buf, hat_closed, bo + samples_for(q),
                     gain=0.10 + 0.04 * (bar / max(bars - 1, 1)))
    return buf


# v5: VIP drums — harder + halftime breaks woven in
def drum_vip(bars: int = 4) -> np.ndarray:
    """VIP section drums — alternating full beat and halftime bars."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        if bar % 2 == 0:
            # Full 4otf
            for beat in range(4):
                mix_into(buf, kick, bo + samples_for(beat), gain=0.90)
            mix_into(buf, snare, bo + samples_for(1), gain=0.78)
            mix_into(buf, clap, bo + samples_for(1), gain=0.35)
            mix_into(buf, snare, bo + samples_for(3), gain=0.78)
            mix_into(buf, clap, bo + samples_for(3), gain=0.35)
            for eighth in range(8):
                if eighth % 2 == 1:
                    mix_into(buf, hat_open, bo + samples_for(eighth * 0.5),
                             gain=0.25)
                else:
                    mix_into(buf, hat_closed, bo + samples_for(eighth * 0.5),
                             gain=0.30)
        else:
            # Halftime break — kick on 1 and 3, snare on 3
            mix_into(buf, kick, bo, gain=0.90)
            mix_into(buf, kick, bo + samples_for(2), gain=0.85)
            mix_into(buf, snare, bo + samples_for(2), gain=0.80)
            mix_into(buf, clap, bo + samples_for(2), gain=0.40)
            for s in range(16):
                mix_into(buf, hat_closed, bo + samples_for(s * 0.25),
                         gain=0.12)
    return peak_normalize(buf)


# ====================================================================
#  CHORD / HOOK / BASS PATTERNS
# ====================================================================

def chord_progression_full(bars: int = 8) -> np.ndarray:
    buf = render_section(bars)
    for bar in range(bars):
        chord_idx = (bar // 2) % 4
        bo = samples_for(bar * 4)
        saw = SAW_CHORDS[chord_idx]
        seg = saw[:min(len(saw), samples_for(4))]
        mix_into(buf, seg, bo, gain=1.40)
        stab = SAW_STABS[chord_idx]
        mix_into(buf, stab, bo, gain=0.75)
    return buf


def chord_progression_filtered(bars: int = 8) -> np.ndarray:
    buf = chord_progression_full(bars)
    return lowpass(buf, cutoff=0.12)


def hook_melody_render(bars: int = 8, pluck_gain: float = 0.32,
                       fm_gain: float = 0.25) -> np.ndarray:
    buf = render_section(bars)
    for beat_off, note_name, dur in HOOK_MELODY:
        offset = samples_for(beat_off)
        if offset < len(buf):
            pluck = hook_notes_pluck[note_name]
            fm = hook_notes_fm[note_name]
            mix_into(buf, pluck, offset, gain=pluck_gain)
            mix_into(buf, fm, offset, gain=fm_gain)
    return buf


def bass_pattern(bars: int = 8, gain: float = 0.55) -> np.ndarray:
    buf = render_section(bars)
    for bar in range(bars):
        chord_idx = (bar // 2) % 4
        bo = samples_for(bar * 4)
        bass_root = BASS_ROOTS[chord_idx]
        seg = bass_root[:min(len(bass_root), samples_for(4))]
        mix_into(buf, seg, bo, gain=gain)
        if bar % 2 == 0:
            mix_into(buf, wobble_bass, bo + samples_for(2), gain=gain * 0.4)
    return buf


# v5: growl bass pattern
def growl_pattern(bars: int = 8, gain: float = 0.45) -> np.ndarray:
    """Growl resampler bass pattern following chord roots with phi-sub reinforcement."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        # Growl one-shot every bar
        seg = growl_oneshot[:min(len(growl_oneshot), samples_for(4))]
        mix_into(buf, seg, bo, gain=gain)
        # Phi sub reinforcement every 2 bars
        if bar % 2 == 0:
            sub_seg = phi_sub_raw[:min(len(phi_sub_raw), samples_for(8))]
            mix_into(buf, sub_seg, bo, gain=gain * 0.3)
    return buf


def acapella_section(bars: int = 8, acap_start: int = 0) -> np.ndarray:
    return slice_acapella(acap_start, bars)


# ====================================================================
#  STRUCTURE — 144 bars (Fibonacci!)
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
VIP_DROP_BARS = 16           # v5: NEW — growl bass VIP
FINAL_CHORUS_BARS = 16
OUTRO_BARS = 16

total_bars = (INTRO_BARS + VERSE1_BARS + PRECHORUS1_BARS + CHORUS1_BARS +
              BREAK_BARS + VERSE2_BARS + PRECHORUS2_BARS + CHORUS2_BARS +
              BRIDGE_BARS + VIP_DROP_BARS + FINAL_CHORUS_BARS + OUTRO_BARS)
total_samples = samples_for(total_bars * 4)
duration_s = total_samples / SR
golden_section_bar = int(total_bars / PHI)

# Section offsets (bar number)
SEC_INTRO = 0
SEC_VERSE1 = INTRO_BARS
SEC_PRE1 = SEC_VERSE1 + VERSE1_BARS
SEC_CHORUS1 = SEC_PRE1 + PRECHORUS1_BARS
SEC_BREAK = SEC_CHORUS1 + CHORUS1_BARS
SEC_VERSE2 = SEC_BREAK + BREAK_BARS
SEC_PRE2 = SEC_VERSE2 + VERSE2_BARS
SEC_CHORUS2 = SEC_PRE2 + PRECHORUS2_BARS
SEC_BRIDGE = SEC_CHORUS2 + CHORUS2_BARS
SEC_VIP = SEC_BRIDGE + BRIDGE_BARS
SEC_FINAL = SEC_VIP + VIP_DROP_BARS
SEC_OUTRO = SEC_FINAL + FINAL_CHORUS_BARS

SECTION_MAP = {
    "INTRO": (SEC_INTRO, INTRO_BARS),
    "VERSE1": (SEC_VERSE1, VERSE1_BARS),
    "PRECHORUS1": (SEC_PRE1, PRECHORUS1_BARS),
    "CHORUS1": (SEC_CHORUS1, CHORUS1_BARS),
    "BREAK": (SEC_BREAK, BREAK_BARS),
    "VERSE2": (SEC_VERSE2, VERSE2_BARS),
    "PRECHORUS2": (SEC_PRE2, PRECHORUS2_BARS),
    "CHORUS2": (SEC_CHORUS2, CHORUS2_BARS),
    "BRIDGE": (SEC_BRIDGE, BRIDGE_BARS),
    "VIP_DROP": (SEC_VIP, VIP_DROP_BARS),
    "FINAL_CHORUS": (SEC_FINAL, FINAL_CHORUS_BARS),
    "OUTRO": (SEC_OUTRO, OUTRO_BARS),
}

assert total_bars == 144, f"Expected 144 bars (Fibonacci!), got {total_bars}"

print(f"  Structure: {total_bars} bars (FIBONACCI!) = {duration_s:.1f}s "
      f"({int(duration_s // 60)}:{int(duration_s % 60):02d})")
print(f"  Sections: {INTRO_BARS}/{VERSE1_BARS}/{PRECHORUS1_BARS}/"
      f"{CHORUS1_BARS}/{BREAK_BARS}/{VERSE2_BARS}/{PRECHORUS2_BARS}/"
      f"{CHORUS2_BARS}/{BRIDGE_BARS}/{VIP_DROP_BARS}/{FINAL_CHORUS_BARS}/"
      f"{OUTRO_BARS}")
print(f"  Golden Section Point: bar ~{golden_section_bar} "
      f"(144/phi = {144/PHI:.1f}) -> Bridge (emotional pivot)")
print()


# ====================================================================
#  STEM BUFFERS — 12 stems (v5: +GROWL, +TEXTURE)
# ====================================================================

STEM_NAMES = [
    "DRUMS", "BASS", "GROWL", "CHORDS", "HOOK", "PAD",
    "VOCAL", "ARP", "RISER", "FX", "TEXTURE", "DRONE",
]

STEM_PAN = {
    "DRUMS": 0.0, "BASS": 0.0, "GROWL": 0.0,
    "CHORDS": 0.10, "HOOK": -0.08,
    "PAD": 0.0, "VOCAL": 0.0, "ARP": -0.18, "RISER": 0.0,
    "FX": 0.0, "TEXTURE": 0.12, "DRONE": 0.0,
}

stems: dict[str, np.ndarray] = {
    name: np.zeros(total_samples) for name in STEM_NAMES
}

cursor = 0

# ── INTRO (8 bars) ─────────────────────────────────────────────────
print("  Rendering Intro (8 bars)...")
intro_start = cursor

intro_pad = lush_pad[:samples_for(INTRO_BARS * 4)]
intro_pad = fade_in(intro_pad, duration_s=BAR * 3)
intro_pad = lowpass(intro_pad, cutoff=0.08)
mix_into(stems["PAD"], intro_pad, intro_start, gain=0.30)

intro_drone = drone[:samples_for(INTRO_BARS * 4)]
intro_drone = fade_in(intro_drone, duration_s=BAR * 4)
mix_into(stems["DRONE"], intro_drone, intro_start, gain=0.25)

_a = ACAP_MAP["INTRO"]
intro_vox = slice_acapella(_a[0], INTRO_BARS)
intro_vox = lowpass(intro_vox, cutoff=0.18)
intro_vox = fade_in(intro_vox, duration_s=BAR * 2)
mix_into(stems["VOCAL"], intro_vox, intro_start, gain=0.30)

intro_drums = drum_intro(INTRO_BARS)
intro_drums = fade_in(intro_drums, duration_s=BAR * 4)
mix_into(stems["DRUMS"], intro_drums, intro_start, gain=0.20)

chord_filt = chord_progression_filtered(4)
chord_filt = fade_in(chord_filt, duration_s=BAR * 2)
mix_into(stems["CHORDS"], chord_filt, intro_start + samples_for(16), gain=0.30)

# v6: granular shimmer + vinyl noise in intro
intro_tex = granular_shimmer[:samples_for(INTRO_BARS * 4)]
intro_tex = fade_in(intro_tex, duration_s=BAR * 4)
mix_into(stems["TEXTURE"], intro_tex, intro_start, gain=0.15)

intro_vinyl = vinyl_noise[:samples_for(INTRO_BARS * 4)]
intro_vinyl = fade_in(intro_vinyl, duration_s=BAR * 2)
mix_into(stems["FX"], intro_vinyl, intro_start, gain=0.08)

rev_off = intro_start + samples_for(INTRO_BARS * 4) - len(reverse_hit)
if rev_off > intro_start:
    mix_into(stems["FX"], reverse_hit, rev_off, gain=0.25)

cursor += samples_for(INTRO_BARS * 4)

# ── VERSE 1 (16 bars) ─────────────────────────────────────────────
print("  Rendering Verse 1 (16 bars)...")
verse1_start = cursor

for rep in range(VERSE1_BARS // 4):
    offset = verse1_start + samples_for(rep * 16)
    d = drum_verse(4)
    mix_into(stems["DRUMS"], d, offset, gain=0.52)

v1_bass = apply_sidechain(bass_pattern(VERSE1_BARS, gain=0.50), SC_PUMP, SR)
mix_into(stems["BASS"], v1_bass, verse1_start, gain=0.48)

_a = ACAP_MAP["VERSE1"]
v1_vox = slice_acapella(_a[0], VERSE1_BARS)
v1_vox = fade_in(v1_vox, duration_s=BAR)
mix_into(stems["VOCAL"], v1_vox, verse1_start, gain=0.55)

verse_pad = lush_pad[:samples_for(VERSE1_BARS * 4)]
verse_pad = lowpass(verse_pad, cutoff=0.15)
mix_into(stems["PAD"], verse_pad, verse1_start, gain=0.22)

for rep in range(VERSE1_BARS // 4):
    offset = verse1_start + samples_for(rep * 16)
    seg = arp_pluck[:min(len(arp_pluck), samples_for(16))]
    mix_into(stems["ARP"], seg, offset, gain=0.12)

for rep in range(VERSE1_BARS // 8 + 1):
    offset = verse1_start + samples_for(rep * 32)
    seg = drone[:min(len(drone), samples_for(32))]
    mix_into(stems["DRONE"], seg, offset, gain=0.12)

cursor += samples_for(VERSE1_BARS * 4)

# ── PRE-CHORUS 1 (8 bars) ─────────────────────────────────────────
print("  Rendering Pre-Chorus 1 (8 bars)...")
pc1_start = cursor

pc1_drums = drum_build(PRECHORUS1_BARS)
mix_into(stems["DRUMS"], pc1_drums, pc1_start, gain=0.45)

riser_seg = pitch_riser[:samples_for(PRECHORUS1_BARS * 4)]
mix_into(stems["RISER"], riser_seg, pc1_start, gain=0.22)
noise_seg = noise_riser[:samples_for(PRECHORUS1_BARS * 4)]
mix_into(stems["RISER"], noise_seg, pc1_start, gain=0.13)

hook_preview = hook_melody_render(8, pluck_gain=0.18, fm_gain=0.12)
hook_preview = lowpass(hook_preview, cutoff=0.25)
mix_into(stems["HOOK"], hook_preview, pc1_start, gain=0.28)

_a = ACAP_MAP["PRECHORUS1"]
pc1_vox = slice_acapella(_a[0], PRECHORUS1_BARS)
mix_into(stems["VOCAL"], pc1_vox, pc1_start, gain=0.50)

for bar in range(PRECHORUS1_BARS):
    bo = pc1_start + samples_for(bar * 4)
    g = build_gain(bar, PRECHORUS1_BARS, start=0.10, end=0.28)
    seg = chord_pad_major[:samples_for(4)]
    mix_into(stems["PAD"], seg, bo, gain=g)

for bar in range(PRECHORUS1_BARS):
    bo = pc1_start + samples_for(bar * 4)
    g = build_gain(bar, PRECHORUS1_BARS, start=0.06, end=0.18)
    mix_into(stems["VOCAL"], chop_stutter, bo, gain=g)

# v5: beat repeat building in last 4 bars
_br_src = stems["DRUMS"][pc1_start + samples_for(16):pc1_start + samples_for(32)].copy()
if len(_br_src) > 0:
    _br_fx = to_np(apply_beat_repeat(_br_src, BEAT_REPEAT_BUILD, bpm=BPM,
                                     sample_rate=SR))
    mix_into(stems["FX"], _br_fx, pc1_start + samples_for(16), gain=0.20)

ee_off = pc1_start + samples_for(PRECHORUS1_BARS * 4) - len(chop_ee) - SR // 4
if ee_off > pc1_start:
    mix_into(stems["VOCAL"], chop_ee, ee_off, gain=0.25)

rev_pc1 = pc1_start + samples_for(PRECHORUS1_BARS * 4) - len(reverse_hit)
if rev_pc1 > pc1_start:
    mix_into(stems["FX"], reverse_hit, rev_pc1, gain=0.35)

cursor += samples_for(PRECHORUS1_BARS * 4)

# ── CHORUS 1 (16 bars) ────────────────────────────────────────────
print("  Rendering Chorus 1 (16 bars — full drop)...")
ch1_start = cursor

mix_into(stems["FX"], sub_boom, ch1_start, gain=0.28)
mix_into(stems["FX"], cinema_hit, ch1_start, gain=0.18)
mix_into(stems["FX"], to_np(impact_boom), ch1_start, gain=0.12)

for rep in range(CHORUS1_BARS // 4):
    offset = ch1_start + samples_for(rep * 16)
    d = drum_chorus(4)
    mix_into(stems["DRUMS"], d, offset, gain=0.55)

for rep in range(CHORUS1_BARS // 8):
    offset = ch1_start + samples_for(rep * 32)
    chords = chord_progression_full(8)
    chords = apply_sidechain(chords, SC_PUMP, SR)
    mix_into(stems["CHORDS"], chords, offset, gain=0.95)

ch1_bass = apply_sidechain(bass_pattern(CHORUS1_BARS, gain=0.58), SC_HARD, SR)
mix_into(stems["BASS"], ch1_bass, ch1_start, gain=0.50)

for rep in range(CHORUS1_BARS // 8):
    offset = ch1_start + samples_for(rep * 32)
    hook = hook_melody_render(8, pluck_gain=0.32, fm_gain=0.26)
    mix_into(stems["HOOK"], hook, offset, gain=0.40)

_a = ACAP_MAP["CHORUS1"]
ch1_vox = slice_acapella(_a[0], CHORUS1_BARS)
mix_into(stems["VOCAL"], ch1_vox, ch1_start, gain=0.60)

ch1_pad = lush_pad[:samples_for(CHORUS1_BARS * 4)]
mix_into(stems["PAD"], ch1_pad, ch1_start, gain=0.18)

for rep in range(CHORUS1_BARS // 4):
    offset = ch1_start + samples_for(rep * 16)
    seg = arp_shimmer[:min(len(arp_shimmer), samples_for(16))]
    mix_into(stems["ARP"], seg, offset, gain=0.14)

for bar in range(0, CHORUS1_BARS, 2):
    mix_into(stems["FX"], fm_hit,
             ch1_start + samples_for(bar * 4), gain=0.13)

stut_off = ch1_start + samples_for((CHORUS1_BARS - 2) * 4)
mix_into(stems["FX"], stutter_fx, stut_off, gain=0.16)

# v6: white air noise over chorus drop
ch1_air = white_air[:samples_for(CHORUS1_BARS * 4)]
mix_into(stems["TEXTURE"], ch1_air, ch1_start, gain=0.06)

tape_ch1 = ch1_start + samples_for(CHORUS1_BARS * 4) - len(tape_stop)
if tape_ch1 > ch1_start:
    mix_into(stems["FX"], tape_stop, tape_ch1, gain=0.20)

cursor += samples_for(CHORUS1_BARS * 4)

# ── BREAK (8 bars) ────────────────────────────────────────────────
print("  Rendering Break (8 bars — ACAPELLA section)...")
break_start = cursor

_a = ACAP_MAP["BREAK"]
acapella = slice_acapella(_a[0], BREAK_BARS)
mix_into(stems["VOCAL"], acapella, break_start, gain=0.65)

break_pad = dark_pad[:samples_for(BREAK_BARS * 4)]
break_pad = fade_in(break_pad, duration_s=BAR)
break_pad = fade_out(break_pad, duration_s=BAR * 2)
mix_into(stems["PAD"], break_pad, break_start, gain=0.25)

for bar in range(BREAK_BARS):
    bo = break_start + samples_for(bar * 4)
    for q in range(4):
        mix_into(stems["DRUMS"], hat_closed, bo + samples_for(q), gain=0.06)

break_drone = drone[:samples_for(BREAK_BARS * 4)]
break_drone = lowpass(break_drone, cutoff=0.08)
mix_into(stems["DRONE"], break_drone, break_start, gain=0.10)

# v6: granular dust texture in break
break_tex = granular_dust[:samples_for(BREAK_BARS * 4)]
break_tex = lowpass(break_tex, cutoff=0.15)
mix_into(stems["TEXTURE"], break_tex, break_start, gain=0.12)

cursor += samples_for(BREAK_BARS * 4)

# ── VERSE 2 (8 bars) ──────────────────────────────────────────────
print("  Rendering Verse 2 (8 bars)...")
verse2_start = cursor

for rep in range(VERSE2_BARS // 4):
    offset = verse2_start + samples_for(rep * 16)
    d = drum_verse(4)
    mix_into(stems["DRUMS"], d, offset, gain=0.55)

v2_bass = apply_sidechain(bass_pattern(VERSE2_BARS, gain=0.52), SC_PUMP, SR)
mix_into(stems["BASS"], v2_bass, verse2_start, gain=0.50)

_a = ACAP_MAP["VERSE2"]
v2_vox = slice_acapella(_a[0], VERSE2_BARS)
mix_into(stems["VOCAL"], v2_vox, verse2_start, gain=0.55)

v2_pad = lush_pad[:samples_for(VERSE2_BARS * 4)]
v2_pad = lowpass(v2_pad, cutoff=0.18)
mix_into(stems["PAD"], v2_pad, verse2_start, gain=0.24)

for rep in range(VERSE2_BARS // 4):
    offset = verse2_start + samples_for(rep * 16)
    seg = arp_pluck[:min(len(arp_pluck), samples_for(16))]
    mix_into(stems["ARP"], seg, offset, gain=0.15)

cursor += samples_for(VERSE2_BARS * 4)

# ── PRE-CHORUS 2 (8 bars) ─────────────────────────────────────────
print("  Rendering Pre-Chorus 2 (8 bars — bigger build)...")
pc2_start = cursor

pc2_drums = drum_build(PRECHORUS2_BARS)
mix_into(stems["DRUMS"], pc2_drums, pc2_start, gain=0.48)

riser2_pitch = pitch_riser[:samples_for(PRECHORUS2_BARS * 4)]
riser2_harm = harmonic_riser[:samples_for(PRECHORUS2_BARS * 4)]
riser2_noise = noise_riser[:samples_for(PRECHORUS2_BARS * 4)]
mix_into(stems["RISER"], riser2_pitch, pc2_start, gain=0.24)
mix_into(stems["RISER"], riser2_harm, pc2_start, gain=0.20)
mix_into(stems["RISER"], riser2_noise, pc2_start, gain=0.15)

hook_pre2 = hook_melody_render(8, pluck_gain=0.22, fm_gain=0.16)
mix_into(stems["HOOK"], hook_pre2, pc2_start, gain=0.32)

for bar in range(PRECHORUS2_BARS):
    bo = pc2_start + samples_for(bar * 4)
    g = build_gain(bar, PRECHORUS2_BARS, start=0.08, end=0.30)
    chord_idx = (bar // 2) % 4
    stab = SAW_STABS[chord_idx]
    mix_into(stems["CHORDS"], stab, bo, gain=g)

_a = ACAP_MAP["PRECHORUS2"]
pc2_vox = slice_acapella(_a[0], PRECHORUS2_BARS)
mix_into(stems["VOCAL"], pc2_vox, pc2_start, gain=0.52)

for bar in range(PRECHORUS2_BARS):
    bo = pc2_start + samples_for(bar * 4)
    g = build_gain(bar, PRECHORUS2_BARS, start=0.06, end=0.20)
    mix_into(stems["VOCAL"], chop_stutter, bo, gain=g)

# v5: beat repeat building in last 4 bars
_br2_src = stems["DRUMS"][pc2_start + samples_for(16):pc2_start + samples_for(32)].copy()
if len(_br2_src) > 0:
    _br2_fx = to_np(apply_beat_repeat(_br2_src, BEAT_REPEAT_BUILD, bpm=BPM,
                                      sample_rate=SR))
    mix_into(stems["FX"], _br2_fx, pc2_start + samples_for(16), gain=0.22)

rev_pc2 = pc2_start + samples_for(PRECHORUS2_BARS * 4) - len(reverse_hit)
if rev_pc2 > pc2_start:
    mix_into(stems["FX"], reverse_hit, rev_pc2, gain=0.30)
dive_pc2 = pc2_start + samples_for((PRECHORUS2_BARS - 1) * 4)
mix_into(stems["FX"], pitch_dive, dive_pc2, gain=0.22)

ee_off2 = pc2_start + samples_for(PRECHORUS2_BARS * 4) - len(chop_ee) - SR // 6
if ee_off2 > pc2_start:
    mix_into(stems["VOCAL"], chop_ee, ee_off2, gain=0.28)

cursor += samples_for(PRECHORUS2_BARS * 4)

# ── CHORUS 2 (16 bars) ────────────────────────────────────────────
print("  Rendering Chorus 2 (16 bars — maximum energy)...")
ch2_start = cursor

mix_into(stems["FX"], sub_boom, ch2_start, gain=0.30)
mix_into(stems["FX"], cinema_hit, ch2_start, gain=0.20)
mix_into(stems["FX"], to_np(impact_boom), ch2_start, gain=0.14)
mix_into(stems["DRUMS"], clap, ch2_start, gain=0.35)

for rep in range(CHORUS2_BARS // 4):
    offset = ch2_start + samples_for(rep * 16)
    d = drum_chorus(4)
    mix_into(stems["DRUMS"], d, offset, gain=0.58)

for rep in range(CHORUS2_BARS // 8):
    offset = ch2_start + samples_for(rep * 32)
    chords = chord_progression_full(8)
    chords = apply_sidechain(chords, SC_HARD, SR)
    mix_into(stems["CHORDS"], chords, offset, gain=0.98)

ch2_bass = apply_sidechain(bass_pattern(CHORUS2_BARS, gain=0.60), SC_HARD, SR)
mix_into(stems["BASS"], ch2_bass, ch2_start, gain=0.52)

for rep in range(CHORUS2_BARS // 8):
    offset = ch2_start + samples_for(rep * 32)
    hook = hook_melody_render(8, pluck_gain=0.35, fm_gain=0.28)
    mix_into(stems["HOOK"], hook, offset, gain=0.42)

_a = ACAP_MAP["CHORUS2"]
ch2_vox = slice_acapella(_a[0], CHORUS2_BARS)
mix_into(stems["VOCAL"], ch2_vox, ch2_start, gain=0.62)

ch2_pad = lush_pad[:samples_for(CHORUS2_BARS * 4)]
mix_into(stems["PAD"], ch2_pad, ch2_start, gain=0.20)

for rep in range(CHORUS2_BARS // 4):
    offset = ch2_start + samples_for(rep * 16)
    seg = arp_shimmer[:min(len(arp_shimmer), samples_for(16))]
    mix_into(stems["ARP"], seg, offset, gain=0.16)

for bar in range(0, CHORUS2_BARS, 2):
    mix_into(stems["FX"], fm_hit,
             ch2_start + samples_for(bar * 4), gain=0.15)

for trans_bar in [6, 14]:
    stut_ch2 = ch2_start + samples_for(trans_bar * 4)
    mix_into(stems["FX"], stutter_fx, stut_ch2, gain=0.18)

# v6: white air noise over chorus 2
ch2_air = white_air[:samples_for(CHORUS2_BARS * 4)]
mix_into(stems["TEXTURE"], ch2_air, ch2_start, gain=0.07)

tape_ch2 = ch2_start + samples_for(CHORUS2_BARS * 4) - len(tape_stop)
if tape_ch2 > ch2_start:
    mix_into(stems["FX"], tape_stop, tape_ch2, gain=0.22)

cursor += samples_for(CHORUS2_BARS * 4)

# ── BRIDGE (8 bars) ─── Golden Section Point (bar ~89) ────────────
print("  Rendering Bridge (8 bars — emotional breakdown, GOLDEN SECTION)...")
bridge_start = cursor

_a = ACAP_MAP["BRIDGE"]
bridge_acapella = slice_acapella(_a[0], BRIDGE_BARS)
mix_into(stems["VOCAL"], bridge_acapella, bridge_start, gain=0.62)

bridge_pad = lush_pad[:samples_for(BRIDGE_BARS * 4)]
bridge_pad = fade_in(bridge_pad, duration_s=BAR)
mix_into(stems["PAD"], bridge_pad, bridge_start, gain=0.30)

for rep in range(BRIDGE_BARS // 4):
    offset = bridge_start + samples_for(rep * 16)
    seg = arp_pluck[:min(len(arp_pluck), samples_for(16))]
    seg = lowpass(seg, cutoff=0.20)
    mix_into(stems["ARP"], seg, offset, gain=0.16)

bridge_drone = drone[:samples_for(BRIDGE_BARS * 4)]
mix_into(stems["DRONE"], bridge_drone, bridge_start, gain=0.15)

# v6: granular shimmer texture bed
bridge_tex = granular_shimmer[:samples_for(BRIDGE_BARS * 4)]
bridge_tex = fade_in(bridge_tex, duration_s=BAR * 2)
mix_into(stems["TEXTURE"], bridge_tex, bridge_start, gain=0.18)

for bar in range(BRIDGE_BARS):
    bo = bridge_start + samples_for(bar * 4)
    for q in range(4):
        mix_into(stems["DRUMS"], hat_closed, bo + samples_for(q), gain=0.07)

riser_bridge = pitch_riser[:samples_for(4 * 4)]
mix_into(stems["RISER"], riser_bridge,
         bridge_start + samples_for(4 * 4), gain=0.25)

rev_bridge = bridge_start + samples_for(BRIDGE_BARS * 4) - len(reverse_hit)
if rev_bridge > bridge_start:
    mix_into(stems["FX"], reverse_hit, rev_bridge, gain=0.28)

cursor += samples_for(BRIDGE_BARS * 4)

# ── VIP DROP (16 bars) ─── NEW in v5: Growl Bass VIP ──────────────
print("  Rendering VIP Drop (16 bars — GROWL BASS VIP)...")
vip_start = cursor

# MASSIVE IMPACT
mix_into(stems["FX"], sub_boom, vip_start, gain=0.35)
mix_into(stems["FX"], cinema_hit, vip_start, gain=0.25)
mix_into(stems["FX"], to_np(impact_boom), vip_start, gain=0.18)
mix_into(stems["DRUMS"], clap, vip_start, gain=0.40)
mix_into(stems["VOCAL"], chop_ee, vip_start, gain=0.30)

# VIP drums — halftime breaks
for rep in range(VIP_DROP_BARS // 4):
    offset = vip_start + samples_for(rep * 16)
    d = drum_vip(4)
    mix_into(stems["DRUMS"], d, offset, gain=0.62)

# GROWL BASS — the VIP star element
vip_growl = growl_pattern(VIP_DROP_BARS, gain=0.55)
vip_growl = apply_sidechain(vip_growl, SC_HARD, SR)
mix_into(stems["GROWL"], vip_growl, vip_start, gain=0.60)

# Chord progression — darker, harder sidechain
for rep in range(VIP_DROP_BARS // 8):
    offset = vip_start + samples_for(rep * 32)
    chords = chord_progression_full(8)
    chords = apply_sidechain(chords, SC_HARD, SR)
    mix_into(stems["CHORDS"], chords, offset, gain=0.85)

# Sub bass underneath growl
vip_bass = apply_sidechain(bass_pattern(VIP_DROP_BARS, gain=0.50), SC_HARD, SR)
mix_into(stems["BASS"], vip_bass, vip_start, gain=0.42)

# Hook melody — still present but growl is the star
for rep in range(VIP_DROP_BARS // 8):
    offset = vip_start + samples_for(rep * 32)
    hook = hook_melody_render(8, pluck_gain=0.28, fm_gain=0.22)
    mix_into(stems["HOOK"], hook, offset, gain=0.35)

# Real acapella — reuse chorus vocal
_a = ACAP_MAP["VIP"]
vip_vox = slice_acapella(_a[0], VIP_DROP_BARS)
mix_into(stems["VOCAL"], vip_vox, vip_start, gain=0.50)

# Pad — minimal
vip_pad = dark_pad[:samples_for(VIP_DROP_BARS * 4)]
mix_into(stems["PAD"], vip_pad, vip_start, gain=0.12)

# Arp — glitchy
for rep in range(VIP_DROP_BARS // 4):
    offset = vip_start + samples_for(rep * 16)
    seg = arp_shimmer[:min(len(arp_shimmer), samples_for(16))]
    mix_into(stems["ARP"], seg, offset, gain=0.14)

# v5: Beat repeat VIP (phi grid!) on growl for extra glitch
_growl_src = stems["GROWL"][vip_start:vip_start + samples_for(VIP_DROP_BARS * 4)].copy()
if len(_growl_src) > 0 and np.max(np.abs(_growl_src)) > 0.001:
    _growl_br = to_np(apply_beat_repeat(_growl_src, BEAT_REPEAT_VIP, bpm=BPM,
                                        sample_rate=SR))
    mix_into(stems["FX"], _growl_br, vip_start, gain=0.18)

# FM accents harder
for bar in range(0, VIP_DROP_BARS, 2):
    mix_into(stems["FX"], fm_hit,
             vip_start + samples_for(bar * 4), gain=0.18)

# Stutter transitions
for trans_bar in [6, 10, 14]:
    stut_vip = vip_start + samples_for(trans_bar * 4)
    mix_into(stems["FX"], stutter_fx, stut_vip, gain=0.20)

# v6: white air noise over VIP drop
vip_air = white_air[:samples_for(VIP_DROP_BARS * 4)]
mix_into(stems["TEXTURE"], vip_air, vip_start, gain=0.07)

# Tape stop at end
tape_vip = vip_start + samples_for(VIP_DROP_BARS * 4) - len(tape_stop)
if tape_vip > vip_start:
    mix_into(stems["FX"], tape_stop, tape_vip, gain=0.22)

cursor += samples_for(VIP_DROP_BARS * 4)

# ── FINAL CHORUS (16 bars) ─── "Climax: everything layered" ───────
print("  Rendering Final Chorus (16 bars — CLIMAX)...")
fc_start = cursor

mix_into(stems["FX"], sub_boom, fc_start, gain=0.32)
mix_into(stems["FX"], cinema_hit, fc_start, gain=0.22)
mix_into(stems["FX"], to_np(impact_boom), fc_start, gain=0.15)
mix_into(stems["DRUMS"], clap, fc_start, gain=0.38)
mix_into(stems["VOCAL"], chop_ee, fc_start, gain=0.25)

for rep in range(FINAL_CHORUS_BARS // 4):
    offset = fc_start + samples_for(rep * 16)
    d = drum_chorus(4)
    mix_into(stems["DRUMS"], d, offset, gain=0.60)

for rep in range(FINAL_CHORUS_BARS // 8):
    offset = fc_start + samples_for(rep * 32)
    chords = chord_progression_full(8)
    chords = apply_sidechain(chords, SC_HARD, SR)
    mix_into(stems["CHORDS"], chords, offset, gain=1.00)

fc_bass = apply_sidechain(bass_pattern(FINAL_CHORUS_BARS, gain=0.62), SC_HARD, SR)
mix_into(stems["BASS"], fc_bass, fc_start, gain=0.55)

# v5: growl layer underneath final chorus too
fc_growl = growl_pattern(FINAL_CHORUS_BARS, gain=0.35)
fc_growl = apply_sidechain(fc_growl, SC_HARD, SR)
mix_into(stems["GROWL"], fc_growl, fc_start, gain=0.30)

for rep in range(FINAL_CHORUS_BARS // 8):
    offset = fc_start + samples_for(rep * 32)
    hook = hook_melody_render(8, pluck_gain=0.38, fm_gain=0.30)
    mix_into(stems["HOOK"], hook, offset, gain=0.45)

_a = ACAP_MAP["FINAL"]
fc_vox = slice_acapella(_a[0], FINAL_CHORUS_BARS)
mix_into(stems["VOCAL"], fc_vox, fc_start, gain=0.65)

fc_pad = lush_pad[:samples_for(FINAL_CHORUS_BARS * 4)]
mix_into(stems["PAD"], fc_pad, fc_start, gain=0.22)

for rep in range(FINAL_CHORUS_BARS // 4):
    offset = fc_start + samples_for(rep * 16)
    seg = arp_shimmer[:min(len(arp_shimmer), samples_for(16))]
    mix_into(stems["ARP"], seg, offset, gain=0.18)

for rep in range(FINAL_CHORUS_BARS // 8 + 1):
    offset = fc_start + samples_for(rep * 32)
    seg = drone[:min(len(drone), samples_for(32))]
    mix_into(stems["DRONE"], seg, offset, gain=0.10)

for bar in range(0, FINAL_CHORUS_BARS, 2):
    mix_into(stems["FX"], fm_hit,
             fc_start + samples_for(bar * 4), gain=0.16)

stut_fc1 = fc_start + samples_for(6 * 4)
stut_fc2 = fc_start + samples_for(14 * 4)
mix_into(stems["FX"], stutter_fx, stut_fc1, gain=0.16)
mix_into(stems["FX"], stutter_fx, stut_fc2, gain=0.19)

# v6: white air noise over final chorus
fc_air = white_air[:samples_for(FINAL_CHORUS_BARS * 4)]
mix_into(stems["TEXTURE"], fc_air, fc_start, gain=0.07)

tape_fc = fc_start + samples_for(FINAL_CHORUS_BARS * 4) - len(tape_stop)
if tape_fc > fc_start:
    mix_into(stems["FX"], tape_stop, tape_fc, gain=0.22)

cursor += samples_for(FINAL_CHORUS_BARS * 4)

# ── OUTRO (16 bars) ───────────────────────────────────────────────
print("  Rendering Outro (16 bars — dissolving)...")
outro_start = cursor

outro_pad = lush_pad[:samples_for(OUTRO_BARS * 4)]
outro_pad = fade_out(outro_pad, duration_s=BAR * 10)
mix_into(stems["PAD"], outro_pad, outro_start, gain=0.28)

_a = ACAP_MAP["OUTRO"]
_outro_len = _a[1] - _a[0]
outro_acapella = slice_acapella(_a[0], min(_outro_len, OUTRO_BARS))
outro_acapella = fade_out(outro_acapella, duration_s=BAR * 6)
mix_into(stems["VOCAL"], outro_acapella, outro_start, gain=0.45)

outro_drone = drone[:samples_for(OUTRO_BARS * 4)]
outro_drone = fade_out(outro_drone, duration_s=BAR * 12)
mix_into(stems["DRONE"], outro_drone, outro_start, gain=0.20)

outro_drums = drum_intro(OUTRO_BARS)
outro_drums = fade_out(outro_drums, duration_s=BAR * 10)
mix_into(stems["DRUMS"], outro_drums, outro_start, gain=0.12)

outro_sub = to_np(synthesize_bass(BassPreset(
    name="WOOutroSub", bass_type="sub_sine", frequency=KEY_FREQS["Ab1"],
    duration_s=OUTRO_BARS * BAR, attack_s=0.01,
    release_s=OUTRO_BARS * BAR * 0.8
)))
outro_sub = fade_out(outro_sub, duration_s=BAR * 12)
mix_into(stems["BASS"], outro_sub, outro_start, gain=0.14)

for rep in range(OUTRO_BARS // 4):
    offset = outro_start + samples_for(rep * 16)
    seg = arp_pluck[:min(len(arp_pluck), samples_for(16))]
    seg = lowpass(seg, cutoff=0.10)
    seg = fade_out(seg, duration_s=BAR * 3)
    mix_into(stems["ARP"], seg, offset, gain=0.10)

mix_into(stems["FX"], pitch_dive,
         outro_start + samples_for(10 * 4), gain=0.20)

chord_ghost = chord_progression_filtered(4)
chord_ghost = fade_out(chord_ghost, duration_s=BAR * 3)
mix_into(stems["CHORDS"], chord_ghost, outro_start, gain=0.20)

# v6: granular shimmer dissolving + vinyl noise fadeout
outro_tex = granular_shimmer[:samples_for(OUTRO_BARS * 4)]
outro_tex = fade_out(outro_tex, duration_s=BAR * 10)
mix_into(stems["TEXTURE"], outro_tex, outro_start, gain=0.15)

outro_vinyl = vinyl_noise[:samples_for(OUTRO_BARS * 4)]
outro_vinyl = fade_out(outro_vinyl, duration_s=BAR * 8)
mix_into(stems["FX"], outro_vinyl, outro_start, gain=0.06)


# ====================================================================
#  v5: PHI CROSSFADES BETWEEN SECTIONS
# ====================================================================
print()
print("  v5: Applying phi crossfades between sections...")

section_boundaries = [
    SEC_VERSE1, SEC_PRE1, SEC_CHORUS1, SEC_BREAK,
    SEC_VERSE2, SEC_PRE2, SEC_CHORUS2, SEC_BRIDGE,
    SEC_VIP, SEC_FINAL, SEC_OUTRO,
]

for name in STEM_NAMES:
    for boundary_bar in section_boundaries:
        stems[name] = phi_crossfade_sections(stems[name], boundary_bar,
                                             fade_bars=0.5)

print(f"    {len(section_boundaries)} boundaries x {len(STEM_NAMES)} stems")


# ====================================================================
#  v5: PER-STEM DYNAMICS & PROCESSING
# ====================================================================
print("  v5: Per-stem dynamics processing...")

# Transient shaping on drums
stems["DRUMS"] = to_np(DYNPROC.transient_shaper(
    stems["DRUMS"].tolist(), attack_gain=1.3, sustain_gain=0.85))
print("    DRUMS   -> transient_shaper (attack=1.3, sustain=0.85)")

# Compress bass
stems["BASS"] = to_np(compress(stems["BASS"], COMP_BASS, SR))
print("    BASS    -> compress (ratio=4.0, threshold=-12dB)")

# Compress growl
stems["GROWL"] = to_np(compress(stems["GROWL"], COMP_BASS, SR))
print("    GROWL   -> compress (ratio=4.0, threshold=-12dB)")

# De-ess vocals, then compress
stems["VOCAL"] = to_np(DYNPROC.de_ess(stems["VOCAL"].tolist(), DEESS))
stems["VOCAL"] = to_np(compress(stems["VOCAL"], COMP_VOCAL, SR))
print("    VOCAL   -> de_ess (6500Hz) + compress (ratio=3.5)")

# Light compression on drums
stems["DRUMS"] = to_np(compress(stems["DRUMS"], COMP_DRUMS, SR))
print("    DRUMS   -> compress (ratio=3.0, threshold=-8dB)")


# ====================================================================
#  DSP POST-PROCESSING
# ====================================================================
print()
print("  Applying DSP processing...")

stems["PAD"] = apply_sidechain(stems["PAD"], SC_PUMP, SR)

# Reverb/delay sends
stems["PAD"] = apply_hall(stems["PAD"], HALL_VERB, SR)
stems["VOCAL"] = apply_hall(stems["VOCAL"], HALL_VERB, SR)
stems["ARP"] = apply_room(stems["ARP"], ROOM_VERB, SR)
stems["HOOK"] = apply_room(stems["HOOK"], ROOM_VERB, SR)
stems["CHORDS"] = apply_hall(stems["CHORDS"], HALL_VERB, SR)
stems["DRONE"] = apply_hall(stems["DRONE"], HALL_VERB, SR)
stems["TEXTURE"] = apply_hall(stems["TEXTURE"], HALL_VERB, SR)
stems["GROWL"] = apply_room(stems["GROWL"], ROOM_VERB, SR)

print("    PAD     -> sidechain + hall")
print("    VOCAL   -> hall")
print("    ARP     -> room")
print("    HOOK    -> room")
print("    CHORDS  -> hall")
print("    DRONE   -> hall")
print("    TEXTURE -> hall")
print("    GROWL   -> room")

# v5: Multi-technique stereo imaging
print("  v5: Multi-technique stereo imaging...")
stems["PAD"] = apply_haas(stems["PAD"], STEREO_PAD, SR)
stems["CHORDS"] = apply_psychoacoustic(stems["CHORDS"], STEREO_CHORD, SR)
stems["ARP"] = apply_frequency_split(stems["ARP"], STEREO_ARP, SR)
stems["HOOK"] = apply_mid_side(stems["HOOK"], STEREO_HOOK, SR)
print("    PAD     -> Haas (12ms, width=1.2)")
print("    CHORDS  -> psychoacoustic (width=1.4)")
print("    ARP     -> frequency_split (2kHz, width=1.1)")
print("    HOOK    -> mid_side (width=0.9)")

# ── Insight 38, 84: Parallel saturation via SaturationEngine (v6) ─
print("  Insight 38/84: SaturationEngine (tape/tube saturation — v6)...")

stems["BASS"] = to_np(SAT_ENGINE.saturate(
    stems["BASS"].tolist() if stems["BASS"].ndim == 1 else stems["BASS"][:, 0].tolist(),
    SatConfig(sat_type="tape", drive=2.5, mix=0.20)))
stems["GROWL"] = to_np(SAT_ENGINE.saturate(
    stems["GROWL"].tolist() if stems["GROWL"].ndim == 1 else stems["GROWL"][:, 0].tolist(),
    SatConfig(sat_type="tube", drive=4.0, mix=0.30)))
stems["HOOK"] = to_np(SAT_ENGINE.saturate(
    stems["HOOK"].tolist() if stems["HOOK"].ndim == 1 else stems["HOOK"][:, 0].tolist(),
    SatConfig(sat_type="tape", drive=1.8, mix=0.12)))
print("    BASS   -> SaturationEngine tape (drive=2.5, mix=20%)")
print("    GROWL  -> SaturationEngine tube (drive=4.0, mix=30%)")
print("    HOOK   -> SaturationEngine tape (drive=1.8, mix=12%)")

# ── Insight 19: Low Pass Gate on drone (LPG: filter+VCA) ────────
print("  Insight 19: Low Pass Gate on drone...")


def _low_pass_gate(signal: np.ndarray, rate_hz: float = 0.15,
                   depth: float = 0.6, sr: int = 44100) -> np.ndarray:
    """Simulated LPG: amplitude and brightness coupled via slow LFO."""
    n = len(signal) if signal.ndim == 1 else signal.shape[0]
    t = np.arange(n, dtype=np.float64) / sr
    lfo = 0.5 + 0.5 * np.sin(2.0 * np.pi * rate_hz * t)
    gate = 1.0 - depth * (1.0 - lfo)
    if signal.ndim == 2:
        gate = gate[:, None]
    return signal * gate


stems["DRONE"] = _low_pass_gate(stems["DRONE"], rate_hz=0.12, depth=0.5)
print("    DRONE  -> LPG (rate=0.12Hz, depth=50%)")


# ====================================================================
#  v5: DYNAMICS ANALYSIS
# ====================================================================
print()
print("  v5: Stem dynamics analysis...")
for name in STEM_NAMES:
    profile = analyze_dynamics(stems[name], SR)
    print(f"    {name:12s}  peak={profile.peak_db:+.1f}dB  "
          f"rms={profile.rms_db:+.1f}dB  "
          f"crest={profile.crest_factor_db:.1f}dB")

# v6: DC removal on all stems before export
print("  v6: DC removal (highpass 5Hz)...")
for name in STEM_NAMES:
    buf = stems[name]
    if buf.ndim == 2 and buf.shape[1] == 2:
        stems[name] = np.column_stack((
            to_np(DC_ENGINE.remove_highpass(buf[:, 0].tolist(), cutoff=5.0)),
            to_np(DC_ENGINE.remove_highpass(buf[:, 1].tolist(), cutoff=5.0)),
        ))
    else:
        if buf.ndim == 2:
            buf = buf[:, 0]
        stems[name] = to_np(DC_ENGINE.remove_highpass(buf.tolist(), cutoff=5.0))
print(f"    {len(STEM_NAMES)} stems DC-cleaned")


# ====================================================================
#  EXPORT STEMS + REFERENCE MIXDOWN + MIDI + ALS
# ====================================================================
print()
print("  Bouncing stems (24-bit)...")

os.makedirs("output/stems", exist_ok=True)
stem_paths: list[str] = []


def _pack_24bit(float_buf: np.ndarray, gain: float) -> bytes:
    """Convert float buffer to 24-bit packed bytes."""
    int_buf = np.clip(float_buf * gain * 8388607.0, -8388608, 8388607).astype('<i4')
    raw = np.frombuffer(int_buf.tobytes(), dtype=np.uint8).reshape(-1, 4)[:, :3]
    return raw.tobytes()


def _interleave_24bit_stereo(packed_L: bytes, packed_R: bytes,
                              n_frames: int) -> bytes:
    """Interleave two mono 24-bit packed buffers into stereo."""
    L_arr = np.frombuffer(packed_L, dtype=np.uint8).reshape(-1, 3)
    R_arr = np.frombuffer(packed_R, dtype=np.uint8).reshape(-1, 3)
    stereo = np.empty((n_frames, 6), dtype=np.uint8)
    stereo[:, 0:3] = L_arr
    stereo[:, 3:6] = R_arr
    return stereo.tobytes()


for name in STEM_NAMES:
    buf = stems[name]
    path = f"output/stems/wild_ones_v6_{name}.wav"

    peak = float(np.max(np.abs(buf))) if len(buf) > 0 else 1.0
    gain = min(1.0, 0.95 / peak) if peak > 0 else 1.0

    # v6: 24-bit stereo/mono output
    if buf.ndim == 2 and buf.shape[1] == 2:
        packed_L = _pack_24bit(buf[:, 0], gain)
        packed_R = _pack_24bit(buf[:, 1], gain)
        interleaved = _interleave_24bit_stereo(packed_L, packed_R, buf.shape[0])
        with wave.open(path, "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(3)
            wf.setframerate(SR)
            wf.writeframes(bytes(interleaved))
    else:
        if buf.ndim == 2:
            buf = buf[:, 0]
        packed = _pack_24bit(buf, gain)
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(3)
            wf.setframerate(SR)
            wf.writeframes(packed)

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

for name in STEM_NAMES:
    buf = stems[name]
    pan = STEM_PAN.get(name, 0.0)
    theta = (pan + 1.0) * 0.5 * (math.pi / 2.0)
    gain_l = math.cos(theta)
    gain_r = math.sin(theta)

    if buf.ndim == 2 and buf.shape[1] == 2:
        n = min(buf.shape[0], total_samples)
        mix_L[:n] += buf[:n, 0] * gain_l
        mix_R[:n] += buf[:n, 1] * gain_r
    else:
        if buf.ndim == 2:
            buf = buf[:, 0]
        n = min(len(buf), total_samples)
        mix_L[:n] += buf[:n] * gain_l
        mix_R[:n] += buf[:n] * gain_r

stereo = np.column_stack((mix_L, mix_R))

# -- Mastering chain (V6 Studio Edition) --
print("  Mastering chain (-10.5 LUFS target, PHI-tuned)...")
master_settings = MasterSettings(
    target_lufs=-10.5,
    ceiling_db=-0.3,
    eq_enabled=True,
    multiband=True,
    stereo_enhance=True,
    bass_boost_db=PHI,
    air_boost_db=1.0 / PHI,
    limiter_release_ms=50.0 * PHI,
)
master_L = auto_master(mix_L[:total_samples].tolist(), master_settings, SR)
master_R = auto_master(mix_R[:total_samples].tolist(), master_settings, SR)
print(f"    Input LUFS:  L={master_L.input_lufs:.1f}  R={master_R.input_lufs:.1f}")
print(f"    Output LUFS: L={master_L.output_lufs:.1f}  R={master_R.output_lufs:.1f}")
print(f"    Peak dB:     L={master_L.peak_db:.1f}  R={master_R.peak_db:.1f}")
print(f"    Stages:      {', '.join(master_L.stages_applied)}")

os.makedirs("output", exist_ok=True)
output_path = "output/wild_ones_v6.wav"

# v6: Apply PHI dithering before 24-bit export
print("  v6: Applying PHI dithering (24-bit, noise-shaped)...")
dithered_L = to_np(DITHER_ENGINE.apply_dither(master_L.signal, DITHER_CFG))
dithered_R = to_np(DITHER_ENGINE.apply_dither(master_R.signal, DITHER_CFG))

# v6: 24-bit stereo mastered export
packed_L = _pack_24bit(dithered_L, 1.0)
packed_R = _pack_24bit(dithered_R, 1.0)
interleaved = _interleave_24bit_stereo(packed_L, packed_R, total_samples)

with wave.open(output_path, "w") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(3)
    wf.setframerate(SR)
    wf.writeframes(bytes(interleaved))

# -- MIDI export --
print("  Exporting MIDI...")
os.makedirs("output/midi", exist_ok=True)

bass_events: list[NoteEvent] = []
for bar in range(total_bars):
    chord_idx = (bar // 2) % 4
    root_midi = [MIDI["Ab1"], MIDI["C2"], MIDI["F2"], MIDI["Db2"]][chord_idx]
    bass_events.append(NoteEvent(pitch=root_midi, start_beat=bar * 4,
                                 duration_beats=2.0, velocity=100))

hook_events: list[NoteEvent] = []
for section_start, section_len in [(SEC_CHORUS1, CHORUS1_BARS),
                                    (SEC_CHORUS2, CHORUS2_BARS),
                                    (SEC_VIP, VIP_DROP_BARS),
                                    (SEC_FINAL, FINAL_CHORUS_BARS)]:
    for rep in range(section_len // 8):
        base_beat = (section_start + rep * 8) * 4
        for beat_off, note_name, dur in HOOK_MELODY:
            hook_events.append(NoteEvent(
                pitch=MIDI[note_name],
                start_beat=base_beat + beat_off,
                duration_beats=dur,
                velocity=90,
            ))

chord_events: list[NoteEvent] = []
for section_start, section_len in [(SEC_CHORUS1, CHORUS1_BARS),
                                    (SEC_CHORUS2, CHORUS2_BARS),
                                    (SEC_VIP, VIP_DROP_BARS),
                                    (SEC_FINAL, FINAL_CHORUS_BARS)]:
    for bar in range(section_len):
        chord_idx = (bar // 2) % 4
        b = (section_start + bar) * 4
        chord_notes = [CHORD_Ab, CHORD_Cm, CHORD_Fm, CHORD_Db][chord_idx]
        for pitch in chord_notes:
            chord_events.append(NoteEvent(
                pitch=pitch, start_beat=b,
                duration_beats=2.0, velocity=82))

vocal_events: list[NoteEvent] = []
for section_start, section_len in [(SEC_BREAK, BREAK_BARS),
                                    (SEC_BRIDGE, BRIDGE_BARS)]:
    for bar in range(section_len):
        chord_idx = (bar // 2) % 4
        root_midi = [MIDI["Ab4"], MIDI["C5"], MIDI["F4"], MIDI["Db4"]][chord_idx]
        b = (section_start + bar) * 4
        vocal_events.append(NoteEvent(
            pitch=root_midi, start_beat=b,
            duration_beats=2.0, velocity=75))

# v5: growl MIDI
growl_events: list[NoteEvent] = []
for section_start, section_len in [(SEC_VIP, VIP_DROP_BARS),
                                    (SEC_FINAL, FINAL_CHORUS_BARS)]:
    for bar in range(section_len):
        chord_idx = (bar // 2) % 4
        root_midi = [MIDI["Ab2"], MIDI["C3"], MIDI["F2"], MIDI["Db3"]][chord_idx]
        b = (section_start + bar) * 4
        growl_events.append(NoteEvent(
            pitch=root_midi, start_beat=b,
            duration_beats=2.0, velocity=100))

midi_tracks = [
    ("Bass", bass_events),
    ("Hook", hook_events),
    ("Chords", chord_events),
    ("Vocal", vocal_events),
    ("Growl", growl_events),
]

midi_path = "output/midi/wild_ones_v6.mid"
write_midi_file(midi_tracks, midi_path, bpm=BPM)
total_notes = sum(len(evts) for _, evts in midi_tracks)
print(f"    {midi_path}  ({total_notes} notes)")


# ====================================================================
#  v5: ENHANCED ABLETON LIVE SET (Tier 1 features)
# ====================================================================
print("  Generating Enhanced Ableton Live project (v6)...")

stem_colors = {
    "DRUMS": 1, "BASS": 3, "GROWL": 4, "CHORDS": 12, "HOOK": 20,
    "PAD": 24, "VOCAL": 36, "ARP": 16, "RISER": 32,
    "FX": 40, "TEXTURE": 44, "DRONE": 28,
}

# Build send levels: [reverb_amount, delay_amount]
STEM_SENDS = {
    "DRUMS": [0.05, 0.10], "BASS": [0.0, 0.0],
    "GROWL": [0.10, 0.15], "CHORDS": [0.25, 0.20],
    "HOOK": [0.15, 0.25], "PAD": [0.35, 0.15],
    "VOCAL": [0.30, 0.10], "ARP": [0.20, 0.30],
    "RISER": [0.15, 0.10], "FX": [0.10, 0.10],
    "TEXTURE": [0.40, 0.20], "DRONE": [0.30, 0.05],
}

als_tracks = []

# ── Insight 34: Ninja Sound Gain Hierarchy ───────────────────────────
# DRUMS > VOCAL > BASS > HOOK > CHORDS > GROWL > PAD > ARP > rest
STEM_VOLUME_DB = {
    "DRUMS": 0.0, "VOCAL": -1.0, "BASS": -2.0, "HOOK": -3.5,
    "CHORDS": -4.0, "GROWL": -3.0, "PAD": -6.0, "ARP": -7.0,
    "RISER": -8.0, "FX": -6.0, "TEXTURE": -10.0, "DRONE": -9.0,
}

# ── Insight 129: Per-section send automation data ────────────────────
# (bar_start, bar_len, reverb_send_val)
_REVERB_SEND_SECTIONS = [
    (SEC_INTRO, INTRO_BARS, 0.40),
    (SEC_VERSE1, VERSE1_BARS, 0.25),
    (SEC_PRE1, PRECHORUS1_BARS, 0.30),
    (SEC_CHORUS1, CHORUS1_BARS, 0.15),
    (SEC_BREAK, BREAK_BARS, 0.45),
    (SEC_VERSE2, VERSE2_BARS, 0.25),
    (SEC_PRE2, PRECHORUS2_BARS, 0.30),
    (SEC_CHORUS2, CHORUS2_BARS, 0.12),
    (SEC_BRIDGE, BRIDGE_BARS, 0.50),
    (SEC_VIP, VIP_DROP_BARS, 0.10),
    (SEC_FINAL, FINAL_CHORUS_BARS, 0.15),
    (SEC_OUTRO, OUTRO_BARS, 0.45),
]

# Audio tracks with arrangement clip positioning + automations + sends
for idx, name in enumerate(STEM_NAMES):
    stem_abs = os.path.abspath(f"output/stems/wild_ones_v6_{name}.wav")
    # v5: proper arrangement clip with beat positioning
    clip_info = ALSClipInfo(
        path=stem_abs,
        start_beat=0.0,
        length_beats=total_bars * 4.0,
        warp_mode=0,
        gain=0.85,
        name=f"{name}_V6",
    )

    track_autos = []

    # v5: volume automation — CURVED fade in/out (insight 101, 123)
    vol_auto = ALSAutomation(
        parameter_name="Volume",
        points=[
            ALSAutomationPoint(time=0.0, value=0.0, curve=0.4),
            ALSAutomationPoint(time=INTRO_BARS * 4.0, value=1.0),
            ALSAutomationPoint(time=(total_bars - OUTRO_BARS) * 4.0, value=1.0, curve=-0.3),
            ALSAutomationPoint(time=total_bars * 4.0, value=0.0),
        ],
    )
    track_autos.append(vol_auto)

    # Insight 21, 117: LP filter sweep on builds (CHORDS, PAD, ARP)
    if name in ("CHORDS", "PAD", "ARP"):
        # Pre-chorus 1 LP sweep (closed → open)
        track_autos.append(make_lp_sweep_automation(
            "Filter Cutoff", SEC_PRE1 * 4.0, SEC_CHORUS1 * 4.0,
            closed_val=0.12, open_val=0.95, curve=0.4,
        ))
        # Pre-chorus 2 LP sweep (bigger build)
        track_autos.append(make_lp_sweep_automation(
            "Filter Cutoff", SEC_PRE2 * 4.0, SEC_CHORUS2 * 4.0,
            closed_val=0.08, open_val=1.0, curve=0.5,
        ))

    # Insight 116: Sine tremolo on ARP during bridge (emotional section)
    if name == "ARP":
        track_autos.append(make_sine_automation(
            "Volume_Mod", SEC_BRIDGE * 4.0, SEC_VIP * 4.0,
            min_val=0.3, max_val=0.8, cycles=4, resolution=32,
        ))

    # Insight 117: Sawtooth filter sweep on BASS during VIP
    if name in ("BASS", "GROWL"):
        track_autos.append(make_sawtooth_automation(
            "Filter Cutoff", SEC_VIP * 4.0, SEC_FINAL * 4.0,
            min_val=0.15, max_val=0.85, cycles=4, resolution=32,
        ))

    # Insight 129: Dynamic send automation (reverb)
    if name == "VOCAL":
        track_autos.append(make_section_send_automation(
            "Send 0", _REVERB_SEND_SECTIONS, total_bars,
        ))

    # Insight 126: Instant filter open on drops (break/continue points)
    if name == "CHORDS":
        for drop_bar in [SEC_CHORUS1, SEC_CHORUS2, SEC_VIP, SEC_FINAL]:
            track_autos.append(ALSAutomation(
                parameter_name="Filter_Reset",
                points=[
                    ALSAutomationPoint(time=drop_bar * 4.0 - 0.01, value=0.0),
                    ALSAutomationPoint(time=drop_bar * 4.0, value=1.0),
                ],
            ))

    als_tracks.append(ALSTrack(
        name=name,
        track_type="audio",
        color=stem_colors.get(name, 0),
        volume_db=STEM_VOLUME_DB.get(name, 0.0),
        pan=STEM_PAN.get(name, 0.0),
        clip_names=[name],
        clip_paths=[stem_abs],
        send_levels=STEM_SENDS.get(name, []),
        arrangement_clips=[clip_info],
        automations=track_autos,
    ))

# MIDI tracks
for track_name in ["Bass_MIDI", "Hook_MIDI", "Chords_MIDI",
                   "Vocal_MIDI", "Growl_MIDI"]:
    als_tracks.append(ALSTrack(
        name=track_name,
        track_type="midi",
        color=stem_colors.get(track_name.split("_")[0].upper(), 0),
        volume_db=-6.0,
        mute=True,
        device_names=["Serum 2"],
        clip_names=[track_name],
    ))

# Return tracks with send levels
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
    ALSScene(name="BRIDGE_GOLDEN", tempo=float(BPM)),
    ALSScene(name="VIP_DROP", tempo=float(BPM)),
    ALSScene(name="FINAL_CHORUS", tempo=float(BPM)),
    ALSScene(name="OUTRO", tempo=float(BPM)),
]

# v5: Cue points at every section boundary
als_cue_points = []
for sec_name, (bar_start, bar_len) in SECTION_MAP.items():
    als_cue_points.append(ALSCuePoint(
        name=sec_name,
        time=bar_start * 4.0,  # convert bars to beats
    ))
# Golden section marker
als_cue_points.append(ALSCuePoint(
    name="GOLDEN_SECTION",
    time=golden_section_bar * 4.0,
))

project = ALSProject(
    name="Wild_Ones_V6",
    bpm=float(BPM),
    tracks=als_tracks,
    scenes=als_scenes,
    notes="Wild Ones V6 (Electro House Remix — Studio Edition) | "
          "Ab major | 127 BPM | 440 Hz | 144 bars (Fibonacci!) | "
          "Chords: Ab-Cm-Fm-Db | Real Acapella + Hook + Growl VIP | "
          "24-bit | Granular + Noise + Saturation + DC + Dither | "
          "Golden Section: bar 89 (Bridge)",
    cue_points=als_cue_points,
)

os.makedirs("output/ableton", exist_ok=True)
als_path = "output/ableton/Wild_Ones_V6.als"
write_als(project, als_path)


# ====================================================================
#  v5: ABLETON BRIDGE + LINK SYNC STATUS
# ====================================================================
print()
print("  v5: Ableton Live integration status...")

# Try AbletonOSC bridge
try:
    bridge = AbletonBridge()
    bridge.connect()
    if bridge.is_connected:
        print("    AbletonOSC: CONNECTED — pushing project settings...")
        bridge.set_tempo(BPM)
        print(f"    Tempo synced to {BPM} BPM")
        bridge.disconnect()
    else:
        print("    AbletonOSC: Not connected (start AbletonOSC in Live)")
except Exception:
    print("    AbletonOSC: Not available (install AbletonOSC plugin)")

# Try Link sync
try:
    link = get_link(tempo=BPM)
    link.enable()
    snap = link.snap()
    print(f"    Link: enabled={snap['enabled']}, peers={snap['peers']}, "
          f"tempo={snap['tempo']}")
    link.disable()
except Exception:
    print("    Link: Not available (install aalink or link-python)")


# ====================================================================
#  SUMMARY
# ====================================================================

duration = total_samples / SR
file_size = os.path.getsize(output_path)
stem_dir_size = sum(
    os.path.getsize(os.path.join("output/stems", f))
    for f in os.listdir("output/stems")
    if f.startswith("wild_ones_v6_") and f.endswith(".wav")
)

print()
print("=" * 60)
print('  DUBFORGE -- "Wild Ones" V6 (Electro House Remix — Studio)')
print("=" * 60)
print(f"  Format:   24-bit WAV @ {SR} Hz")
print(f"  BPM:      {BPM}  |  Key: Ab major  |  Tuning: 440 Hz")
print(f"  Chords:   Ab - Cm - Fm - Db  (I - iii - vi - IV)")
print(f"  Duration: {duration:.1f}s "
      f"({int(duration // 60)}:{int(duration % 60):02d})")
print(f"  Bars:     {total_bars} (FIBONACCI!)  "
      f"(Golden Section Point: bar ~{golden_section_bar})")
print()
print("  V6 Studio Enhancements:")
print("    * 24-bit WAV export (stems + master) — studio-grade")
print("    * PHI dithering (noise-shaped) on master")
print("    * SaturationEngine (tape/tube) replaces inline saturator")
print("    * DC removal (highpass 5Hz) on all stems")
print("    * Granular shimmer texture (intro/bridge/outro)")
print("    * Granular dust (scatter mode, break section)")
print("    * Vinyl noise bed (intro/outro ambience)")
print("    * White noise air (chorus/VIP/final drops)")
print("    * Python mastering chain (-10.5 LUFS, PHI-tuned EQ + limiter)")
print("  V5 Features (inherited):")
print("    * 144 bars — Fibonacci structure with VIP Drop")
print("    * 12 stems — GROWL (resampled mid-bass) + TEXTURE (shimmer grain)")
print("    * Growl resampler bass (phi-modulated, waveshaped)")
print("    * Phi-harmonic sub reinforcement (8 partials)")
print("    * Beat repeat FX (phi grid in VIP, 1/8 grid in builds)")
print("    * Per-stem dynamics (transient shaping, compression, de-essing)")
print("    * Multi-technique stereo (Haas, psychoacoustic, freq split)")
print("    * Phi crossfades between all 12 section boundaries")
print("    * Enhanced ALS (cue points, automation, send routing)")
print("    * AbletonOSC bridge + Link sync integration")
print("  150 Insights Applied (Dojo × Subtronics × Live 12):")
print("    * Curved automation breakpoints (ALT+drag in Live 12)")
print("    * LP filter sweep automation on builds (Dojo insight 21)")
print("    * Ninja sound gain hierarchy (Dojo insights 26-34)")
print("    * Parallel saturation — Saturator Digital Clip (Dojo insight 38)")
print("    * Low Pass Gate on drone (Dojo insight 19)")
print("    * Sawtooth filter automation on VIP bass (Live 12 shapes)")
print("    * Sine tremolo modulation on bridge ARP (Live 12 insight 116)")
print("    * Dynamic reverb send automation per section (insight 129)")
print("    * Instant filter resets on drop boundaries (insight 126)")
print()
print(f"  Stems:    {len(STEM_NAMES)} tracks in output/stems/")
for name in STEM_NAMES:
    print(f"            - {name}")
print(f"  Stems:    {stem_dir_size / 1024 / 1024:.1f} MB total")
print(f"  Mixdown:  {output_path} ({file_size / 1024 / 1024:.1f} MB)")
print(f"  MIDI:     {midi_path} ({total_notes} notes)")
print(f"  Serum 2:  output/serum2/wild_ones_v6_patches.json")
print(f"  Presets:  output/presets/ ({len(fxp_presets)} .fxp + 1 .fxb bank)")
print(f"  Ableton:  {als_path} (cue points: {len(als_cue_points)}, "
      f"automations: {len(STEM_NAMES)})")
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
print(f"    Bridge         {BRIDGE_BARS:3d} bars  (GOLDEN SECTION — emotional pivot)")
print(f"    VIP Drop       {VIP_DROP_BARS:3d} bars  (GROWL BASS VIP — NEW)")
print(f"    Final Chorus   {FINAL_CHORUS_BARS:3d} bars  (CLIMAX)")
print(f"    Outro          {OUTRO_BARS:3d} bars")
print(f"    TOTAL         {total_bars:3d} bars (= Fibonacci 144)")
print()
print("  Song DNA Reference: Wild Ones (Flo Rida feat. Sia)")
print("    Ab major | 127 BPM | Ab-Cm-Fm-Db | Vocal range Eb4-C5")
print("    Vocals: studio acapella (Sia & Flo Rida)")
print("    Instrumental: 100% synthesized by DUBFORGE engines")
print("    V5: growl resampler + phi harmonics + beat repeat")
print("    V6: granular + noise + saturation + DC + dither + 24-bit")
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

    _stems_dst = _user_lib / "Samples" / "DUBFORGE" / "Wild_Ones_V6" / "Stems"
    _stems_dst.mkdir(parents=True, exist_ok=True)
    for _f in Path("output/stems").glob("wild_ones_v6_*.wav"):
        shutil.copy2(_f, _stems_dst / _f.name)
        _installed += 1
    print(f"    Stems:   {_installed} -> {_stems_dst}")

    _midi_dst = _user_lib / "Samples" / "DUBFORGE" / "Wild_Ones_V6" / "MIDI"
    _midi_dst.mkdir(parents=True, exist_ok=True)
    for _f in Path("output/midi").glob("wild_ones_v6*.mid"):
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

    # v5: Install remote script
    _rs_dst = _user_lib / "Remote Scripts" / "DUBFORGE"
    _rs_dst.mkdir(parents=True, exist_ok=True)
    _rs_src = Path("output/remote_scripts/DUBFORGE/__init__.py")
    if _rs_src.exists():
        shutil.copy2(_rs_src, _rs_dst / "__init__.py")
        _installed += 1
        print(f"    Remote:  1 -> {_rs_dst}")

    # v5: Install M4L device
    _m4l_dst = _user_lib / "Max for Live Devices" / "DUBFORGE"
    _m4l_dst.mkdir(parents=True, exist_ok=True)
    _m4l_src = Path("output/m4l/DUBFORGE_Control.js")
    if _m4l_src.exists():
        shutil.copy2(_m4l_src, _m4l_dst / "DUBFORGE_Control.js")
        _installed += 1
        print(f"    M4L:     1 -> {_m4l_dst}")

    print(f"    TOTAL:   {_installed} files installed")
else:
    print("    Ableton User Library not found (set ABLETON_USER_LIBRARY env var)")

# -- Open in Ableton Live --
print()
_ableton_running = False
_ableton_exe = None

try:
    _tasklist = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq Ableton Live*", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, timeout=5
    )
    if "Ableton Live" in _tasklist.stdout:
        _ableton_running = True
except Exception:
    pass

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

print("  Done. Wild Ones V6 Remix — Studio edition pipeline complete.")
print()
