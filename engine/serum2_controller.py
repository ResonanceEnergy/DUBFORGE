"""
DUBFORGE Engine — Serum 2 Complete Parameter Controller

Full command-and-control of Xfer Serum 2 (VST2/VST3) via the AbletonBridge.
Every knob, slider, and switch — oscillators, filters, envelopes, LFOs,
FX chain, mod matrix, macros, voicing, global. 230+ parameters.

Architecture:
  1. Serum 2 loads as a PluginDevice on an Ableton MIDI track
  2. AbletonBridge discovers parameter names & indices at runtime
  3. This controller maps human-readable names → indices for fast access
  4. Preset builders create complete sound designs from Python

Usage:
    from engine.ableton_bridge import AbletonBridge
    from engine.serum2_controller import Serum2Controller

    ab = AbletonBridge()
    ab.connect()
    serum = Serum2Controller(ab, track=0, device=0)
    serum.discover()  # reads all param names from live Serum instance
    serum.set_osc_a_wt_position(0.75)
    serum.set_filter1_cutoff(0.3)
    serum.apply_preset("DUBFORGE_GROWL_BASS")
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.log import get_logger

_log = get_logger("dubforge.serum2_controller")


# ═══════════════════════════════════════════════════════════════════════════
# SERUM 2 PARAMETER MAP — All Known Automatable Parameters
# ═══════════════════════════════════════════════════════════════════════════
#
# Serum exposes ~230+ parameters to the DAW via the VST2/VST3 interface.
# The exact index numbers depend on the Serum version and load order.
# We discover indices at runtime but map to known names.
#
# Names below match Serum's actual parameter naming convention
# as exposed in Ableton Live's device view.

SERUM_PARAMS = {
    # ── OSCILLATOR A ─────────────────────────────────────────────────────
    "A Oct":           {"category": "osc_a", "desc": "Oscillator A octave (-4 to +4)", "range": (-4, 4), "default": 0},
    "A Semi":          {"category": "osc_a", "desc": "Semitone offset (-24 to +24)", "range": (-24, 24), "default": 0},
    "A Fine":          {"category": "osc_a", "desc": "Fine tuning (-100 to +100 cents)", "range": (-100, 100), "default": 0},
    "A Coarse":        {"category": "osc_a", "desc": "Coarse tuning", "range": (-24, 24), "default": 0},
    "A Level":         {"category": "osc_a", "desc": "Oscillator A level", "range": (0, 1), "default": 0.7},
    "A Pan":           {"category": "osc_a", "desc": "Pan (-1 L to +1 R)", "range": (-1, 1), "default": 0},
    "A WT Pos":        {"category": "osc_a", "desc": "Wavetable position", "range": (0, 1), "default": 0},
    "A Phase":         {"category": "osc_a", "desc": "Phase offset", "range": (0, 1), "default": 0},
    "A Random":        {"category": "osc_a", "desc": "Random phase", "range": (0, 1), "default": 0},
    "A Warp":          {"category": "osc_a", "desc": "Warp amount", "range": (0, 1), "default": 0},
    "A Uni Voices":    {"category": "osc_a", "desc": "Unison voice count (1-16)", "range": (1, 16), "default": 1},
    "A Uni Det":       {"category": "osc_a", "desc": "Unison detune", "range": (0, 1), "default": 0.2},
    "A Uni Blend":     {"category": "osc_a", "desc": "Unison blend", "range": (0, 1), "default": 0.5},
    "A Uni Width":     {"category": "osc_a", "desc": "Unison stereo width", "range": (0, 1), "default": 1.0},
    "A Uni Stack":     {"category": "osc_a", "desc": "Unison stack mode", "range": (0, 1), "default": 0},

    # ── OSCILLATOR B ─────────────────────────────────────────────────────
    "B Oct":           {"category": "osc_b", "desc": "Oscillator B octave", "range": (-4, 4), "default": 0},
    "B Semi":          {"category": "osc_b", "desc": "Semitone offset", "range": (-24, 24), "default": 0},
    "B Fine":          {"category": "osc_b", "desc": "Fine tuning", "range": (-100, 100), "default": 0},
    "B Coarse":        {"category": "osc_b", "desc": "Coarse tuning", "range": (-24, 24), "default": 0},
    "B Level":         {"category": "osc_b", "desc": "Oscillator B level", "range": (0, 1), "default": 0.7},
    "B Pan":           {"category": "osc_b", "desc": "Pan", "range": (-1, 1), "default": 0},
    "B WT Pos":        {"category": "osc_b", "desc": "Wavetable position", "range": (0, 1), "default": 0},
    "B Phase":         {"category": "osc_b", "desc": "Phase offset", "range": (0, 1), "default": 0},
    "B Random":        {"category": "osc_b", "desc": "Random phase", "range": (0, 1), "default": 0},
    "B Warp":          {"category": "osc_b", "desc": "Warp amount", "range": (0, 1), "default": 0},
    "B Uni Voices":    {"category": "osc_b", "desc": "Unison voices", "range": (1, 16), "default": 1},
    "B Uni Det":       {"category": "osc_b", "desc": "Unison detune", "range": (0, 1), "default": 0.2},
    "B Uni Blend":     {"category": "osc_b", "desc": "Unison blend", "range": (0, 1), "default": 0.5},
    "B Uni Width":     {"category": "osc_b", "desc": "Unison width", "range": (0, 1), "default": 1.0},
    "B Uni Stack":     {"category": "osc_b", "desc": "Unison stack mode", "range": (0, 1), "default": 0},

    # ── SUB OSCILLATOR ───────────────────────────────────────────────────
    "Sub Level":       {"category": "sub", "desc": "Sub oscillator level", "range": (0, 1), "default": 0},
    "Sub Oct":         {"category": "sub", "desc": "Sub octave offset", "range": (-4, 0), "default": -1},
    "Sub Shape":       {"category": "sub", "desc": "Sub waveform shape", "range": (0, 1), "default": 0},
    "Sub Direct Out":  {"category": "sub", "desc": "Sub bypasses filter", "range": (0, 1), "default": 0},

    # ── NOISE OSCILLATOR ─────────────────────────────────────────────────
    "Noise Level":     {"category": "noise", "desc": "Noise oscillator level", "range": (0, 1), "default": 0},
    "Noise Phase":     {"category": "noise", "desc": "Noise phase", "range": (0, 1), "default": 0},
    "Noise Pitch":     {"category": "noise", "desc": "Noise pitch tracking", "range": (0, 1), "default": 0},
    "Noise Direct Out": {"category": "noise", "desc": "Noise bypasses filter", "range": (0, 1), "default": 0},

    # ── FILTER 1 ─────────────────────────────────────────────────────────
    "Fil1 Type":       {"category": "filter1", "desc": "Filter 1 type (LP/BP/HP/Notch/Comb/Flange/etc)", "range": (0, 1), "default": 0},
    "Fil1 Cutoff":     {"category": "filter1", "desc": "Filter 1 cutoff frequency", "range": (0, 1), "default": 1.0},
    "Fil1 Res":        {"category": "filter1", "desc": "Filter 1 resonance", "range": (0, 1), "default": 0},
    "Fil1 Drive":      {"category": "filter1", "desc": "Filter 1 drive/saturation", "range": (0, 1), "default": 0},
    "Fil1 Fat":        {"category": "filter1", "desc": "Filter 1 fat (wider)", "range": (0, 1), "default": 0},
    "Fil1 Mix":        {"category": "filter1", "desc": "Filter 1 wet/dry mix", "range": (0, 1), "default": 1.0},
    "Fil1 Pan":        {"category": "filter1", "desc": "Filter 1 pan spread", "range": (-1, 1), "default": 0},
    "Fil1 Env":        {"category": "filter1", "desc": "Filter 1 envelope amount", "range": (-1, 1), "default": 0},
    "Fil1 KeyTrk":     {"category": "filter1", "desc": "Filter 1 key tracking", "range": (0, 1), "default": 0},
    "Fil1 Vel":        {"category": "filter1", "desc": "Filter 1 velocity sensitivity", "range": (0, 1), "default": 0},

    # ── FILTER 2 ─────────────────────────────────────────────────────────
    "Fil2 Type":       {"category": "filter2", "desc": "Filter 2 type", "range": (0, 1), "default": 0},
    "Fil2 Cutoff":     {"category": "filter2", "desc": "Filter 2 cutoff", "range": (0, 1), "default": 1.0},
    "Fil2 Res":        {"category": "filter2", "desc": "Filter 2 resonance", "range": (0, 1), "default": 0},
    "Fil2 Drive":      {"category": "filter2", "desc": "Filter 2 drive", "range": (0, 1), "default": 0},
    "Fil2 Fat":        {"category": "filter2", "desc": "Filter 2 fat", "range": (0, 1), "default": 0},
    "Fil2 Mix":        {"category": "filter2", "desc": "Filter 2 mix", "range": (0, 1), "default": 1.0},
    "Fil2 Pan":        {"category": "filter2", "desc": "Filter 2 pan", "range": (-1, 1), "default": 0},
    "Fil2 Env":        {"category": "filter2", "desc": "Filter 2 envelope amount", "range": (-1, 1), "default": 0},
    "Fil2 KeyTrk":     {"category": "filter2", "desc": "Key tracking", "range": (0, 1), "default": 0},

    # ── ENVELOPE 1 (AMP) ─────────────────────────────────────────────────
    "Env1 Atk":        {"category": "env1", "desc": "Envelope 1 attack", "range": (0, 1), "default": 0.01},
    "Env1 Hold":       {"category": "env1", "desc": "Envelope 1 hold", "range": (0, 1), "default": 0},
    "Env1 Dec":        {"category": "env1", "desc": "Envelope 1 decay", "range": (0, 1), "default": 0.3},
    "Env1 Sus":        {"category": "env1", "desc": "Envelope 1 sustain", "range": (0, 1), "default": 0.7},
    "Env1 Rel":        {"category": "env1", "desc": "Envelope 1 release", "range": (0, 1), "default": 0.15},

    # ── ENVELOPE 2 (FILTER) ──────────────────────────────────────────────
    "Env2 Atk":        {"category": "env2", "desc": "Envelope 2 attack", "range": (0, 1), "default": 0.01},
    "Env2 Hold":       {"category": "env2", "desc": "Envelope 2 hold", "range": (0, 1), "default": 0},
    "Env2 Dec":        {"category": "env2", "desc": "Envelope 2 decay", "range": (0, 1), "default": 0.3},
    "Env2 Sus":        {"category": "env2", "desc": "Envelope 2 sustain", "range": (0, 1), "default": 0},
    "Env2 Rel":        {"category": "env2", "desc": "Envelope 2 release", "range": (0, 1), "default": 0.15},

    # ── ENVELOPE 3 (MOD) ─────────────────────────────────────────────────
    "Env3 Atk":        {"category": "env3", "desc": "Envelope 3 attack", "range": (0, 1), "default": 0.01},
    "Env3 Hold":       {"category": "env3", "desc": "Envelope 3 hold", "range": (0, 1), "default": 0},
    "Env3 Dec":        {"category": "env3", "desc": "Envelope 3 decay", "range": (0, 1), "default": 0.3},
    "Env3 Sus":        {"category": "env3", "desc": "Envelope 3 sustain", "range": (0, 1), "default": 0},
    "Env3 Rel":        {"category": "env3", "desc": "Envelope 3 release", "range": (0, 1), "default": 0.15},

    # ── LFO 1 ────────────────────────────────────────────────────────────
    "LFO1 Rate":       {"category": "lfo1", "desc": "LFO 1 rate/speed", "range": (0, 1), "default": 0.5},
    "LFO1 Rise":       {"category": "lfo1", "desc": "LFO 1 rise/fade-in time", "range": (0, 1), "default": 0},
    "LFO1 Delay":      {"category": "lfo1", "desc": "LFO 1 delay before start", "range": (0, 1), "default": 0},
    "LFO1 Smooth":     {"category": "lfo1", "desc": "LFO 1 smoothing", "range": (0, 1), "default": 0},
    "LFO1 BPM Sync":   {"category": "lfo1", "desc": "BPM sync on/off", "range": (0, 1), "default": 0},
    "LFO1 Phase":      {"category": "lfo1", "desc": "LFO 1 phase offset", "range": (0, 1), "default": 0},

    # ── LFO 2 ────────────────────────────────────────────────────────────
    "LFO2 Rate":       {"category": "lfo2", "desc": "LFO 2 rate", "range": (0, 1), "default": 0.5},
    "LFO2 Rise":       {"category": "lfo2", "desc": "LFO 2 rise", "range": (0, 1), "default": 0},
    "LFO2 Delay":      {"category": "lfo2", "desc": "LFO 2 delay", "range": (0, 1), "default": 0},
    "LFO2 Smooth":     {"category": "lfo2", "desc": "LFO 2 smooth", "range": (0, 1), "default": 0},
    "LFO2 BPM Sync":   {"category": "lfo2", "desc": "BPM sync", "range": (0, 1), "default": 0},

    # ── LFO 3 ────────────────────────────────────────────────────────────
    "LFO3 Rate":       {"category": "lfo3", "desc": "LFO 3 rate", "range": (0, 1), "default": 0.5},
    "LFO3 Rise":       {"category": "lfo3", "desc": "LFO 3 rise", "range": (0, 1), "default": 0},
    "LFO3 Delay":      {"category": "lfo3", "desc": "LFO 3 delay", "range": (0, 1), "default": 0},
    "LFO3 Smooth":     {"category": "lfo3", "desc": "LFO 3 smooth", "range": (0, 1), "default": 0},

    # ── LFO 4 ────────────────────────────────────────────────────────────
    "LFO4 Rate":       {"category": "lfo4", "desc": "LFO 4 rate", "range": (0, 1), "default": 0.5},
    "LFO4 Rise":       {"category": "lfo4", "desc": "LFO 4 rise", "range": (0, 1), "default": 0},
    "LFO4 Delay":      {"category": "lfo4", "desc": "LFO 4 delay", "range": (0, 1), "default": 0},
    "LFO4 Smooth":     {"category": "lfo4", "desc": "LFO 4 smooth", "range": (0, 1), "default": 0},

    # ── MACROS ───────────────────────────────────────────────────────────
    "Macro 1":         {"category": "macros", "desc": "Macro knob 1", "range": (0, 1), "default": 0},
    "Macro 2":         {"category": "macros", "desc": "Macro knob 2", "range": (0, 1), "default": 0},
    "Macro 3":         {"category": "macros", "desc": "Macro knob 3", "range": (0, 1), "default": 0},
    "Macro 4":         {"category": "macros", "desc": "Macro knob 4", "range": (0, 1), "default": 0},

    # ── FX — DISTORTION ──────────────────────────────────────────────────
    "FX Dist On":      {"category": "fx_dist", "desc": "Distortion enable", "range": (0, 1), "default": 0},
    "FX Dist Mode":    {"category": "fx_dist", "desc": "Distortion type (Tube/Soft/Hard/Lin Fold/Sin Fold/etc)", "range": (0, 1), "default": 0},
    "FX Dist Amount":  {"category": "fx_dist", "desc": "Distortion amount/drive", "range": (0, 1), "default": 0},
    "FX Dist Mix":     {"category": "fx_dist", "desc": "Distortion wet/dry", "range": (0, 1), "default": 1.0},
    "FX Dist Pre":     {"category": "fx_dist", "desc": "Pre-filter for distortion", "range": (0, 1), "default": 0},
    "FX Dist Post":    {"category": "fx_dist", "desc": "Post-filter for distortion", "range": (0, 1), "default": 1.0},

    # ── FX — FLANGER / PHASER ────────────────────────────────────────────
    "FX Flang On":     {"category": "fx_flang", "desc": "Flanger/phaser enable", "range": (0, 1), "default": 0},
    "FX Flang Rate":   {"category": "fx_flang", "desc": "Flanger rate", "range": (0, 1), "default": 0.3},
    "FX Flang Depth":  {"category": "fx_flang", "desc": "Flanger depth", "range": (0, 1), "default": 0.5},
    "FX Flang Feed":   {"category": "fx_flang", "desc": "Flanger feedback", "range": (0, 1), "default": 0.5},
    "FX Flang Mix":    {"category": "fx_flang", "desc": "Flanger mix", "range": (0, 1), "default": 0.5},
    "FX Flang BPM":    {"category": "fx_flang", "desc": "BPM sync", "range": (0, 1), "default": 0},

    # ── FX — CHORUS ──────────────────────────────────────────────────────
    "FX Chor On":      {"category": "fx_chorus", "desc": "Chorus enable", "range": (0, 1), "default": 0},
    "FX Chor Rate":    {"category": "fx_chorus", "desc": "Chorus rate", "range": (0, 1), "default": 0.3},
    "FX Chor Depth":   {"category": "fx_chorus", "desc": "Chorus depth", "range": (0, 1), "default": 0.4},
    "FX Chor Delay":   {"category": "fx_chorus", "desc": "Chorus delay time", "range": (0, 1), "default": 0.3},
    "FX Chor Mix":     {"category": "fx_chorus", "desc": "Chorus mix", "range": (0, 1), "default": 0.5},
    "FX Chor Feed":    {"category": "fx_chorus", "desc": "Chorus feedback", "range": (0, 1), "default": 0.3},
    "FX Chor BPM":     {"category": "fx_chorus", "desc": "BPM sync", "range": (0, 1), "default": 0},

    # ── FX — DELAY ───────────────────────────────────────────────────────
    "FX Delay On":     {"category": "fx_delay", "desc": "Delay enable", "range": (0, 1), "default": 0},
    "FX Delay Time":   {"category": "fx_delay", "desc": "Delay time", "range": (0, 1), "default": 0.35},
    "FX Delay Feed":   {"category": "fx_delay", "desc": "Delay feedback", "range": (0, 1), "default": 0.4},
    "FX Delay Mix":    {"category": "fx_delay", "desc": "Delay mix", "range": (0, 1), "default": 0.3},
    "FX Delay BPM":    {"category": "fx_delay", "desc": "BPM sync", "range": (0, 1), "default": 1},
    "FX Delay Filter": {"category": "fx_delay", "desc": "Delay filter", "range": (0, 1), "default": 0.5},
    "FX Delay Width":  {"category": "fx_delay", "desc": "Delay stereo width", "range": (0, 1), "default": 0.5},

    # ── FX — REVERB ──────────────────────────────────────────────────────
    "FX Rev On":       {"category": "fx_reverb", "desc": "Reverb enable", "range": (0, 1), "default": 0},
    "FX Rev Size":     {"category": "fx_reverb", "desc": "Reverb room size", "range": (0, 1), "default": 0.5},
    "FX Rev Decay":    {"category": "fx_reverb", "desc": "Reverb decay time", "range": (0, 1), "default": 0.5},
    "FX Rev Mix":      {"category": "fx_reverb", "desc": "Reverb mix", "range": (0, 1), "default": 0.15},
    "FX Rev Damp":     {"category": "fx_reverb", "desc": "Reverb damping", "range": (0, 1), "default": 0.5},
    "FX Rev Pre":      {"category": "fx_reverb", "desc": "Pre-delay", "range": (0, 1), "default": 0.1},
    "FX Rev Spin":     {"category": "fx_reverb", "desc": "Modulation spin rate", "range": (0, 1), "default": 0.3},
    "FX Rev Width":    {"category": "fx_reverb", "desc": "Stereo width", "range": (0, 1), "default": 1.0},

    # ── FX — COMPRESSOR ──────────────────────────────────────────────────
    "FX Comp On":      {"category": "fx_comp", "desc": "Compressor enable", "range": (0, 1), "default": 0},
    "FX Comp Thresh":  {"category": "fx_comp", "desc": "Compressor threshold", "range": (0, 1), "default": 0.5},
    "FX Comp Ratio":   {"category": "fx_comp", "desc": "Compressor ratio", "range": (0, 1), "default": 0.3},
    "FX Comp Atk":     {"category": "fx_comp", "desc": "Compressor attack", "range": (0, 1), "default": 0.1},
    "FX Comp Rel":     {"category": "fx_comp", "desc": "Compressor release", "range": (0, 1), "default": 0.3},
    "FX Comp Gain":    {"category": "fx_comp", "desc": "Compressor make-up gain", "range": (0, 1), "default": 0},
    "FX Comp MB":      {"category": "fx_comp", "desc": "Multiband mode", "range": (0, 1), "default": 0},

    # ── FX — EQ ──────────────────────────────────────────────────────────
    "FX EQ On":        {"category": "fx_eq", "desc": "EQ enable", "range": (0, 1), "default": 0},
    "FX EQ Low":       {"category": "fx_eq", "desc": "EQ low gain", "range": (0, 1), "default": 0.5},
    "FX EQ Mid":       {"category": "fx_eq", "desc": "EQ mid gain", "range": (0, 1), "default": 0.5},
    "FX EQ High":      {"category": "fx_eq", "desc": "EQ high gain", "range": (0, 1), "default": 0.5},
    "FX EQ LowFreq":   {"category": "fx_eq", "desc": "EQ low frequency", "range": (0, 1), "default": 0.2},
    "FX EQ HighFreq":  {"category": "fx_eq", "desc": "EQ high frequency", "range": (0, 1), "default": 0.8},
    "FX EQ Q":         {"category": "fx_eq", "desc": "EQ Q/bandwidth", "range": (0, 1), "default": 0.5},

    # ── FX — FILTER ──────────────────────────────────────────────────────
    "FX Filter On":    {"category": "fx_filter", "desc": "FX filter enable", "range": (0, 1), "default": 0},
    "FX Filter Type":  {"category": "fx_filter", "desc": "FX filter type", "range": (0, 1), "default": 0},
    "FX Filter Cutoff": {"category": "fx_filter", "desc": "FX filter cutoff", "range": (0, 1), "default": 0.5},
    "FX Filter Res":   {"category": "fx_filter", "desc": "FX filter resonance", "range": (0, 1), "default": 0},

    # ── FX — HYPER / DIMENSION ───────────────────────────────────────────
    "FX Hyper On":     {"category": "fx_hyper", "desc": "Hyper/Dimension enable", "range": (0, 1), "default": 0},
    "FX Hyper Rate":   {"category": "fx_hyper", "desc": "Hyper rate", "range": (0, 1), "default": 0.3},
    "FX Hyper Amount": {"category": "fx_hyper", "desc": "Hyper amount", "range": (0, 1), "default": 0.3},
    "FX Hyper Mix":    {"category": "fx_hyper", "desc": "Hyper mix", "range": (0, 1), "default": 0.5},
    "FX Hyper Unison":  {"category": "fx_hyper", "desc": "Hyper unison voices", "range": (0, 1), "default": 0.3},
    "FX Hyper Det":    {"category": "fx_hyper", "desc": "Hyper detune", "range": (0, 1), "default": 0.3},

    # ── GLOBAL / VOICING ─────────────────────────────────────────────────
    "Master Vol":      {"category": "global", "desc": "Master output volume", "range": (0, 1), "default": 0.7},
    "Voices":          {"category": "global", "desc": "Max polyphony voices", "range": (1, 32), "default": 8},
    "Porta Time":      {"category": "global", "desc": "Portamento/glide time", "range": (0, 1), "default": 0},
    "Porta Mode":      {"category": "global", "desc": "Portamento mode (0=off, 1=always, 2=legato)", "range": (0, 2), "default": 0},
    "Mono":            {"category": "global", "desc": "Monophonic mode", "range": (0, 1), "default": 0},
    "Legato":          {"category": "global", "desc": "Legato mode", "range": (0, 1), "default": 0},
    "Vel Track":       {"category": "global", "desc": "Velocity tracking amount", "range": (0, 1), "default": 1.0},
    "Osc Mix":         {"category": "global", "desc": "Crossfade between Osc A and B", "range": (-1, 1), "default": 0},
    "Bend Range":      {"category": "global", "desc": "Pitch bend range (semitones)", "range": (0, 48), "default": 2},
}


# ═══════════════════════════════════════════════════════════════════════════
# PRESET LIBRARY — DUBFORGE Sound Designs for Serum 2
# ═══════════════════════════════════════════════════════════════════════════

DUBFORGE_PRESETS = {
    # ── BASS PRESETS ─────────────────────────────────────────────────────

    "DUBFORGE_SUB_BASS": {
        "description": "Deep sub bass — mono, sine-like, low-passed",
        "params": {
            "A Level": 1.0, "A WT Pos": 0.0,  # pure sine
            "A Uni Voices": 1,
            "B Level": 0.0,  # B off
            "Sub Level": 0.8, "Sub Oct": -1,
            "Fil1 Cutoff": 0.15, "Fil1 Res": 0.0, "Fil1 Type": 0.0,
            "Env1 Atk": 0.005, "Env1 Dec": 0.2, "Env1 Sus": 0.9, "Env1 Rel": 0.1,
            "Mono": 1, "Porta Time": 0.05, "Porta Mode": 2,
            "Voices": 1, "Master Vol": 0.85,
        },
    },

    "DUBFORGE_GROWL_BASS": {
        "description": "Aggressive mid-bass growl — Subtronics style, filter LFO modulation",
        "params": {
            "A Level": 0.8, "A WT Pos": 0.35,
            "A Uni Voices": 5, "A Uni Det": 0.15, "A Uni Blend": 0.7, "A Uni Width": 0.8,
            "A Warp": 0.4,
            "B Level": 0.6, "B WT Pos": 0.65,
            "B Uni Voices": 3, "B Uni Det": 0.2, "B Uni Blend": 0.5,
            "Fil1 Cutoff": 0.3, "Fil1 Res": 0.45, "Fil1 Drive": 0.6, "Fil1 Env": 0.7,
            "Fil1 Type": 0.0,  # LP
            "Env1 Atk": 0.001, "Env1 Dec": 0.15, "Env1 Sus": 0.6, "Env1 Rel": 0.1,
            "Env2 Atk": 0.001, "Env2 Dec": 0.25, "Env2 Sus": 0.0, "Env2 Rel": 0.1,
            "LFO1 Rate": 0.6, "LFO1 BPM Sync": 1,
            "FX Dist On": 1, "FX Dist Mode": 0.3, "FX Dist Amount": 0.55, "FX Dist Mix": 0.8,
            "Mono": 1, "Porta Time": 0.03, "Porta Mode": 2,
            "Voices": 1, "Master Vol": 0.8,
        },
    },

    "DUBFORGE_RIDDIM_BASS": {
        "description": "Riddim-style bass — tight, mid-range focused, heavy filter",
        "params": {
            "A Level": 0.85, "A WT Pos": 0.5,
            "A Uni Voices": 7, "A Uni Det": 0.12, "A Uni Blend": 0.6,
            "B Level": 0.5, "B WT Pos": 0.4,
            "B Uni Voices": 5, "B Uni Det": 0.18,
            "Fil1 Cutoff": 0.25, "Fil1 Res": 0.55, "Fil1 Drive": 0.7,
            "Fil1 Env": 0.8, "Fil1 Type": 0.0,
            "Env1 Atk": 0.001, "Env1 Dec": 0.1, "Env1 Sus": 0.5, "Env1 Rel": 0.08,
            "Env2 Atk": 0.001, "Env2 Dec": 0.15, "Env2 Sus": 0.0, "Env2 Rel": 0.08,
            "FX Dist On": 1, "FX Dist Mode": 0.5, "FX Dist Amount": 0.65, "FX Dist Mix": 0.7,
            "FX Comp On": 1, "FX Comp Thresh": 0.4, "FX Comp Ratio": 0.6,
            "Mono": 1, "Porta Time": 0.0, "Voices": 1, "Master Vol": 0.85,
        },
    },

    "DUBFORGE_TEAROUT_BASS": {
        "description": "Tearout/heavy bass — aggressive wavetable + distortion stacking",
        "params": {
            "A Level": 0.9, "A WT Pos": 0.6,
            "A Uni Voices": 7, "A Uni Det": 0.2, "A Uni Blend": 0.8, "A Warp": 0.5,
            "B Level": 0.7, "B WT Pos": 0.8, "B Semi": 12,
            "B Uni Voices": 5, "B Uni Det": 0.25, "B Warp": 0.6,
            "Fil1 Cutoff": 0.35, "Fil1 Res": 0.5, "Fil1 Drive": 0.8,
            "Fil1 Env": 0.6, "Fil1 Fat": 0.4,
            "Env1 Atk": 0.001, "Env1 Dec": 0.2, "Env1 Sus": 0.5, "Env1 Rel": 0.1,
            "Env2 Atk": 0.001, "Env2 Dec": 0.3, "Env2 Sus": 0.0, "Env2 Rel": 0.15,
            "FX Dist On": 1, "FX Dist Mode": 0.7, "FX Dist Amount": 0.8, "FX Dist Mix": 0.9,
            "FX Comp On": 1, "FX Comp Thresh": 0.35, "FX Comp Ratio": 0.7,
            "Mono": 1, "Porta Time": 0.02, "Porta Mode": 2,
            "Voices": 1, "Master Vol": 0.8,
        },
    },

    "DUBFORGE_REESE_BASS": {
        "description": "Reese bass — detuned saws, phasing movement",
        "params": {
            "A Level": 0.85, "A WT Pos": 0.0,
            "A Uni Voices": 3, "A Uni Det": 0.08, "A Uni Blend": 0.3, "A Uni Width": 0.6,
            "B Level": 0.85, "B WT Pos": 0.0, "B Fine": 8,
            "B Uni Voices": 3, "B Uni Det": 0.10, "B Uni Blend": 0.3,
            "Fil1 Cutoff": 0.4, "Fil1 Res": 0.2, "Fil1 Drive": 0.2,
            "Env1 Atk": 0.01, "Env1 Dec": 0.5, "Env1 Sus": 0.8, "Env1 Rel": 0.3,
            "LFO1 Rate": 0.15, "LFO1 Smooth": 0.7,
            "FX Chor On": 1, "FX Chor Rate": 0.2, "FX Chor Depth": 0.3, "FX Chor Mix": 0.15,
            "Mono": 1, "Porta Time": 0.08, "Porta Mode": 2,
            "Voices": 1, "Master Vol": 0.8,
        },
    },

    "DUBFORGE_FM_BASS": {
        "description": "FM-style bass — metallic, complex harmonics",
        "params": {
            "A Level": 0.8, "A WT Pos": 0.0,
            "A Uni Voices": 1,
            "B Level": 0.6, "B WT Pos": 0.3, "B Semi": 7,
            "B Uni Voices": 1,
            "Osc Mix": 0.3,
            "Fil1 Cutoff": 0.5, "Fil1 Res": 0.3, "Fil1 Drive": 0.4,
            "Fil1 Env": 0.5,
            "Env1 Atk": 0.001, "Env1 Dec": 0.2, "Env1 Sus": 0.4, "Env1 Rel": 0.1,
            "Env2 Atk": 0.001, "Env2 Dec": 0.15, "Env2 Sus": 0.0, "Env2 Rel": 0.1,
            "FX Dist On": 1, "FX Dist Amount": 0.4, "FX Dist Mix": 0.6,
            "Mono": 1, "Voices": 1, "Master Vol": 0.8,
        },
    },

    # ── LEAD PRESETS ─────────────────────────────────────────────────────

    "DUBFORGE_SCREECH_LEAD": {
        "description": "Screaming lead — bright, aggressive, wide",
        "params": {
            "A Level": 0.9, "A WT Pos": 0.7,
            "A Uni Voices": 7, "A Uni Det": 0.25, "A Uni Blend": 0.8, "A Uni Width": 1.0,
            "A Warp": 0.5,
            "B Level": 0.5, "B WT Pos": 0.9, "B Semi": 12,
            "Fil1 Cutoff": 0.7, "Fil1 Res": 0.3, "Fil1 Drive": 0.5,
            "Env1 Atk": 0.001, "Env1 Dec": 0.3, "Env1 Sus": 0.6, "Env1 Rel": 0.15,
            "FX Dist On": 1, "FX Dist Amount": 0.5, "FX Dist Mix": 0.7,
            "FX Rev On": 1, "FX Rev Size": 0.3, "FX Rev Mix": 0.1,
            "FX Delay On": 1, "FX Delay Time": 0.25, "FX Delay Mix": 0.15, "FX Delay BPM": 1,
            "Mono": 0, "Voices": 4, "Master Vol": 0.75,
        },
    },

    "DUBFORGE_SUPERSAW_LEAD": {
        "description": "Thick supersaw lead — massive unison, wide stereo",
        "params": {
            "A Level": 0.9, "A WT Pos": 0.0,  # saw
            "A Uni Voices": 16, "A Uni Det": 0.3, "A Uni Blend": 0.5, "A Uni Width": 1.0,
            "B Level": 0.4, "B WT Pos": 0.0, "B Semi": 12,
            "B Uni Voices": 8, "B Uni Det": 0.25,
            "Fil1 Cutoff": 0.65, "Fil1 Res": 0.15, "Fil1 Env": 0.2,
            "Env1 Atk": 0.01, "Env1 Dec": 0.4, "Env1 Sus": 0.7, "Env1 Rel": 0.3,
            "FX Rev On": 1, "FX Rev Size": 0.5, "FX Rev Mix": 0.15,
            "FX Chor On": 1, "FX Chor Rate": 0.15, "FX Chor Mix": 0.1,
            "Mono": 0, "Voices": 8, "Master Vol": 0.75,
        },
    },

    # ── PAD PRESETS ──────────────────────────────────────────────────────

    "DUBFORGE_DARK_PAD": {
        "description": "Dark atmospheric pad — slow attack, filtered, reverbed",
        "params": {
            "A Level": 0.6, "A WT Pos": 0.3,
            "A Uni Voices": 5, "A Uni Det": 0.1, "A Uni Width": 1.0,
            "B Level": 0.5, "B WT Pos": 0.6,
            "B Uni Voices": 5, "B Uni Det": 0.12,
            "Fil1 Cutoff": 0.25, "Fil1 Res": 0.1, "Fil1 Env": 0.15,
            "Env1 Atk": 0.4, "Env1 Dec": 0.6, "Env1 Sus": 0.5, "Env1 Rel": 0.8,
            "LFO1 Rate": 0.1, "LFO1 Smooth": 0.8,
            "FX Rev On": 1, "FX Rev Size": 0.8, "FX Rev Mix": 0.4, "FX Rev Decay": 0.7,
            "FX Chor On": 1, "FX Chor Rate": 0.1, "FX Chor Mix": 0.15,
            "Mono": 0, "Voices": 8, "Master Vol": 0.6,
        },
    },

    "DUBFORGE_AMBIENT_PAD": {
        "description": "Ethereal ambient pad — gentle, washed, evolving",
        "params": {
            "A Level": 0.5, "A WT Pos": 0.4,
            "A Uni Voices": 7, "A Uni Det": 0.08, "A Uni Width": 1.0,
            "B Level": 0.4, "B WT Pos": 0.7, "B Semi": 7,
            "B Uni Voices": 5, "B Uni Det": 0.1,
            "Fil1 Cutoff": 0.45, "Fil1 Res": 0.05,
            "Env1 Atk": 0.8, "Env1 Dec": 0.8, "Env1 Sus": 0.6, "Env1 Rel": 1.0,
            "LFO1 Rate": 0.05, "LFO1 Smooth": 1.0,
            "FX Rev On": 1, "FX Rev Size": 0.9, "FX Rev Mix": 0.55, "FX Rev Decay": 0.85,
            "FX Delay On": 1, "FX Delay Time": 0.4, "FX Delay Mix": 0.2, "FX Delay BPM": 1, "FX Delay Feed": 0.5,
            "Mono": 0, "Voices": 8, "Master Vol": 0.55,
        },
    },

    # ── FX / RISER / HIT PRESETS ─────────────────────────────────────────

    "DUBFORGE_RISER": {
        "description": "Tension riser — rising filter + pitch, noise layer",
        "params": {
            "A Level": 0.5, "A WT Pos": 0.5,
            "A Uni Voices": 7, "A Uni Det": 0.15, "A Uni Width": 1.0,
            "Noise Level": 0.3, "Noise Direct Out": 0,
            "Fil1 Cutoff": 0.1, "Fil1 Res": 0.3, "Fil1 Env": 1.0,
            "Env1 Atk": 1.0, "Env1 Dec": 0.5, "Env1 Sus": 0.8, "Env1 Rel": 0.3,
            "Env2 Atk": 1.0, "Env2 Dec": 0.5, "Env2 Sus": 1.0, "Env2 Rel": 0.3,
            "FX Rev On": 1, "FX Rev Size": 0.7, "FX Rev Mix": 0.3,
            "FX Delay On": 1, "FX Delay Time": 0.35, "FX Delay Mix": 0.15, "FX Delay BPM": 1,
            "Mono": 0, "Voices": 4, "Master Vol": 0.65,
        },
    },

    "DUBFORGE_IMPACT": {
        "description": "Noise impact hit — short, punchy, layered",
        "params": {
            "A Level": 0.7, "A WT Pos": 0.8,
            "Noise Level": 0.6,
            "Fil1 Cutoff": 0.7, "Fil1 Res": 0.4, "Fil1 Env": -0.8,
            "Env1 Atk": 0.001, "Env1 Dec": 0.15, "Env1 Sus": 0.0, "Env1 Rel": 0.2,
            "Env2 Atk": 0.001, "Env2 Dec": 0.1, "Env2 Sus": 0.0, "Env2 Rel": 0.1,
            "FX Dist On": 1, "FX Dist Amount": 0.4, "FX Dist Mix": 0.5,
            "FX Rev On": 1, "FX Rev Size": 0.3, "FX Rev Mix": 0.2,
            "Mono": 0, "Voices": 4, "Master Vol": 0.8,
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# SERUM 2 CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════

class Serum2Controller:
    """Full Serum 2 parameter controller using AbletonBridge.

    Discovers Serum 2's actual parameter indices at runtime from a live
    Ableton session, then provides named access to every parameter.
    """

    def __init__(self, bridge, track: int, device: int = 0):
        """
        Args:
            bridge: AbletonBridge instance (connected)
            track: Track index where Serum 2 is loaded
            device: Device index on that track (usually 0)
        """
        self.bridge = bridge
        self.track = track
        self.device = device
        self._param_map: dict[str, dict] = {}  # name → {index, value, min, max}
        self._discovered = False
        self._fuzzy_cache: dict[str, str] = {}  # our_name → actual_name

    # ── DISCOVERY ────────────────────────────────────────────────────────

    def discover(self) -> bool:
        """Discover all Serum 2 parameters from live instance.

        Must be called before setting parameters. Reads every parameter
        name and index from the running Serum 2 instance in Ableton.
        """
        params = self.bridge.discover_device_params(self.track, self.device)
        if not params:
            _log.warning("No parameters found. Is Serum 2 loaded on "
                         f"track {self.track}, device {self.device}?")
            return False

        self._param_map = params
        self._discovered = True
        self._build_fuzzy_cache()

        _log.info(f"Discovered {len(params)} Serum 2 parameters on "
                  f"track {self.track}, device {self.device}")
        return True

    def _build_fuzzy_cache(self):
        """Build fuzzy name matching from SERUM_PARAMS to actual param names."""
        actual_names = list(self._param_map.keys())
        actual_lower = {n.lower(): n for n in actual_names}

        for our_name in SERUM_PARAMS:
            # Exact match
            if our_name in self._param_map:
                self._fuzzy_cache[our_name] = our_name
                continue
            # Case-insensitive match
            if our_name.lower() in actual_lower:
                self._fuzzy_cache[our_name] = actual_lower[our_name.lower()]
                continue
            # Partial match — find best substring match
            best = None
            for actual in actual_names:
                if our_name.lower().replace(" ", "") in actual.lower().replace(" ", ""):
                    best = actual
                    break
            if best:
                self._fuzzy_cache[our_name] = best

    def _resolve_name(self, name: str) -> str | None:
        """Resolve a DUBFORGE param name to actual Serum param name."""
        if name in self._fuzzy_cache:
            return self._fuzzy_cache[name]
        if name in self._param_map:
            return name
        # Try case-insensitive
        for actual in self._param_map:
            if actual.lower() == name.lower():
                self._fuzzy_cache[name] = actual
                return actual
        return None

    # ── PARAMETER ACCESS ─────────────────────────────────────────────────

    def set_param(self, name: str, value: float) -> bool:
        """Set a Serum 2 parameter by name.

        Accepts DUBFORGE names (e.g., "A WT Pos") or exact Serum names.
        """
        actual = self._resolve_name(name)
        if not actual:
            _log.warning(f"Parameter '{name}' not found in Serum 2")
            return False

        info = self._param_map[actual]
        self.bridge.set_device_parameter(
            self.track, self.device, info["index"], value)
        return True

    def get_param(self, name: str) -> float | None:
        """Get current value of a Serum 2 parameter."""
        actual = self._resolve_name(name)
        if not actual:
            return None

        info = self._param_map[actual]
        return self.bridge.get_device_parameter_value(
            self.track, self.device, info["index"])

    def set_params(self, params: dict[str, float]):
        """Set multiple parameters at once."""
        for name, value in params.items():
            self.set_param(name, value)

    # ── OSCILLATOR A ─────────────────────────────────────────────────────

    def set_osc_a_wt_position(self, pos: float):
        """Set Osc A wavetable position (0-1)."""
        self.set_param("A WT Pos", pos)

    def set_osc_a_level(self, level: float):
        self.set_param("A Level", level)

    def set_osc_a_pan(self, pan: float):
        self.set_param("A Pan", pan)

    def set_osc_a_octave(self, octave: int):
        self.set_param("A Oct", float(octave))

    def set_osc_a_semi(self, semi: int):
        self.set_param("A Semi", float(semi))

    def set_osc_a_fine(self, cents: float):
        self.set_param("A Fine", cents)

    def set_osc_a_unison(self, voices: int, detune: float = 0.2,
                          blend: float = 0.5, width: float = 1.0):
        """Configure Osc A unison."""
        self.set_param("A Uni Voices", float(voices))
        self.set_param("A Uni Det", detune)
        self.set_param("A Uni Blend", blend)
        self.set_param("A Uni Width", width)

    def set_osc_a_warp(self, amount: float):
        self.set_param("A Warp", amount)

    def set_osc_a_phase(self, phase: float):
        self.set_param("A Phase", phase)

    # ── OSCILLATOR B ─────────────────────────────────────────────────────

    def set_osc_b_wt_position(self, pos: float):
        self.set_param("B WT Pos", pos)

    def set_osc_b_level(self, level: float):
        self.set_param("B Level", level)

    def set_osc_b_pan(self, pan: float):
        self.set_param("B Pan", pan)

    def set_osc_b_octave(self, octave: int):
        self.set_param("B Oct", float(octave))

    def set_osc_b_semi(self, semi: int):
        self.set_param("B Semi", float(semi))

    def set_osc_b_fine(self, cents: float):
        self.set_param("B Fine", cents)

    def set_osc_b_unison(self, voices: int, detune: float = 0.2,
                          blend: float = 0.5, width: float = 1.0):
        self.set_param("B Uni Voices", float(voices))
        self.set_param("B Uni Det", detune)
        self.set_param("B Uni Blend", blend)
        self.set_param("B Uni Width", width)

    def set_osc_b_warp(self, amount: float):
        self.set_param("B Warp", amount)

    # ── SUB / NOISE ──────────────────────────────────────────────────────

    def set_sub_level(self, level: float):
        self.set_param("Sub Level", level)

    def set_sub_octave(self, oct: int):
        self.set_param("Sub Oct", float(oct))

    def set_noise_level(self, level: float):
        self.set_param("Noise Level", level)

    # ── FILTER 1 ─────────────────────────────────────────────────────────

    def set_filter1(self, cutoff: float, resonance: float = 0.0,
                    drive: float = 0.0, env_amount: float = 0.0,
                    filter_type: float = 0.0):
        """Configure Filter 1."""
        self.set_param("Fil1 Cutoff", cutoff)
        self.set_param("Fil1 Res", resonance)
        self.set_param("Fil1 Drive", drive)
        self.set_param("Fil1 Env", env_amount)
        if filter_type:
            self.set_param("Fil1 Type", filter_type)

    def set_filter1_cutoff(self, cutoff: float):
        self.set_param("Fil1 Cutoff", cutoff)

    def set_filter1_resonance(self, res: float):
        self.set_param("Fil1 Res", res)

    def set_filter1_drive(self, drive: float):
        self.set_param("Fil1 Drive", drive)

    # ── FILTER 2 ─────────────────────────────────────────────────────────

    def set_filter2(self, cutoff: float, resonance: float = 0.0,
                    drive: float = 0.0, env_amount: float = 0.0):
        self.set_param("Fil2 Cutoff", cutoff)
        self.set_param("Fil2 Res", resonance)
        self.set_param("Fil2 Drive", drive)
        self.set_param("Fil2 Env", env_amount)

    def set_filter2_cutoff(self, cutoff: float):
        self.set_param("Fil2 Cutoff", cutoff)

    # ── ENVELOPES ────────────────────────────────────────────────────────

    def set_envelope(self, env_num: int, attack: float, decay: float,
                     sustain: float, release: float, hold: float = 0.0):
        """Set envelope 1-3 (AHDSR)."""
        prefix = f"Env{env_num}"
        self.set_param(f"{prefix} Atk", attack)
        self.set_param(f"{prefix} Hold", hold)
        self.set_param(f"{prefix} Dec", decay)
        self.set_param(f"{prefix} Sus", sustain)
        self.set_param(f"{prefix} Rel", release)

    def set_amp_envelope(self, attack: float, decay: float,
                          sustain: float, release: float):
        """Shortcut for Envelope 1 (amplitude)."""
        self.set_envelope(1, attack, decay, sustain, release)

    def set_filter_envelope(self, attack: float, decay: float,
                              sustain: float, release: float):
        """Shortcut for Envelope 2 (filter)."""
        self.set_envelope(2, attack, decay, sustain, release)

    # ── LFOs ─────────────────────────────────────────────────────────────

    def set_lfo(self, lfo_num: int, rate: float, bpm_sync: bool = False,
                rise: float = 0.0, delay: float = 0.0, smooth: float = 0.0):
        """Configure LFO 1-4."""
        prefix = f"LFO{lfo_num}"
        self.set_param(f"{prefix} Rate", rate)
        self.set_param(f"{prefix} Rise", rise)
        self.set_param(f"{prefix} Delay", delay)
        self.set_param(f"{prefix} Smooth", smooth)
        if lfo_num <= 2:
            self.set_param(f"{prefix} BPM Sync", float(bpm_sync))

    def set_lfo_rate(self, lfo_num: int, rate: float):
        self.set_param(f"LFO{lfo_num} Rate", rate)

    # ── MACROS ───────────────────────────────────────────────────────────

    def set_macro(self, macro_num: int, value: float):
        """Set Macro 1-4 value."""
        self.set_param(f"Macro {macro_num}", value)

    def set_macros(self, values: list[float]):
        """Set all macros at once. values=[m1, m2, m3, m4]."""
        for i, v in enumerate(values[:4], 1):
            self.set_macro(i, v)

    # ── FX CHAIN ─────────────────────────────────────────────────────────

    def set_distortion(self, enabled: bool = True, amount: float = 0.5,
                       mode: float = 0.3, mix: float = 0.8):
        """Configure Serum's distortion FX."""
        self.set_param("FX Dist On", float(enabled))
        self.set_param("FX Dist Amount", amount)
        self.set_param("FX Dist Mode", mode)
        self.set_param("FX Dist Mix", mix)

    def set_reverb(self, enabled: bool = True, size: float = 0.5,
                   mix: float = 0.2, decay: float = 0.5,
                   damping: float = 0.5, width: float = 1.0):
        """Configure Serum's reverb FX."""
        self.set_param("FX Rev On", float(enabled))
        self.set_param("FX Rev Size", size)
        self.set_param("FX Rev Mix", mix)
        self.set_param("FX Rev Decay", decay)
        self.set_param("FX Rev Damp", damping)
        self.set_param("FX Rev Width", width)

    def set_delay(self, enabled: bool = True, time: float = 0.35,
                  feedback: float = 0.4, mix: float = 0.2,
                  bpm_sync: bool = True, width: float = 0.5):
        """Configure Serum's delay FX."""
        self.set_param("FX Delay On", float(enabled))
        self.set_param("FX Delay Time", time)
        self.set_param("FX Delay Feed", feedback)
        self.set_param("FX Delay Mix", mix)
        self.set_param("FX Delay BPM", float(bpm_sync))
        self.set_param("FX Delay Width", width)

    def set_chorus(self, enabled: bool = True, rate: float = 0.3,
                   depth: float = 0.4, mix: float = 0.3):
        """Configure Serum's chorus FX."""
        self.set_param("FX Chor On", float(enabled))
        self.set_param("FX Chor Rate", rate)
        self.set_param("FX Chor Depth", depth)
        self.set_param("FX Chor Mix", mix)

    def set_flanger(self, enabled: bool = True, rate: float = 0.3,
                    depth: float = 0.5, feedback: float = 0.5,
                    mix: float = 0.3):
        """Configure Serum's flanger/phaser FX."""
        self.set_param("FX Flang On", float(enabled))
        self.set_param("FX Flang Rate", rate)
        self.set_param("FX Flang Depth", depth)
        self.set_param("FX Flang Feed", feedback)
        self.set_param("FX Flang Mix", mix)

    def set_compressor(self, enabled: bool = True, threshold: float = 0.5,
                       ratio: float = 0.3, attack: float = 0.1,
                       release: float = 0.3, gain: float = 0.0):
        """Configure Serum's compressor FX."""
        self.set_param("FX Comp On", float(enabled))
        self.set_param("FX Comp Thresh", threshold)
        self.set_param("FX Comp Ratio", ratio)
        self.set_param("FX Comp Atk", attack)
        self.set_param("FX Comp Rel", release)
        self.set_param("FX Comp Gain", gain)

    def set_eq(self, enabled: bool = True, low: float = 0.5,
               mid: float = 0.5, high: float = 0.5):
        """Configure Serum's EQ FX."""
        self.set_param("FX EQ On", float(enabled))
        self.set_param("FX EQ Low", low)
        self.set_param("FX EQ Mid", mid)
        self.set_param("FX EQ High", high)

    def set_hyper(self, enabled: bool = True, rate: float = 0.3,
                  amount: float = 0.3, mix: float = 0.5,
                  unison: float = 0.3, detune: float = 0.3):
        """Configure Serum's Hyper/Dimension FX."""
        self.set_param("FX Hyper On", float(enabled))
        self.set_param("FX Hyper Rate", rate)
        self.set_param("FX Hyper Amount", amount)
        self.set_param("FX Hyper Mix", mix)
        self.set_param("FX Hyper Unison", unison)
        self.set_param("FX Hyper Det", detune)

    def disable_all_fx(self):
        """Disable all FX."""
        for fx in ["Dist", "Flang", "Chor", "Delay", "Rev", "Comp", "EQ",
                    "Filter", "Hyper"]:
            self.set_param(f"FX {fx} On", 0.0)

    # ── GLOBAL / VOICING ─────────────────────────────────────────────────

    def set_mono(self, enabled: bool = True):
        """Enable monophonic mode."""
        self.set_param("Mono", float(enabled))

    def set_voices(self, count: int):
        """Set max polyphony."""
        self.set_param("Voices", float(count))

    def set_portamento(self, time: float, mode: int = 2):
        """Set portamento/glide. mode: 0=off, 1=always, 2=legato."""
        self.set_param("Porta Time", time)
        self.set_param("Porta Mode", float(mode))

    def set_master_volume(self, volume: float):
        self.set_param("Master Vol", volume)

    # ── PRESET APPLICATION ───────────────────────────────────────────────

    def apply_preset(self, preset_name: str) -> bool:
        """Apply a DUBFORGE preset to Serum 2.

        Args:
            preset_name: Key from DUBFORGE_PRESETS dict
        """
        preset = DUBFORGE_PRESETS.get(preset_name)
        if not preset:
            _log.warning(f"Unknown preset: {preset_name}")
            available = list(DUBFORGE_PRESETS.keys())
            _log.info(f"Available: {available}")
            return False

        _log.info(f"Applying preset: {preset_name} — {preset['description']}")
        self.set_params(preset["params"])
        return True

    def apply_custom_preset(self, params: dict[str, float]):
        """Apply a custom parameter set."""
        self.set_params(params)

    # ── PRESET SAVE / LOAD ───────────────────────────────────────────────

    def save_preset_snapshot(self, name: str, output_dir: str = "output/serum_presets"):
        """Save current state as a DUBFORGE preset JSON."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        state = {}
        for our_name in SERUM_PARAMS:
            actual = self._resolve_name(our_name)
            if actual and actual in self._param_map:
                val = self.get_param(our_name)
                if val is not None:
                    state[our_name] = val

        preset_data = {
            "name": name,
            "description": f"DUBFORGE snapshot — {name}",
            "params": state,
        }
        path = Path(output_dir) / f"{name.lower().replace(' ', '_')}.json"
        path.write_text(json.dumps(preset_data, indent=2))
        _log.info(f"Saved preset snapshot: {path}")
        return str(path)

    def load_preset_snapshot(self, path: str) -> bool:
        """Load a DUBFORGE preset JSON and apply it."""
        p = Path(path)
        if not p.exists():
            _log.warning(f"Preset file not found: {path}")
            return False

        data = json.loads(p.read_text())
        if "params" in data:
            self.set_params(data["params"])
            _log.info(f"Loaded preset: {data.get('name', path)}")
            return True
        return False

    # ── PARAMETER DUMP ───────────────────────────────────────────────────

    def dump_all_params(self, output_file: str = ""):
        """Dump all discovered parameters for debugging."""
        return self.bridge.dump_device_params(
            self.track, self.device, output_file)

    def list_params_by_category(self, category: str) -> list[str]:
        """List DUBFORGE param names for a category."""
        return [name for name, info in SERUM_PARAMS.items()
                if info["category"] == category]

    def get_categories(self) -> list[str]:
        """Get all parameter categories."""
        return sorted(set(info["category"] for info in SERUM_PARAMS.values()))

    # ── WAVETABLE LOADING ────────────────────────────────────────────────

    def load_wavetable(self, osc: str, wav_path: str):
        """Load a wavetable file into Serum's Osc A or B.

        Note: This requires the wavetable to be placed in Serum's
        Tables folder. Use the file path approach:
          ~/Library/Audio/Presets/Xfer Records/Serum Presets/Tables/

        Then reference it by WT position after loading via Serum's UI
        or by setting up a custom MIDI CC mapping.
        """
        _log.info(f"Wavetable loading requires manual placement in Serum's Tables folder. "
                  f"Copy {wav_path} to Serum Presets/Tables/ and reload.")

    # ── INFO ─────────────────────────────────────────────────────────────

    @property
    def param_count(self) -> int:
        return len(self._param_map)

    @property
    def is_discovered(self) -> bool:
        return self._discovered

    def __repr__(self):
        return (f"Serum2Controller(track={self.track}, device={self.device}, "
                f"params={self.param_count}, discovered={self._discovered})")


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE
# ═══════════════════════════════════════════════════════════════════════════

def list_presets() -> list[str]:
    """List all available DUBFORGE Serum 2 presets."""
    return list(DUBFORGE_PRESETS.keys())


def get_preset_info(name: str) -> dict | None:
    """Get info about a preset."""
    return DUBFORGE_PRESETS.get(name)


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\nDUBFORGE — Serum 2 Controller")
    print("=" * 50)
    print(f"SERUM_PARAMS defined: {len(SERUM_PARAMS)}")
    print(f"DUBFORGE_PRESETS: {len(DUBFORGE_PRESETS)}")
    print(f"\nCategories: {sorted(set(v['category'] for v in SERUM_PARAMS.values()))}")
    print(f"\nPresets:")
    for name, preset in DUBFORGE_PRESETS.items():
        print(f"  {name}: {preset['description']}")
