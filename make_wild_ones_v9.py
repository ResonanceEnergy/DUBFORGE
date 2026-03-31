#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║  DUBFORGE — Wild Ones V9 (Electro House Remix — ULTIMATE Edition)  ║
║  Key: Ab major | BPM: 127 | Tuning: 440 Hz | Bars: 144 (Fibonacci)║
║  Chords: Ab - Cm - Fm - Db (I - iii - vi - IV)                    ║
║  Stems:  16 (4 NEW: WOBBLE, SUB, RIDDIM, FORMANT)                 ║
╚══════════════════════════════════════════════════════════════════════╝

V9 ULTIMATE — ALL ENGINE MODULES ACTIVE

NEW in V9 over V6:
  * 16 stems (was 12) — WOBBLE, SUB, RIDDIM, FORMANT added
  * Wobble bass synthesis (engine.wobble_bass) — LFO-driven filter wobble
  * Sub bass layer (engine.sub_bass) — dedicated sub-40Hz sine layer
  * Formant "talking" bass (engine.formant_synth) — vowel-shifting bass
  * Riddim engine patterns (engine.riddim_engine) — gap-based riddim bass
  * Multiband distortion (engine.multiband_distortion) — on growl/wobble
  * Wave folder (engine.wave_folder) — harmonic richness on bass
  * Intelligent EQ (engine.intelligent_eq) — spectral auto-balance on mix
  * Mastering chain (engine.mastering_chain) — replaces auto_master
  * Wavetable morph (engine.wavetable_morph) — evolving bridge textures
  * LFO matrix (engine.lfo_matrix) — modulation on pads/arps
  * Vocal processor (engine.vocal_processor) — pitch correction + FX
  * Pitch automation (engine.pitch_automation) — pitch dives on drops
  * Convolution reverb (engine.convolution) — room/plate IRs
  * Perc synth (engine.perc_synth) — custom electronic percussion
  * Karplus-Strong (engine.karplus_strong) — organic pluck sounds
  * TurboQuant (engine.turboquant) — phi-optimal compression on all stems
  * Sound palette (engine.sound_palette) — tonal consistency
  * Additive synth (engine.additive_synth) — harmonic texture layers
  * Chord progression (engine.chord_progression) — programmatic chord gen

INHERITED from V6:
  * 24-bit WAV export (stems + master)
  * PHI dithering (noise-shaped) on master
  * SaturationEngine (tape/tube) on bass/growl/hook
  * DC removal (highpass 5Hz) on all stems
  * Granular shimmer texture (intro/bridge/outro)
  * Granular dust (scatter mode, break)
  * Vinyl noise bed (intro/outro ambience)
  * White noise air (chorus/VIP/final drops)
  * 144 bars — Fibonacci structure with VIP Drop
  * Growl resampler bass (phi-modulated, waveshaped)
  * Phi-harmonic sub reinforcement (8 partials)
  * Beat repeat FX (phi grid in VIP, 1/8 grid in builds)
  * Per-stem dynamics (transient shaping, compression, de-essing)
  * Multi-technique stereo (Haas, psychoacoustic, freq split, mid-side)
  * Phi crossfades between all 12 section boundaries
  * Enhanced ALS (cue points, automation, send routing)
  * AbletonOSC bridge + Link sync integration
  * 150 Dojo insights applied

Usage:
    python make_wild_ones_v9.py

Requires:
    - GALATCIA samples at C:\\dev\\DUBFORGE GALATCIA\\
    - Real acapella: Flo-Rida-ft-Sia-Wild-Ones-Studio-Acapella.mp3
    - DUBFORGE engine modules (all 50+ active)
"""

# ====================================================================
#  IMPORTS
# ====================================================================
import os
import sys
import math
import wave
import pickle
import subprocess
import json
import numpy as np

# Force line-buffered stdout so progress is visible when piped
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(line_buffering=True)

# -- Core synthesis (matching v6 module paths) --
from engine.bass_oneshot import BassPreset, synthesize_bass
from engine.pluck_synth import PluckPreset, synthesize_pluck
from engine.pad_synth import PadPreset, synthesize_pad
from engine.arp_synth import ArpSynthPreset as ArpPreset, synthesize_arp
from engine.fm_synth import FMPatch, FMOperator, render_fm

# -- v9: NEW synthesis engines --
from engine.wobble_bass import WobblePreset, synthesize_wobble
from engine.sub_bass import SubBassPreset, synthesize_sub_bass
from engine.formant_synth import FormantPreset, synthesize_formant
from engine.riddim_engine import RiddimPreset, generate_riddim_minimal
from engine.additive_synth import AdditivePatch, render_additive, phi_partials
from engine.perc_synth import PercPreset, synthesize_perc
from engine.karplus_strong import KarplusStrongPatch, render_ks
from engine.wavetable_morph import MorphPreset, morph_wavetable
from engine.sound_palette import PalettePreset, generate_palette, render_palette_tone
from engine.chord_progression import build_progression

# -- Serum 2 & presets (v6 approach) --
from engine.serum2 import build_dubstep_patches
from engine.fxp_writer import FXPPreset, FXPBank, VSTParam, write_fxp, write_fxb, write_preset_manifest

# -- Audio math & DSP --
# (fade_in, fade_out, lowpass, highpass, mix_into, samples_for,
#  phi_crossfade_sections defined as local helpers below)

# -- FX processing (corrected module paths) --
from engine.sidechain import apply_sidechain, SidechainPreset
from engine.reverb_delay import apply_hall, apply_room, ReverbDelayPreset
from engine.stereo_imager import (
    apply_haas, apply_psychoacoustic, apply_frequency_split,
    apply_mid_side, StereoPreset,
)
from engine.dynamics import (
    compress, CompressorSettings, analyze_dynamics, limit,
)
from engine.dynamics_processor import DynamicsProcessor, DeEsserConfig
from engine.beat_repeat import BeatRepeatPatch as BeatRepeatPreset, apply_beat_repeat
from engine.glitch_engine import GlitchPreset, synthesize_stutter
from engine.noise_generator import NoisePreset, synthesize_noise
from engine.granular_synth import GranularPreset, synthesize_granular
from engine.saturation import SatConfig, SaturationEngine
from engine.dc_remover import DCRemover
from engine.dither import DitherConfig, DitherEngine

# -- v9: NEW FX processing engines --
from engine.multiband_distortion import MultibandDistPreset, apply_multiband_distortion
from engine.wave_folder import fold, WaveFolderPatch
from engine.intelligent_eq import auto_eq
from engine.lfo_matrix import LFOPreset, generate_lfo, apply_lfo
from engine.vocal_processor import VocalPreset, apply_vocal_processing
from engine.pitch_automation import PitchAutoPreset, apply_pitch_automation
from engine.convolution import ConvolutionPreset, apply_convolution

# -- v9: Mastering chain (replaces auto_master) --
from engine.mastering_chain import (
    MasterSettings as MCMasterSettings,
    MasterReport, master as master_chain,
)
# Keep auto_master for legacy compatibility
from engine.auto_master import auto_master, MasterSettings, MasterResult

# -- v9: TurboQuant compression --
from engine.turboquant import (
    compress_audio_buffer, CompressedAudioBuffer, TurboQuantConfig,
)

# -- Audio I/O --
from engine.midi_export import NoteEvent, write_midi_file

# -- Ableton --
from engine.als_generator import (
    ALSProject, ALSTrack, ALSScene, ALSCuePoint,
    ALSClipInfo, ALSAutomation, ALSAutomationPoint,
    write_als,
    make_lp_sweep_automation, make_sine_automation,
    make_sawtooth_automation, make_section_send_automation,
)
from engine.ableton_bridge import AbletonBridge
from engine.link_sync import LinkSync, get_link


# ====================================================================
#  CONSTANTS
# ====================================================================
PHI = (1.0 + math.sqrt(5.0)) / 2.0          # 1.618...
SR = 44100                                    # Sample rate
BPM = 127                                     # Wild Ones BPM
BAR = 60.0 / BPM * 4                         # 1 bar in seconds
BEAT = 60.0 / BPM                            # 1 beat in seconds

# -- Key: Ab major (Ab, Bb, C, Db, Eb, F, G) --
KEY_FREQS = {
    "Ab1": 51.91, "Bb1": 58.27, "C2": 65.41, "Db2": 69.30,
    "Eb2": 77.78, "F2": 87.31, "G2": 98.00,
    "Ab2": 103.83, "Bb2": 116.54, "C3": 130.81, "Db3": 138.59,
    "Eb3": 155.56, "F3": 174.61, "G3": 196.00,
    "Ab3": 207.65, "Bb3": 233.08, "C4": 261.63, "Db4": 277.18,
    "Eb4": 311.13, "F4": 349.23, "G4": 392.00,
    "Ab4": 415.30, "Bb4": 466.16, "C5": 523.25, "Db5": 554.37,
    "Eb5": 622.25, "F5": 698.46,
}

MIDI = {
    "Ab1": 44, "Bb1": 46, "C2": 48, "Db2": 49,
    "Eb2": 51, "F2": 53, "G2": 55,
    "Ab2": 56, "Bb2": 58, "C3": 60, "Db3": 61,
    "Eb3": 63, "F3": 65, "G3": 67,
    "Ab3": 68, "Bb3": 70, "C4": 72, "Db4": 73,
    "Eb4": 75, "F4": 77, "G4": 79,
    "Ab4": 80, "Bb4": 82, "C5": 84, "Db5": 85,
    "Eb5": 87, "F5": 89,
}

# Chord voicings (MIDI)
CHORD_Ab = [MIDI["Ab3"], MIDI["C4"], MIDI["Eb4"]]        # I
CHORD_Cm = [MIDI["C3"], MIDI["Eb3"], MIDI["G3"]]         # iii
CHORD_Fm = [MIDI["F3"], MIDI["Ab3"], MIDI["C4"]]         # vi
CHORD_Db = [MIDI["Db3"], MIDI["F3"], MIDI["Ab3"]]        # IV

CHORD_VOICINGS = [CHORD_Ab, CHORD_Cm, CHORD_Fm, CHORD_Db]

# ── DSP Presets ──────────────────────────────────────────────────────
SC_PUMP = SidechainPreset("Pump", "pump", bpm=BPM, depth=0.70,
                          attack_ms=5, release_ms=180)
SC_HARD = SidechainPreset("Hard", "pump", bpm=BPM, depth=0.85,
                          attack_ms=2, release_ms=120)

HALL_VERB = ReverbDelayPreset(name="Hall", effect_type="hall", decay_time=3.2,
                              damping=0.4, mix=0.25, pre_delay_ms=30)
ROOM_VERB = ReverbDelayPreset(name="Room", effect_type="room", decay_time=1.2,
                              damping=0.6, mix=0.18, pre_delay_ms=10)

STEREO_PAD = StereoPreset(name="PadStereo", image_type="haas",
                          delay_ms=12.0, width=1.2)
STEREO_CHORD = StereoPreset(name="ChordStereo", image_type="psychoacoustic",
                            width=1.4)
STEREO_ARP = StereoPreset(name="ArpStereo", image_type="frequency_split",
                          crossover_hz=2000.0, width=1.1)
STEREO_HOOK = StereoPreset(name="HookStereo", image_type="mid_side",
                           width=0.9)

COMP_BASS = CompressorSettings(threshold_db=-12, ratio=4.0,
                               attack_ms=10, release_ms=80)
COMP_VOCAL = CompressorSettings(threshold_db=-15, ratio=3.5,
                                attack_ms=8, release_ms=100)
COMP_DRUMS = CompressorSettings(threshold_db=-8, ratio=3.0,
                                attack_ms=5, release_ms=60)

DEESS = DeEsserConfig(frequency=6500, threshold_db=-20, reduction_db=-6)

DYNPROC = DynamicsProcessor(sample_rate=SR)
SAT_ENGINE = SaturationEngine()
DC_ENGINE = DCRemover(sample_rate=SR)
DITHER_ENGINE = DitherEngine()
DITHER_CFG = DitherConfig(dither_type="tpdf", target_bits=24, noise_shaping=True)

# -- v9: Multiband distortion presets --
MBDIST_GROWL = MultibandDistPreset(
    name="GrowlMBDist", dist_type="tube",
    low_drive=0.2, mid_drive=0.6, high_drive=0.4,
    crossover_low=150.0, crossover_high=2500.0,
    output_gain=0.75, mix=0.35,
)
MBDIST_WOBBLE = MultibandDistPreset(
    name="WobbleMBDist", dist_type="tape",
    low_drive=0.3, mid_drive=0.5, high_drive=0.3,
    crossover_low=120.0, crossover_high=2000.0,
    output_gain=0.80, mix=0.30,
)

# -- v9: Convolution reverb presets --
CONV_PLATE = ConvolutionPreset(
    name="V9Plate", conv_type="plate_ir",
    plate_size=1.2, plate_damping=0.4, plate_brightness=0.7,
    ir_length_ms=800.0, ir_decay=0.92, mix=0.25,
)
CONV_ROOM = ConvolutionPreset(
    name="V9Room", conv_type="room_ir",
    room_length_m=12.0, room_width_m=9.0, room_height_m=4.0,
    wall_absorption=0.35, ir_length_ms=600.0, ir_decay=0.90, mix=0.20,
)

# -- v9: LFO presets --
LFO_PAD_FILTER = LFOPreset(
    name="PadFilter", lfo_type="sine",
    rate_hz=0.15, depth=0.4, phase_offset=0.0,
)
LFO_ARP_PAN = LFOPreset(
    name="ArpPan", lfo_type="triangle",
    rate_hz=0.25, depth=0.3, phase_offset=0.0,
)

# -- v9: Vocal processor preset --
VOCAL_FX = VocalPreset(
    name="V9Vocal", vocal_type="pitch_correct",
    scale_root=8, correction_speed=0.6,
    lo_cut_hz=200.0, hi_cut_hz=4000.0,
    saturation=0.15, mix=0.7,
)

# -- v9: Pitch automation presets --
PITCH_DIVE = PitchAutoPreset(
    name="DropDive", auto_type="dive",
    start_semitones=0.0, end_semitones=-12.0,
    duration_s=0.5, curve_exp=2.0,
)
PITCH_RISE = PitchAutoPreset(
    name="BuildRise", auto_type="rise",
    start_semitones=-7.0, end_semitones=0.0,
    duration_s=1.0, curve_exp=1.5,
)


# ====================================================================
#  STEM NAMES (16 stems — 4 NEW in v9)
# ====================================================================
STEM_NAMES = [
    "DRUMS", "BASS", "GROWL", "CHORDS", "HOOK", "PAD",
    "VOCAL", "ARP", "RISER", "FX", "TEXTURE", "DRONE",
    # v9 NEW stems:
    "WOBBLE", "SUB", "RIDDIM", "FORMANT",
]

STEM_PAN = {
    "DRUMS": 0.0, "BASS": 0.0, "GROWL": 0.05,
    "CHORDS": 0.15, "HOOK": -0.10, "PAD": 0.20,
    "VOCAL": 0.0, "ARP": -0.25, "RISER": 0.0,
    "FX": 0.30, "TEXTURE": -0.35, "DRONE": -0.15,
    # v9:
    "WOBBLE": -0.05, "SUB": 0.0, "RIDDIM": 0.10,
    "FORMANT": -0.08,
}


# ====================================================================
#  GALATCIA SAMPLE PATHS
# ====================================================================
GALATCIA_ROOT = r"C:\dev\DUBFORGE GALATCIA"
SAMPLE_ROOT = os.path.join(GALATCIA_ROOT, "Samples", "Samples")
ACAPELLA_PATH = os.path.join(
    GALATCIA_ROOT, "Flo-Rida-ft-Sia-Wild-Ones-Studio-Acapella.mp3"
)


# ====================================================================
#  HELPERS
# ====================================================================
def to_np(x):
    """Convert any array-like to float64 numpy array."""
    if isinstance(x, np.ndarray):
        return x.astype(np.float64)
    return np.array(x, dtype=np.float64)


def samples_for(beats: float) -> int:
    return int(beats * BEAT * SR)


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


def highpass(signal: np.ndarray, cutoff: float = 0.3) -> np.ndarray:
    return signal - lowpass(signal, cutoff)


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
    t = np.linspace(0.0, 1.0, n)
    curve = 1.0 - (1.0 - t) ** PHI
    out[start:end] *= curve
    return out


def build_gain(bar_idx: int, total_bars: int,
               start: float = 0.0, end: float = 1.0) -> float:
    """Linear gain ramp over bars."""
    t = bar_idx / max(total_bars - 1, 1)
    return start + (end - start) * t


def load_sample(path: str) -> np.ndarray:
    """Load a WAV sample, return float64 mono."""
    try:
        import soundfile as sf
        data, sr = sf.read(path, dtype="float64")
        if data.ndim == 2:
            data = data.mean(axis=1)
        if sr != SR:
            # Simple resample
            ratio = SR / sr
            indices = np.arange(0, len(data), 1.0 / ratio)
            indices = indices[indices < len(data)].astype(int)
            data = data[indices]
        return data
    except Exception:
        return np.zeros(SR)


def load_acapella() -> np.ndarray:
    """Load acapella MP3 as float64 mono."""
    try:
        import soundfile as sf
        data, sr = sf.read(ACAPELLA_PATH, dtype="float64")
        if data.ndim == 2:
            data = data.mean(axis=1)
        if sr != SR:
            ratio = SR / sr
            indices = np.arange(0, len(data), 1.0 / ratio)
            indices = indices[indices < len(data)].astype(int)
            data = data[indices]
        return data
    except Exception:
        return np.zeros(int(SR * 240))


def slice_acapella(bar_start: int, bar_count: int) -> np.ndarray:
    """Slice acapella from bar offset."""
    s = int(bar_start * BAR * SR)
    e = s + int(bar_count * BAR * SR)
    segment = ACAPELLA[s:e]
    if len(segment) < int(bar_count * BAR * SR):
        segment = np.pad(segment, (0, int(bar_count * BAR * SR) - len(segment)))
    return segment


# ====================================================================
#  ACAPELLA MAP (bar offsets into acapella file)
# ====================================================================
# These map section names to (start_bar, end_bar) in the source acapella
ACAP_MAP = {
    "INTRO": (0, 8),
    "VERSE1": (8, 16),
    "PRECHORUS1": (16, 24),
    "CHORUS1": (24, 40),
    "BREAK": (40, 48),
    "VERSE2": (48, 56),
    "PRECHORUS2": (56, 64),
    "CHORUS2": (64, 80),
    "BRIDGE": (80, 88),
    "VIP": (24, 40),          # Reuse chorus vocal for VIP
    "FINAL": (64, 80),        # Reuse chorus 2 vocal for final
    "OUTRO": (80, 96),
}


# ====================================================================
#  HOOK MELODY
# ====================================================================
HOOK_MELODY = [
    (0.0, "Eb4", 1.0), (1.0, "F4", 0.5), (1.5, "Ab4", 1.5),
    (3.0, "Bb4", 1.0), (4.0, "Ab4", 0.5), (4.5, "F4", 1.0),
    (5.5, "Eb4", 0.5), (6.0, "C4", 1.5), (7.5, "Db4", 0.5),
    (8.0, "Eb4", 1.0), (9.0, "F4", 1.0), (10.0, "Ab4", 1.0),
    (11.0, "C5", 1.0), (12.0, "Bb4", 2.0), (14.0, "Ab4", 1.0),
    (15.0, "F4", 1.0), (16.0, "Eb4", 2.0), (18.0, "C4", 1.5),
    (19.5, "Db4", 0.5), (20.0, "Eb4", 2.0), (22.0, "F4", 1.0),
    (23.0, "Ab4", 1.0), (24.0, "Bb4", 1.5), (25.5, "Ab4", 0.5),
    (26.0, "F4", 1.0), (27.0, "Eb4", 1.0), (28.0, "Db4", 1.0),
    (29.0, "C4", 1.5), (30.5, "Db4", 0.5), (31.0, "Eb4", 1.0),
]


# ====================================================================
#  MAIN SCRIPT
# ====================================================================
print()
print("=" * 68)
print('  DUBFORGE — "Wild Ones" V9 (ULTIMATE Edition)')
print("  19 NEW engine modules | 16 stems | TurboQuant | Mastering Chain")
print("=" * 68)
print()

ACAPELLA = load_acapella()
print(f"  Acapella loaded: {len(ACAPELLA)/SR:.1f}s")


# ====================================================================
#  SOUND DESIGN — STEPS 1-16 (INHERITED FROM V6)
# ====================================================================
print()
print("  ┌─ SOUND DESIGN ─────────────────────────────────────────────┐")

# ── Step 1: Serum 2 Base Patches ─────────────────────────────────────
print("  │ Step 1:  Serum 2 patches (bass, lead, pad, pluck)")
serum_patches = build_dubstep_patches()
os.makedirs("output/serum2", exist_ok=True)
with open("output/serum2/wild_ones_v9_patches.json", "w") as f:
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

bank = FXPBank(name="WILD_ONES_V9_BANK", presets=list(fxp_presets.values()))
write_fxb(bank, "output/presets/WILD_ONES_V9_BANK.fxb")
write_preset_manifest(fxp_presets, "output/presets")
print(f"         {len(fxp_presets)} .fxp presets + 1 .fxb bank written")

# ── Step 2: GALATCIA drum samples ───────────────────────────────────
print("  │ Step 2:  GALATCIA drum kit (kick, snare, hats, clap)")

kick_path = os.path.join(SAMPLE_ROOT, "kick_thick.wav")
snare_path = os.path.join(SAMPLE_ROOT, "snare_crack.wav")
hat_closed_path = os.path.join(SAMPLE_ROOT, "hat_closed.wav")
hat_open_path = os.path.join(SAMPLE_ROOT, "hat_open.wav")
clap_path = os.path.join(SAMPLE_ROOT, "clap.wav")

kick = load_sample(kick_path)
snare = load_sample(snare_path)
hat_closed = load_sample(hat_closed_path)
hat_open = load_sample(hat_open_path)
clap = load_sample(clap_path)

# ── Step 3: Bass — main synthesis ────────────────────────────────────
print("  │ Step 3:  Bass synthesis (saw bass, Ab1)")
bass_main = to_np(synthesize_bass(BassPreset(
    name="WO9Bass", bass_type="saw", frequency=KEY_FREQS["Ab1"],
    duration_s=BAR * 2, attack_s=0.005, release_s=0.15,
)))

# ── Step 4: Phi-harmonic sub reinforcement (8 partials) ─────────────
print("  │ Step 4:  Phi-harmonic sub (8 partials)")
phi_sub = np.zeros(int(BAR * 2 * SR))
for k in range(1, 9):
    freq = KEY_FREQS["Ab1"] * (PHI ** (k - 1))
    if freq > 15000:
        break
    amp = 1.0 / (k * PHI)
    t = np.arange(len(phi_sub)) / SR
    phi_sub += amp * np.sin(2.0 * np.pi * freq * t)
phi_sub *= 0.15 / max(np.max(np.abs(phi_sub)), 1e-10)

# ── Step 5: Growl resampler ──────────────────────────────────────────
print("  │ Step 5:  Growl resampler (phi-mod, waveshape)")
growl_base = to_np(synthesize_bass(BassPreset(
    name="WO9Growl", bass_type="growl", frequency=KEY_FREQS["Ab2"],
    duration_s=BAR * 2, attack_s=0.002, release_s=0.08,
)))
# Waveshape: soft clip
growl_base = np.tanh(growl_base * 2.5)
# Phi-modulate: detune by phi ratio
t_growl = np.arange(len(growl_base)) / SR
growl_mod = 0.3 * np.sin(2.0 * np.pi * (KEY_FREQS["Ab2"] / PHI) * t_growl)
growl_base = growl_base * (1.0 + 0.3 * growl_mod)
growl_base *= 0.4

# ── Step 6: Supersaw chords ─────────────────────────────────────────
print("  │ Step 6:  Supersaw chord stabs (Ab-Cm-Fm-Db)")
SAW_STABS = []
for chord_midi in CHORD_VOICINGS:
    stab = np.zeros(int(BAR * 2 * SR))
    for midi_note in chord_midi:
        freq = 440.0 * (2.0 ** ((midi_note - 69) / 12.0))
        t = np.arange(len(stab)) / SR
        for detune in [-0.12, -0.06, 0.0, 0.06, 0.12]:
            stab += 0.12 * np.sin(2.0 * np.pi * freq * (1 + detune * 0.01) * t)
    stab = fade_in(stab, duration_s=0.005)
    stab = fade_out(stab, duration_s=0.05)
    stab *= 0.35
    SAW_STABS.append(stab)

# ── Step 7: Hook melody (pluck + FM) ────────────────────────────────
print("  │ Step 7:  Hook melody (pluck + FM synthesis)")


def hook_melody_render(bars: int, pluck_gain: float = 0.3,
                       fm_gain: float = 0.2) -> np.ndarray:
    """Render hook melody for given number of bars."""
    out = np.zeros(int(bars * BAR * SR))
    for beat_off, note_name, dur in HOOK_MELODY:
        if beat_off >= bars * 4:
            break
        freq = KEY_FREQS.get(note_name, 440.0)
        n_samp = int(dur * BEAT * SR)
        offset = int(beat_off * BEAT * SR)
        if offset + n_samp > len(out):
            n_samp = len(out) - offset
        if n_samp <= 0:
            continue

        pluck = to_np(synthesize_pluck(PluckPreset(
            name="HookPluck", pluck_type="string",
            frequency=freq, duration_s=dur * BEAT,
            brightness=0.7, decay_s=dur * BEAT * 0.8,
        )))[:n_samp]
        mix_into(out, pluck, offset, gain=pluck_gain)

        fm = to_np(render_fm(FMPatch(
            name=f"HookFM_{i}",
            operators=[
                FMOperator(freq_ratio=1.0, amplitude=1.0, mod_index=2.0,
                           envelope=(0.002, 0.08, 0.0, 0.15)),
                FMOperator(freq_ratio=PHI, amplitude=0.6, mod_index=1.5,
                           envelope=(0.002, 0.10, 0.0, 0.18)),
            ],
            algorithm=0, master_gain=0.60,
        ), freq=freq, duration=dur * BEAT))[:n_samp]
        mix_into(out, fm, offset, gain=fm_gain)
    return out


# ── Step 8: Acapella processing ──────────────────────────────────────
print("  │ Step 8:  Acapella slicing (vocal chops)")
# Pre-chop some vocal stutter FX
chop_length = int(BEAT * 0.5 * SR)
chop_stutter = ACAPELLA[int(24 * BAR * SR):int(24 * BAR * SR) + chop_length]
chop_ee = ACAPELLA[int(38 * BAR * SR):int(38 * BAR * SR) + int(BEAT * SR)]

# ── Step 9: Pads (lush + dark) ──────────────────────────────────────
print("  │ Step 9:  Pad synthesis (lush + dark)")
lush_pad = to_np(synthesize_pad(PadPreset(
    name="WO9Lush", pad_type="warm",
    frequency=KEY_FREQS["Ab3"], duration_s=BAR * 16,
    attack_s=1.5, release_s=3.0, brightness=0.4,
)))

dark_pad = to_np(synthesize_pad(PadPreset(
    name="WO9Dark", pad_type="dark",
    frequency=KEY_FREQS["Ab2"], duration_s=BAR * 16,
    attack_s=2.0, release_s=4.0, brightness=0.2,
)))

# ── Step 10: Texture layers (granular) ───────────────────────────────
print("  │ Step 10: Granular textures (shimmer + dust)")
granular_shimmer = to_np(synthesize_granular(GranularPreset(
    name="V9Shimmer", grain_type="shimmer",
    frequency=KEY_FREQS["Ab4"], duration_s=BAR * 16,
    grain_size_ms=80, grain_density=0.6, pitch_spread=0.3,
    attack_s=1.5, release_s=2.0, brightness=0.45,
    reverb_amount=0.55, scatter_amount=0.2,
)))

granular_dust = to_np(synthesize_granular(GranularPreset(
    name="V9Dust", grain_type="scatter",
    frequency=KEY_FREQS["Eb3"], duration_s=BAR * 8,
    grain_size_ms=30, grain_density=0.3, pitch_spread=0.5,
    attack_s=0.5, release_s=1.0, brightness=0.30,
    scatter_amount=0.6,
)))

# ── Step 11: Arp synthesis ───────────────────────────────────────────
print("  │ Step 11: Arp synthesis (shimmer + pluck)")
arp_shimmer = to_np(synthesize_arp(ArpPreset(
    name="V9ArpShim", arp_type="acid",
    base_freq=KEY_FREQS["Ab3"], duration_s=BAR * 4,
    step_count=16, filter_cutoff=0.35, resonance=0.45,
    octave_range=2,
)))

arp_pluck = to_np(synthesize_arp(ArpPreset(
    name="V9ArpPlk", arp_type="pulse",
    base_freq=KEY_FREQS["Eb4"], duration_s=BAR * 4,
    step_count=16, filter_cutoff=0.50, resonance=0.35,
    octave_range=2,
)))

# ── Step 12: Risers / impacts ────────────────────────────────────────
print("  │ Step 12: Risers + impacts (pitch, harmonic, noise)")
pitch_riser = to_np(synthesize_noise(NoisePreset(
    name="PitchRiser", noise_type="white",
    duration_s=BAR * 8, brightness=0.6, modulation=0.3, mod_rate=0.5,
)))
pitch_riser = lowpass(pitch_riser, cutoff=0.15)
pitch_riser = fade_in(pitch_riser, duration_s=BAR * 6)

harmonic_riser = to_np(synthesize_noise(NoisePreset(
    name="HarmRiser", noise_type="pink",
    duration_s=BAR * 8, brightness=0.5, modulation=0.4, mod_rate=0.3,
)))

noise_riser = to_np(synthesize_noise(NoisePreset(
    name="NoiseRiser", noise_type="white",
    duration_s=BAR * 8,
)))
noise_riser = fade_in(noise_riser, duration_s=BAR * 7)
noise_riser *= 0.15

# Impact FX
sub_boom = to_np(synthesize_bass(BassPreset(
    name="SubBoom", bass_type="saw", frequency=35.0,
    duration_s=1.5, attack_s=0.001, release_s=1.2,
)))
sub_boom *= 0.5

cinema_hit = to_np(synthesize_noise(NoisePreset(
    name="CinemaHit", noise_type="brown", duration_s=0.8,
    brightness=0.55, attack_s=0.001, release_s=0.6,
)))
cinema_hit *= 0.4

impact_boom = render_fm(FMPatch(
    name="ImpactBoom",
    operators=[
        FMOperator(freq_ratio=1.0, amplitude=1.0, mod_index=8.0,
                   envelope=(0.001, 0.3, 0.0, 0.3)),
        FMOperator(freq_ratio=PHI, amplitude=0.8, mod_index=4.0,
                   envelope=(0.001, 0.2, 0.0, 0.4)),
    ],
    algorithm=0, master_gain=0.70,
), freq=40.0, duration=0.6)
impact_boom = to_np(impact_boom)
impact_boom = fade_out(impact_boom, duration_s=0.5)
impact_boom *= 0.3

reverse_hit = cinema_hit[::-1].copy()
reverse_hit = fade_in(reverse_hit, duration_s=0.3)

# ── Step 13: Drones ──────────────────────────────────────────────────
print("  │ Step 13: Drone synthesis (Ab1 + sub harmonics)")
drone = np.zeros(int(BAR * 16 * SR))
t_drone = np.arange(len(drone)) / SR
for k, amp in [(1, 0.3), (PHI, 0.15), (2, 0.10), (3, 0.05)]:
    drone += amp * np.sin(2.0 * np.pi * KEY_FREQS["Ab1"] * k * t_drone)
drone *= 0.2

# ── Step 14: FM synthesis hits ───────────────────────────────────────
print("  │ Step 14: FM synth hits")
fm_hit = to_np(render_fm(FMPatch(
    name="FMAccent",
    operators=[
        FMOperator(freq_ratio=1.0, amplitude=1.0, mod_index=3.5,
                   envelope=(0.002, 0.08, 0.0, 0.15)),
        FMOperator(freq_ratio=2.0, amplitude=0.7, mod_index=2.0,
                   envelope=(0.002, 0.10, 0.0, 0.18)),
    ],
    algorithm=0, master_gain=0.60,
), freq=KEY_FREQS["Ab3"], duration=BEAT * 0.5))
fm_hit = fade_out(fm_hit, duration_s=BEAT * 0.3)
fm_hit *= 0.25

# ── Step 15: v6 — Granular shimmer + dust ────────────────────────────
print("  │ Step 15: Additional noise layers (vinyl, white air)")
vinyl_noise = to_np(synthesize_noise(NoisePreset(
    name="VinylNoise", noise_type="pink", duration_s=BAR * 16,
)))
vinyl_noise = lowpass(vinyl_noise, cutoff=0.03)
vinyl_noise *= 0.08

white_air = to_np(synthesize_noise(NoisePreset(
    name="WhiteAir", noise_type="white", duration_s=BAR * 16,
)))
white_air = highpass(white_air, cutoff=0.25)
white_air *= 0.05

# ── Step 16: v6 — Stutter / beat repeat / FX presets ─────────────────
print("  │ Step 16: Beat repeat presets + stutter + FX")
BEAT_REPEAT_BUILD = BeatRepeatPreset(
    name="BuildBR", grid="1/8", repeats=4,
    decay=0.618, pitch_shift=0, reverse_probability=0.0,
    gate=0.8, mix=0.35, probability=0.7,
)
BEAT_REPEAT_VIP = BeatRepeatPreset(
    name="VipBR", grid="phi", repeats=8,
    decay=0.382, pitch_shift=2, reverse_probability=0.15,
    gate=0.6, mix=0.50, probability=0.85,
)

stutter_fx = to_np(synthesize_stutter(
    GlitchPreset(name="StutFX", glitch_type="stutter",
                 duration_s=BEAT * 2, rate=8, depth=0.7, mix=0.9),
    SR,
))

pitch_dive = to_np(synthesize_bass(BassPreset(
    name="PitchDive", bass_type="saw", frequency=200,
    duration_s=BEAT * 2, attack_s=0.001, release_s=BEAT * 1.5,
)))
# Pitch envelope: sweep down
t_dive = np.arange(len(pitch_dive)) / SR
pitch_dive *= np.sin(2.0 * np.pi * 200.0 *
                     np.exp(-3.0 * t_dive / (BEAT * 2)) * t_dive)
pitch_dive *= 0.3

tape_stop = pitch_dive[::-1].copy()
tape_stop = fade_in(tape_stop, duration_s=0.1)
tape_stop = fade_out(tape_stop, duration_s=BEAT)
tape_stop *= 0.25


# ====================================================================
#  SOUND DESIGN — STEPS 17-28 (NEW IN V9)
# ====================================================================
print("  │")
print("  │ ── V9 NEW ENGINE MODULES ──────────────────────────────────")

# ── Step 17: Wobble Bass (engine.wobble_bass) ────────────────────────
print("  │ Step 17: Wobble bass (LFO-driven filter wobble)")
wobble_drop = to_np(synthesize_wobble(WobblePreset(
    name="WO9_WobbleDrop", wobble_type="classic",
    frequency=KEY_FREQS["Ab1"], duration_s=BAR * 4,
    lfo_rate=BPM / 60.0 * 2.0, lfo_depth=0.85,
    filter_cutoff=0.7, resonance=0.55,
    distortion=0.2, sub_mix=0.35,
)))

wobble_slow = to_np(synthesize_wobble(WobblePreset(
    name="WO9_WobbleSlow", wobble_type="classic",
    frequency=KEY_FREQS["Ab1"], duration_s=BAR * 4,
    lfo_rate=BPM / 60.0, lfo_depth=0.6,
    filter_cutoff=0.5, resonance=0.4,
    distortion=0.1, sub_mix=0.4,
)))

# ── Step 18: Sub Bass (engine.sub_bass) ──────────────────────────────
print("  │ Step 18: Sub bass (dedicated sub-40Hz layer)")
sub_bass_layer = to_np(synthesize_sub_bass(SubBassPreset(
    name="WO9_Sub", sub_type="deep_sine",
    frequency=KEY_FREQS["Ab1"] / 2.0,  # Ab0 ~26Hz
    duration_s=BAR * 4,
    attack_s=0.008, decay_s=0.5, sustain=0.85, release_s=0.3,
    drive=0.1, sub_weight=1.0, harmonic_mix=0.15,
)))

# ── Step 19: Formant "Talking" Bass (engine.formant_synth) ───────────
print("  │ Step 19: Formant bass (vowel-shifting talking bass)")
formant_talk = to_np(synthesize_formant(FormantPreset(
    name="WO9_TalkBass", formant_type="morph",
    frequency=KEY_FREQS["Ab2"], duration_s=BAR * 4,
    formant1=700.0, formant2=1400.0, bandwidth=120.0,
    brightness=0.65, attack_s=0.003, release_s=0.08,
    distortion=0.15, vibrato_rate=0.0,
)))

formant_yoi = to_np(synthesize_formant(FormantPreset(
    name="WO9_Yoi", formant_type="morph",
    frequency=KEY_FREQS["Ab2"], duration_s=BEAT * 2,
    formant1=400.0, formant2=2000.0, bandwidth=80.0,
    brightness=0.8, attack_s=0.002, release_s=0.05,
    distortion=0.25,
)))

# ── Step 20: Riddim Engine (engine.riddim_engine) ────────────────────
print("  │ Step 20: Riddim engine (gap-based riddim patterns)")
riddim_pattern_main = to_np(generate_riddim_minimal(RiddimPreset(
    name="WO9_RiddimMain", riddim_type="minimal",
    frequency=KEY_FREQS["Ab1"], duration_s=BAR * 4,
    gap_ratio=0.3, attack_s=0.003, release_s=0.015,
    distortion=0.45, subdivisions=4, bpm=BPM, depth=0.9,
)))

riddim_half = to_np(generate_riddim_minimal(RiddimPreset(
    name="WO9_RiddimHalf", riddim_type="halftime",
    frequency=KEY_FREQS["Ab1"], duration_s=BAR * 4,
    gap_ratio=0.4, attack_s=0.005, release_s=0.025,
    distortion=0.35, subdivisions=2, bpm=BPM, depth=0.8,
)))

# ── Step 21: Wavetable Morph (engine.wavetable_morph) ────────────────
print("  │ Step 21: Wavetable morph (evolving spectral textures)")
# Generate base frames from different synthesis types
morph_frames = []
for i in range(8):
    freq = KEY_FREQS["Ab3"] * (PHI ** (i * 0.1))
    frame = np.zeros(2048)
    t_frame = np.arange(2048) / SR
    for h in range(1, 6):
        phase = i * math.pi / 4.0
        frame += (1.0 / h) * np.sin(2.0 * np.pi * freq * h * t_frame + phase)
    frame /= max(np.max(np.abs(frame)), 1e-10)
    morph_frames.append(frame)

morphed_wt = morph_wavetable(morph_frames, MorphPreset(
    name="V9Morph", morph_type="spectral",
    num_frames=8, frame_size=2048,
    morph_curve=PHI, spectral_smooth=0.15,
))

# Render morphed wavetable as texture
morph_texture = np.zeros(int(BAR * 8 * SR))
frame_len = len(morph_texture) // len(morphed_wt)
for i, frame in enumerate(morphed_wt):
    start = i * frame_len
    reps = frame_len // len(frame) + 1
    tiled = np.tile(frame, reps)[:frame_len]
    mix_into(morph_texture, tiled, start, gain=0.12)

# ── Step 22: Additive Synth (engine.additive_synth) ──────────────────
print("  │ Step 22: Additive synth (phi-partial harmonic layer)")
additive_layer = to_np(render_additive(
    AdditivePatch(
        name="V9Additive",
        partials=phi_partials(8),
        master_gain=0.6,
    ),
    freq=KEY_FREQS["Ab3"], duration=BAR * 4, sample_rate=SR,
))

# ── Step 23: Perc Synth (engine.perc_synth) ──────────────────────────
print("  │ Step 23: Perc synth (custom electronic hits)")
perc_click = to_np(synthesize_perc(PercPreset(
    name="V9Click", perc_type="rim",
    duration_s=0.08, pitch=80.0, decay_s=0.05,
    tone_mix=0.7, brightness=0.9, attack_s=0.001,
)))

perc_zap = to_np(synthesize_perc(PercPreset(
    name="V9Zap", perc_type="cowbell",
    duration_s=0.15, pitch=200.0, decay_s=0.10,
    tone_mix=0.5, brightness=0.8, distortion=0.3,
)))

perc_thud = to_np(synthesize_perc(PercPreset(
    name="V9Thud", perc_type="kick",
    duration_s=0.25, pitch=50.0, decay_s=0.18,
    tone_mix=0.8, brightness=0.3, attack_s=0.002,
)))

# ── Step 24: Karplus-Strong (engine.karplus_strong) ──────────────────
print("  │ Step 24: Karplus-Strong plucks (organic attack)")
ks_pluck_Ab = to_np(render_ks(KarplusStrongPatch(
    frequency=KEY_FREQS["Ab3"], duration=BEAT * 2,
    damping=0.4, brightness=0.6, stretch=0.0,
    pluck_position=0.3, feedback=0.995,
), sample_rate=SR))

ks_pluck_Eb = to_np(render_ks(KarplusStrongPatch(
    frequency=KEY_FREQS["Eb4"], duration=BEAT * 2,
    damping=0.35, brightness=0.65, pluck_position=0.4,
    feedback=0.993,
), sample_rate=SR))

ks_pluck_C = to_np(render_ks(KarplusStrongPatch(
    frequency=KEY_FREQS["C4"], duration=BEAT * 2,
    damping=0.45, brightness=0.55, pluck_position=0.35,
    feedback=0.994,
), sample_rate=SR))

# ── Step 25: Sound Palette (engine.sound_palette) ────────────────────
print("  │ Step 25: Sound palette (tonal color consistency)")
palette = generate_palette(PalettePreset(
    name="WO9Palette", palette_type="warm",
    num_colors=5, base_freq=KEY_FREQS["Ab3"],
    phi_spacing=True,
))

palette_tones = []
for color in palette:
    tone = render_palette_tone(color, duration=BAR * 2)
    palette_tones.append(to_np(tone))
print(f"  │          {len(palette_tones)} palette tones generated")

# ── Step 26: Pitch Dive FX (engine.pitch_automation) ─────────────────
print("  │ Step 26: Pitch dive FX (drop transitions)")
# Pre-render a pitch dive effect on a bass tone
dive_source = to_np(synthesize_bass(BassPreset(
    name="DiveSrc", bass_type="saw", frequency=KEY_FREQS["Ab2"],
    duration_s=0.5, attack_s=0.001, release_s=0.3,
)))
pitch_dive_fx = to_np(apply_pitch_automation(
    dive_source, PITCH_DIVE,
    base_freq=KEY_FREQS["Ab2"], sample_rate=SR,
))

# Pre-render a pitch rise effect
rise_source = to_np(synthesize_bass(BassPreset(
    name="RiseSrc", bass_type="saw", frequency=KEY_FREQS["Ab2"],
    duration_s=1.0, attack_s=0.001, release_s=0.5,
)))
pitch_rise_fx = to_np(apply_pitch_automation(
    rise_source, PITCH_RISE,
    base_freq=KEY_FREQS["Ab2"], sample_rate=SR,
))

# ── Step 27: Convolution IRs (engine.convolution) ────────────────────
print("  │ Step 27: Convolution reverb IRs (plate + room)")
# Pre-render convolution on a test impulse to verify
_test_impulse = np.zeros(int(0.5 * SR))
_test_impulse[0] = 1.0
conv_plate_ir = to_np(apply_convolution(_test_impulse, CONV_PLATE, SR))
conv_room_ir = to_np(apply_convolution(_test_impulse, CONV_ROOM, SR))
print(f"  │          Plate IR: {len(conv_plate_ir)/SR:.2f}s, "
      f"Room IR: {len(conv_room_ir)/SR:.2f}s")

# ── Step 28: LFO Matrix waveforms (engine.lfo_matrix) ────────────────
print("  │ Step 28: LFO matrix modulation waveforms")
lfo_pad_wave = to_np(generate_lfo(
    LFO_PAD_FILTER, duration_s=BAR * 16, sample_rate=SR,
))
lfo_arp_wave = to_np(generate_lfo(
    LFO_ARP_PAN, duration_s=BAR * 8, sample_rate=SR,
))

# ── Step 29: Chord Progression (engine.chord_progression) ────────────
print("  │ Step 29: Programmatic chord progression (Ab-Cm-Fm-Db)")
chord_prog = build_progression(
    name="WildOnesV9", key="G#", scale_type="major",
    roman_sequence=["I", "iii", "vi", "IV"],
)
print(f"  │          {chord_prog.name}: {len(chord_prog.chords)} chords in "
      f"{chord_prog.key} {chord_prog.scale_type}")

print("  └────────────────────────────────────────────────────────────┘")
print(f"  Total: 29 sound design steps ({len(serum_patches)} Serum 2 patches)")


# ====================================================================
#  CHORD / HOOK / BASS / GROWL PATTERN HELPERS
# ====================================================================

def chord_progression_full(bars: int) -> np.ndarray:
    """Render full chord progression (supersaw stabs) for N bars."""
    out = np.zeros(int(bars * BAR * SR))
    for bar in range(bars):
        chord_idx = (bar // 2) % 4
        stab = SAW_STABS[chord_idx]
        offset = int(bar * BAR * SR)
        seg = stab[:min(len(stab), int(BAR * 2 * SR))]
        mix_into(out, seg, offset, gain=0.8)
    return out


def chord_progression_filtered(bars: int) -> np.ndarray:
    """Render filtered chord progression."""
    chords = chord_progression_full(bars)
    return lowpass(chords, cutoff=0.15)


def bass_pattern(bars: int, gain: float = 0.5) -> np.ndarray:
    """Render bass pattern for N bars."""
    out = np.zeros(int(bars * BAR * SR))
    for bar in range(bars):
        chord_idx = (bar // 2) % 4
        freq = [KEY_FREQS["Ab1"], KEY_FREQS["C2"],
                KEY_FREQS["F2"], KEY_FREQS["Db2"]][chord_idx]
        note = to_np(synthesize_bass(BassPreset(
            name=f"B{bar}", bass_type="saw", frequency=freq,
            duration_s=BEAT * 2, attack_s=0.005, release_s=0.1,
        )))
        offset = int(bar * BAR * SR)
        mix_into(out, note, offset, gain=gain)
        # Phi sub underneath
        mix_into(out, phi_sub[:min(len(phi_sub), int(BEAT * 2 * SR))],
                 offset, gain=gain * 0.3)
    return out


def growl_pattern(bars: int, gain: float = 0.5) -> np.ndarray:
    """Render growl pattern for N bars."""
    out = np.zeros(int(bars * BAR * SR))
    for bar in range(bars):
        chord_idx = (bar // 2) % 4
        freq = [KEY_FREQS["Ab2"], KEY_FREQS["C3"],
                KEY_FREQS["F2"], KEY_FREQS["Db3"]][chord_idx]
        note = to_np(synthesize_bass(BassPreset(
            name=f"G{bar}", bass_type="growl", frequency=freq,
            duration_s=BEAT * 2, attack_s=0.002, release_s=0.08,
        )))
        note = np.tanh(note * 2.5) * 0.5
        offset = int(bar * BAR * SR)
        mix_into(out, note, offset, gain=gain)
    return out


# v9: Wobble pattern for drop sections
def wobble_pattern(bars: int, gain: float = 0.5,
                   fast: bool = True) -> np.ndarray:
    """Render wobble bass pattern for N bars."""
    out = np.zeros(int(bars * BAR * SR))
    src = wobble_drop if fast else wobble_slow
    src_len = len(src)
    for rep in range(bars * int(BAR * SR) // src_len + 1):
        offset = rep * src_len
        if offset >= len(out):
            break
        mix_into(out, src, offset, gain=gain)
    return out[:int(bars * BAR * SR)]


# v9: Sub bass pattern (follows root notes)
def sub_pattern(bars: int, gain: float = 0.4) -> np.ndarray:
    """Render sub bass pattern for N bars."""
    out = np.zeros(int(bars * BAR * SR))
    for bar in range(bars):
        chord_idx = (bar // 2) % 4
        freq = [KEY_FREQS["Ab1"], KEY_FREQS["C2"],
                KEY_FREQS["F2"], KEY_FREQS["Db2"]][chord_idx]
        sub = to_np(synthesize_sub_bass(SubBassPreset(
            name=f"Sub{bar}", sub_type="deep_sine",
            frequency=freq / 2.0, duration_s=BEAT * 2,
            attack_s=0.008, sustain=0.85, release_s=0.2,
            harmonic_mix=0.1,
        )))
        offset = int(bar * BAR * SR)
        mix_into(out, sub, offset, gain=gain)
    return out


# v9: Riddim pattern (follows chord progression)
def riddim_render(bars: int, gain: float = 0.5) -> np.ndarray:
    """Render riddim pattern for N bars."""
    out = np.zeros(int(bars * BAR * SR))
    src_len = len(riddim_pattern_main)
    for rep in range(bars * int(BAR * SR) // src_len + 1):
        offset = rep * src_len
        if offset >= len(out):
            break
        mix_into(out, riddim_pattern_main, offset, gain=gain)
    return out[:int(bars * BAR * SR)]


# v9: Formant pattern (talking bass hits)
def formant_render(bars: int, gain: float = 0.4) -> np.ndarray:
    """Render formant bass hits."""
    out = np.zeros(int(bars * BAR * SR))
    for bar in range(bars):
        offset = int(bar * BAR * SR)
        # Alternate between talk and yoi
        src = formant_talk if bar % 2 == 0 else formant_yoi
        seg = src[:min(len(src), int(BAR * SR))]
        mix_into(out, seg, offset, gain=gain)
    return out


# ====================================================================
#  DRUM PATTERN HELPERS
# ====================================================================

def drum_chorus(bars: int) -> np.ndarray:
    """Build chorus drum pattern: 4-on-floor + snares + hats."""
    out = np.zeros(int(bars * BAR * SR))
    for bar in range(bars):
        bo = int(bar * BAR * SR)
        for beat in range(4):
            qo = bo + int(beat * BEAT * SR)
            mix_into(out, kick, qo, gain=0.55)
            if beat % 2 == 1:
                mix_into(out, snare, qo, gain=0.40)
            mix_into(out, hat_closed, qo, gain=0.15)
            # Offbeat hats
            mix_into(out, hat_closed, qo + int(BEAT * 0.5 * SR), gain=0.10)
        # Open hat every 2 bars
        if bar % 2 == 1:
            mix_into(out, hat_open, bo + int(3 * BEAT * SR), gain=0.12)
    return out


def drum_verse(bars: int) -> np.ndarray:
    """Lighter verse pattern."""
    out = np.zeros(int(bars * BAR * SR))
    for bar in range(bars):
        bo = int(bar * BAR * SR)
        mix_into(out, kick, bo, gain=0.45)
        mix_into(out, kick, bo + int(2 * BEAT * SR), gain=0.40)
        mix_into(out, snare, bo + int(BEAT * SR), gain=0.30)
        mix_into(out, snare, bo + int(3 * BEAT * SR), gain=0.32)
        for beat in range(4):
            mix_into(out, hat_closed, bo + int(beat * BEAT * SR), gain=0.10)
    return out


def drum_build(bars: int) -> np.ndarray:
    """Build-up drum pattern with increasing density."""
    out = np.zeros(int(bars * BAR * SR))
    for bar in range(bars):
        bo = int(bar * BAR * SR)
        density = bar / max(bars - 1, 1)
        mix_into(out, kick, bo, gain=0.40 + 0.15 * density)
        if bar >= bars // 2:
            # 8th note kick in second half
            for sub in range(8):
                g = 0.15 + 0.25 * density
                mix_into(out, kick, bo + int(sub * BEAT * 0.5 * SR), gain=g)
        mix_into(out, snare, bo + int(BEAT * SR), gain=0.25 + 0.15 * density)
        mix_into(out, snare, bo + int(3 * BEAT * SR), gain=0.28 + 0.15 * density)
        # Rolling snare in last 2 bars
        if bar >= bars - 2:
            for sub in range(16):
                g = 0.08 + 0.15 * (sub / 16.0)
                mix_into(out, snare, bo + int(sub * BEAT * 0.25 * SR), gain=g)
        for beat in range(4):
            mix_into(out, hat_closed, bo + int(beat * BEAT * SR),
                     gain=0.08 + 0.10 * density)
    return out


def drum_intro(bars: int) -> np.ndarray:
    """Minimal intro drums."""
    out = np.zeros(int(bars * BAR * SR))
    for bar in range(bars):
        bo = int(bar * BAR * SR)
        for beat in range(4):
            mix_into(out, hat_closed, bo + int(beat * BEAT * SR),
                     gain=0.06 + 0.02 * (bar / max(bars - 1, 1)))
    return out


def drum_vip(bars: int) -> np.ndarray:
    """VIP halftime drums — heavy, sparse."""
    out = np.zeros(int(bars * BAR * SR))
    for bar in range(bars):
        bo = int(bar * BAR * SR)
        mix_into(out, kick, bo, gain=0.60)
        mix_into(out, snare, bo + int(2 * BEAT * SR), gain=0.50)
        mix_into(out, clap, bo + int(2 * BEAT * SR), gain=0.30)
        for beat in range(4):
            mix_into(out, hat_closed, bo + int(beat * BEAT * SR), gain=0.12)
            if beat % 2 == 1:
                mix_into(out, hat_open,
                         bo + int((beat + 0.5) * BEAT * SR), gain=0.08)
        # v9: perc synth accents
        mix_into(out, perc_click, bo + int(BEAT * SR), gain=0.15)
        if bar % 2 == 0:
            mix_into(out, perc_zap, bo + int(3 * BEAT * SR), gain=0.12)
    return out


# ====================================================================
#  SONG STRUCTURE — 144 bars (Fibonacci!)
# ====================================================================
INTRO_BARS = 8
VERSE1_BARS = 8
PRECHORUS1_BARS = 8
CHORUS1_BARS = 16
BREAK_BARS = 8
VERSE2_BARS = 8
PRECHORUS2_BARS = 8
CHORUS2_BARS = 16
BRIDGE_BARS = 16
VIP_DROP_BARS = 16
FINAL_CHORUS_BARS = 16
OUTRO_BARS = 16

# Section bar offsets
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

total_bars = SEC_OUTRO + OUTRO_BARS
assert total_bars == 144, f"Expected 144 bars (Fibonacci), got {total_bars}"

golden_section_bar = int(total_bars / PHI)  # ~89 (bridge start!)

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

total_samples = int(total_bars * BAR * SR)

print()
print(f"  Structure: {total_bars} bars (Fibonacci) = "
      f"{total_samples / SR:.1f}s  |  Golden section: bar ~{golden_section_bar}")


# ====================================================================
#  STEM BUFFERS
# ====================================================================
print("  Allocating 16 stem buffers...")
stems: dict[str, np.ndarray] = {
    name: np.zeros(total_samples) for name in STEM_NAMES
}


# ====================================================================
#  ARRANGEMENT RENDERING
# ====================================================================
print()
print("  ┌─ ARRANGEMENT ──────────────────────────────────────────────┐")

cursor = 0

# ── INTRO (8 bars) ────────────────────────────────────────────────
print("  │ Rendering Intro (8 bars — atmospheric build)...")
intro_start = cursor

# Vinyl noise bed
intro_vinyl = vinyl_noise[:samples_for(INTRO_BARS * 4)]
intro_vinyl = fade_in(intro_vinyl, duration_s=BAR * 2)
mix_into(stems["FX"], intro_vinyl, intro_start, gain=0.08)

# Light drums
intro_drums = drum_intro(INTRO_BARS)
mix_into(stems["DRUMS"], intro_drums, intro_start, gain=0.30)

# Filtered pad fading in
intro_pad = lush_pad[:samples_for(INTRO_BARS * 4)]
intro_pad = lowpass(intro_pad, cutoff=0.10)
intro_pad = fade_in(intro_pad, duration_s=BAR * 4)
mix_into(stems["PAD"], intro_pad, intro_start, gain=0.20)

# Drone
intro_drone = drone[:samples_for(INTRO_BARS * 4)]
intro_drone = lowpass(intro_drone, cutoff=0.06)
intro_drone = fade_in(intro_drone, duration_s=BAR * 4)
mix_into(stems["DRONE"], intro_drone, intro_start, gain=0.12)

# Acapella teaser
_a = ACAP_MAP["INTRO"]
intro_vox = slice_acapella(_a[0], INTRO_BARS)
intro_vox = lowpass(intro_vox, cutoff=0.12)
intro_vox = fade_in(intro_vox, duration_s=BAR * 2)
mix_into(stems["VOCAL"], intro_vox, intro_start, gain=0.25)

# v6: Granular shimmer texture
intro_tex = granular_shimmer[:samples_for(INTRO_BARS * 4)]
intro_tex = fade_in(intro_tex, duration_s=BAR * 4)
mix_into(stems["TEXTURE"], intro_tex, intro_start, gain=0.10)

# v9: Additive harmonic layer fading in
intro_add = additive_layer[:min(len(additive_layer),
                                samples_for(INTRO_BARS * 4))]
intro_add = fade_in(intro_add, duration_s=BAR * 6)
mix_into(stems["TEXTURE"], intro_add, intro_start, gain=0.06)

# v9: Sub bass — barely audible sub rumble
intro_sub = sub_pattern(INTRO_BARS, gain=0.15)
intro_sub = fade_in(intro_sub, duration_s=BAR * 4)
mix_into(stems["SUB"], intro_sub, intro_start, gain=0.10)

cursor += samples_for(INTRO_BARS * 4)

# ── VERSE 1 (8 bars) ──────────────────────────────────────────────
print("  │ Rendering Verse 1 (8 bars)...")
verse1_start = cursor

v1_drums = drum_verse(VERSE1_BARS)
mix_into(stems["DRUMS"], v1_drums, verse1_start, gain=0.50)

# v9: perc synth accents on verse
for bar in range(VERSE1_BARS):
    bo = verse1_start + samples_for(bar * 4)
    mix_into(stems["DRUMS"], perc_click, bo + samples_for(1), gain=0.08)

v1_bass = apply_sidechain(bass_pattern(VERSE1_BARS, gain=0.50),
                          SC_PUMP, SR)
mix_into(stems["BASS"], v1_bass, verse1_start, gain=0.48)

# v9: Sub bass layer
v1_sub = sub_pattern(VERSE1_BARS, gain=0.30)
v1_sub = apply_sidechain(v1_sub, SC_PUMP, SR)
mix_into(stems["SUB"], v1_sub, verse1_start, gain=0.25)

_a = ACAP_MAP["VERSE1"]
v1_vox = slice_acapella(_a[0], VERSE1_BARS)
mix_into(stems["VOCAL"], v1_vox, verse1_start, gain=0.55)

v1_pad = lush_pad[:samples_for(VERSE1_BARS * 4)]
v1_pad = lowpass(v1_pad, cutoff=0.18)
mix_into(stems["PAD"], v1_pad, verse1_start, gain=0.22)

for rep in range(VERSE1_BARS // 4):
    offset = verse1_start + samples_for(rep * 16)
    seg = arp_pluck[:min(len(arp_pluck), samples_for(16))]
    mix_into(stems["ARP"], seg, offset, gain=0.12)

cursor += samples_for(VERSE1_BARS * 4)

# ── PRE-CHORUS 1 (8 bars) ─────────────────────────────────────────
print("  │ Rendering Pre-Chorus 1 (8 bars — building)...")
pc1_start = cursor

pc1_drums = drum_build(PRECHORUS1_BARS)
mix_into(stems["DRUMS"], pc1_drums, pc1_start, gain=0.48)

riser1_pitch = pitch_riser[:samples_for(PRECHORUS1_BARS * 4)]
riser1_harm = harmonic_riser[:samples_for(PRECHORUS1_BARS * 4)]
riser1_noise = noise_riser[:samples_for(PRECHORUS1_BARS * 4)]
mix_into(stems["RISER"], riser1_pitch, pc1_start, gain=0.22)
mix_into(stems["RISER"], riser1_harm, pc1_start, gain=0.18)
mix_into(stems["RISER"], riser1_noise, pc1_start, gain=0.12)

_a = ACAP_MAP["PRECHORUS1"]
pc1_vox = slice_acapella(_a[0], PRECHORUS1_BARS)
mix_into(stems["VOCAL"], pc1_vox, pc1_start, gain=0.50)

for bar in range(PRECHORUS1_BARS):
    bo = pc1_start + samples_for(bar * 4)
    g = build_gain(bar, PRECHORUS1_BARS, start=0.10, end=0.28)
    seg = lush_pad[:samples_for(4)]
    mix_into(stems["PAD"], seg, bo, gain=g)

for bar in range(PRECHORUS1_BARS):
    bo = pc1_start + samples_for(bar * 4)
    g = build_gain(bar, PRECHORUS1_BARS, start=0.06, end=0.18)
    mix_into(stems["VOCAL"], chop_stutter, bo, gain=g)

# Beat repeat building in last 4 bars
_br_src = stems["DRUMS"][pc1_start + samples_for(16):
                         pc1_start + samples_for(32)].copy()
if len(_br_src) > 0:
    _br_fx = to_np(apply_beat_repeat(_br_src, BEAT_REPEAT_BUILD,
                                     bpm=BPM, sample_rate=SR))
    mix_into(stems["FX"], _br_fx, pc1_start + samples_for(16), gain=0.20)

ee_off = pc1_start + samples_for(PRECHORUS1_BARS * 4) - len(chop_ee) - SR // 4
if ee_off > pc1_start:
    mix_into(stems["VOCAL"], chop_ee, ee_off, gain=0.25)

rev_pc1 = pc1_start + samples_for(PRECHORUS1_BARS * 4) - len(reverse_hit)
if rev_pc1 > pc1_start:
    mix_into(stems["FX"], reverse_hit, rev_pc1, gain=0.35)

# v9: pitch rise FX at end of pre-chorus
rise_off = pc1_start + samples_for((PRECHORUS1_BARS - 2) * 4)
mix_into(stems["FX"], pitch_rise_fx, rise_off, gain=0.20)

cursor += samples_for(PRECHORUS1_BARS * 4)

# ── CHORUS 1 (16 bars) ────────────────────────────────────────────
print("  │ Rendering Chorus 1 (16 bars — full drop)...")
ch1_start = cursor

mix_into(stems["FX"], sub_boom, ch1_start, gain=0.28)
mix_into(stems["FX"], cinema_hit, ch1_start, gain=0.18)
mix_into(stems["FX"], impact_boom, ch1_start, gain=0.12)

# v9: pitch dive on drop entry
mix_into(stems["FX"], pitch_dive_fx, ch1_start, gain=0.22)

for rep in range(CHORUS1_BARS // 4):
    offset = ch1_start + samples_for(rep * 16)
    d = drum_chorus(4)
    mix_into(stems["DRUMS"], d, offset, gain=0.55)

for rep in range(CHORUS1_BARS // 8):
    offset = ch1_start + samples_for(rep * 32)
    chords = chord_progression_full(8)
    chords = apply_sidechain(chords, SC_PUMP, SR)
    mix_into(stems["CHORDS"], chords, offset, gain=0.95)

ch1_bass = apply_sidechain(bass_pattern(CHORUS1_BARS, gain=0.58),
                           SC_HARD, SR)
mix_into(stems["BASS"], ch1_bass, ch1_start, gain=0.50)

# v9: Sub bass layer
ch1_sub = sub_pattern(CHORUS1_BARS, gain=0.35)
ch1_sub = apply_sidechain(ch1_sub, SC_HARD, SR)
mix_into(stems["SUB"], ch1_sub, ch1_start, gain=0.30)

# v9: Wobble bass (slow wobble under chorus)
ch1_wobble = wobble_pattern(CHORUS1_BARS, gain=0.25, fast=False)
ch1_wobble = apply_sidechain(ch1_wobble, SC_HARD, SR)
mix_into(stems["WOBBLE"], ch1_wobble, ch1_start, gain=0.20)

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

# v6: white air noise
ch1_air = white_air[:samples_for(CHORUS1_BARS * 4)]
mix_into(stems["TEXTURE"], ch1_air, ch1_start, gain=0.06)

tape_ch1 = ch1_start + samples_for(CHORUS1_BARS * 4) - len(tape_stop)
if tape_ch1 > ch1_start:
    mix_into(stems["FX"], tape_stop, tape_ch1, gain=0.20)

cursor += samples_for(CHORUS1_BARS * 4)

# ── BREAK (8 bars) ────────────────────────────────────────────────
print("  │ Rendering Break (8 bars — ACAPELLA section)...")
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

# v6: granular dust
break_tex = granular_dust[:samples_for(BREAK_BARS * 4)]
break_tex = lowpass(break_tex, cutoff=0.15)
mix_into(stems["TEXTURE"], break_tex, break_start, gain=0.12)

# v9: Karplus-Strong pluck accents in break (sparse, emotional)
for bar in range(0, BREAK_BARS, 2):
    bo = break_start + samples_for(bar * 4)
    ks = [ks_pluck_Ab, ks_pluck_C, ks_pluck_Eb, ks_pluck_Ab][bar // 2 % 4]
    mix_into(stems["HOOK"], ks, bo, gain=0.15)

cursor += samples_for(BREAK_BARS * 4)

# ── VERSE 2 (8 bars) ──────────────────────────────────────────────
print("  │ Rendering Verse 2 (8 bars)...")
verse2_start = cursor

for rep in range(VERSE2_BARS // 4):
    offset = verse2_start + samples_for(rep * 16)
    d = drum_verse(4)
    mix_into(stems["DRUMS"], d, offset, gain=0.55)

v2_bass = apply_sidechain(bass_pattern(VERSE2_BARS, gain=0.52),
                          SC_PUMP, SR)
mix_into(stems["BASS"], v2_bass, verse2_start, gain=0.50)

# v9: Sub bass
v2_sub = sub_pattern(VERSE2_BARS, gain=0.28)
mix_into(stems["SUB"], v2_sub, verse2_start, gain=0.22)

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
print("  │ Rendering Pre-Chorus 2 (8 bars — bigger build)...")
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

_br2_src = stems["DRUMS"][pc2_start + samples_for(16):
                          pc2_start + samples_for(32)].copy()
if len(_br2_src) > 0:
    _br2_fx = to_np(apply_beat_repeat(_br2_src, BEAT_REPEAT_BUILD,
                                      bpm=BPM, sample_rate=SR))
    mix_into(stems["FX"], _br2_fx, pc2_start + samples_for(16), gain=0.22)

rev_pc2 = pc2_start + samples_for(PRECHORUS2_BARS * 4) - len(reverse_hit)
if rev_pc2 > pc2_start:
    mix_into(stems["FX"], reverse_hit, rev_pc2, gain=0.30)
dive_pc2 = pc2_start + samples_for((PRECHORUS2_BARS - 1) * 4)
mix_into(stems["FX"], pitch_dive, dive_pc2, gain=0.22)

ee_off2 = pc2_start + samples_for(PRECHORUS2_BARS * 4) - len(chop_ee) - SR // 6
if ee_off2 > pc2_start:
    mix_into(stems["VOCAL"], chop_ee, ee_off2, gain=0.28)

# v9: pitch rise FX
rise_off2 = pc2_start + samples_for((PRECHORUS2_BARS - 2) * 4)
mix_into(stems["FX"], pitch_rise_fx, rise_off2, gain=0.22)

cursor += samples_for(PRECHORUS2_BARS * 4)

# ── CHORUS 2 (16 bars) ────────────────────────────────────────────
print("  │ Rendering Chorus 2 (16 bars — maximum energy)...")
ch2_start = cursor

mix_into(stems["FX"], sub_boom, ch2_start, gain=0.30)
mix_into(stems["FX"], cinema_hit, ch2_start, gain=0.20)
mix_into(stems["FX"], impact_boom, ch2_start, gain=0.14)
mix_into(stems["DRUMS"], clap, ch2_start, gain=0.35)

# v9: pitch dive on every drop
mix_into(stems["FX"], pitch_dive_fx, ch2_start, gain=0.24)

for rep in range(CHORUS2_BARS // 4):
    offset = ch2_start + samples_for(rep * 16)
    d = drum_chorus(4)
    mix_into(stems["DRUMS"], d, offset, gain=0.58)

for rep in range(CHORUS2_BARS // 8):
    offset = ch2_start + samples_for(rep * 32)
    chords = chord_progression_full(8)
    chords = apply_sidechain(chords, SC_HARD, SR)
    mix_into(stems["CHORDS"], chords, offset, gain=0.98)

ch2_bass = apply_sidechain(bass_pattern(CHORUS2_BARS, gain=0.60),
                           SC_HARD, SR)
mix_into(stems["BASS"], ch2_bass, ch2_start, gain=0.52)

# v9: Sub + wobble
ch2_sub = sub_pattern(CHORUS2_BARS, gain=0.38)
ch2_sub = apply_sidechain(ch2_sub, SC_HARD, SR)
mix_into(stems["SUB"], ch2_sub, ch2_start, gain=0.32)

ch2_wobble = wobble_pattern(CHORUS2_BARS, gain=0.30, fast=False)
ch2_wobble = apply_sidechain(ch2_wobble, SC_HARD, SR)
mix_into(stems["WOBBLE"], ch2_wobble, ch2_start, gain=0.22)

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

ch2_air = white_air[:samples_for(CHORUS2_BARS * 4)]
mix_into(stems["TEXTURE"], ch2_air, ch2_start, gain=0.07)

tape_ch2 = ch2_start + samples_for(CHORUS2_BARS * 4) - len(tape_stop)
if tape_ch2 > ch2_start:
    mix_into(stems["FX"], tape_stop, tape_ch2, gain=0.22)

cursor += samples_for(CHORUS2_BARS * 4)

# ── BRIDGE (8 bars) ─── Golden Section Point (bar ~89) ────────────
print("  │ Rendering Bridge (8 bars — emotional breakdown, GOLDEN SECTION)...")
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

# v6: granular shimmer
bridge_tex = granular_shimmer[:samples_for(BRIDGE_BARS * 4)]
bridge_tex = fade_in(bridge_tex, duration_s=BAR * 2)
mix_into(stems["TEXTURE"], bridge_tex, bridge_start, gain=0.18)

# v9: Wavetable morph evolving texture layer
bridge_morph = morph_texture[:min(len(morph_texture),
                                  samples_for(BRIDGE_BARS * 4))]
bridge_morph = fade_in(bridge_morph, duration_s=BAR * 2)
bridge_morph = fade_out(bridge_morph, duration_s=BAR * 2)
mix_into(stems["TEXTURE"], bridge_morph, bridge_start, gain=0.14)

# v9: Karplus-Strong plucks for emotional bridge melody
for bar in range(BRIDGE_BARS):
    bo = bridge_start + samples_for(bar * 4)
    ks = [ks_pluck_Ab, ks_pluck_C, ks_pluck_Eb, ks_pluck_Ab][bar % 4]
    mix_into(stems["HOOK"], ks, bo, gain=0.18)

# v9: Palette tone accents
for bar in range(0, BRIDGE_BARS, 2):
    bo = bridge_start + samples_for(bar * 4)
    tone_idx = (bar // 2) % len(palette_tones)
    tone = palette_tones[tone_idx][:min(len(palette_tones[tone_idx]),
                                        samples_for(4))]
    mix_into(stems["TEXTURE"], tone, bo, gain=0.08)

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

# ── VIP DROP (16 bars) ─── GROWL + WOBBLE + RIDDIM + FORMANT VIP ──
print("  │ Rendering VIP Drop (16 bars — ULTIMATE VIP)...")
vip_start = cursor

# MASSIVE IMPACT
mix_into(stems["FX"], sub_boom, vip_start, gain=0.35)
mix_into(stems["FX"], cinema_hit, vip_start, gain=0.25)
mix_into(stems["FX"], impact_boom, vip_start, gain=0.18)
mix_into(stems["DRUMS"], clap, vip_start, gain=0.40)
mix_into(stems["VOCAL"], chop_ee, vip_start, gain=0.30)

# v9: pitch dive on VIP entry
mix_into(stems["FX"], pitch_dive_fx, vip_start, gain=0.28)

# VIP drums — halftime breaks
for rep in range(VIP_DROP_BARS // 4):
    offset = vip_start + samples_for(rep * 16)
    d = drum_vip(4)
    mix_into(stems["DRUMS"], d, offset, gain=0.62)

# GROWL BASS — the VIP star element
vip_growl = growl_pattern(VIP_DROP_BARS, gain=0.55)
vip_growl = apply_sidechain(vip_growl, SC_HARD, SR)
mix_into(stems["GROWL"], vip_growl, vip_start, gain=0.60)

# v9 NEW: WOBBLE BASS — fast wobble in VIP
vip_wobble = wobble_pattern(VIP_DROP_BARS, gain=0.50, fast=True)
vip_wobble = apply_sidechain(vip_wobble, SC_HARD, SR)
mix_into(stems["WOBBLE"], vip_wobble, vip_start, gain=0.45)

# v9 NEW: RIDDIM — gap-based riddim pattern
vip_riddim = riddim_render(VIP_DROP_BARS, gain=0.45)
vip_riddim = apply_sidechain(vip_riddim, SC_HARD, SR)
mix_into(stems["RIDDIM"], vip_riddim, vip_start, gain=0.40)

# v9 NEW: FORMANT — talking bass hits
vip_formant = formant_render(VIP_DROP_BARS, gain=0.40)
vip_formant = apply_sidechain(vip_formant, SC_HARD, SR)
mix_into(stems["FORMANT"], vip_formant, vip_start, gain=0.35)

# Chord progression — darker, harder sidechain
for rep in range(VIP_DROP_BARS // 8):
    offset = vip_start + samples_for(rep * 32)
    chords = chord_progression_full(8)
    chords = apply_sidechain(chords, SC_HARD, SR)
    mix_into(stems["CHORDS"], chords, offset, gain=0.85)

# Sub bass underneath
vip_bass = apply_sidechain(bass_pattern(VIP_DROP_BARS, gain=0.50),
                           SC_HARD, SR)
mix_into(stems["BASS"], vip_bass, vip_start, gain=0.42)

# v9: Sub layer
vip_sub = sub_pattern(VIP_DROP_BARS, gain=0.40)
vip_sub = apply_sidechain(vip_sub, SC_HARD, SR)
mix_into(stems["SUB"], vip_sub, vip_start, gain=0.35)

# Hook melody
for rep in range(VIP_DROP_BARS // 8):
    offset = vip_start + samples_for(rep * 32)
    hook = hook_melody_render(8, pluck_gain=0.28, fm_gain=0.22)
    mix_into(stems["HOOK"], hook, offset, gain=0.35)

_a = ACAP_MAP["VIP"]
vip_vox = slice_acapella(_a[0], VIP_DROP_BARS)
mix_into(stems["VOCAL"], vip_vox, vip_start, gain=0.50)

vip_pad = dark_pad[:samples_for(VIP_DROP_BARS * 4)]
mix_into(stems["PAD"], vip_pad, vip_start, gain=0.12)

for rep in range(VIP_DROP_BARS // 4):
    offset = vip_start + samples_for(rep * 16)
    seg = arp_shimmer[:min(len(arp_shimmer), samples_for(16))]
    mix_into(stems["ARP"], seg, offset, gain=0.14)

# Beat repeat on growl (phi grid)
_growl_src = stems["GROWL"][vip_start:
                            vip_start + samples_for(VIP_DROP_BARS * 4)].copy()
if len(_growl_src) > 0 and np.max(np.abs(_growl_src)) > 0.001:
    _growl_br = to_np(apply_beat_repeat(_growl_src, BEAT_REPEAT_VIP,
                                        bpm=BPM, sample_rate=SR))
    mix_into(stems["FX"], _growl_br, vip_start, gain=0.18)

# FM accents
for bar in range(0, VIP_DROP_BARS, 2):
    mix_into(stems["FX"], fm_hit,
             vip_start + samples_for(bar * 4), gain=0.18)

# Stutter transitions
for trans_bar in [6, 10, 14]:
    stut_vip = vip_start + samples_for(trans_bar * 4)
    mix_into(stems["FX"], stutter_fx, stut_vip, gain=0.20)

# v9: perc synth accents in VIP
for bar in range(0, VIP_DROP_BARS, 4):
    bo = vip_start + samples_for(bar * 4)
    mix_into(stems["DRUMS"], perc_thud, bo, gain=0.20)
    mix_into(stems["DRUMS"], perc_zap, bo + samples_for(2), gain=0.15)

# White air noise
vip_air = white_air[:samples_for(VIP_DROP_BARS * 4)]
mix_into(stems["TEXTURE"], vip_air, vip_start, gain=0.07)

tape_vip = vip_start + samples_for(VIP_DROP_BARS * 4) - len(tape_stop)
if tape_vip > vip_start:
    mix_into(stems["FX"], tape_stop, tape_vip, gain=0.22)

cursor += samples_for(VIP_DROP_BARS * 4)

# ── FINAL CHORUS (16 bars) ─── "Climax: everything layered" ───────
print("  │ Rendering Final Chorus (16 bars — CLIMAX)...")
fc_start = cursor

mix_into(stems["FX"], sub_boom, fc_start, gain=0.32)
mix_into(stems["FX"], cinema_hit, fc_start, gain=0.22)
mix_into(stems["FX"], impact_boom, fc_start, gain=0.15)
mix_into(stems["DRUMS"], clap, fc_start, gain=0.38)
mix_into(stems["VOCAL"], chop_ee, fc_start, gain=0.25)

# v9: pitch dive on final drop
mix_into(stems["FX"], pitch_dive_fx, fc_start, gain=0.25)

for rep in range(FINAL_CHORUS_BARS // 4):
    offset = fc_start + samples_for(rep * 16)
    d = drum_chorus(4)
    mix_into(stems["DRUMS"], d, offset, gain=0.60)

for rep in range(FINAL_CHORUS_BARS // 8):
    offset = fc_start + samples_for(rep * 32)
    chords = chord_progression_full(8)
    chords = apply_sidechain(chords, SC_HARD, SR)
    mix_into(stems["CHORDS"], chords, offset, gain=1.00)

fc_bass = apply_sidechain(bass_pattern(FINAL_CHORUS_BARS, gain=0.62),
                          SC_HARD, SR)
mix_into(stems["BASS"], fc_bass, fc_start, gain=0.55)

# v9: Sub + wobble + formant in final chorus (EVERYTHING!)
fc_sub = sub_pattern(FINAL_CHORUS_BARS, gain=0.40)
fc_sub = apply_sidechain(fc_sub, SC_HARD, SR)
mix_into(stems["SUB"], fc_sub, fc_start, gain=0.35)

fc_wobble = wobble_pattern(FINAL_CHORUS_BARS, gain=0.30, fast=True)
fc_wobble = apply_sidechain(fc_wobble, SC_HARD, SR)
mix_into(stems["WOBBLE"], fc_wobble, fc_start, gain=0.25)

fc_formant = formant_render(FINAL_CHORUS_BARS, gain=0.30)
fc_formant = apply_sidechain(fc_formant, SC_HARD, SR)
mix_into(stems["FORMANT"], fc_formant, fc_start, gain=0.22)

# Growl layer
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

fc_air = white_air[:samples_for(FINAL_CHORUS_BARS * 4)]
mix_into(stems["TEXTURE"], fc_air, fc_start, gain=0.07)

# v9: perc synth in final chorus
for bar in range(0, FINAL_CHORUS_BARS, 2):
    bo = fc_start + samples_for(bar * 4)
    mix_into(stems["DRUMS"], perc_click, bo + samples_for(1), gain=0.10)
    mix_into(stems["DRUMS"], perc_zap, bo + samples_for(3), gain=0.08)

tape_fc = fc_start + samples_for(FINAL_CHORUS_BARS * 4) - len(tape_stop)
if tape_fc > fc_start:
    mix_into(stems["FX"], tape_stop, tape_fc, gain=0.22)

cursor += samples_for(FINAL_CHORUS_BARS * 4)

# ── OUTRO (16 bars) ───────────────────────────────────────────────
print("  │ Rendering Outro (16 bars — dissolving)...")
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

outro_sub_note = to_np(synthesize_bass(BassPreset(
    name="WOOutroSub", bass_type="saw",
    frequency=KEY_FREQS["Ab1"],
    duration_s=OUTRO_BARS * BAR, attack_s=0.01,
    release_s=OUTRO_BARS * BAR * 0.8,
)))
outro_sub_note = fade_out(outro_sub_note, duration_s=BAR * 12)
mix_into(stems["BASS"], outro_sub_note, outro_start, gain=0.14)

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

# v6: granular shimmer + vinyl fadeout
outro_tex = granular_shimmer[:samples_for(OUTRO_BARS * 4)]
outro_tex = fade_out(outro_tex, duration_s=BAR * 10)
mix_into(stems["TEXTURE"], outro_tex, outro_start, gain=0.15)

outro_vinyl = vinyl_noise[:samples_for(OUTRO_BARS * 4)]
outro_vinyl = fade_out(outro_vinyl, duration_s=BAR * 8)
mix_into(stems["FX"], outro_vinyl, outro_start, gain=0.06)

# v9: Wavetable morph dissolving
outro_morph = morph_texture[:min(len(morph_texture),
                                 samples_for(OUTRO_BARS * 4))]
outro_morph = fade_out(outro_morph, duration_s=BAR * 10)
mix_into(stems["TEXTURE"], outro_morph, outro_start, gain=0.10)

# v9: Additive layer dissolving
outro_add = additive_layer[:min(len(additive_layer),
                                samples_for(OUTRO_BARS * 4))]
outro_add = fade_out(outro_add, duration_s=BAR * 8)
mix_into(stems["TEXTURE"], outro_add, outro_start, gain=0.06)

# v9: KS pluck — final sparse notes
for bar in [0, 3, 6, 10]:
    if bar < OUTRO_BARS:
        bo = outro_start + samples_for(bar * 4)
        ks = ks_pluck_Ab[:min(len(ks_pluck_Ab), samples_for(4))]
        ks = fade_out(ks, duration_s=BEAT * 3)
        mix_into(stems["HOOK"], ks, bo, gain=0.10 * (1.0 - bar / OUTRO_BARS))

print("  └────────────────────────────────────────────────────────────┘")


# ====================================================================
#  PHI CROSSFADES BETWEEN SECTIONS
# ====================================================================
print()
print("  Applying phi crossfades between sections...")

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
#  PER-STEM DYNAMICS & PROCESSING
# ====================================================================
print("  Per-stem dynamics processing...")

# Transient shaping on drums
stems["DRUMS"] = to_np(DYNPROC.transient_shaper(
    stems["DRUMS"].tolist(), attack_gain=1.3, sustain_gain=0.85))
print("    DRUMS    -> transient_shaper (attack=1.3, sustain=0.85)")

# Compress bass
stems["BASS"] = to_np(compress(stems["BASS"].tolist(), COMP_BASS, SR))
print("    BASS     -> compress (ratio=4.0, threshold=-12dB)")

# Compress growl
stems["GROWL"] = to_np(compress(stems["GROWL"].tolist(), COMP_BASS, SR))
print("    GROWL    -> compress (ratio=4.0, threshold=-12dB)")

# De-ess vocals, then compress
stems["VOCAL"] = to_np(DYNPROC.de_ess(stems["VOCAL"].tolist(), DEESS))
stems["VOCAL"] = to_np(compress(stems["VOCAL"].tolist(), COMP_VOCAL, SR))
print("    VOCAL    -> de_ess (6500Hz) + compress (ratio=3.5)")

# Light compression on drums
stems["DRUMS"] = to_np(compress(stems["DRUMS"].tolist(), COMP_DRUMS, SR))
print("    DRUMS    -> compress (ratio=3.0, threshold=-8dB)")

# v9: Compress wobble
stems["WOBBLE"] = to_np(compress(stems["WOBBLE"].tolist(), COMP_BASS, SR))
print("    WOBBLE   -> compress (ratio=4.0, threshold=-12dB)")

# v9: Compress riddim
stems["RIDDIM"] = to_np(compress(stems["RIDDIM"].tolist(), COMP_BASS, SR))
print("    RIDDIM   -> compress (ratio=4.0, threshold=-12dB)")

# v9: Compress formant
stems["FORMANT"] = to_np(compress(stems["FORMANT"].tolist(), COMP_BASS, SR))
print("    FORMANT  -> compress (ratio=4.0, threshold=-12dB)")


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

print("    PAD      -> sidechain + hall")
print("    VOCAL    -> hall")
print("    ARP      -> room")
print("    HOOK     -> room")
print("    CHORDS   -> hall")
print("    DRONE    -> hall")
print("    TEXTURE  -> hall")
print("    GROWL    -> room")

# v9: Convolution reverb on PAD and DRONE (replaces hall on these)
print("  v9: Convolution reverb (plate + room)...")
stems["PAD"] = to_np(apply_convolution(stems["PAD"], CONV_PLATE, SR))
stems["DRONE"] = to_np(apply_convolution(stems["DRONE"], CONV_ROOM, SR))
print("    PAD      -> convolution plate (size=1.2, decay=0.92)")
print("    DRONE    -> convolution room (12x9x4m)")

# v9: Reverb on new stems
stems["WOBBLE"] = apply_room(stems["WOBBLE"], ROOM_VERB, SR)
stems["RIDDIM"] = apply_room(stems["RIDDIM"], ROOM_VERB, SR)
stems["FORMANT"] = apply_room(stems["FORMANT"], ROOM_VERB, SR)
print("    WOBBLE   -> room")
print("    RIDDIM   -> room")
print("    FORMANT  -> room")

# Multi-technique stereo imaging
print("  Multi-technique stereo imaging...")
stems["PAD"] = apply_haas(stems["PAD"], STEREO_PAD, SR)
stems["CHORDS"] = apply_psychoacoustic(stems["CHORDS"], STEREO_CHORD, SR)
stems["ARP"] = apply_frequency_split(stems["ARP"], STEREO_ARP, SR)
stems["HOOK"] = apply_mid_side(stems["HOOK"], STEREO_HOOK, SR)
print("    PAD      -> Haas (12ms, width=1.2)")
print("    CHORDS   -> psychoacoustic (width=1.4)")
print("    ARP      -> frequency_split (2kHz, width=1.1)")
print("    HOOK     -> mid_side (width=0.9)")

# Saturation (v6)
print("  SaturationEngine (tape/tube saturation)...")

stems["BASS"] = to_np(SAT_ENGINE.saturate(
    stems["BASS"].tolist() if stems["BASS"].ndim == 1
    else stems["BASS"][:, 0].tolist(),
    SatConfig(sat_type="tape", drive=2.5, mix=0.20)))
stems["GROWL"] = to_np(SAT_ENGINE.saturate(
    stems["GROWL"].tolist() if stems["GROWL"].ndim == 1
    else stems["GROWL"][:, 0].tolist(),
    SatConfig(sat_type="tube", drive=4.0, mix=0.30)))
stems["HOOK"] = to_np(SAT_ENGINE.saturate(
    stems["HOOK"].tolist() if stems["HOOK"].ndim == 1
    else stems["HOOK"][:, 0].tolist(),
    SatConfig(sat_type="tape", drive=1.8, mix=0.12)))
print("    BASS     -> SaturationEngine tape (drive=2.5, mix=20%)")
print("    GROWL    -> SaturationEngine tube (drive=4.0, mix=30%)")
print("    HOOK     -> SaturationEngine tape (drive=1.8, mix=12%)")


# ── v9: Multiband Distortion ─────────────────────────────────────────
print("  v9: Multiband distortion (growl + wobble)...")
stems["GROWL"] = to_np(apply_multiband_distortion(
    stems["GROWL"] if stems["GROWL"].ndim == 1
    else stems["GROWL"][:, 0],
    MBDIST_GROWL, SR))
stems["WOBBLE"] = to_np(apply_multiband_distortion(
    stems["WOBBLE"] if stems["WOBBLE"].ndim == 1
    else stems["WOBBLE"][:, 0],
    MBDIST_WOBBLE, SR))
print("    GROWL    -> MB dist tube (lo=0.2, mid=0.6, hi=0.4)")
print("    WOBBLE   -> MB dist tape (lo=0.3, mid=0.5, hi=0.3)")

# ── v9: Wave Folding on BASS ─────────────────────────────────────────
print("  v9: Wave folding on bass (harmonic enrichment)...")
bass_1d = stems["BASS"] if stems["BASS"].ndim == 1 else stems["BASS"][:, 0]
bass_folded = np.vectorize(lambda x: fold(x, amount=2.5))(bass_1d)
stems["BASS"] = to_np(bass_1d * 0.7 + bass_folded * 0.3)  # Parallel blend
print("    BASS     -> wave_fold (amount=2.5, mix=30%)")

# ── v9: LFO Matrix on PAD and ARP ────────────────────────────────────
print("  v9: LFO matrix modulation (pad filter + arp pan)...")
pad_1d = stems["PAD"] if stems["PAD"].ndim == 1 else stems["PAD"][:, 0]
lfo_for_pad = lfo_pad_wave[:len(pad_1d)]
if len(lfo_for_pad) < len(pad_1d):
    lfo_for_pad = np.pad(lfo_for_pad, (0, len(pad_1d) - len(lfo_for_pad)))
stems["PAD"] = to_np(pad_1d * (0.7 + 0.3 * lfo_for_pad))
print("    PAD      -> LFO filter mod (sine, 0.15Hz, depth=40%)")

arp_1d = stems["ARP"] if stems["ARP"].ndim == 1 else stems["ARP"][:, 0]
lfo_for_arp = lfo_arp_wave[:len(arp_1d)]
if len(lfo_for_arp) < len(arp_1d):
    lfo_for_arp = np.pad(lfo_for_arp, (0, len(arp_1d) - len(lfo_for_arp)))
stems["ARP"] = to_np(arp_1d * (0.8 + 0.2 * lfo_for_arp))
print("    ARP      -> LFO pan mod (triangle, 0.25Hz, depth=30%)")

# ── v9: Vocal Processing ─────────────────────────────────────────────
print("  v9: Vocal processing (pitch correction + FX)...")
vocal_1d = stems["VOCAL"] if stems["VOCAL"].ndim == 1 else stems["VOCAL"][:, 0]
stems["VOCAL"] = to_np(apply_vocal_processing(vocal_1d, VOCAL_FX, SR))
print("    VOCAL    -> pitch_correct (speed=0.6, sat=0.15)")

# ── Low Pass Gate on drone ────────────────────────────────────────────
print("  Low Pass Gate on drone...")


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
print("    DRONE    -> LPG (rate=0.12Hz, depth=50%)")


# ====================================================================
#  STEM DYNAMICS ANALYSIS
# ====================================================================
print()
print("  Stem dynamics analysis...")
for name in STEM_NAMES:
    profile = analyze_dynamics(stems[name], SR)
    print(f"    {name:12s}  peak={profile.peak_db:+.1f}dB  "
          f"rms={profile.rms_db:+.1f}dB  "
          f"crest={profile.crest_factor_db:.1f}dB")


# ====================================================================
#  v6: DC REMOVAL ON ALL STEMS
# ====================================================================
print("  DC removal (highpass 5Hz)...")
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
        stems[name] = to_np(DC_ENGINE.remove_highpass(buf.tolist(),
                                                      cutoff=5.0))
print(f"    {len(STEM_NAMES)} stems DC-cleaned")


# ====================================================================
#  v9: TURBOQUANT COMPRESSION ON ALL STEMS
# ====================================================================
print()
print("  v9: TurboQuant phi-optimal compression on all stems...")
tq_results: dict[str, CompressedAudioBuffer] = {}

for name in STEM_NAMES:
    buf = stems[name]
    if buf.ndim == 2:
        buf = buf[:, 0]
    cab = compress_audio_buffer(
        buf.tolist(),
        buffer_id=f"WO9_{name}",
        sample_rate=SR,
        label=f"Wild Ones V9 {name}",
    )
    tq_results[name] = cab
    compressed_size = len(pickle.dumps(cab))
    original_size = len(buf) * 8  # float64 = 8 bytes
    ratio = original_size / max(compressed_size, 1)
    print(f"    {name:12s}  {original_size/1024:.0f}KB -> "
          f"{compressed_size/1024:.0f}KB  ({ratio:.1f}x)")

print(f"    {len(tq_results)} stems TurboQuant-compressed")


# ====================================================================
#  EXPORT STEMS + MIXDOWN + MIDI + ALS
# ====================================================================
print()
print("  Bouncing stems (24-bit)...")

os.makedirs("output/stems", exist_ok=True)
stem_paths: list[str] = []


def _pack_24bit(float_buf: np.ndarray, gain: float) -> bytes:
    """Convert float buffer to 24-bit packed bytes."""
    int_buf = np.clip(float_buf * gain * 8388607.0,
                      -8388608, 8388607).astype('<i4')
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
    path = f"output/stems/wild_ones_v9_{name}.wav"

    peak = float(np.max(np.abs(buf))) if len(buf) > 0 else 1.0
    gain = min(1.0, 0.95 / peak) if peak > 0 else 1.0

    if buf.ndim == 2 and buf.shape[1] == 2:
        packed_L = _pack_24bit(buf[:, 0], gain)
        packed_R = _pack_24bit(buf[:, 1], gain)
        interleaved = _interleave_24bit_stereo(packed_L, packed_R,
                                               buf.shape[0])
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


# ── Stereo mixdown with constant-power pan law ───────────────────────
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


# ── v9: Intelligent EQ on mix ────────────────────────────────────────
print("  v9: Intelligent EQ on stereo mix...")
mix_L_eq = to_np(auto_eq(mix_L[:total_samples].tolist(), SR))
mix_R_eq = to_np(auto_eq(mix_R[:total_samples].tolist(), SR))
# Blend: 60% EQ'd, 40% original (gentle correction)
mix_L = mix_L[:total_samples] * 0.4 + mix_L_eq * 0.6
mix_R = mix_R[:total_samples] * 0.4 + mix_R_eq * 0.6
print("    L + R -> auto_eq (60% blend)")


# ── v9: Mastering Chain (replaces auto_master) ───────────────────────
print("  v9: Mastering chain (full parametric master)...")
mc_settings = MCMasterSettings(
    target_lufs=-10.5,
    ceiling_db=-0.3,
    eq_low_shelf_db=PHI,         # +1.618 dB bass warmth
    eq_low_shelf_freq=80.0,
    eq_high_shelf_db=1.0 / PHI,  # +0.618 dB air
    eq_high_shelf_freq=10000.0,
    eq_mid_boost_db=0.5,
    eq_mid_freq=3000.0,
    eq_mid_q=1.5,
    compression_threshold_db=-12.0,
    compression_ratio=3.0,
    compression_attack_ms=8.0,
    compression_release_ms=50.0 * PHI,
    stereo_width=1.05,
    limiter_enabled=True,
)

# Process L and R separately
mastered_L, report_L = master_chain(mix_L[:total_samples], SR, mc_settings)
mastered_R, report_R = master_chain(mix_R[:total_samples], SR, mc_settings)

# Ensure they're numpy arrays
mastered_L = to_np(mastered_L)
mastered_R = to_np(mastered_R)

print(f"    Mastering chain applied (target -10.5 LUFS)")

# Also run auto_master for comparison report
print("  Legacy auto_master comparison...")
legacy_settings = MasterSettings(
    target_lufs=-10.5,
    ceiling_db=-0.3,
    eq_enabled=True,
    multiband=True,
    stereo_enhance=True,
    bass_boost_db=PHI,
    air_boost_db=1.0 / PHI,
    limiter_release_ms=50.0 * PHI,
)
legacy_L = auto_master(mix_L[:total_samples].tolist(), legacy_settings, SR)
legacy_R = auto_master(mix_R[:total_samples].tolist(), legacy_settings, SR)
print(f"    Legacy LUFS: L={legacy_L.input_lufs:.1f}->{legacy_L.output_lufs:.1f}  "
      f"R={legacy_R.input_lufs:.1f}->{legacy_R.output_lufs:.1f}")
print(f"    Stages: {', '.join(legacy_L.stages_applied)}")


# ── Export mastered WAV ──────────────────────────────────────────────
os.makedirs("output", exist_ok=True)
output_path = "output/wild_ones_v9.wav"

# v6: Apply PHI dithering before 24-bit export
print("  Applying PHI dithering (24-bit, noise-shaped)...")
dithered_L = to_np(DITHER_ENGINE.apply_dither(
    mastered_L.tolist() if isinstance(mastered_L, np.ndarray)
    else mastered_L, DITHER_CFG))
dithered_R = to_np(DITHER_ENGINE.apply_dither(
    mastered_R.tolist() if isinstance(mastered_R, np.ndarray)
    else mastered_R, DITHER_CFG))

# 24-bit stereo mastered export
packed_L = _pack_24bit(dithered_L, 1.0)
packed_R = _pack_24bit(dithered_R, 1.0)
interleaved = _interleave_24bit_stereo(packed_L, packed_R, total_samples)

with wave.open(output_path, "w") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(3)
    wf.setframerate(SR)
    wf.writeframes(bytes(interleaved))


# ── MIDI export ──────────────────────────────────────────────────────
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
        root_midi = [MIDI["Ab4"], MIDI["C5"], MIDI["F4"],
                     MIDI["Db4"]][chord_idx]
        b = (section_start + bar) * 4
        vocal_events.append(NoteEvent(
            pitch=root_midi, start_beat=b,
            duration_beats=2.0, velocity=75))

growl_events: list[NoteEvent] = []
for section_start, section_len in [(SEC_VIP, VIP_DROP_BARS),
                                    (SEC_FINAL, FINAL_CHORUS_BARS)]:
    for bar in range(section_len):
        chord_idx = (bar // 2) % 4
        root_midi = [MIDI["Ab2"], MIDI["C3"], MIDI["F2"],
                     MIDI["Db3"]][chord_idx]
        b = (section_start + bar) * 4
        growl_events.append(NoteEvent(
            pitch=root_midi, start_beat=b,
            duration_beats=2.0, velocity=100))

# v9: Wobble MIDI
wobble_events: list[NoteEvent] = []
for section_start, section_len in [(SEC_CHORUS1, CHORUS1_BARS),
                                    (SEC_CHORUS2, CHORUS2_BARS),
                                    (SEC_VIP, VIP_DROP_BARS),
                                    (SEC_FINAL, FINAL_CHORUS_BARS)]:
    for bar in range(section_len):
        chord_idx = (bar // 2) % 4
        root_midi = [MIDI["Ab1"], MIDI["C2"], MIDI["F2"],
                     MIDI["Db2"]][chord_idx]
        b = (section_start + bar) * 4
        wobble_events.append(NoteEvent(
            pitch=root_midi, start_beat=b,
            duration_beats=2.0, velocity=95))

midi_tracks = [
    ("Bass", bass_events),
    ("Hook", hook_events),
    ("Chords", chord_events),
    ("Vocal", vocal_events),
    ("Growl", growl_events),
    ("Wobble", wobble_events),  # v9
]

midi_path = "output/midi/wild_ones_v9.mid"
write_midi_file(midi_tracks, midi_path, bpm=BPM)
total_notes = sum(len(evts) for _, evts in midi_tracks)
print(f"    {midi_path}  ({total_notes} notes)")


# ====================================================================
#  ABLETON LIVE SET
# ====================================================================
print("  Generating Enhanced Ableton Live project (v9)...")

stem_colors = {
    "DRUMS": 1, "BASS": 3, "GROWL": 4, "CHORDS": 12, "HOOK": 20,
    "PAD": 24, "VOCAL": 36, "ARP": 16, "RISER": 32,
    "FX": 40, "TEXTURE": 44, "DRONE": 28,
    # v9:
    "WOBBLE": 5, "SUB": 2, "RIDDIM": 6, "FORMANT": 8,
}

STEM_SENDS = {
    "DRUMS": [0.05, 0.10], "BASS": [0.0, 0.0],
    "GROWL": [0.10, 0.15], "CHORDS": [0.25, 0.20],
    "HOOK": [0.15, 0.25], "PAD": [0.35, 0.15],
    "VOCAL": [0.30, 0.10], "ARP": [0.20, 0.30],
    "RISER": [0.15, 0.10], "FX": [0.10, 0.10],
    "TEXTURE": [0.40, 0.20], "DRONE": [0.30, 0.05],
    # v9:
    "WOBBLE": [0.08, 0.12], "SUB": [0.0, 0.0],
    "RIDDIM": [0.08, 0.10], "FORMANT": [0.12, 0.15],
}

als_tracks = []

STEM_VOLUME_DB = {
    "DRUMS": 0.0, "VOCAL": -1.0, "BASS": -2.0, "HOOK": -3.5,
    "CHORDS": -4.0, "GROWL": -3.0, "PAD": -6.0, "ARP": -7.0,
    "RISER": -8.0, "FX": -6.0, "TEXTURE": -10.0, "DRONE": -9.0,
    # v9:
    "WOBBLE": -3.5, "SUB": -4.0, "RIDDIM": -3.5, "FORMANT": -5.0,
}

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

# Audio tracks with arrangement clips + automations + sends
for idx, name in enumerate(STEM_NAMES):
    stem_abs = os.path.abspath(f"output/stems/wild_ones_v9_{name}.wav")
    clip_info = ALSClipInfo(
        path=stem_abs,
        start_beat=0.0,
        length_beats=total_bars * 4.0,
        warp_mode=0,
        gain=0.85,
        name=f"{name}_V9",
    )

    track_autos = []

    # Volume automation: curved fade in/out
    vol_auto = ALSAutomation(
        parameter_name="Volume",
        points=[
            ALSAutomationPoint(time=0.0, value=0.0, curve=0.4),
            ALSAutomationPoint(time=INTRO_BARS * 4.0, value=1.0),
            ALSAutomationPoint(time=(total_bars - OUTRO_BARS) * 4.0,
                               value=1.0, curve=-0.3),
            ALSAutomationPoint(time=total_bars * 4.0, value=0.0),
        ],
    )
    track_autos.append(vol_auto)

    # LP filter sweeps on builds
    if name in ("CHORDS", "PAD", "ARP"):
        track_autos.append(make_lp_sweep_automation(
            "Filter Cutoff", SEC_PRE1 * 4.0, SEC_CHORUS1 * 4.0,
            closed_val=0.12, open_val=0.95, curve=0.4,
        ))
        track_autos.append(make_lp_sweep_automation(
            "Filter Cutoff", SEC_PRE2 * 4.0, SEC_CHORUS2 * 4.0,
            closed_val=0.08, open_val=1.0, curve=0.5,
        ))

    # Sine tremolo on ARP during bridge
    if name == "ARP":
        track_autos.append(make_sine_automation(
            "Volume_Mod", SEC_BRIDGE * 4.0, SEC_VIP * 4.0,
            min_val=0.3, max_val=0.8, cycles=4, resolution=32,
        ))

    # Sawtooth filter on BASS/GROWL during VIP
    if name in ("BASS", "GROWL", "WOBBLE", "RIDDIM"):
        track_autos.append(make_sawtooth_automation(
            "Filter Cutoff", SEC_VIP * 4.0, SEC_FINAL * 4.0,
            min_val=0.15, max_val=0.85, cycles=4, resolution=32,
        ))

    # Dynamic send automation on VOCAL
    if name == "VOCAL":
        track_autos.append(make_section_send_automation(
            "Send 0", _REVERB_SEND_SECTIONS, total_bars,
        ))

    # Instant filter open on drops
    if name == "CHORDS":
        for drop_bar in [SEC_CHORUS1, SEC_CHORUS2, SEC_VIP, SEC_FINAL]:
            track_autos.append(ALSAutomation(
                parameter_name="Filter_Reset",
                points=[
                    ALSAutomationPoint(time=drop_bar * 4.0 - 0.01,
                                       value=0.0),
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
                   "Vocal_MIDI", "Growl_MIDI", "Wobble_MIDI"]:
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
    ALSScene(name="BRIDGE_GOLDEN", tempo=float(BPM)),
    ALSScene(name="VIP_DROP", tempo=float(BPM)),
    ALSScene(name="FINAL_CHORUS", tempo=float(BPM)),
    ALSScene(name="OUTRO", tempo=float(BPM)),
]

als_cue_points = []
for sec_name, (bar_start, bar_len) in SECTION_MAP.items():
    als_cue_points.append(ALSCuePoint(
        name=sec_name,
        time=bar_start * 4.0,
    ))
als_cue_points.append(ALSCuePoint(
    name="GOLDEN_SECTION",
    time=golden_section_bar * 4.0,
))

project = ALSProject(
    name="Wild_Ones_V9",
    bpm=float(BPM),
    tracks=als_tracks,
    scenes=als_scenes,
    notes="Wild Ones V9 (ULTIMATE Edition) | "
          "Ab major | 127 BPM | 440 Hz | 144 bars (Fibonacci!) | "
          "Chords: Ab-Cm-Fm-Db | 19 NEW engine modules | "
          "16 stems | TurboQuant | Mastering Chain | "
          "Wobble + Sub + Riddim + Formant | "
          "Golden Section: bar 89 (Bridge)",
    cue_points=als_cue_points,
)

os.makedirs("output/ableton", exist_ok=True)
als_path = "output/ableton/Wild_Ones_V9.als"
write_als(project, als_path)


# ====================================================================
#  ABLETON BRIDGE + LINK SYNC
# ====================================================================
print()
print("  Ableton Live integration status...")

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
    if f.startswith("wild_ones_v9_") and f.endswith(".wav")
)

print()
print("=" * 68)
print('  DUBFORGE -- "Wild Ones" V9 (ULTIMATE Edition)')
print("=" * 68)
print(f"  Format:    24-bit WAV @ {SR} Hz")
print(f"  BPM:       {BPM}  |  Key: Ab major  |  Tuning: 440 Hz")
print(f"  Chords:    Ab - Cm - Fm - Db  (I - iii - vi - IV)")
print(f"  Duration:  {duration:.1f}s "
      f"({int(duration // 60)}:{int(duration % 60):02d})")
print(f"  Bars:      {total_bars} (FIBONACCI!)  "
      f"(Golden Section Point: bar ~{golden_section_bar})")
print()
print("  V9 ULTIMATE Enhancements (19 new engine modules):")
print("    [SYNTHESIS]")
print("    * Wobble bass — LFO-driven filter wobble (WOBBLE stem)")
print("    * Sub bass — dedicated sub-40Hz sine layer (SUB stem)")
print("    * Formant bass — vowel-shifting talking bass (FORMANT stem)")
print("    * Riddim engine — gap-based riddim patterns (RIDDIM stem)")
print("    * Additive synth — phi-partial harmonic layers")
print("    * Perc synth — custom electronic percussion (click+zap+thud)")
print("    * Karplus-Strong — organic pluck sounds")
print("    * Wavetable morph — evolving spectral textures")
print("    * Sound palette — tonal color consistency (5 phi-spaced tones)")
print("    * Chord progression — programmatic chord generation")
print("    [PROCESSING]")
print("    * Multiband distortion — tube/tape on growl + wobble")
print("    * Wave folder — harmonic enrichment on bass (2.5x, 30% blend)")
print("    * Intelligent EQ — spectral auto-balance on mix (60% blend)")
print("    * LFO matrix — modulation on pad filter + arp pan")
print("    * Vocal processor — pitch correction + FX on vocals")
print("    * Pitch automation — pitch dives on all drop entries")
print("    * Convolution reverb — plate on pad, room on drone")
print("    [MASTERING]")
print("    * Mastering chain — full parametric master (replaces auto_master)")
print("    * TurboQuant — phi-optimal compression on all 16 stems")
print()
print("  INHERITED from V6:")
print("    * 24-bit WAV export + PHI dithering")
print("    * SaturationEngine (tape/tube) on bass/growl/hook")
print("    * DC removal (highpass 5Hz) on all stems")
print("    * Granular shimmer + dust textures")
print("    * Vinyl noise bed + white air noise")
print("    * 144 bars Fibonacci structure with VIP Drop")
print("    * Growl resampler + phi harmonics + beat repeat")
print("    * Per-stem dynamics (transient, compress, de-ess)")
print("    * Multi-technique stereo imaging")
print("    * Phi crossfades + ALS automation + Ableton integration")
print()
print(f"  Stems:     {len(STEM_NAMES)} tracks in output/stems/")
for name in STEM_NAMES:
    marker = " (NEW)" if name in ("WOBBLE", "SUB", "RIDDIM", "FORMANT") else ""
    print(f"             - {name}{marker}")
print(f"  Stems:     {stem_dir_size / 1024 / 1024:.1f} MB total")
print(f"  Mixdown:   {output_path} ({file_size / 1024 / 1024:.1f} MB)")
print(f"  MIDI:      {midi_path} ({total_notes} notes)")
print(f"  Serum 2:   output/serum2/wild_ones_v9_patches.json")
print(f"  Presets:   output/presets/ ({len(fxp_presets)} .fxp + 1 .fxb bank)")
print(f"  Ableton:   {als_path} (cue points: {len(als_cue_points)}, "
      f"tracks: {len(als_tracks)})")
print(f"  TQ:        {len(tq_results)} stems compressed")
print()
print("  Structure:")
print(f"    Intro          {INTRO_BARS:3d} bars")
print(f"    Verse 1        {VERSE1_BARS:3d} bars")
print(f"    Pre-Chorus 1   {PRECHORUS1_BARS:3d} bars")
print(f"    Chorus 1       {CHORUS1_BARS:3d} bars  (hook + full drop + wobble)")
print(f"    Break          {BREAK_BARS:3d} bars  (ACAPELLA + KS plucks)")
print(f"    Verse 2        {VERSE2_BARS:3d} bars")
print(f"    Pre-Chorus 2   {PRECHORUS2_BARS:3d} bars")
print(f"    Chorus 2       {CHORUS2_BARS:3d} bars  (max energy + wobble)")
print(f"    Bridge         {BRIDGE_BARS:3d} bars  (GOLDEN SECTION + morph)")
print(f"    VIP Drop       {VIP_DROP_BARS:3d} bars  (GROWL+WOBBLE+RIDDIM+FORMANT)")
print(f"    Final Chorus   {FINAL_CHORUS_BARS:3d} bars  (CLIMAX — all 16 stems)")
print(f"    Outro          {OUTRO_BARS:3d} bars")
print(f"    TOTAL         {total_bars:3d} bars (= Fibonacci 144)")
print()
print("  Song DNA Reference: Wild Ones (Flo Rida feat. Sia)")
print("    Ab major | 127 BPM | Ab-Cm-Fm-Db | Vocal range Eb4-C5")
print("    Vocals: studio acapella (Sia & Flo Rida)")
print("    Instrumental: 100% synthesized by DUBFORGE engines")
print("    V9: 19 new modules + TurboQuant + mastering chain + 16 stems")
print("=" * 68)


# ── Install to Ableton User Library ──────────────────────────────────
print()
print("  Installing to Ableton User Library...")
import shutil
from pathlib import Path

_user_lib = None
for _candidate in [
    Path.home() / "Documents" / "Ableton" / "User Library",
    Path.home() / "Music" / "Ableton" / "User Library",
    Path(os.environ.get("ABLETON_USER_LIBRARY", ""))
    if os.environ.get("ABLETON_USER_LIBRARY") else None,
]:
    if _candidate and _candidate.exists():
        _user_lib = _candidate
        break

if _user_lib:
    _installed = 0

    _stems_dst = (_user_lib / "Samples" / "DUBFORGE" / "Wild_Ones_V9"
                  / "Stems")
    _stems_dst.mkdir(parents=True, exist_ok=True)
    for _f in Path("output/stems").glob("wild_ones_v9_*.wav"):
        shutil.copy2(_f, _stems_dst / _f.name)
        _installed += 1
    print(f"    Stems:   {_installed} -> {_stems_dst}")

    _midi_dst = (_user_lib / "Samples" / "DUBFORGE" / "Wild_Ones_V9"
                 / "MIDI")
    _midi_dst.mkdir(parents=True, exist_ok=True)
    for _f in Path("output/midi").glob("wild_ones_v9*.mid"):
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

    _rs_dst = _user_lib / "Remote Scripts" / "DUBFORGE"
    _rs_dst.mkdir(parents=True, exist_ok=True)
    _rs_src = Path("output/remote_scripts/DUBFORGE/__init__.py")
    if _rs_src.exists():
        shutil.copy2(_rs_src, _rs_dst / "__init__.py")
        _installed += 1
        print(f"    Remote:  1 -> {_rs_dst}")

    _m4l_dst = _user_lib / "Max for Live Devices" / "DUBFORGE"
    _m4l_dst.mkdir(parents=True, exist_ok=True)
    _m4l_src = Path("output/m4l/DUBFORGE_Control.js")
    if _m4l_src.exists():
        shutil.copy2(_m4l_src, _m4l_dst / "DUBFORGE_Control.js")
        _installed += 1
        print(f"    M4L:     1 -> {_m4l_dst}")

    print(f"    TOTAL:   {_installed} files installed")
else:
    print("    Ableton User Library not found "
          "(set ABLETON_USER_LIBRARY env var)")


# ── Open in Ableton Live ─────────────────────────────────────────────
print()
_ableton_running = False
_ableton_exe = None

try:
    _tasklist = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq Ableton Live*",
         "/FO", "CSV", "/NH"],
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
    print("  Ableton Live is running -- opening project...")
    subprocess.Popen(["cmd", "/c", "start", "", _als_abs],
                     creationflags=0x08000000)
elif _ableton_exe:
    print(f"  Ableton Live installed ({_ableton_exe.stem}) but not running.")
    print(f"  Launching Ableton with project...")
    subprocess.Popen([str(_ableton_exe), _als_abs],
                     creationflags=0x08000000)
else:
    print("  WARNING: Ableton Live not detected -- skipping auto-open.")
    print(f"  Install Ableton, then open: {_als_abs}")

print("  Done. Wild Ones V9 Remix -- ULTIMATE edition pipeline complete.")
print()
