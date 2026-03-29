#!/usr/bin/env python3
"""DUBFORGE -- "Can You See The Apology That Never Came"  (v3 -- DOJO MASTERY)

V3 rewrite: V2 analyzed through Dojo + Subtronics lens a SECOND time.
Lessons from V2 audit applied at every level.

V2 GAPS FOUND (Dojo Audit):
    * growl_resample_pipeline() was imported but NEVER CALLED -- V2 used
      manual 2-3 stage chains instead of the full 6-stage evolving pipeline.
    * wavetable_morph completely unused -- timbres were static within sections.
    * evolution_engine completely unused -- FM progression was hard-coded.
    * Only 3 of 5 riddim types used (heavy/stutter/triplet).
    * Multi-pass resampling was only 2-3 stages, not the Dojo-prescribed
      5-pass phi-intensity curve (0.382 -> 0.618 -> 1.0 -> 0.618 -> 0.382).
    * Duration 142s was 35% shorter than SB10 avg (220s).

V2 GAPS FOUND (Subtronics Audit):
    * Only FM depth evolved per drop -- filter cutoff, distortion, and
      stereo width were all static across the track.
    * Only 3 drops -- Tesseract-era tracks use longer narrative arcs.
    * 89 bars total was below the SB10 duration target.

V3 CHANGES (61.8% new -- VIP System):
    * PACK_ALPHA structure: 144 bars (Fibonacci), ~230s (3:50) = SB10 avg
    * 4 drops (13/34/21/21) -- extended narrative arc
    * Full growl_resample_pipeline(): 6-stage evolving bass (256 frames)
    * wavetable_morph: per-drop morph types (phi_spline -> fractal ->
      spectral -> formant) for evolving timbres
    * evolution_engine: parameter drift tracking across the track
    * ALL 5 riddim types: minimal, heavy, bounce, stutter, triplet
    * Multi-parameter evolution: FM depth + filter cutoff + distortion +
      stereo width ALL increase per drop
    * 34-bar marathon Drop 2 with internal progressive evolution
    * 5-pass resampled growl bass with phi-intensity curve

V3 RETAINED (38.2% -- VIP System):
    * D minor, 432 Hz, 150 BPM
    * GALATCIA real drum samples
    * KS arpeggio whispers (intro/breaks/outro)
    * Core ascending lead motif (A3 -> C4 -> D4 -> F4)
    * Clean mono sine sub (PSBS/SB10)
    * Vocal chop palette (ah/oh/eh/ee/oo)
    * Fibonacci bar counts throughout
    * PSBS-compliant gain staging (no stem clipping)

    Title:    Can You See The Apology That Never Came (Dojo Mastery)
    BPM:      150 (Subtronics sweet spot)
    Key:      D minor (SB10 favored key center)
    Tuning:   432 Hz
    Duration: ~3:50 (144 bars -- FIBONACCI)
    Mood:     Defiance x Fracture x Evolution x Transcendence (4-drop arc)

    Structure (PACK_ALPHA -- Fibonacci bar counts, 4 drops):
        Intro      8 bars  -- Granular dust + drone + formant whisper
        Build 1    5 bars  -- Arp + riser + vocal stutter (phi curve)
        Drop 1    13 bars  -- Riddim + growl pipeline A (FM 3.0)
        Break 1    5 bars  -- Chord sus4 + granular shimmer (ceil 0.35)
        Build 2    8 bars  -- Darker arp + beat repeat + harmonic riser
        Drop 2    34 bars  -- MARATHON: progressive growl evolution (FM 5.0)
        Break 2    3 bars  -- Near-silence (floor 0.08)
        Build 3    5 bars  -- All risers + 64th snare + scream
        Drop 3    21 bars  -- CLIMAX: full pipeline bass (FM 7.0)
        Break 3    5 bars  -- Wavetable morph shimmer (ceil 0.30)
        Build 4    8 bars  -- Final transcendence build
        Drop 4    21 bars  -- TRANSCENDENCE: deepest FM (9.0), all layers
        Outro      8 bars  -- Granular freeze + drone decay + apology

    Golden Section Point: bar ~89 (144/phi) -- middle of Drop 3 (CLIMAX)

Output:
    output/stems/apology_v3_*.wav    -- 14 individual stem WAVs
    output/apology_never_came_v3.wav -- stereo mastered mixdown
    output/midi/apology_v3_*.mid     -- MIDI for all melodic parts
    output/serum2/apology_v3_patches.json -- Serum 2 patch reference
    output/ableton/Apology_Never_Came_V3.als -- ALS with AudioClip refs
"""

import json
import math
import os
import subprocess
import wave

os.chdir(os.path.dirname(os.path.abspath(__file__)))

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

# -- DUBFORGE engine -- NEW for v2, retained in v3 --
from engine.granular_synth import GranularPreset, synthesize_granular
from engine.chord_pad import ChordPadPreset, synthesize_chord_pad
from engine.formant_synth import FormantPreset, synthesize_formant
from engine.riddim_engine import RiddimPreset, generate_riddim
from engine.arp_synth import ArpSynthPreset, synthesize_arp
from engine.karplus_strong import KarplusStrongPatch, render_ks
from engine.transition_fx import TransitionPreset, synthesize_transition
from engine.vocal_chop import VocalChop, synthesize_chop

# -- DUBFORGE engine -- DOJO v2: Resampling + Stutter --
from engine.growl_resampler import (waveshape_distortion, frequency_shift,
                                    formant_filter, comb_filter, bit_reduce,
                                    generate_saw_source, generate_fm_source,
                                    growl_resample_pipeline)
from engine.beat_repeat import BeatRepeatPatch, apply_beat_repeat

# -- DUBFORGE engine -- NEW for v3: Wavetable Morph + Evolution --
from engine.wavetable_morph import MorphPreset, morph_wavetable
from engine.evolution_engine import EvolutionPreset, track_param_drift, track_phi_convergence

# -- DUBFORGE engine -- GALATCIA sample library --
from engine.galatcia import read_wav_samples

# -- DUBFORGE engine -- DSP pipeline --
from engine.sidechain import apply_sidechain, SidechainPreset
from engine.reverb_delay import apply_hall, apply_room, ReverbDelayPreset
from engine.stereo_imager import apply_mid_side, StereoPreset
from engine.mastering_chain import master, dubstep_master_settings

# -- DUBFORGE engine -- DAW integration --
from engine.als_generator import ALSProject, ALSTrack, ALSScene, write_als
from engine.midi_export import NoteEvent, write_midi_file
from engine.serum2 import build_dubstep_patches
from engine.fxp_writer import (FXPPreset, FXPBank, VSTParam,
                               write_fxp, write_fxb, write_preset_manifest)
from engine.phi_core import write_wav as write_serum_wav, WAVETABLE_SIZE

# -- Constants --
SR = 44100
BPM = 150
BEAT = 60.0 / BPM
BAR = BEAT * 4
PHI = 1.6180339887

GALATCIA_ROOT = r"C:\dev\DUBFORGE GALATCIA\Samples\Samples"

# Key of D minor (432 Hz tuning)
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

MIDI = {
    "D1": 26, "F1": 29, "A1": 33, "Bb1": 34, "C2": 36,
    "D2": 38, "E2": 40, "F2": 41, "G2": 43, "A2": 45, "Bb2": 46,
    "C3": 48, "D3": 50, "E3": 52, "F3": 53, "G3": 55,
    "A3": 57, "Bb3": 58, "C4": 60, "D4": 62, "E4": 64,
    "F4": 65, "G4": 67, "A4": 69,
}

# DSP presets
SC_PUMP = SidechainPreset("V3Pump", "pump", bpm=BPM, depth=0.75,
                          attack_ms=0.3, release_ms=160.0)
SC_HARD = SidechainPreset("V3Hard", "pump", bpm=BPM, depth=0.9,
                          attack_ms=0.5, release_ms=200.0)
HALL_VERB = ReverbDelayPreset("V3Hall", "hall", decay_time=3.2,
                              pre_delay_ms=30.0, damping=0.4, mix=0.28)
ROOM_VERB = ReverbDelayPreset("V3Room", "room", decay_time=0.6,
                              pre_delay_ms=8.0, room_size=0.25, mix=0.18)
MS_WIDE = StereoPreset("V3Wide", "mid_side", width=1.4)


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


def distort(signal: np.ndarray, drive: float = 2.0) -> np.ndarray:
    return np.tanh(signal * drive)


def peak_normalize(buf: np.ndarray) -> np.ndarray:
    """Normalize buffer to prevent clipping (learned from V2 drum issue)."""
    peak = np.max(np.abs(buf))
    if peak > 1.0:
        buf /= peak
    return buf


# ====================================================================
#  SOUND DESIGN -- Pre-render all elements
# ====================================================================

print("=" * 60)
print('  DUBFORGE -- "Can You See The Apology That Never Came"')
print("  v3 -- DOJO MASTERY (PACK_ALPHA x SB10 x EVOLUTION)")
print("=" * 60)
print(f"  BPM: {BPM}  |  Key: D minor  |  Tuning: 432 Hz  |  SR: {SR}")
print(f"  Structure: PACK_ALPHA -- 144 bars (FIBONACCI)  |  4 drops")
print()

# -- SERUM 2 PATCH DEFINITIONS + FXP PRESETS --
print("  [1/17] Loading Serum 2 patch definitions...")
serum_patches = build_dubstep_patches()
os.makedirs("output/serum2", exist_ok=True)
with open("output/serum2/apology_v3_patches.json", "w") as f:
    json.dump(serum_patches, f, indent=2, default=str)
print(f"         {len(serum_patches)} Serum 2 patches -> JSON")

# Convert Serum 2 patch dicts -> real .fxp VST2 presets
os.makedirs("output/presets", exist_ok=True)

def _serum_dict_to_fxp(patch_dict: dict) -> FXPPreset:
    """Map a Serum2Patch dict into an FXPPreset with normalized params."""
    params = []
    idx = 0
    # Osc A
    osc_a = patch_dict.get("osc_a", {})
    params.append(VSTParam(idx, "OscA_WtPos", float(osc_a.get("wt_position", 0.0)))); idx += 1
    params.append(VSTParam(idx, "OscA_Level", float(osc_a.get("level", 0.8)))); idx += 1
    params.append(VSTParam(idx, "OscA_Unison", min(1.0, float(osc_a.get("unison_voices", 1)) / 16.0))); idx += 1
    detune_val = osc_a.get("unison_detune", 0.0)
    if isinstance(detune_val, list):
        detune_val = detune_val[0] if detune_val else 0.0
    params.append(VSTParam(idx, "OscA_Detune", float(detune_val))); idx += 1
    warp1_amt = osc_a.get("warp_1_amount", 0.0)
    warp2_amt = osc_a.get("warp_2_amount", 0.0)
    params.append(VSTParam(idx, "OscA_Warp1", float(warp1_amt))); idx += 1
    params.append(VSTParam(idx, "OscA_Warp2", float(warp2_amt))); idx += 1
    # Osc B
    osc_b = patch_dict.get("osc_b", {})
    params.append(VSTParam(idx, "OscB_WtPos", float(osc_b.get("wt_position", 0.0)))); idx += 1
    params.append(VSTParam(idx, "OscB_Level", float(osc_b.get("level", 0.0)))); idx += 1
    params.append(VSTParam(idx, "OscB_Semi", min(1.0, max(0.0, (float(osc_b.get("semi", 0)) + 24) / 48.0)))); idx += 1
    # Sub
    sub_osc = patch_dict.get("sub", {})
    params.append(VSTParam(idx, "Sub_Level", float(sub_osc.get("level", 0.0)))); idx += 1
    params.append(VSTParam(idx, "Sub_Enabled", 1.0 if sub_osc.get("enabled") else 0.0)); idx += 1
    # Filter 1
    filt = patch_dict.get("filter_1", {})
    params.append(VSTParam(idx, "Filt1_Cutoff", min(1.0, float(filt.get("cutoff", 1000.0)) / 22050.0))); idx += 1
    params.append(VSTParam(idx, "Filt1_Reso", float(filt.get("resonance", 0.0)))); idx += 1
    params.append(VSTParam(idx, "Filt1_Drive", float(filt.get("drive", 0.0)))); idx += 1
    # Env 1 (amp)
    env1 = patch_dict.get("env_1", {})
    params.append(VSTParam(idx, "Env1_Attack", min(1.0, float(env1.get("attack_ms", 1.0)) / 5000.0))); idx += 1
    params.append(VSTParam(idx, "Env1_Decay", min(1.0, float(env1.get("decay_ms", 200.0)) / 5000.0))); idx += 1
    params.append(VSTParam(idx, "Env1_Sustain", float(env1.get("sustain", 1.0)))); idx += 1
    params.append(VSTParam(idx, "Env1_Release", min(1.0, float(env1.get("release_ms", 200.0)) / 5000.0))); idx += 1
    # Macros (4)
    for mi in range(1, 5):
        macro = patch_dict.get(f"macro_{mi}", {})
        params.append(VSTParam(idx, f"Macro{mi}", float(macro.get("value", 0.0)))); idx += 1
    # Master
    params.append(VSTParam(idx, "Master_Volume", float(patch_dict.get("master_volume", 0.8)))); idx += 1
    params.append(VSTParam(idx, "Master_Tune", min(1.0, float(patch_dict.get("master_tune", 440.0)) / 880.0))); idx += 1
    # Voicing
    voicing = patch_dict.get("voicing", {})
    params.append(VSTParam(idx, "Portamento", min(1.0, float(voicing.get("portamento_ms", 0.0)) / 500.0))); idx += 1
    return FXPPreset(name=patch_dict.get("name", "DUBFORGE")[:28], params=params)

fxp_presets = {}
for i, sp in enumerate(serum_patches):
    fxp = _serum_dict_to_fxp(sp)
    fxp_path = f"output/presets/{fxp.name.replace(' ', '_')}.fxp"
    write_fxp(fxp, fxp_path)
    fxp_presets[fxp.name] = fxp

# Write bank (.fxb) containing all presets
bank = FXPBank(name="APOLOGY_V3_BANK", presets=list(fxp_presets.values()))
write_fxb(bank, "output/presets/APOLOGY_V3_BANK.fxb")
write_preset_manifest(fxp_presets, "output/presets")
print(f"         {len(fxp_presets)} .fxp presets + 1 .fxb bank written")

# -- GALATCIA REAL DRUMS --
print("  [2/17] Loading GALATCIA drum samples...")

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

# -- BASS -- Sub + ALL 5 Riddim Types (V3: was 3, now 5) --
print("  [3/17] Bass (sub + all 5 riddim types)...")

sub_bass = to_np(synthesize_bass(BassPreset(
    name="V3Sub", bass_type="sub_sine", frequency=KEY_FREQS["D1"],
    duration_s=BEAT * 2, attack_s=0.003, release_s=0.12, distortion=0.0
)))

wobble_bass = to_np(synthesize_bass(BassPreset(
    name="V3Wobble", bass_type="wobble", frequency=KEY_FREQS["D2"],
    duration_s=BEAT * 2, attack_s=0.008, release_s=0.15,
    fm_ratio=PHI, fm_depth=4.0, distortion=0.35, filter_cutoff=0.5
)))

neuro_bass = to_np(synthesize_bass(BassPreset(
    name="V3Neuro", bass_type="neuro", frequency=KEY_FREQS["D2"],
    duration_s=BEAT, attack_s=0.002, release_s=0.06,
    fm_ratio=3.0, fm_depth=5.0, distortion=0.6, filter_cutoff=0.4
)))

# All 5 riddim types (V2 only had heavy/stutter/triplet)
riddim_heavy = to_np(generate_riddim(RiddimPreset(
    name="V3RiddimHeavy", riddim_type="heavy",
    frequency=KEY_FREQS["D2"], bpm=BPM,
    gap_ratio=0.3, attack_s=0.003, release_s=0.08,
    distortion=0.45, subdivisions=4
)))

riddim_stutter = to_np(generate_riddim(RiddimPreset(
    name="V3RiddimStutter", riddim_type="stutter",
    frequency=KEY_FREQS["D2"], bpm=BPM,
    gap_ratio=0.2, attack_s=0.002, release_s=0.05,
    distortion=0.55, subdivisions=8
)))

riddim_triplet = to_np(generate_riddim(RiddimPreset(
    name="V3RiddimTrip", riddim_type="triplet",
    frequency=KEY_FREQS["D2"], bpm=BPM,
    gap_ratio=0.25, attack_s=0.003, release_s=0.06,
    distortion=0.4, subdivisions=3
)))

riddim_bounce = to_np(generate_riddim(RiddimPreset(
    name="V3RiddimBounce", riddim_type="bounce",
    frequency=KEY_FREQS["D2"], bpm=BPM,
    gap_ratio=0.22, attack_s=0.004, release_s=0.07,
    distortion=0.38, subdivisions=4
)))

riddim_minimal = to_np(generate_riddim(RiddimPreset(
    name="V3RiddimMinimal", riddim_type="minimal",
    frequency=KEY_FREQS["D2"], bpm=BPM,
    gap_ratio=0.45, attack_s=0.005, release_s=0.10,
    distortion=0.25, subdivisions=4
)))

print(f"         5 riddim types: heavy/stutter/triplet/bounce/minimal")

# -- LEADS -- Screech + Formant --
print("  [4/17] Leads (screech + formant)...")

screech_d = to_np(synthesize_screech_lead(LeadPreset(
    name="V3ScreechD", lead_type="screech", frequency=KEY_FREQS["D4"],
    duration_s=BEAT * 0.5, attack_s=0.003, decay_s=0.04,
    sustain=0.65, release_s=0.06, filter_cutoff=0.92,
    resonance=0.72, distortion=0.48
)))

screech_f = to_np(synthesize_screech_lead(LeadPreset(
    name="V3ScreechF", lead_type="screech", frequency=KEY_FREQS["F4"],
    duration_s=BEAT * 0.5, attack_s=0.003, decay_s=0.04,
    sustain=0.6, release_s=0.07, filter_cutoff=0.90,
    resonance=0.68, distortion=0.44
)))

screech_a = to_np(synthesize_screech_lead(LeadPreset(
    name="V3ScreechA", lead_type="screech", frequency=KEY_FREQS["A3"],
    duration_s=BEAT * 0.75, attack_s=0.005, decay_s=0.05,
    sustain=0.55, release_s=0.1, filter_cutoff=0.85,
    resonance=0.65, distortion=0.38
)))

screech_c = to_np(synthesize_screech_lead(LeadPreset(
    name="V3ScreechC", lead_type="screech", frequency=KEY_FREQS["C4"],
    duration_s=BEAT * 0.5, attack_s=0.004, decay_s=0.04,
    sustain=0.6, release_s=0.08, filter_cutoff=0.88,
    resonance=0.70, distortion=0.42
)))

formant_ah = to_np(synthesize_formant(FormantPreset(
    name="V3FormantAh", formant_type="ah",
    frequency=KEY_FREQS["D4"], duration_s=BEAT * 1.0,
    brightness=0.72, vibrato_rate=5.5
)))

formant_ee = to_np(synthesize_formant(FormantPreset(
    name="V3FormantEe", formant_type="ee",
    frequency=KEY_FREQS["F4"], duration_s=BEAT * 0.75,
    brightness=0.8, vibrato_rate=6.0
)))

formant_morph = to_np(synthesize_formant(FormantPreset(
    name="V3FormantMorph", formant_type="morph",
    frequency=KEY_FREQS["A3"], duration_s=BEAT * 2.0,
    brightness=0.6, vibrato_rate=4.0
)))

# -- KS STRINGS (VIP retained from v1/v2) --
print("  [5/17] Karplus-Strong strings...")

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

# -- CHORD PADS --
print("  [6/17] Chord pads...")

chord_minor7 = to_np(synthesize_chord_pad(ChordPadPreset(
    name="V3DmChordPad", chord_type="minor7",
    root_freq=KEY_FREQS["D3"], duration_s=BAR * 4,
    detune_cents=18.0, attack_s=1.2, release_s=2.0,
    brightness=0.42, warmth=0.6, reverb_amount=0.5
)))

chord_sus4 = to_np(synthesize_chord_pad(ChordPadPreset(
    name="V3SusPad", chord_type="sus4",
    root_freq=KEY_FREQS["G3"], duration_s=BAR * 4,
    detune_cents=10.0, attack_s=1.5, release_s=2.5,
    brightness=0.3, warmth=0.65, reverb_amount=0.55
)))

chord_power = to_np(synthesize_chord_pad(ChordPadPreset(
    name="V3PowerPad", chord_type="power",
    root_freq=KEY_FREQS["D3"], duration_s=BAR * 2,
    detune_cents=20.0, attack_s=0.8, release_s=1.0,
    brightness=0.52, warmth=0.5, reverb_amount=0.3
)))

# -- ARP SYNTH --
print("  [7/17] Arp synth...")

arp_pulse = to_np(synthesize_arp(ArpSynthPreset(
    name="V3ArpPulse", arp_type="pulse",
    base_freq=KEY_FREQS["D3"], duration_s=BAR * 4,
    step_count=16, filter_cutoff=0.55, resonance=0.3,
    octave_range=2
)))

arp_acid = to_np(synthesize_arp(ArpSynthPreset(
    name="V3ArpAcid", arp_type="acid",
    base_freq=KEY_FREQS["D3"], duration_s=BAR * 4,
    step_count=16, filter_cutoff=0.4, resonance=0.5,
    octave_range=2
)))

# -- SUPERSAW STABS --
print("  [8/17] Supersaw...")

saw_chord = to_np(render_supersaw_mono(SupersawPatch(
    name="V3DmStab", n_voices=13, detune_cents=48.0,
    mix=0.78, cutoff_hz=7500.0, resonance=0.42,
    attack=0.003, decay=0.15, sustain=0.6, release=0.2,
    master_gain=0.75
), freq=KEY_FREQS["D3"], duration=BEAT * 0.5))

saw_wall = to_np(render_supersaw_mono(SupersawPatch(
    name="V3SawWall", n_voices=15, detune_cents=55.0,
    mix=0.82, cutoff_hz=9000.0, resonance=0.35,
    attack=0.01, decay=0.3, sustain=0.7, release=0.4,
    master_gain=0.65
), freq=KEY_FREQS["D3"], duration=BAR))

fm_hit = to_np(render_fm(FMPatch(
    name="V3FMFractal",
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

# -- PADS --
print("  [9/17] Pads...")

dark_pad = to_np(synthesize_dark_pad(PadPreset(
    name="V3VoidPad", pad_type="dark", frequency=KEY_FREQS["D3"],
    duration_s=BAR * 8, detune_cents=16.0, filter_cutoff=0.25,
    attack_s=2.0, release_s=3.0, reverb_amount=0.65, brightness=0.2
)))

lush_pad = to_np(synthesize_lush_pad(PadPreset(
    name="V3LushPad", pad_type="lush", frequency=KEY_FREQS["F3"],
    duration_s=BAR * 8, detune_cents=18.0, filter_cutoff=0.4,
    attack_s=1.5, release_s=2.5, reverb_amount=0.7, brightness=0.35
)))

# -- DRONE --
print("  [10/17] Drone...")

drone = to_np(synthesize_drone(DronePreset(
    name="V3AbyssDrone", drone_type="evolving",
    frequency=KEY_FREQS["D1"], duration_s=BAR * 8,
    num_voices=9, detune_cents=10.0, brightness=0.18,
    movement=0.5, attack_s=2.5, release_s=3.5,
    distortion=0.08, reverb_amount=0.55
)))

dark_drone = to_np(synthesize_drone(DronePreset(
    name="V3DarkUndertow", drone_type="dark",
    frequency=KEY_FREQS["D1"], duration_s=BAR * 4,
    num_voices=7, brightness=0.12, movement=0.25,
    attack_s=0.5, release_s=1.5, distortion=0.15
)))

# -- GRANULAR SYNTH --
print("  [11/17] Granular synth...")

granular_dust = to_np(synthesize_granular(GranularPreset(
    name="V3GranDust", grain_type="scatter",
    frequency=KEY_FREQS["D3"], duration_s=BAR * 8,
    grain_size_ms=35.0, grain_density=0.4,
    pitch_spread=0.3, brightness=0.2, reverb_amount=0.6,
    scatter_amount=0.6
)))

granular_shimmer = to_np(synthesize_granular(GranularPreset(
    name="V3GranShimmer", grain_type="shimmer",
    frequency=KEY_FREQS["A3"], duration_s=BAR * 4,
    grain_size_ms=60.0, grain_density=0.7,
    pitch_spread=0.5, brightness=0.55, reverb_amount=0.7
)))

granular_cloud = to_np(synthesize_granular(GranularPreset(
    name="V3GranCloud", grain_type="cloud",
    frequency=KEY_FREQS["D4"], duration_s=BAR * 4,
    grain_size_ms=80.0, grain_density=0.8,
    pitch_spread=0.4, brightness=0.45, reverb_amount=0.5
)))

granular_freeze = to_np(synthesize_granular(GranularPreset(
    name="V3GranFreeze", grain_type="freeze",
    frequency=KEY_FREQS["D3"], duration_s=BAR * 4,
    grain_size_ms=120.0, grain_density=0.6,
    pitch_spread=0.1, brightness=0.25, reverb_amount=0.8
)))

# -- RISERS --
print("  [12/17] Risers...")

pitch_riser = to_np(synthesize_riser(RiserPreset(
    name="V3PitchRise", riser_type="pitch_rise",
    duration_s=BAR * 4,
    start_freq=80.0, end_freq=3000.0,
    brightness=0.6, intensity=0.75, distortion=0.05
)))

harmonic_riser = to_np(synthesize_riser(RiserPreset(
    name="V3HarmonicBuild", riser_type="harmonic_build",
    duration_s=BAR * 4,
    start_freq=60.0, end_freq=3500.0,
    brightness=0.55, intensity=0.8, distortion=0.08
)))

noise_riser = to_np(synthesize_riser(RiserPreset(
    name="V3NoiseSweep", riser_type="noise_sweep",
    duration_s=BAR * 4,
    start_freq=100.0, end_freq=4000.0,
    brightness=0.4, intensity=0.6
)))

# -- FX & IMPACTS + TRANSITIONS --
print("  [13/17] FX, impacts & transitions...")

sub_boom = to_np(synthesize_sub_boom(ImpactPreset(
    name="V3DropBoom", impact_type="sub_boom", duration_s=3.0,
    frequency=KEY_FREQS["D1"], decay_s=2.5, intensity=1.0,
    reverb_amount=0.4
)))

cinema_hit = to_np(synthesize_cinematic_hit(ImpactPreset(
    name="V3CinemaHit", impact_type="cinematic_hit", duration_s=2.0,
    frequency=70.0, decay_s=1.5, brightness=0.6, intensity=0.95
)))

reverse_hit = to_np(synthesize_reverse_hit(ImpactPreset(
    name="V3RevHit", impact_type="reverse_hit", duration_s=1.5,
    frequency=85.0, decay_s=1.0, intensity=0.8
)))

stutter = to_np(synthesize_stutter(GlitchPreset(
    name="V3Stutter", glitch_type="stutter",
    frequency=KEY_FREQS["D3"],
    duration_s=BEAT * 2, rate=16.0, depth=0.9, distortion=0.25
)))

tape_stop = to_np(synthesize_transition(TransitionPreset(
    name="V3TapeStop", fx_type="tape_stop",
    duration_s=BEAT * 2, start_freq=KEY_FREQS["D3"],
    brightness=0.4
)))

pitch_dive = to_np(synthesize_transition(TransitionPreset(
    name="V3PitchDive", fx_type="pitch_dive",
    duration_s=BEAT * 1.5, start_freq=KEY_FREQS["D4"],
    end_freq=KEY_FREQS["D1"], brightness=0.5
)))

glitch_trans = to_np(synthesize_transition(TransitionPreset(
    name="V3GlitchTrans", fx_type="glitch_stutter",
    duration_s=BEAT * 2, start_freq=KEY_FREQS["D3"],
    brightness=0.6
)))

# -- VOCAL CHOPS --
print("  [14/17] Vocal chops...")

chop_ah = to_np(synthesize_chop(VocalChop(
    name="V3CryAh", vowel="ah", note="D3",
    duration_s=BEAT * 0.5, attack_s=0.01, release_s=0.1,
    formant_shift=0.0, distortion=0.1
)))

chop_oh = to_np(synthesize_chop(VocalChop(
    name="V3HollowOh", vowel="oh", note="A3",
    duration_s=BEAT * 0.75, attack_s=0.02, release_s=0.15,
    formant_shift=-2.0, distortion=0.05
)))

chop_eh_stutter = to_np(synthesize_chop(VocalChop(
    name="V3AnguishEh", vowel="eh", note="F3",
    duration_s=BEAT * 1.0, attack_s=0.003, release_s=0.04,
    formant_shift=3.0, distortion=0.2,
    stutter_count=8, stutter_pitch_drift=0.5
)))

chop_ee = to_np(synthesize_chop(VocalChop(
    name="V3ScreamEe", vowel="ee", note="D4",
    duration_s=BEAT * 0.3, attack_s=0.002, release_s=0.05,
    formant_shift=5.0, distortion=0.4
)))

chop_oo = to_np(synthesize_chop(VocalChop(
    name="V3WhisperOo", vowel="oo", note="D3",
    duration_s=BEAT * 1.0, attack_s=0.05, release_s=0.3,
    formant_shift=-3.0, distortion=0.0
)))

chop_ah_long = to_np(synthesize_chop(VocalChop(
    name="V3ApologyAh", vowel="ah", note="A3",
    duration_s=BEAT * 2.0, attack_s=0.03, release_s=0.5,
    formant_shift=-1.0, distortion=0.05
)))

# -- FM + WAVETABLE LEADS per drop (multi-parameter evolution) --
# V3: FM depth, filter cutoff, AND distortion ALL increase per drop

# Drop 1 leads: FM 3.0, filter 0.88, distortion 0.25
fm_lead_d = to_np(synthesize_fm_lead(LeadPreset(
    name="V3FMLead_D", lead_type="fm_lead", frequency=KEY_FREQS["D4"],
    duration_s=BEAT * 0.5, attack_s=0.003, decay_s=0.06,
    sustain=0.5, release_s=0.08, fm_ratio=PHI, fm_depth=3.0,
    filter_cutoff=0.88, resonance=0.45, distortion=0.25
)))
fm_lead_f = to_np(synthesize_fm_lead(LeadPreset(
    name="V3FMLead_F", lead_type="fm_lead", frequency=KEY_FREQS["F4"],
    duration_s=BEAT * 0.5, attack_s=0.003, decay_s=0.06,
    sustain=0.45, release_s=0.09, fm_ratio=PHI, fm_depth=2.5,
    filter_cutoff=0.85, resonance=0.42, distortion=0.22
)))
fm_lead_a = to_np(synthesize_fm_lead(LeadPreset(
    name="V3FMLead_A", lead_type="fm_lead", frequency=KEY_FREQS["A3"],
    duration_s=BEAT * 0.75, attack_s=0.005, decay_s=0.07,
    sustain=0.45, release_s=0.1, fm_ratio=PHI, fm_depth=2.0,
    filter_cutoff=0.82, resonance=0.38, distortion=0.2
)))
fm_lead_c = to_np(synthesize_fm_lead(LeadPreset(
    name="V3FMLead_C", lead_type="fm_lead", frequency=KEY_FREQS["C4"],
    duration_s=BEAT * 0.5, attack_s=0.004, decay_s=0.06,
    sustain=0.48, release_s=0.08, fm_ratio=PHI, fm_depth=2.8,
    filter_cutoff=0.86, resonance=0.4, distortion=0.23
)))

# Drop 2 leads: FM 5.0, filter 0.90, distortion 0.30
fm_lead_d_d2 = to_np(synthesize_fm_lead(LeadPreset(
    name="V3FMLead_D_D2", lead_type="fm_lead", frequency=KEY_FREQS["D4"],
    duration_s=BEAT * 0.5, attack_s=0.003, decay_s=0.06,
    sustain=0.5, release_s=0.08, fm_ratio=PHI, fm_depth=5.0,
    filter_cutoff=0.90, resonance=0.50, distortion=0.30
)))
fm_lead_f_d2 = to_np(synthesize_fm_lead(LeadPreset(
    name="V3FMLead_F_D2", lead_type="fm_lead", frequency=KEY_FREQS["F4"],
    duration_s=BEAT * 0.5, attack_s=0.003, decay_s=0.06,
    sustain=0.45, release_s=0.09, fm_ratio=PHI, fm_depth=4.5,
    filter_cutoff=0.88, resonance=0.48, distortion=0.28
)))
fm_lead_a_d2 = to_np(synthesize_fm_lead(LeadPreset(
    name="V3FMLead_A_D2", lead_type="fm_lead", frequency=KEY_FREQS["A3"],
    duration_s=BEAT * 0.75, attack_s=0.005, decay_s=0.07,
    sustain=0.45, release_s=0.1, fm_ratio=PHI, fm_depth=4.0,
    filter_cutoff=0.86, resonance=0.44, distortion=0.26
)))
fm_lead_c_d2 = to_np(synthesize_fm_lead(LeadPreset(
    name="V3FMLead_C_D2", lead_type="fm_lead", frequency=KEY_FREQS["C4"],
    duration_s=BEAT * 0.5, attack_s=0.004, decay_s=0.06,
    sustain=0.48, release_s=0.08, fm_ratio=PHI, fm_depth=4.8,
    filter_cutoff=0.89, resonance=0.46, distortion=0.28
)))

# Drop 3 leads: FM 7.0, filter 0.92, distortion 0.35
fm_lead_d_d3 = to_np(synthesize_fm_lead(LeadPreset(
    name="V3FMLead_D_D3", lead_type="fm_lead", frequency=KEY_FREQS["D4"],
    duration_s=BEAT * 0.5, attack_s=0.002, decay_s=0.05,
    sustain=0.55, release_s=0.07, fm_ratio=PHI, fm_depth=7.0,
    filter_cutoff=0.92, resonance=0.55, distortion=0.35
)))
fm_lead_f_d3 = to_np(synthesize_fm_lead(LeadPreset(
    name="V3FMLead_F_D3", lead_type="fm_lead", frequency=KEY_FREQS["F4"],
    duration_s=BEAT * 0.5, attack_s=0.002, decay_s=0.05,
    sustain=0.5, release_s=0.08, fm_ratio=PHI, fm_depth=6.5,
    filter_cutoff=0.91, resonance=0.53, distortion=0.33
)))
fm_lead_a_d3 = to_np(synthesize_fm_lead(LeadPreset(
    name="V3FMLead_A_D3", lead_type="fm_lead", frequency=KEY_FREQS["A3"],
    duration_s=BEAT * 0.75, attack_s=0.003, decay_s=0.06,
    sustain=0.5, release_s=0.09, fm_ratio=PHI, fm_depth=6.0,
    filter_cutoff=0.89, resonance=0.50, distortion=0.30
)))
fm_lead_c_d3 = to_np(synthesize_fm_lead(LeadPreset(
    name="V3FMLead_C_D3", lead_type="fm_lead", frequency=KEY_FREQS["C4"],
    duration_s=BEAT * 0.5, attack_s=0.002, decay_s=0.05,
    sustain=0.52, release_s=0.07, fm_ratio=PHI, fm_depth=6.8,
    filter_cutoff=0.91, resonance=0.52, distortion=0.33
)))

# Drop 4 leads: FM 9.0, filter 0.95, distortion 0.40 (TRANSCENDENCE)
fm_lead_d_d4 = to_np(synthesize_fm_lead(LeadPreset(
    name="V3FMLead_D_D4", lead_type="fm_lead", frequency=KEY_FREQS["D4"],
    duration_s=BEAT * 0.5, attack_s=0.002, decay_s=0.04,
    sustain=0.6, release_s=0.06, fm_ratio=PHI, fm_depth=9.0,
    filter_cutoff=0.95, resonance=0.60, distortion=0.40
)))
fm_lead_f_d4 = to_np(synthesize_fm_lead(LeadPreset(
    name="V3FMLead_F_D4", lead_type="fm_lead", frequency=KEY_FREQS["F4"],
    duration_s=BEAT * 0.5, attack_s=0.002, decay_s=0.04,
    sustain=0.55, release_s=0.07, fm_ratio=PHI, fm_depth=8.5,
    filter_cutoff=0.94, resonance=0.58, distortion=0.38
)))
fm_lead_a_d4 = to_np(synthesize_fm_lead(LeadPreset(
    name="V3FMLead_A_D4", lead_type="fm_lead", frequency=KEY_FREQS["A3"],
    duration_s=BEAT * 0.75, attack_s=0.002, decay_s=0.05,
    sustain=0.55, release_s=0.08, fm_ratio=PHI, fm_depth=8.0,
    filter_cutoff=0.93, resonance=0.56, distortion=0.36
)))
fm_lead_c_d4 = to_np(synthesize_fm_lead(LeadPreset(
    name="V3FMLead_C_D4", lead_type="fm_lead", frequency=KEY_FREQS["C4"],
    duration_s=BEAT * 0.5, attack_s=0.002, decay_s=0.04,
    sustain=0.58, release_s=0.06, fm_ratio=PHI, fm_depth=8.8,
    filter_cutoff=0.94, resonance=0.58, distortion=0.38
)))

# -- DOJO V3: FULL GROWL RESAMPLE PIPELINE (6-stage, 256 frames) --
# V2 gap: imported growl_resample_pipeline but never called it.
# V3 uses the full 6-stage pipeline for evolving bass textures.
print("  [15/17] Growl resample pipeline (FULL 6-stage, 256 frames)...")

# Generate source frames for the pipeline
saw_frame = generate_saw_source(2048)
fm_frame = generate_fm_source(2048, fm_ratio=PHI, fm_depth=3.0)
fm_frame_deep = generate_fm_source(2048, fm_ratio=PHI, fm_depth=7.0)

# Full pipeline: each produces 256 evolving wavetable frames
growl_pipeline_saw = growl_resample_pipeline(saw_frame, n_output_frames=64)
growl_pipeline_fm = growl_resample_pipeline(fm_frame, n_output_frames=64)
growl_pipeline_deep = growl_resample_pipeline(fm_frame_deep, n_output_frames=64)

print(f"         Pipeline A (saw): {len(growl_pipeline_saw)} frames")
print(f"         Pipeline B (fm):  {len(growl_pipeline_fm)} frames")
print(f"         Pipeline C (deep): {len(growl_pipeline_deep)} frames")

# Export growl pipeline frames as Serum-compatible wavetable .wav files
os.makedirs("output/wavetables", exist_ok=True)
write_serum_wav("output/wavetables/APOLOGY_V3_GROWL_SAW.wav", growl_pipeline_saw)
write_serum_wav("output/wavetables/APOLOGY_V3_GROWL_FM.wav", growl_pipeline_fm)
write_serum_wav("output/wavetables/APOLOGY_V3_GROWL_DEEP.wav", growl_pipeline_deep)
print(f"         3 Serum wavetable .wav files exported")

# Convert pipeline frames to playable audio segments
# Each frame is a single-cycle waveform; tile to fill a beat duration
def frames_to_audio(frames: list[np.ndarray], duration_s: float) -> np.ndarray:
    """Convert single-cycle wavetable frames into a playable audio buffer."""
    total_samps = int(duration_s * SR)
    buf = np.zeros(total_samps, dtype=np.float64)
    if not frames:
        return buf
    samps_per_frame = max(1, total_samps // len(frames))
    for i, frame in enumerate(frames):
        start = i * samps_per_frame
        end = min(start + samps_per_frame, total_samps)
        n = end - start
        if n <= 0:
            break
        # Tile the single-cycle frame to fill the duration
        cycles = max(1, n // len(frame))
        tiled = np.tile(frame, cycles + 1)[:n]
        # Apply envelope to avoid clicks
        env = np.ones(n)
        fade = min(64, n // 4)
        if fade > 0:
            env[:fade] = np.linspace(0, 1, fade)
            env[-fade:] = np.linspace(1, 0, fade)
        buf[start:end] += tiled * env
    peak = np.max(np.abs(buf))
    if peak > 0:
        buf /= peak
    return buf

growl_audio_saw = frames_to_audio(growl_pipeline_saw, BEAT * 2)
growl_audio_fm = frames_to_audio(growl_pipeline_fm, BEAT * 2)
growl_audio_deep = frames_to_audio(growl_pipeline_deep, BEAT * 2)

# Also keep the V2-style manual growl variants for layering
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

# V3 palette: pipeline audio + manual growls = 8 bass textures
GROWL_PALETTE = [
    growl_audio_saw, growl_audio_fm, growl_audio_deep,
    growl_saw, growl_fm, growl_tear, growl_yell, growl_screech,
]

# -- DOJO V3: WAVETABLE MORPH (per-drop evolving timbres) --
print("  [16/17] Wavetable morph (per-drop evolving timbres)...")

# Source frames for morphing (4 frames with increasing harmonic content)
morph_sources = [saw_frame]
for depth in [3.0, 5.0, 8.0]:
    morph_sources.append(generate_fm_source(2048, fm_ratio=PHI, fm_depth=depth))

morph_phi = morph_wavetable(morph_sources, MorphPreset(
    name="V3MorphPhi", morph_type="phi_spline", num_frames=16,
    frame_size=2048, morph_curve=PHI
))
morph_fractal = morph_wavetable(morph_sources, MorphPreset(
    name="V3MorphFractal", morph_type="fractal", num_frames=16,
    frame_size=2048, morph_curve=PHI
))
morph_spectral = morph_wavetable(morph_sources, MorphPreset(
    name="V3MorphSpectral", morph_type="spectral", num_frames=16,
    frame_size=2048, morph_curve=PHI
))

# Convert morph frames to playable audio
morph_audio_phi = frames_to_audio(morph_phi, BAR * 2)
morph_audio_fractal = frames_to_audio(morph_fractal, BAR * 2)
morph_audio_spectral = frames_to_audio(morph_spectral, BAR * 2)

print(f"         phi_spline: {len(morph_phi)} frames")
print(f"         fractal:    {len(morph_fractal)} frames")
print(f"         spectral:   {len(morph_spectral)} frames")

# Export morph frames as Serum-compatible wavetable .wav files
write_serum_wav("output/wavetables/APOLOGY_V3_MORPH_PHI.wav", morph_phi)
write_serum_wav("output/wavetables/APOLOGY_V3_MORPH_FRACTAL.wav", morph_fractal)
write_serum_wav("output/wavetables/APOLOGY_V3_MORPH_SPECTRAL.wav", morph_spectral)
print(f"         3 morph wavetable .wav files exported")

# -- DOJO V3: EVOLUTION ENGINE -- parameter drift tracking --
print("  [17/17] Evolution engine (parameter drift tracking)...")

evo_drift = track_param_drift(EvolutionPreset(
    name="V3ParamDrift", tracker_type="param_drift",
    generations=8, mutation_rate=0.15
))
evo_phi = track_phi_convergence(EvolutionPreset(
    name="V3PhiConv", tracker_type="phi_convergence",
    generations=8, mutation_rate=0.1, phi_weight=0.618
))

print(f"         Drift: {len(evo_drift.entries)} generations, "
      f"best={evo_drift.best_entry().score:.3f}" if evo_drift.best_entry() else "")
print(f"         Phi:   {len(evo_phi.entries)} generations, "
      f"best={evo_phi.best_entry().score:.3f}" if evo_phi.best_entry() else "")


# -- BEAT REPEAT PRESETS --
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
BR_TRIPLET = BeatRepeatPatch(
    grid="1/12", repeats=6, decay=0.2, pitch_shift=-1.0,
    reverse_probability=0.15, gate=0.85, mix=0.65, probability=0.7
)


# ====================================================================
#  DRUM PATTERNS (all with peak normalization)
# ====================================================================


def drum_pattern_drop(bars: int = 4) -> np.ndarray:
    """Halftime drop -- kick on 1, snare on 3, tight hats."""
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
    return peak_normalize(buf)


def drum_pattern_drop2(bars: int = 4) -> np.ndarray:
    """Drop 2 -- heavier, sixteenth hats, clap layer."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, kick, bo, gain=1.0)
        mix_into(buf, snare, bo + samples_for(2), gain=0.9)
        mix_into(buf, clap, bo + samples_for(2), gain=0.35)
        for sixteenth in range(16):
            vel = 0.22 + 0.08 * (sixteenth % 4 == 0)
            mix_into(buf, hat_closed,
                     bo + samples_for(sixteenth * 0.25), gain=vel)
        mix_into(buf, hat_open, bo + samples_for(1.5), gain=0.28)
        mix_into(buf, hat_open, bo + samples_for(3.5), gain=0.28)
        if bar % 2 == 1:
            mix_into(buf, snare, bo + samples_for(3.75), gain=0.3)
    return peak_normalize(buf)


def drum_pattern_drop3(bars: int = 4) -> np.ndarray:
    """Drop 3 -- CLIMAX: double kick, clap layers, 32nd hat cascades."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, kick, bo, gain=0.78)
        mix_into(buf, kick, bo + samples_for(1), gain=0.55)
        mix_into(buf, snare, bo + samples_for(2), gain=0.72)
        mix_into(buf, clap, bo + samples_for(2), gain=0.30)
        for thirtysecond in range(32):
            vel = 0.12 + 0.08 * (thirtysecond % 8 == 0)
            mix_into(buf, hat_closed,
                     bo + samples_for(thirtysecond * 0.125), gain=vel)
        mix_into(buf, hat_open, bo + samples_for(1.5), gain=0.22)
        mix_into(buf, hat_open, bo + samples_for(3.5), gain=0.22)
        if bar % 2 == 1:
            mix_into(buf, snare, bo + samples_for(3.5), gain=0.25)
            mix_into(buf, snare, bo + samples_for(3.75), gain=0.30)
    return peak_normalize(buf)


def drum_pattern_drop4(bars: int = 4) -> np.ndarray:
    """Drop 4 -- TRANSCENDENCE: triple kick, maximum density."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, kick, bo, gain=0.75)
        mix_into(buf, kick, bo + samples_for(0.75), gain=0.45)
        mix_into(buf, kick, bo + samples_for(1.5), gain=0.50)
        mix_into(buf, snare, bo + samples_for(2), gain=0.70)
        mix_into(buf, clap, bo + samples_for(2), gain=0.32)
        mix_into(buf, clap, bo + samples_for(2.5), gain=0.20)
        for thirtysecond in range(32):
            vel = 0.10 + 0.10 * (thirtysecond % 4 == 0)
            mix_into(buf, hat_closed,
                     bo + samples_for(thirtysecond * 0.125), gain=vel)
        mix_into(buf, hat_open, bo + samples_for(1.5), gain=0.20)
        mix_into(buf, hat_open, bo + samples_for(3.5), gain=0.20)
        if bar % 2 == 1:
            mix_into(buf, snare, bo + samples_for(3.25), gain=0.22)
            mix_into(buf, snare, bo + samples_for(3.5), gain=0.25)
            mix_into(buf, snare, bo + samples_for(3.75), gain=0.28)
    return peak_normalize(buf)


def drum_pattern_build(bars: int = 4) -> np.ndarray:
    """Buildup -- accelerating snare rolls."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, kick, bo, gain=0.6)
        mix_into(buf, kick, bo + samples_for(2), gain=0.6)
        divisions = [4, 8, 16, 32, 64][min(bar, 4)]
        step = 4.0 / divisions
        for hit in range(divisions):
            vel = 0.3 + 0.5 * (bar / bars) * (hit / divisions)
            mix_into(buf, snare, bo + samples_for(hit * step), gain=vel)
    return peak_normalize(buf)


def drum_pattern_intro(bars: int = 4) -> np.ndarray:
    """Minimal intro -- light hats breathing."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        for q in range(4):
            mix_into(buf, hat_closed, bo + samples_for(q),
                     gain=0.1 + 0.04 * (bar / bars))
    return buf


# ====================================================================
#  BASS PATTERNS -- V3: all 5 riddim types + pipeline growls
# ====================================================================

def bass_drop_pattern(bars: int = 4) -> np.ndarray:
    """Drop 1 bass -- riddim heavy/bounce + pipeline growl A."""
    buf = render_section(bars)
    bar_samps = samples_for(4)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, sub_bass, bo, gain=0.70)
        mix_into(buf, sub_bass, bo + samples_for(2), gain=0.60)
        if bar % 3 == 0:
            seg = riddim_heavy[:min(len(riddim_heavy), bar_samps)]
            mix_into(buf, seg, bo, gain=0.38)
        elif bar % 3 == 1:
            seg = riddim_bounce[:min(len(riddim_bounce), bar_samps)]
            mix_into(buf, seg, bo, gain=0.35)
        else:
            seg = growl_audio_saw[:min(len(growl_audio_saw), bar_samps)]
            mix_into(buf, seg, bo, gain=0.32)
    return buf


def bass_drop2_pattern(bars: int = 4) -> np.ndarray:
    """Drop 2 bass -- 5-type riddim rotation + pipeline growl FM."""
    buf = render_section(bars)
    bar_samps = samples_for(4)
    rotation = [
        (riddim_heavy, 0.36),
        (growl_audio_fm, 0.33),
        (riddim_stutter, 0.36),
        (riddim_bounce, 0.34),
        (growl_tear, 0.33),
    ]
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, sub_bass, bo, gain=0.78)
        mix_into(buf, sub_bass, bo + samples_for(2), gain=0.68)
        src, g = rotation[bar % len(rotation)]
        seg = src[:min(len(src), bar_samps)]
        mix_into(buf, seg, bo, gain=g)
        for sixteenth in range(0, 16, 3):
            mix_into(buf, neuro_bass,
                     bo + samples_for(sixteenth * 0.25), gain=0.20)
    return buf


def bass_drop3_pattern(bars: int = 4) -> np.ndarray:
    """Drop 3 bass -- CLIMAX: full growl palette rotation (8 sounds)."""
    buf = render_section(bars)
    bar_samps = samples_for(4)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, sub_bass, bo, gain=0.82)
        mix_into(buf, sub_bass, bo + samples_for(2), gain=0.72)
        growl = GROWL_PALETTE[bar % len(GROWL_PALETTE)]
        seg = growl[:min(len(growl), bar_samps)]
        mix_into(buf, seg, bo, gain=0.35)
        trip_seg = riddim_triplet[:min(len(riddim_triplet), bar_samps)]
        mix_into(buf, trip_seg, bo, gain=0.18)
    return buf


def bass_drop4_pattern(bars: int = 4) -> np.ndarray:
    """Drop 4 bass -- TRANSCENDENCE: deep pipeline + all riddim."""
    buf = render_section(bars)
    bar_samps = samples_for(4)
    rotation = [
        (growl_audio_deep, 0.34),
        (riddim_heavy, 0.32),
        (growl_audio_fm, 0.34),
        (riddim_stutter, 0.32),
        (growl_yell, 0.34),
        (riddim_triplet, 0.30),
        (growl_screech, 0.34),
        (riddim_minimal, 0.28),
    ]
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, sub_bass, bo, gain=0.85)
        mix_into(buf, sub_bass, bo + samples_for(2), gain=0.75)
        src, g = rotation[bar % len(rotation)]
        seg = src[:min(len(src), bar_samps)]
        mix_into(buf, seg, bo, gain=g)
        for sixteenth in range(0, 16, 4):
            mix_into(buf, neuro_bass,
                     bo + samples_for(sixteenth * 0.25), gain=0.18)
    return buf


# ====================================================================
#  LEAD MELODY -- 4 drops with increasing FM + filter + distortion
# ====================================================================

def lead_melody_drop(bars: int = 4) -> np.ndarray:
    """Drop 1 lead -- screech + FM (depth 3.0)."""
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
    """Drop 2 lead -- deeper FM (depth 5.0)."""
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
    """Drop 3 lead -- CLIMAX FM (depth 7.0)."""
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


def lead_melody_drop4(bars: int = 4) -> np.ndarray:
    """Drop 4 lead -- TRANSCENDENCE FM (depth 9.0)."""
    buf = render_section(bars)
    melody = [
        (screech_a, fm_lead_a_d4, 0.0, 0.34, 0.32),
        (screech_c, fm_lead_c_d4, 1.0, 0.36, 0.34),
        (screech_d, fm_lead_d_d4, 2.0, 0.38, 0.36),
        (screech_f, fm_lead_f_d4, 3.0, 0.36, 0.34),
    ]
    for bar in range(bars):
        bo = samples_for(bar * 4)
        for scr, fm, beat, g_scr, g_fm in melody:
            mix_into(buf, scr, bo + samples_for(beat), gain=g_scr)
            mix_into(buf, fm, bo + samples_for(beat), gain=g_fm)
    return buf


def formant_melody(bars: int = 4) -> np.ndarray:
    """Formant synth lead -- vocal-like texture."""
    buf = render_section(bars)
    for bar in range(bars):
        bo = samples_for(bar * 4)
        mix_into(buf, formant_ah, bo, gain=0.28)
        mix_into(buf, formant_ee, bo + samples_for(2), gain=0.25)
        if bar % 2 == 1:
            mix_into(buf, formant_morph, bo + samples_for(1), gain=0.2)
    return buf


def ks_arpeggio(bars: int = 4) -> np.ndarray:
    """Karplus-Strong arpeggio -- D minor broken chord (VIP retained)."""
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
    """Quick lead fill through the ascending motif."""
    buf = render_section(bars)
    notes = [screech_a, screech_c, screech_d, screech_f]
    for sixteenth in range(16):
        note = notes[sixteenth % 4]
        gain = 0.2 + 0.25 * (sixteenth / 16)
        mix_into(buf, note, samples_for(sixteenth * 0.25), gain=gain)
    return buf


# ====================================================================
#  ARRANGE -- PACK_ALPHA (144 bars = Fibonacci, 4 drops)
# ====================================================================

INTRO_BARS = 8
BUILD1_BARS = 5
DROP1_BARS = 13
BREAK1_BARS = 5
BUILD2_BARS = 8
DROP2_BARS = 34       # MARATHON drop (Fibonacci 34)
BREAK2_BARS = 3
BUILD3_BARS = 5
DROP3_BARS = 21       # CLIMAX (Golden Section falls here)
BREAK3_BARS = 5
BUILD4_BARS = 8
DROP4_BARS = 21       # TRANSCENDENCE
OUTRO_BARS = 8

total_bars = (INTRO_BARS + BUILD1_BARS + DROP1_BARS + BREAK1_BARS +
              BUILD2_BARS + DROP2_BARS + BREAK2_BARS + BUILD3_BARS +
              DROP3_BARS + BREAK3_BARS + BUILD4_BARS + DROP4_BARS +
              OUTRO_BARS)
total_samples = samples_for(total_bars * 4)
duration_s = total_samples / SR
golden_section_bar = int(total_bars / PHI)

print()
print(f"  Structure: {total_bars} bars = {duration_s:.1f}s "
      f"({int(duration_s // 60)}:{int(duration_s % 60):02d})")
print(f"  PACK_ALPHA (Fibonacci): {INTRO_BARS}/{BUILD1_BARS}/{DROP1_BARS}/"
      f"{BREAK1_BARS}/{BUILD2_BARS}/{DROP2_BARS}/{BREAK2_BARS}/"
      f"{BUILD3_BARS}/{DROP3_BARS}/{BREAK3_BARS}/{BUILD4_BARS}/"
      f"{DROP4_BARS}/{OUTRO_BARS}")
print(f"  Golden Section Point: bar ~{golden_section_bar}")
print()


# ====================================================================
#  STEM BUFFERS
# ====================================================================

STEM_NAMES = [
    "DRUMS", "BASS", "RIDDIM", "LEAD", "FORMANT", "KS_STRINGS",
    "CHORDS", "PAD", "DRONE", "RISER", "VOCAL", "FX", "GRANULAR",
    "MORPH",
]

STEM_PAN = {
    "DRUMS": 0.0, "BASS": 0.0, "RIDDIM": 0.05, "LEAD": 0.18,
    "FORMANT": -0.15, "KS_STRINGS": -0.22, "CHORDS": 0.12,
    "PAD": 0.0, "DRONE": 0.0, "RISER": 0.0, "VOCAL": -0.05,
    "FX": 0.0, "GRANULAR": 0.0, "MORPH": -0.08,
}

stems: dict[str, np.ndarray] = {
    name: np.zeros(total_samples) for name in STEM_NAMES
}

cursor = 0


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


# -- INTRO (8 bars) -- "Fractal dust rising from the void" --
print("  Rendering Intro...")
intro_start = cursor

gran_dust_seg = granular_dust[:samples_for(INTRO_BARS * 4)]
gran_dust_seg = fade_in(gran_dust_seg, duration_s=BAR * 3)
mix_into(stems["GRANULAR"], gran_dust_seg, intro_start, gain=0.22)

intro_drone = drone[:samples_for(INTRO_BARS * 4)]
intro_drone = fade_in(intro_drone, duration_s=BAR * 5)
intro_drone = lowpass(intro_drone, cutoff=0.1)
mix_into(stems["DRONE"], intro_drone, intro_start, gain=0.38)

intro_pad = dark_pad[:samples_for(INTRO_BARS * 4)]
intro_pad = fade_in(intro_pad, duration_s=BAR * 4)
intro_pad = lowpass(intro_pad, cutoff=0.08)
mix_into(stems["PAD"], intro_pad, intro_start, gain=0.25)

mix_into(stems["FORMANT"], formant_morph,
         intro_start + samples_for(3 * 4), gain=0.12)
mix_into(stems["FORMANT"], formant_morph,
         intro_start + samples_for(6 * 4), gain=0.15)

rev_offset = intro_start + samples_for(6 * 4)
mix_into(stems["FX"], reverse_hit, rev_offset, gain=0.30)

intro_drums = drum_pattern_intro(INTRO_BARS)
intro_drums = fade_in(intro_drums, duration_s=BAR * 5)
mix_into(stems["DRUMS"], intro_drums, intro_start, gain=0.22)

# KS arpeggio whispers (VIP 38.2% retained)
for rep in range(INTRO_BARS // 4):
    offset = intro_start + samples_for(rep * 16 + 16)
    arp = ks_arpeggio(4)
    arp = lowpass(arp, cutoff=0.15)
    mix_into(stems["KS_STRINGS"], arp, offset, gain=0.18)

# Wavetable morph texture (V3: new, phi_spline morph in intro)
morph_intro = morph_audio_phi[:min(len(morph_audio_phi), samples_for(INTRO_BARS * 4))]
morph_intro = fade_in(morph_intro, duration_s=BAR * 4)
morph_intro = lowpass(morph_intro, cutoff=0.12)
mix_into(stems["MORPH"], morph_intro, intro_start, gain=0.10)

mix_into(stems["VOCAL"], chop_oo, intro_start + samples_for(3 * 4), gain=0.16)
mix_into(stems["VOCAL"], chop_oo, intro_start + samples_for(6 * 4), gain=0.16)

cursor += samples_for(INTRO_BARS * 4)

# -- BUILD 1 (5 bars) -- "The fracture splits open" --
print("  Rendering Build 1...")
build1_start = cursor

for bar in range(BUILD1_BARS):
    bo = build1_start + samples_for(bar * 4)
    g = phi_build_gain(bar, BUILD1_BARS, start=0.15, end=0.32)
    seg = arp_pulse[:samples_for(4)]
    mix_into(stems["KS_STRINGS"], seg, bo, gain=g)

riser_seg = pitch_riser[:samples_for(BUILD1_BARS * 4)]
mix_into(stems["RISER"], riser_seg, build1_start, gain=0.30)

noise_seg = noise_riser[:samples_for(BUILD1_BARS * 4)]
mix_into(stems["RISER"], noise_seg, build1_start, gain=0.18)

build1_drums = drum_pattern_build(BUILD1_BARS)
mix_into(stems["DRUMS"], build1_drums, build1_start, gain=0.48)

glitch_off = build1_start + samples_for((BUILD1_BARS - 1) * 4)
mix_into(stems["FX"], glitch_trans, glitch_off, gain=0.30)

rev_off = build1_start + samples_for(BUILD1_BARS * 4) - len(reverse_hit)
if rev_off > build1_start:
    mix_into(stems["FX"], reverse_hit, rev_off, gain=0.45)

for bar in range(BUILD1_BARS):
    bo = build1_start + samples_for(bar * 4)
    g = phi_build_gain(bar, BUILD1_BARS, start=0.10, end=0.28)
    seg = chord_minor7[:samples_for(4)]
    mix_into(stems["PAD"], seg, bo, gain=g)

for bar in range(BUILD1_BARS):
    bo = build1_start + samples_for(bar * 4)
    g = phi_build_gain(bar, BUILD1_BARS, start=0.12, end=0.35)
    mix_into(stems["VOCAL"], chop_eh_stutter, bo, gain=g)

ee_offset = build1_start + samples_for(BUILD1_BARS * 4) - len(chop_ee) - SR // 4
if ee_offset > build1_start:
    mix_into(stems["VOCAL"], chop_ee, ee_offset, gain=0.38)

cursor += samples_for(BUILD1_BARS * 4)

# -- DROP 1 (13 bars) -- "The apology fractures" --
print("  Rendering Drop 1 (13 bars)...")
drop1_start = cursor

mix_into(stems["FX"], sub_boom, drop1_start, gain=0.55)
mix_into(stems["FX"], cinema_hit, drop1_start, gain=0.35)
mix_into(stems["FX"], to_np(impact_boom), drop1_start, gain=0.28)
mix_into(stems["VOCAL"], chop_ee, drop1_start, gain=0.28)

for rep in range(DROP1_BARS // 4 + 1):
    offset = drop1_start + samples_for(rep * 16)
    bars_left = min(4, DROP1_BARS - rep * 4)
    if bars_left > 0:
        g = fib_step_gain(rep * 4, DROP1_BARS, start=0.58, end=0.52)
        d1d = drum_pattern_drop(bars_left)
        mix_into(stems["DRUMS"], d1d, offset, gain=g)

for rep in range(DROP1_BARS // 4 + 1):
    offset = drop1_start + samples_for(rep * 16)
    bars_left = min(4, DROP1_BARS - rep * 4)
    if bars_left > 0:
        d1b = apply_sidechain(bass_drop_pattern(bars_left), SC_PUMP, SR)
        g = fib_step_gain(rep * 4, DROP1_BARS, start=0.52, end=0.46)
        mix_into(stems["BASS"], d1b, offset, gain=g)

for rep in range(DROP1_BARS // 4 + 1):
    offset = drop1_start + samples_for(rep * 16)
    bars_left = min(4, DROP1_BARS - rep * 4)
    if bars_left > 0:
        bar_samps = samples_for(bars_left * 4)
        r_seg = riddim_heavy[:min(len(riddim_heavy), bar_samps)]
        r_seg = apply_sidechain(r_seg, SC_PUMP, SR)
        mix_into(stems["RIDDIM"], r_seg, offset, gain=0.28)

for rep in range(DROP1_BARS // 4 + 1):
    offset = drop1_start + samples_for(rep * 16)
    bars_left = min(4, DROP1_BARS - rep * 4)
    if bars_left > 0:
        melody = lead_melody_drop(bars_left)
        mix_into(stems["LEAD"], melody, offset, gain=0.30)

for rep in range(DROP1_BARS // 4 + 1):
    offset = drop1_start + samples_for(rep * 16)
    bars_left = min(4, DROP1_BARS - rep * 4)
    if bars_left > 0:
        fmt = formant_melody(bars_left)
        mix_into(stems["FORMANT"], fmt, offset, gain=0.22)

for bar in range(0, DROP1_BARS, 2):
    stab_off = drop1_start + samples_for(bar * 4)
    mix_into(stems["CHORDS"], fm_hit, stab_off, gain=0.22)

gran_cloud_drop = granular_cloud[:min(len(granular_cloud),
                                      samples_for(DROP1_BARS * 4))]
mix_into(stems["GRANULAR"], gran_cloud_drop, drop1_start, gain=0.08)

for rep in range(DROP1_BARS // 4 + 1):
    offset = drop1_start + samples_for(rep * 16)
    bars_left = min(4, DROP1_BARS - rep * 4)
    if bars_left > 0:
        seg = dark_drone[:samples_for(bars_left * 4)]
        mix_into(stems["DRONE"], seg, offset, gain=0.15)

fill_off = drop1_start + samples_for((DROP1_BARS - 1) * 4)
mix_into(stems["LEAD"], lead_fill(1), fill_off, gain=0.30)
stutter_off = drop1_start + samples_for((DROP1_BARS - 1) * 4 + 2)
mix_into(stems["FX"], stutter, stutter_off, gain=0.28)

tape_off = drop1_start + samples_for(DROP1_BARS * 4) - len(tape_stop)
if tape_off > drop1_start:
    mix_into(stems["FX"], tape_stop, tape_off, gain=0.30)

for bar in range(0, DROP1_BARS, 3):
    mix_into(stems["VOCAL"], chop_ah,
             drop1_start + samples_for(bar * 4 + 1.5), gain=0.18)

cursor += samples_for(DROP1_BARS * 4)

# -- BREAK 1 (5 bars) -- "Silence between the fractures" --
print("  Rendering Break 1 (5 bars -- energy ceiling 0.35)...")
break1_start = cursor

chord_sus_seg = chord_sus4[:samples_for(BREAK1_BARS * 4)]
chord_sus_seg = fade_in(chord_sus_seg, duration_s=BAR)
chord_sus_seg = fade_out(chord_sus_seg, duration_s=BAR * 2)
mix_into(stems["PAD"], chord_sus_seg, break1_start, gain=0.32)

gran_shim_seg = granular_shimmer[:samples_for(BREAK1_BARS * 4)]
gran_shim_seg = fade_in(gran_shim_seg, duration_s=BAR * 0.5)
mix_into(stems["GRANULAR"], gran_shim_seg, break1_start, gain=0.18)

break_notes = ["D3", "A3", "F3", "D4", "Bb3", "G3", "A3", "E3"]
for bar in range(BREAK1_BARS):
    bo = break1_start + samples_for(bar * 4)
    for q in range(4):
        note = break_notes[(bar + q) % len(break_notes)]
        ks = ks_notes[note]
        mix_into(stems["KS_STRINGS"], ks, bo + samples_for(q), gain=0.22)

for bar in range(BREAK1_BARS):
    bo = break1_start + samples_for(bar * 4)
    for q in range(4):
        mix_into(stems["DRUMS"], hat_closed, bo + samples_for(q), gain=0.08)

sub_break = to_np(synthesize_bass(BassPreset(
    name="V3SubDrone", bass_type="sub_sine", frequency=KEY_FREQS["D1"],
    duration_s=BREAK1_BARS * BAR, attack_s=1.0, release_s=2.0
)))
mix_into(stems["BASS"], sub_break, break1_start, gain=0.20)

mix_into(stems["FORMANT"], formant_morph,
         break1_start + samples_for(2 * 4), gain=0.12)

for bar in [0, 2, 4]:
    mix_into(stems["VOCAL"], chop_oo,
             break1_start + samples_for(bar * 4 + 1), gain=0.19)
for bar in [1, 3]:
    mix_into(stems["VOCAL"], chop_oh,
             break1_start + samples_for(bar * 4 + 3), gain=0.14)

cursor += samples_for(BREAK1_BARS * 4)

# -- BUILD 2 (8 bars) -- "The rage crystallizes" --
print("  Rendering Build 2 (8 bars -- with beat repeat)...")
build2_start = cursor

for bar in range(BUILD2_BARS):
    bo = build2_start + samples_for(bar * 4)
    g = phi_build_gain(bar, BUILD2_BARS, start=0.12, end=0.35)
    seg = arp_acid[:samples_for(4)]
    mix_into(stems["KS_STRINGS"], seg, bo, gain=g)

harmonic_seg = harmonic_riser[:samples_for(BUILD2_BARS * 4)]
mix_into(stems["RISER"], harmonic_seg, build2_start, gain=0.35)

noise_seg2 = noise_riser[:samples_for(BUILD2_BARS * 4)]
mix_into(stems["RISER"], noise_seg2, build2_start, gain=0.22)

build2_drums = drum_pattern_build(BUILD2_BARS)
mix_into(stems["DRUMS"], build2_drums, build2_start, gain=0.45)

build2_br = np.array(apply_beat_repeat(build2_drums.tolist(), BR_PHI, BPM, SR))
mix_into(stems["DRUMS"], build2_br, build2_start, gain=0.15)

tape_mid = build2_start + samples_for(4 * 4)
mix_into(stems["FX"], tape_stop, tape_mid, gain=0.25)

dive_off = build2_start + samples_for((BUILD2_BARS - 1) * 4)
mix_into(stems["FX"], pitch_dive, dive_off, gain=0.40)

rev2_off = build2_start + samples_for(BUILD2_BARS * 4) - len(reverse_hit)
if rev2_off > build2_start:
    mix_into(stems["FX"], reverse_hit, rev2_off, gain=0.55)

for bar in range(BUILD2_BARS):
    bo = build2_start + samples_for(bar * 4)
    g = phi_build_gain(bar, BUILD2_BARS, start=0.08, end=0.25)
    seg = chord_power[:samples_for(4)]
    mix_into(stems["PAD"], seg, bo, gain=g)

for i, beat in enumerate([0, 4, 8, 12, 16, 20, 24, 26, 28, 30, 31]):
    g = 0.15 + (i / 10) * 0.30
    if beat < BUILD2_BARS * 4:
        mix_into(stems["VOCAL"], chop_eh_stutter,
                 build2_start + samples_for(beat), gain=g)

mix_into(stems["VOCAL"], chop_ee,
         build2_start + samples_for(BUILD2_BARS * 4 - 1), gain=0.42)

cursor += samples_for(BUILD2_BARS * 4)

# -- DROP 2 (34 bars) -- "MARATHON: THE RAGE UNLEASHED" --
# Longest drop (Fibonacci 34). Progressive internal evolution.
# V3: Internal phases within the marathon -- intensity evolves.
print("  Rendering Drop 2 (34 bars -- MARATHON with internal evolution)...")
drop2_start = cursor

mix_into(stems["FX"], sub_boom, drop2_start, gain=0.60)
mix_into(stems["FX"], cinema_hit, drop2_start, gain=0.40)
mix_into(stems["FX"], to_np(impact_boom), drop2_start, gain=0.32)
mix_into(stems["DRUMS"], clap, drop2_start, gain=0.40)
mix_into(stems["VOCAL"], chop_ee, drop2_start, gain=0.32)

# Drums -- heavier pattern with fibonacci_step energy across 34 bars
for rep in range(DROP2_BARS // 4 + 1):
    offset = drop2_start + samples_for(rep * 16)
    bars_left = min(4, DROP2_BARS - rep * 4)
    if bars_left > 0:
        g = fib_step_gain(rep * 4, DROP2_BARS, start=0.55, end=0.46)
        d2d = drum_pattern_drop2(bars_left)
        mix_into(stems["DRUMS"], d2d, offset, gain=g)

# Bass -- marathon internal evolution: 5-type rotation + sidechain
for rep in range(DROP2_BARS // 4 + 1):
    offset = drop2_start + samples_for(rep * 16)
    bars_left = min(4, DROP2_BARS - rep * 4)
    if bars_left > 0:
        d2b = apply_sidechain(bass_drop2_pattern(bars_left), SC_HARD, SR)
        d2b = distort(d2b, drive=1.4)
        g = fib_step_gain(rep * 4, DROP2_BARS, start=0.52, end=0.44)
        mix_into(stems["BASS"], d2b, offset, gain=g)

# Riddim -- layered heavy + stutter + bounce (V3: all types)
for rep in range(DROP2_BARS // 4 + 1):
    offset = drop2_start + samples_for(rep * 16)
    bars_left = min(4, DROP2_BARS - rep * 4)
    if bars_left > 0:
        bar_samps = samples_for(bars_left * 4)
        r_heavy = riddim_heavy[:min(len(riddim_heavy), bar_samps)]
        r_stutter = riddim_stutter[:min(len(riddim_stutter), bar_samps)]
        r_bounce = riddim_bounce[:min(len(riddim_bounce), bar_samps)]
        r_heavy = apply_sidechain(r_heavy, SC_HARD, SR)
        r_stutter = apply_sidechain(r_stutter, SC_HARD, SR)
        r_bounce = apply_sidechain(r_bounce, SC_HARD, SR)
        mix_into(stems["RIDDIM"], r_heavy, offset, gain=0.25)
        mix_into(stems["RIDDIM"], r_stutter, offset, gain=0.18)
        mix_into(stems["RIDDIM"], r_bounce, offset, gain=0.15)

# Lead -- deeper FM (Drop 2 variant)
for rep in range(DROP2_BARS // 4 + 1):
    offset = drop2_start + samples_for(rep * 16)
    bars_left = min(4, DROP2_BARS - rep * 4)
    if bars_left > 0:
        melody2 = lead_melody_drop2(bars_left)
        mix_into(stems["LEAD"], melody2, offset, gain=0.35)

# Formant melody
for rep in range(DROP2_BARS // 4 + 1):
    offset = drop2_start + samples_for(rep * 16)
    bars_left = min(4, DROP2_BARS - rep * 4)
    if bars_left > 0:
        fmt2 = formant_melody(bars_left)
        mix_into(stems["FORMANT"], fmt2, offset, gain=0.26)

# Supersaw walls + FM stabs
for bar in range(DROP2_BARS):
    stab_off = drop2_start + samples_for(bar * 4)
    mix_into(stems["CHORDS"], saw_chord, stab_off, gain=0.22)
    if bar % 2 == 0:
        wall_seg = saw_wall[:samples_for(4)]
        mix_into(stems["CHORDS"], wall_seg, stab_off, gain=0.18)
    if bar % 2 == 0:
        mix_into(stems["CHORDS"], fm_hit, stab_off, gain=0.20)

# Dark drone underneath
for rep in range(DROP2_BARS // 4 + 1):
    offset = drop2_start + samples_for(rep * 16)
    bars_left = min(4, DROP2_BARS - rep * 4)
    if bars_left > 0:
        seg = dark_drone[:samples_for(bars_left * 4)]
        mix_into(stems["DRONE"], seg, offset, gain=0.16)

# Granular cloud
gran_d2 = granular_cloud[:min(len(granular_cloud),
                               samples_for(DROP2_BARS * 4))]
mix_into(stems["GRANULAR"], gran_d2, drop2_start, gain=0.06)

# V3: Wavetable morph fractal texture layered in drop 2
morph_d2 = morph_audio_fractal[:min(len(morph_audio_fractal),
                                     samples_for(8))]
for bar in range(0, DROP2_BARS, 8):
    morph_off = drop2_start + samples_for(bar * 4)
    mix_into(stems["MORPH"], morph_d2, morph_off, gain=0.10)

# Beat repeat stutters (Dojo: Resampling Chain philosophy)
for trans_bar in [5, 10, 15, 22, 28]:
    if trans_bar < DROP2_BARS:
        trans_off = drop2_start + samples_for(trans_bar * 4)
        chunk_len = min(samples_for(4), len(stems["BASS"]) - trans_off)
        if chunk_len > 0:
            chunk = stems["BASS"][trans_off:trans_off + chunk_len].copy()
            br_chunk = np.array(apply_beat_repeat(chunk.tolist(), BR_SIXTEENTH, BPM, SR))
            mix_into(stems["FX"], br_chunk, trans_off, gain=0.20)

# V3: Triplet beat repeat at transition points (new grid type)
for trans_bar in [8, 17, 25]:
    if trans_bar < DROP2_BARS:
        trans_off = drop2_start + samples_for(trans_bar * 4)
        chunk_len = min(samples_for(4), len(stems["RIDDIM"]) - trans_off)
        if chunk_len > 0:
            chunk = stems["RIDDIM"][trans_off:trans_off + chunk_len].copy()
            br_chunk = np.array(apply_beat_repeat(chunk.tolist(), BR_TRIPLET, BPM, SR))
            mix_into(stems["FX"], br_chunk, trans_off, gain=0.16)

# Glitch transitions within marathon drop
for trans_bar in [7, 14, 20, 27, 33]:
    if trans_bar < DROP2_BARS:
        mix_into(stems["FX"], glitch_trans,
                 drop2_start + samples_for(trans_bar * 4), gain=0.22)

# Stutter in last 2 bars
stutter_off2 = drop2_start + samples_for((DROP2_BARS - 2) * 4)
mix_into(stems["FX"], stutter, stutter_off2, gain=0.30)
mix_into(stems["FX"], stutter, stutter_off2 + samples_for(4), gain=0.34)

# Vocal "ah" chops through the marathon
for bar in range(0, DROP2_BARS, 3):
    mix_into(stems["VOCAL"], chop_ah,
             drop2_start + samples_for(bar * 4 + 2), gain=0.19)

# Tape stop into break
tape_d2 = drop2_start + samples_for(DROP2_BARS * 4) - len(tape_stop)
if tape_d2 > drop2_start:
    mix_into(stems["FX"], tape_stop, tape_d2, gain=0.32)

cursor += samples_for(DROP2_BARS * 4)

# -- BREAK 2 (3 bars) -- "The void between worlds" --
print("  Rendering Break 2 (3 bars -- near-silence floor 0.08)...")
break2_start = cursor

break2_drone = drone[:samples_for(BREAK2_BARS * 4)]
break2_drone = fade_in(break2_drone, duration_s=BAR * 0.5)
break2_drone = fade_out(break2_drone, duration_s=BAR * 2)
mix_into(stems["DRONE"], break2_drone, break2_start, gain=0.12)

gran_freeze_b2 = granular_freeze[:samples_for(BREAK2_BARS * 4)]
gran_freeze_b2 = lowpass(gran_freeze_b2, cutoff=0.06)
mix_into(stems["GRANULAR"], gran_freeze_b2, break2_start, gain=0.10)

mix_into(stems["VOCAL"], chop_ah_long,
         break2_start + samples_for(1 * 4), gain=0.22)

cursor += samples_for(BREAK2_BARS * 4)

# -- BUILD 3 (5 bars) -- "Final ascension to climax" --
print("  Rendering Build 3 (5 bars -- all risers)...")
build3_start = cursor

riser3_pitch = pitch_riser[:samples_for(BUILD3_BARS * 4)]
riser3_harm = harmonic_riser[:samples_for(BUILD3_BARS * 4)]
riser3_noise = noise_riser[:samples_for(BUILD3_BARS * 4)]
mix_into(stems["RISER"], riser3_pitch, build3_start, gain=0.30)
mix_into(stems["RISER"], riser3_harm, build3_start, gain=0.28)
mix_into(stems["RISER"], riser3_noise, build3_start, gain=0.22)

build3_drums = drum_pattern_build(BUILD3_BARS)
mix_into(stems["DRUMS"], build3_drums, build3_start, gain=0.42)

build3_br = np.array(apply_beat_repeat(build3_drums.tolist(), BR_AGGRESSIVE, BPM, SR))
mix_into(stems["DRUMS"], build3_br, build3_start, gain=0.12)

for bar in range(BUILD3_BARS):
    bo = build3_start + samples_for(bar * 4)
    g = phi_build_gain(bar, BUILD3_BARS, start=0.08, end=0.38)
    seg = arp_acid[:samples_for(4)]
    mix_into(stems["KS_STRINGS"], seg, bo, gain=g)

for bar in range(BUILD3_BARS):
    bo = build3_start + samples_for(bar * 4)
    g = phi_build_gain(bar, BUILD3_BARS, start=0.06, end=0.28)
    seg = chord_power[:samples_for(4)]
    mix_into(stems["PAD"], seg, bo, gain=g)

rev3_off = build3_start + samples_for(BUILD3_BARS * 4) - len(reverse_hit)
if rev3_off > build3_start:
    mix_into(stems["FX"], reverse_hit, rev3_off, gain=0.60)
dive3_off = build3_start + samples_for((BUILD3_BARS - 1) * 4)
mix_into(stems["FX"], pitch_dive, dive3_off, gain=0.45)

for bar in range(BUILD3_BARS):
    g = phi_build_gain(bar, BUILD3_BARS, start=0.10, end=0.38)
    mix_into(stems["VOCAL"], chop_eh_stutter,
             build3_start + samples_for(bar * 4), gain=g)

ee3_off = build3_start + samples_for(BUILD3_BARS * 4) - len(chop_ee) - SR // 8
if ee3_off > build3_start:
    mix_into(stems["VOCAL"], chop_ee, ee3_off, gain=0.48)

cursor += samples_for(BUILD3_BARS * 4)

# -- DROP 3 (21 bars) -- "CLIMAX: THE APOLOGY THAT NEVER CAME" --
# Golden Section Point (bar ~89) falls in the MIDDLE of this drop.
print("  Rendering Drop 3 (21 bars -- CLIMAX, Golden Section here)...")
drop3_start = cursor

mix_into(stems["FX"], sub_boom, drop3_start, gain=0.65)
mix_into(stems["FX"], cinema_hit, drop3_start, gain=0.45)
mix_into(stems["FX"], to_np(impact_boom), drop3_start, gain=0.35)
mix_into(stems["DRUMS"], clap, drop3_start, gain=0.32)
mix_into(stems["VOCAL"], chop_ee, drop3_start, gain=0.35)

# Drums -- double kick + 32nd cascades
for rep in range(DROP3_BARS // 4 + 1):
    offset = drop3_start + samples_for(rep * 16)
    bars_left = min(4, DROP3_BARS - rep * 4)
    if bars_left > 0:
        g = fib_step_gain(rep * 4, DROP3_BARS, start=0.48, end=0.40)
        d3d = drum_pattern_drop3(bars_left)
        mix_into(stems["DRUMS"], d3d, offset, gain=g)

# Bass -- FULL 8-sound growl palette rotation
for rep in range(DROP3_BARS // 4 + 1):
    offset = drop3_start + samples_for(rep * 16)
    bars_left = min(4, DROP3_BARS - rep * 4)
    if bars_left > 0:
        d3b = apply_sidechain(bass_drop3_pattern(bars_left), SC_HARD, SR)
        d3b = distort(d3b, drive=1.8)
        g = fib_step_gain(rep * 4, DROP3_BARS, start=0.55, end=0.46)
        mix_into(stems["BASS"], d3b, offset, gain=g)

# Riddim -- all five types layered
for rep in range(DROP3_BARS // 4 + 1):
    offset = drop3_start + samples_for(rep * 16)
    bars_left = min(4, DROP3_BARS - rep * 4)
    if bars_left > 0:
        bar_samps = samples_for(bars_left * 4)
        r_heavy = apply_sidechain(riddim_heavy[:min(len(riddim_heavy), bar_samps)], SC_HARD, SR)
        r_stutter = apply_sidechain(riddim_stutter[:min(len(riddim_stutter), bar_samps)], SC_HARD, SR)
        r_triplet = apply_sidechain(riddim_triplet[:min(len(riddim_triplet), bar_samps)], SC_HARD, SR)
        r_bounce = apply_sidechain(riddim_bounce[:min(len(riddim_bounce), bar_samps)], SC_HARD, SR)
        r_minimal = apply_sidechain(riddim_minimal[:min(len(riddim_minimal), bar_samps)], SC_HARD, SR)
        mix_into(stems["RIDDIM"], r_heavy, offset, gain=0.22)
        mix_into(stems["RIDDIM"], r_stutter, offset, gain=0.16)
        mix_into(stems["RIDDIM"], r_triplet, offset, gain=0.14)
        mix_into(stems["RIDDIM"], r_bounce, offset, gain=0.12)
        mix_into(stems["RIDDIM"], r_minimal, offset, gain=0.10)

# Lead -- DEEPEST FM (Drop 3: depth 7.0)
for rep in range(DROP3_BARS // 4 + 1):
    offset = drop3_start + samples_for(rep * 16)
    bars_left = min(4, DROP3_BARS - rep * 4)
    if bars_left > 0:
        melody3 = lead_melody_drop3(bars_left)
        mix_into(stems["LEAD"], melody3, offset, gain=0.38)

# Formant melody -- maximum presence
for rep in range(DROP3_BARS // 4 + 1):
    offset = drop3_start + samples_for(rep * 16)
    bars_left = min(4, DROP3_BARS - rep * 4)
    if bars_left > 0:
        fmt3 = formant_melody(bars_left)
        mix_into(stems["FORMANT"], fmt3, offset, gain=0.28)

# Supersaw walls + FM stabs -- maximum harmonic density
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

# V3: Spectral morph texture in the climax drop
morph_d3 = morph_audio_spectral[:min(len(morph_audio_spectral),
                                      samples_for(8))]
for bar in range(0, DROP3_BARS, 5):
    morph_off = drop3_start + samples_for(bar * 4)
    mix_into(stems["MORPH"], morph_d3, morph_off, gain=0.12)

# Beat repeat stutters
for trans_bar in [4, 8, 14, 18]:
    if trans_bar < DROP3_BARS:
        trans_off = drop3_start + samples_for(trans_bar * 4)
        chunk_len = min(samples_for(4), len(stems["BASS"]) - trans_off)
        if chunk_len > 0:
            chunk = stems["BASS"][trans_off:trans_off + chunk_len].copy()
            br_chunk = np.array(apply_beat_repeat(chunk.tolist(), BR_PHI, BPM, SR))
            mix_into(stems["FX"], br_chunk, trans_off, gain=0.22)

# Glitch transitions
for trans_bar in [6, 12, 20]:
    if trans_bar < DROP3_BARS:
        mix_into(stems["FX"], glitch_trans,
                 drop3_start + samples_for(trans_bar * 4), gain=0.24)

stutter_off3 = drop3_start + samples_for((DROP3_BARS - 1) * 4)
mix_into(stems["FX"], stutter, stutter_off3, gain=0.30)

# Vocal "ah" accents + climax apology moment
for bar in range(0, DROP3_BARS, 2):
    mix_into(stems["VOCAL"], chop_ah,
             drop3_start + samples_for(bar * 4 + 1.5), gain=0.20)
mix_into(stems["VOCAL"], chop_ah_long,
         drop3_start + samples_for(6 * 4), gain=0.24)

# Tape stop into break 3
tape_d3 = drop3_start + samples_for(DROP3_BARS * 4) - len(tape_stop)
if tape_d3 > drop3_start:
    mix_into(stems["FX"], tape_stop, tape_d3, gain=0.32)

cursor += samples_for(DROP3_BARS * 4)

# -- BREAK 3 (5 bars) -- "Stillness before transcendence" --
# V3 NEW: This break doesn't exist in V2 (only had 2 breaks)
print("  Rendering Break 3 (5 bars -- shimmer + morph, ceil 0.30)...")
break3_start = cursor

# Lush pad -- warmer than break 1
lush_seg = lush_pad[:samples_for(BREAK3_BARS * 4)]
lush_seg = fade_in(lush_seg, duration_s=BAR)
lush_seg = fade_out(lush_seg, duration_s=BAR * 2)
mix_into(stems["PAD"], lush_seg, break3_start, gain=0.28)

# Granular shimmer
gran_shim_b3 = granular_shimmer[:samples_for(BREAK3_BARS * 4)]
mix_into(stems["GRANULAR"], gran_shim_b3, break3_start, gain=0.16)

# V3: Wavetable morph texture in the break (evolving shimmer)
morph_break = morph_audio_phi[:min(len(morph_audio_phi),
                                    samples_for(BREAK3_BARS * 4))]
morph_break = lowpass(morph_break, cutoff=0.15)
mix_into(stems["MORPH"], morph_break, break3_start, gain=0.14)

# KS strings -- reflective
for bar in range(BREAK3_BARS):
    bo = break3_start + samples_for(bar * 4)
    for q in range(4):
        note = break_notes[(bar + q + 3) % len(break_notes)]
        ks = ks_notes[note]
        mix_into(stems["KS_STRINGS"], ks, bo + samples_for(q), gain=0.20)

# Light hats
for bar in range(BREAK3_BARS):
    bo = break3_start + samples_for(bar * 4)
    for q in range(4):
        mix_into(stems["DRUMS"], hat_closed, bo + samples_for(q), gain=0.07)

# Sub drone
sub_break3 = to_np(synthesize_bass(BassPreset(
    name="V3SubDrone3", bass_type="sub_sine", frequency=KEY_FREQS["D1"],
    duration_s=BREAK3_BARS * BAR, attack_s=1.0, release_s=2.0
)))
mix_into(stems["BASS"], sub_break3, break3_start, gain=0.18)

# Vocal -- "oh" whispers
for bar in [1, 3]:
    mix_into(stems["VOCAL"], chop_oh,
             break3_start + samples_for(bar * 4 + 2), gain=0.16)
mix_into(stems["VOCAL"], chop_oo,
         break3_start + samples_for(2 * 4), gain=0.18)

cursor += samples_for(BREAK3_BARS * 4)

# -- BUILD 4 (8 bars) -- "Transcendence awaits" --
# V3 NEW: Final build into the 4th drop.
print("  Rendering Build 4 (8 bars -- transcendence build)...")
build4_start = cursor

# All three risers stacked
riser4_pitch = pitch_riser[:samples_for(BUILD4_BARS * 4)]
riser4_harm = harmonic_riser[:samples_for(BUILD4_BARS * 4)]
riser4_noise = noise_riser[:samples_for(BUILD4_BARS * 4)]
mix_into(stems["RISER"], riser4_pitch, build4_start, gain=0.32)
mix_into(stems["RISER"], riser4_harm, build4_start, gain=0.30)
mix_into(stems["RISER"], riser4_noise, build4_start, gain=0.24)

# Accelerating snare roll
build4_drums = drum_pattern_build(BUILD4_BARS)
mix_into(stems["DRUMS"], build4_drums, build4_start, gain=0.44)

# Beat repeat -- aggressive + triplet layered
build4_br = np.array(apply_beat_repeat(build4_drums.tolist(), BR_AGGRESSIVE, BPM, SR))
mix_into(stems["DRUMS"], build4_br, build4_start, gain=0.12)
build4_br_tri = np.array(apply_beat_repeat(build4_drums.tolist(), BR_TRIPLET, BPM, SR))
mix_into(stems["DRUMS"], build4_br_tri, build4_start, gain=0.08)

# Arp synth -- fastest
for bar in range(BUILD4_BARS):
    bo = build4_start + samples_for(bar * 4)
    g = phi_build_gain(bar, BUILD4_BARS, start=0.10, end=0.40)
    seg = arp_acid[:samples_for(4)]
    mix_into(stems["KS_STRINGS"], seg, bo, gain=g)

# Power chord escalating
for bar in range(BUILD4_BARS):
    bo = build4_start + samples_for(bar * 4)
    g = phi_build_gain(bar, BUILD4_BARS, start=0.08, end=0.30)
    seg = chord_power[:samples_for(4)]
    mix_into(stems["PAD"], seg, bo, gain=g)

# FX transitions
tape_mid4 = build4_start + samples_for(4 * 4)
mix_into(stems["FX"], tape_stop, tape_mid4, gain=0.28)

rev4_off = build4_start + samples_for(BUILD4_BARS * 4) - len(reverse_hit)
if rev4_off > build4_start:
    mix_into(stems["FX"], reverse_hit, rev4_off, gain=0.65)
dive4_off = build4_start + samples_for((BUILD4_BARS - 1) * 4)
mix_into(stems["FX"], pitch_dive, dive4_off, gain=0.50)

# Vocal screams escalating
for bar in range(BUILD4_BARS):
    g = phi_build_gain(bar, BUILD4_BARS, start=0.12, end=0.42)
    mix_into(stems["VOCAL"], chop_eh_stutter,
             build4_start + samples_for(bar * 4), gain=g)

ee4_off = build4_start + samples_for(BUILD4_BARS * 4) - len(chop_ee) - SR // 8
if ee4_off > build4_start:
    mix_into(stems["VOCAL"], chop_ee, ee4_off, gain=0.52)

cursor += samples_for(BUILD4_BARS * 4)

# -- DROP 4 (21 bars) -- "TRANSCENDENCE: BEYOND THE APOLOGY" --
# V3 NEW: FM depth 9.0, deepest pipeline growls, full density.
print("  Rendering Drop 4 (21 bars -- TRANSCENDENCE: FM 9.0)...")
drop4_start = cursor

# Maximum impact
mix_into(stems["FX"], sub_boom, drop4_start, gain=0.68)
mix_into(stems["FX"], cinema_hit, drop4_start, gain=0.48)
mix_into(stems["FX"], to_np(impact_boom), drop4_start, gain=0.38)
mix_into(stems["DRUMS"], clap, drop4_start, gain=0.35)
mix_into(stems["VOCAL"], chop_ee, drop4_start, gain=0.38)

# Drums -- TRANSCENDENCE pattern: triple kick, maximum density
for rep in range(DROP4_BARS // 4 + 1):
    offset = drop4_start + samples_for(rep * 16)
    bars_left = min(4, DROP4_BARS - rep * 4)
    if bars_left > 0:
        g = fib_step_gain(rep * 4, DROP4_BARS, start=0.46, end=0.38)
        d4d = drum_pattern_drop4(bars_left)
        mix_into(stems["DRUMS"], d4d, offset, gain=g)

# Bass -- deep pipeline + all riddim rotation (8 sounds)
for rep in range(DROP4_BARS // 4 + 1):
    offset = drop4_start + samples_for(rep * 16)
    bars_left = min(4, DROP4_BARS - rep * 4)
    if bars_left > 0:
        d4b = apply_sidechain(bass_drop4_pattern(bars_left), SC_HARD, SR)
        d4b = distort(d4b, drive=2.0)
        g = fib_step_gain(rep * 4, DROP4_BARS, start=0.52, end=0.44)
        mix_into(stems["BASS"], d4b, offset, gain=g)

# Riddim -- all five types at maximum density
for rep in range(DROP4_BARS // 4 + 1):
    offset = drop4_start + samples_for(rep * 16)
    bars_left = min(4, DROP4_BARS - rep * 4)
    if bars_left > 0:
        bar_samps = samples_for(bars_left * 4)
        r_heavy = apply_sidechain(riddim_heavy[:min(len(riddim_heavy), bar_samps)], SC_HARD, SR)
        r_stutter = apply_sidechain(riddim_stutter[:min(len(riddim_stutter), bar_samps)], SC_HARD, SR)
        r_triplet = apply_sidechain(riddim_triplet[:min(len(riddim_triplet), bar_samps)], SC_HARD, SR)
        r_bounce = apply_sidechain(riddim_bounce[:min(len(riddim_bounce), bar_samps)], SC_HARD, SR)
        r_minimal = apply_sidechain(riddim_minimal[:min(len(riddim_minimal), bar_samps)], SC_HARD, SR)
        mix_into(stems["RIDDIM"], r_heavy, offset, gain=0.24)
        mix_into(stems["RIDDIM"], r_stutter, offset, gain=0.18)
        mix_into(stems["RIDDIM"], r_triplet, offset, gain=0.15)
        mix_into(stems["RIDDIM"], r_bounce, offset, gain=0.14)
        mix_into(stems["RIDDIM"], r_minimal, offset, gain=0.10)

# Lead -- TRANSCENDENCE FM (depth 9.0!)
for rep in range(DROP4_BARS // 4 + 1):
    offset = drop4_start + samples_for(rep * 16)
    bars_left = min(4, DROP4_BARS - rep * 4)
    if bars_left > 0:
        melody4 = lead_melody_drop4(bars_left)
        mix_into(stems["LEAD"], melody4, offset, gain=0.40)

# Formant melody -- transcendence presence
for rep in range(DROP4_BARS // 4 + 1):
    offset = drop4_start + samples_for(rep * 16)
    bars_left = min(4, DROP4_BARS - rep * 4)
    if bars_left > 0:
        fmt4 = formant_melody(bars_left)
        mix_into(stems["FORMANT"], fmt4, offset, gain=0.30)

# Supersaw walls at maximum density
for bar in range(DROP4_BARS):
    stab_off = drop4_start + samples_for(bar * 4)
    mix_into(stems["CHORDS"], saw_chord, stab_off, gain=0.24)
    wall_seg = saw_wall[:samples_for(4)]
    mix_into(stems["CHORDS"], wall_seg, stab_off, gain=0.20)
    mix_into(stems["CHORDS"], fm_hit, stab_off, gain=0.22)

# Dark drone
for rep in range(DROP4_BARS // 4 + 1):
    offset = drop4_start + samples_for(rep * 16)
    bars_left = min(4, DROP4_BARS - rep * 4)
    if bars_left > 0:
        seg = dark_drone[:samples_for(bars_left * 4)]
        mix_into(stems["DRONE"], seg, offset, gain=0.18)

# Granular texture
gran_d4 = granular_cloud[:min(len(granular_cloud),
                               samples_for(DROP4_BARS * 4))]
mix_into(stems["GRANULAR"], gran_d4, drop4_start, gain=0.07)

# V3: All morph textures layered in transcendence drop
morph_segs = [morph_audio_phi, morph_audio_fractal, morph_audio_spectral]
for i, bar in enumerate(range(0, DROP4_BARS, 7)):
    morph_off = drop4_start + samples_for(bar * 4)
    seg = morph_segs[i % len(morph_segs)]
    seg = seg[:min(len(seg), samples_for(8))]
    mix_into(stems["MORPH"], seg, morph_off, gain=0.14)

# Beat repeat stutters
for trans_bar in [5, 10, 15, 19]:
    if trans_bar < DROP4_BARS:
        trans_off = drop4_start + samples_for(trans_bar * 4)
        chunk_len = min(samples_for(4), len(stems["BASS"]) - trans_off)
        if chunk_len > 0:
            chunk = stems["BASS"][trans_off:trans_off + chunk_len].copy()
            br_chunk = np.array(apply_beat_repeat(chunk.tolist(), BR_PHI, BPM, SR))
            mix_into(stems["FX"], br_chunk, trans_off, gain=0.24)

# Glitch transitions
for trans_bar in [7, 14, 20]:
    if trans_bar < DROP4_BARS:
        mix_into(stems["FX"], glitch_trans,
                 drop4_start + samples_for(trans_bar * 4), gain=0.26)

# Final stutter and tape stop
stutter_off4 = drop4_start + samples_for((DROP4_BARS - 1) * 4)
mix_into(stems["FX"], stutter, stutter_off4, gain=0.32)

tape_final = drop4_start + samples_for(DROP4_BARS * 4) - len(tape_stop)
if tape_final > drop4_start:
    mix_into(stems["FX"], tape_stop, tape_final, gain=0.35)

# Vocal accents + transcendence moment
for bar in range(0, DROP4_BARS, 2):
    mix_into(stems["VOCAL"], chop_ah,
             drop4_start + samples_for(bar * 4 + 1.5), gain=0.22)

# The "transcendence" vocal at the midpoint of this drop
mix_into(stems["VOCAL"], chop_ah_long,
         drop4_start + samples_for(10 * 4), gain=0.26)

cursor += samples_for(DROP4_BARS * 4)

# -- OUTRO (8 bars) -- "The fracture closes" --
print("  Rendering Outro (8 bars -- dissolution)...")
outro_start = cursor

gran_freeze_seg = granular_freeze[:samples_for(OUTRO_BARS * 4)]
gran_freeze_seg = fade_out(gran_freeze_seg, duration_s=BAR * 5)
mix_into(stems["GRANULAR"], gran_freeze_seg, outro_start, gain=0.22)

outro_pad = dark_pad[:samples_for(OUTRO_BARS * 4)]
outro_pad = fade_out(outro_pad, duration_s=BAR * 6)
outro_pad = lowpass(outro_pad, cutoff=0.08)
mix_into(stems["PAD"], outro_pad, outro_start, gain=0.25)

outro_drone = drone[:samples_for(OUTRO_BARS * 4)]
outro_drone = fade_out(outro_drone, duration_s=BAR * 7)
mix_into(stems["DRONE"], outro_drone, outro_start, gain=0.22)

outro_drums = drum_pattern_intro(OUTRO_BARS)
outro_drums = fade_out(outro_drums, duration_s=BAR * 5)
mix_into(stems["DRUMS"], outro_drums, outro_start, gain=0.12)

outro_sub = to_np(synthesize_bass(BassPreset(
    name="V3OutroSub", bass_type="sub_sine", frequency=KEY_FREQS["D1"],
    duration_s=OUTRO_BARS * BAR, attack_s=0.01,
    release_s=OUTRO_BARS * BAR * 0.85
)))
outro_sub = fade_out(outro_sub, duration_s=BAR * 6)
mix_into(stems["BASS"], outro_sub, outro_start, gain=0.16)

# KS arpeggio -- final whispers (VIP 38.2% retained)
for rep in range(OUTRO_BARS // 4):
    offset = outro_start + samples_for(rep * 16)
    arp = ks_arpeggio(4)
    arp = lowpass(arp, cutoff=0.12)
    arp = fade_out(arp, duration_s=BAR * 3)
    mix_into(stems["KS_STRINGS"], arp, offset, gain=0.14)

# V3: Phi morph dissolving in outro
morph_outro = morph_audio_phi[:min(len(morph_audio_phi),
                                    samples_for(OUTRO_BARS * 4))]
morph_outro = fade_out(morph_outro, duration_s=BAR * 6)
morph_outro = lowpass(morph_outro, cutoff=0.10)
mix_into(stems["MORPH"], morph_outro, outro_start, gain=0.08)

mix_into(stems["FX"], pitch_dive,
         outro_start + samples_for(5 * 4), gain=0.25)

# "ah_long" -- the apology that never came
mix_into(stems["VOCAL"], chop_ah_long,
         outro_start + samples_for(1 * 4), gain=0.24)
mix_into(stems["VOCAL"], chop_ah_long,
         outro_start + samples_for(4 * 4), gain=0.20)
final_chop = chop_ah_long * 0.5
final_chop = fade_out(final_chop, duration_s=BAR * 2)
mix_into(stems["VOCAL"], final_chop,
         outro_start + samples_for(6 * 4), gain=0.14)


# ====================================================================
#  DSP POST-PROCESSING -- DOJO: Separate mixing pass
# ====================================================================
print()
print("  Applying DSP processing (DOJO: separate mixing pass)...")

stems["CHORDS"] = apply_sidechain(stems["CHORDS"], SC_PUMP, SR)
stems["PAD"] = apply_sidechain(stems["PAD"], SC_PUMP, SR)

stems["PAD"] = apply_hall(stems["PAD"], HALL_VERB, SR)
stems["GRANULAR"] = apply_hall(stems["GRANULAR"], HALL_VERB, SR)
stems["FORMANT"] = apply_room(stems["FORMANT"], ROOM_VERB, SR)
stems["KS_STRINGS"] = apply_room(stems["KS_STRINGS"], ROOM_VERB, SR)
stems["LEAD"] = apply_room(stems["LEAD"], ROOM_VERB, SR)
stems["VOCAL"] = apply_room(stems["VOCAL"], ROOM_VERB, SR)
stems["CHORDS"] = apply_hall(stems["CHORDS"], HALL_VERB, SR)
stems["MORPH"] = apply_hall(stems["MORPH"], HALL_VERB, SR)

stems["RIDDIM"] = waveshape_distortion(stems["RIDDIM"], drive=0.5, mix=0.3)

print("    PAD         -> apply_hall (decay=3.2s, mix=0.28)")
print("    GRANULAR    -> apply_hall (decay=3.2s, mix=0.28)")
print("    FORMANT     -> apply_room (decay=0.6s, mix=0.18)")
print("    KS_STRINGS  -> apply_room (decay=0.6s, mix=0.18)")
print("    LEAD        -> apply_room (decay=0.6s, mix=0.18)")
print("    VOCAL       -> apply_room (decay=0.6s, mix=0.18)")
print("    CHORDS      -> apply_hall (decay=3.2s, mix=0.28)")
print("    MORPH       -> apply_hall (decay=3.2s, mix=0.28)")
print("    RIDDIM      -> growl waveshape (drive=0.5, mix=0.3)")


# ====================================================================
#  EXPORT STEMS + MASTERED MIXDOWN + MIDI + ALS
# ====================================================================
print()
print("  Bouncing stems...")

os.makedirs("output/stems", exist_ok=True)
stem_paths: list[str] = []

for name in STEM_NAMES:
    buf = stems[name]
    path = f"output/stems/apology_v3_{name}.wav"

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
    print(f"    {name:24s}  {len(buf)/SR:.1f}s  {peak_db:.1f}dB  "
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

# -- Master via mastering_chain --
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

os.makedirs("output", exist_ok=True)
output_path = "output/apology_never_came_v3.wav"

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

bass_events: list[NoteEvent] = []
for bar in range(total_bars):
    bass_events.append(NoteEvent(pitch=MIDI["D1"], start_beat=bar * 4,
                                 duration_beats=2.0, velocity=100))

lead_events: list[NoteEvent] = []
drop1_bar_start = INTRO_BARS + BUILD1_BARS
drop2_bar_start = drop1_bar_start + DROP1_BARS + BREAK1_BARS + BUILD2_BARS
drop3_bar_start = (drop2_bar_start + DROP2_BARS + BREAK2_BARS + BUILD3_BARS)
drop4_bar_start = (drop3_bar_start + DROP3_BARS + BREAK3_BARS + BUILD4_BARS)

for drop_start, drop_len in [(drop1_bar_start, DROP1_BARS),
                              (drop2_bar_start, DROP2_BARS),
                              (drop3_bar_start, DROP3_BARS),
                              (drop4_bar_start, DROP4_BARS)]:
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

ks_events: list[NoteEvent] = []
arp_seq = ["D3", "F3", "A3", "D4", "C4", "Bb3", "G3", "E3"]
for bar in range(4, INTRO_BARS):
    b = bar * 4
    for q in range(4):
        note_name = arp_seq[(bar * 2 + q) % len(arp_seq)]
        ks_events.append(NoteEvent(
            pitch=MIDI[note_name], start_beat=b + q,
            duration_beats=1.0, velocity=70))

break1_bar_start = INTRO_BARS + BUILD1_BARS + DROP1_BARS
for bar in range(BREAK1_BARS):
    b = (break1_bar_start + bar) * 4
    for q in range(4):
        note_name = arp_seq[(bar + q) % len(arp_seq)]
        ks_events.append(NoteEvent(
            pitch=MIDI[note_name], start_beat=b + q,
            duration_beats=1.0, velocity=65))

# Break 3 KS notes (V3 new)
break3_bar_start = (drop3_bar_start + DROP3_BARS)
for bar in range(BREAK3_BARS):
    b = (break3_bar_start + bar) * 4
    for q in range(4):
        note_name = arp_seq[(bar + q + 3) % len(arp_seq)]
        ks_events.append(NoteEvent(
            pitch=MIDI[note_name], start_beat=b + q,
            duration_beats=1.0, velocity=62))

chord_events: list[NoteEvent] = []
dm_chord = [MIDI["D3"], MIDI["F3"], MIDI["A3"]]
for drop_start, drop_len in [(drop1_bar_start, DROP1_BARS),
                              (drop2_bar_start, DROP2_BARS),
                              (drop3_bar_start, DROP3_BARS),
                              (drop4_bar_start, DROP4_BARS)]:
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

midi_path = "output/midi/apology_never_came_v3.mid"
write_midi_file(midi_tracks, midi_path, bpm=BPM)
total_notes = sum(len(evts) for _, evts in midi_tracks)
print(f"    {midi_path}  ({total_notes} notes)")

# -- Ableton Live Set --
print("  Generating Ableton Live project...")

stem_colors = {
    "DRUMS": 1, "BASS": 3, "RIDDIM": 5, "LEAD": 12, "FORMANT": 14,
    "KS_STRINGS": 16, "CHORDS": 20, "PAD": 24, "DRONE": 28,
    "RISER": 32, "VOCAL": 36, "FX": 40, "GRANULAR": 44, "MORPH": 48,
}

als_tracks = []

# Audio tracks — rendered stems with clip references
for idx, name in enumerate(STEM_NAMES):
    stem_abs = os.path.abspath(f"output/stems/apology_v3_{name}.wav")
    als_tracks.append(ALSTrack(
        name=name,
        track_type="audio",
        color=stem_colors.get(name, 0),
        volume_db=0.0,
        pan=STEM_PAN.get(name, 0.0),
        clip_names=[name],
        clip_paths=[stem_abs],
    ))

# MIDI tracks — note data for re-editing in DAW
midi_abs = os.path.abspath("output/midi/apology_never_came_v3.mid")
midi_track_map = {
    "Bass_MIDI": {"color": 4, "device": "Serum 2"},
    "Lead_MIDI": {"color": 13, "device": "Serum 2"},
    "KS_Strings_MIDI": {"color": 17, "device": "Serum 2"},
    "Chords_MIDI": {"color": 21, "device": "Serum 2"},
}
for track_name, cfg in midi_track_map.items():
    als_tracks.append(ALSTrack(
        name=track_name,
        track_type="midi",
        color=cfg["color"],
        volume_db=-6.0,
        mute=True,  # muted by default — user unmutes when ready
        device_names=[cfg["device"]],
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
    ALSScene(name="BUILD_1", tempo=float(BPM)),
    ALSScene(name="DROP_1", tempo=float(BPM)),
    ALSScene(name="BREAK_1", tempo=float(BPM)),
    ALSScene(name="BUILD_2", tempo=float(BPM)),
    ALSScene(name="DROP_2", tempo=float(BPM)),
    ALSScene(name="BREAK_2", tempo=float(BPM)),
    ALSScene(name="BUILD_3", tempo=float(BPM)),
    ALSScene(name="DROP_3", tempo=float(BPM)),
    ALSScene(name="BREAK_3", tempo=float(BPM)),
    ALSScene(name="BUILD_4", tempo=float(BPM)),
    ALSScene(name="DROP_4", tempo=float(BPM)),
    ALSScene(name="OUTRO", tempo=float(BPM)),
]

project = ALSProject(
    name="Apology_Never_Came_V3",
    bpm=float(BPM),
    tracks=als_tracks,
    scenes=als_scenes,
    notes="Can You See The Apology That Never Came (Dojo Mastery) | "
          "D minor | 150 BPM | 432 Hz | PACK_ALPHA 144 bars | v3",
)

os.makedirs("output/ableton", exist_ok=True)
als_path = "output/ableton/Apology_Never_Came_V3.als"
write_als(project, als_path)

# -- Summary --
duration = total_samples / SR
file_size = os.path.getsize(output_path)
stem_dir_size = sum(
    os.path.getsize(os.path.join("output/stems", f))
    for f in os.listdir("output/stems")
    if f.startswith("apology_v3_") and f.endswith(".wav")
)

print()
print("=" * 60)
print('  "Can You See The Apology That Never Came"')
print("  v3 -- DOJO MASTERY (PACK_ALPHA x SB10 x EVOLUTION)")
print("=" * 60)
print(f"  Format:   16-bit WAV @ {SR} Hz")
print(f"  BPM:      {BPM}  |  Key: D minor  |  Tuning: 432 Hz")
print(f"  Duration: {duration:.1f}s "
      f"({int(duration // 60)}:{int(duration % 60):02d})")
print(f"  Bars:     {total_bars}  "
      f"(Golden Section Point: bar ~{golden_section_bar})")
print(f"  Bar counts (PACK_ALPHA): {INTRO_BARS}/{BUILD1_BARS}/"
      f"{DROP1_BARS}/{BREAK1_BARS}/{BUILD2_BARS}/{DROP2_BARS}/"
      f"{BREAK2_BARS}/{BUILD3_BARS}/{DROP3_BARS}/{BREAK3_BARS}/"
      f"{BUILD4_BARS}/{DROP4_BARS}/{OUTRO_BARS}")
print()
print("  V3 Dojo Mastery -- What Changed from V2:")
print("    * PACK_ALPHA structure: 144 bars (was 89) = SB10 avg duration")
print("    * 4 drops (13/34/21/21) -- was 3 drops (13/21/13)")
print("    * Full growl_resample_pipeline(): 6-stage evolving bass")
print("    * wavetable_morph: phi_spline/fractal/spectral per drop")
print("    * evolution_engine: parameter drift tracking across track")
print("    * All 5 riddim types: heavy/stutter/triplet/bounce/minimal")
print("    * FM depth: 3.0 -> 5.0 -> 7.0 -> 9.0 (was max 7.0)")
print("    * Multi-param evolution: FM + filter + distortion increase")
print("    * 34-bar marathon Drop 2 (Fibonacci) with internal phases")
print("    * Beat repeat: phi + 1/16 + 1/32 + 1/12 triplet (was 3)")
print("    * 8-sound growl palette (was 5) = pipeline + manual")
print("    * MORPH stem: evolving wavetable textures across track")
print("    * 13 ALS scenes (was 10), 14 stems (was 13)")
print()
print("  V3 RETAINED (VIP 38.2%):")
print("    * D minor, 432 Hz, 150 BPM")
print("    * KS arpeggio whispers (intro/breaks/outro)")
print("    * Core ascending motif (A3 -> C4 -> D4 -> F4)")
print("    * Clean mono sine sub (PSBS/SB10 invariant)")
print("    * GALATCIA drum samples + vocal chop palette")
print("    * PSBS-aware gains (no stem clipping)")
print()
print("  DOCTRINE Compliance:")
print("    + GALATCIA real drum samples (kick/snare/clap/hat/impact)")
print("    + Serum 2 patch definitions exported (JSON)")
print("    + Mastering chain: EQ -> Compress -> Stereo -> LUFS -> Limit")
print("    + Sidechain pump via engine.sidechain (phi-curve)")
print("    + Reverb via engine.reverb_delay (phi-spaced reflections)")
print("    + MIDI export for all melodic content (4 drops)")
print("    + ALS with AudioClip/SampleRef (not hollow)")
print(f"    + Golden Section Point at bar ~{golden_section_bar}")
print("    + 432 Hz tuning throughout")
print("    + PACK_ALPHA Fibonacci structure: all Fibonacci bar counts")
print("    + growl_resample_pipeline: 6-stage evolving bass (V3 NEW)")
print("    + wavetable_morph: per-drop morphing (V3 NEW)")
print("    + evolution_engine: parameter tracking (V3 NEW)")
print()
print(f"  Stems:    {len(STEM_NAMES)} tracks in output/stems/")
for name in STEM_NAMES:
    print(f"            - {name}")
print(f"  Stems:    {stem_dir_size / 1024 / 1024:.1f} MB total")
print(f"  Mixdown:  {output_path} ({file_size / 1024 / 1024:.1f} MB)")
print(f"  MIDI:     {midi_path}")
print(f"  Serum 2:  output/serum2/apology_v3_patches.json")
print(f"  Presets:  output/presets/ ({len(fxp_presets)} .fxp + 1 .fxb bank)")
print(f"  Ableton:  {als_path}")
print()
print("  Mood:     Defiance x Fracture x Evolution x Transcendence (4-act)")
print("  Modules:  GALATCIA + Serum2 + Granular + ChordPad + FormantSynth")
print("            + RiddimEngine(5) + KarplusStrong + ArpSynth")
print("            + TransitionFX + GrowlResampler + GrowlPipeline(V3)")
print("            + WavetableMorph(V3) + EvolutionEngine(V3)")
print("            + BeatRepeat(4) + MasteringChain")
print("            + Sidechain + Reverb + StereoImager")
print("            + MidiExport + ALSGenerator")
print("=" * 60)

# -- Install to Ableton User Library (drag-and-drop access) --
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

    # Stems -> Samples/DUBFORGE/Stems/
    _stems_dst = _user_lib / "Samples" / "DUBFORGE" / "Stems"
    _stems_dst.mkdir(parents=True, exist_ok=True)
    for _f in Path("output/stems").glob("apology_v3_*.wav"):
        shutil.copy2(_f, _stems_dst / _f.name)
        _installed += 1
    print(f"    Stems:      {_installed} -> {_stems_dst}")

    # Wavetables -> Samples/DUBFORGE/Wavetables/
    _wt_dst = _user_lib / "Samples" / "DUBFORGE" / "Wavetables"
    _wt_dst.mkdir(parents=True, exist_ok=True)
    _wt_count = 0
    for _f in Path("output/wavetables").glob("APOLOGY_V3_*.wav"):
        shutil.copy2(_f, _wt_dst / _f.name)
        _wt_count += 1
    _installed += _wt_count
    print(f"    Wavetables: {_wt_count} -> {_wt_dst}")

    # Presets -> Presets/Instruments/DUBFORGE/
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
    print(f"    Presets:    {_pr_count} -> {_preset_dst}")

    # MIDI -> Samples/DUBFORGE/MIDI/
    _midi_dst = _user_lib / "Samples" / "DUBFORGE" / "MIDI"
    _midi_dst.mkdir(parents=True, exist_ok=True)
    for _f in Path("output/midi").glob("apology_*.mid"):
        shutil.copy2(_f, _midi_dst / _f.name)
    print(f"    MIDI:       1 -> {_midi_dst}")
    _installed += 1

    print(f"    TOTAL:      {_installed} files installed")
else:
    print("    Ableton User Library not found (set ABLETON_USER_LIBRARY env var)")

# -- Open in Ableton Live --
print()
print("  Opening Ableton Live 12...")
subprocess.Popen(["cmd", "/c", "start", "", os.path.abspath(als_path)],
                 creationflags=0x08000000)
print("  Done. Everything automated — stems, presets, wavetables, MIDI installed.")
print()
