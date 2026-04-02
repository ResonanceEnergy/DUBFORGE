#!/usr/bin/env python3
"""Comprehensive import test for V9 pipeline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _v9_fast_init  # noqa

print("=== Testing stem render imports ===")
from make_apology import build_apology_dna, kill_noise_sources, set_female_vocal_chops
from make_full_track import SAMPLE_RATE, write_wav_stereo, stereo_place, sidechain_duck
from make_full_track import render_vocal_chops, render_bass_drop, render_drone
from make_full_track import render_lead_melody, render_noise_bed, render_pad, render_riser
print("  OK make_apology + make_full_track")

from engine.drum_pipeline import DrumPipeline
from engine.fx_pipeline import FxPipeline
from engine.lead_pipeline import LeadPipeline
from engine.atmos_pipeline import AtmosPipeline
from engine.midbass_pipeline import MidBassPipeline
from engine.sub_pipeline import SubBassPipeline
print("  OK All 6 pipeline modules")

from engine.vocal_tts import render_singing_vocal_stem_v8, SINGING_LYRICS
from engine.vocal_tts import generate_line, _compute_tts_pitch_for_target
from engine.vocal_tts import _detect_pitch_hz, _hz_to_midi, _rubberband_pitch_and_time
print("  OK vocal_tts")

from engine.fx_rack import FXRack
print("  OK fx_rack")

print()
print("=== Testing mix imports ===")
from engine.dsp_core import dc_block
from engine.mix_bus import MixBusConfig, process_mix_bus
print("  OK mix_bus")

print()
print("=== Testing master imports ===")
from engine.mastering_chain import db_to_linear, dubstep_master_settings, estimate_lufs, master
from engine.qa_validator import validate_render
print("  OK mastering_chain + qa_validator")

from engine.artwork_generator import generate_full_artwork
print("  OK artwork_generator")

print()
print("=== Build DNA test ===")
dna = build_apology_dna()
print(f"  title: {dna.title}")
print(f"  bpm: {dna.bpm}")
print(f"  key: {dna.key}")
print(f"  root_freq: {dna.root_freq}")
print(f"  sections: {len(dna.arrangement)}")
for sec in dna.arrangement:
    print(f"    {sec.name}: {sec.bars} bars, energy={sec.energy:.2f}, elements={sec.elements}")

print()
print("ALL IMPORTS PASS")
