#!/usr/bin/env python3
"""DUBFORGE — Single Stem Renderer (Isolated Process)

Renders ONE stem pipeline to WAV then exits, freeing all RAM.
Run each stem as a separate subprocess for maximum memory efficiency.

Dojo Approach Integration:
  - Separate passes: each stem rendered in isolation (Sound Design pass)
  - Focus on one element at a time — maximum quality per stem
  - VIP methodology: stems can be re-rendered independently

Subtronics Integration:
  - Per-stem gain staging matches Subtronics-calibrated bus_gains
  - Each stem gets full 16-bit dynamic range (no amplitude crushing)
  - Stems rendered at 48kHz for full frequency content

Usage:
    python _stem_render.py --stem drums
    python _stem_render.py --stem fx
    python _stem_render.py --stem lead
    python _stem_render.py --stem atmos
    python _stem_render.py --stem midbass
    python _stem_render.py --stem sub
    python _stem_render.py --stem vocals
"""

from __future__ import annotations

import argparse
import gc
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_apology_v3 import build_apology_v3_dna, kill_noise_sources, set_female_vocal_chops
from make_full_track import SAMPLE_RATE, write_wav_stereo

STEM_DIR = Path("output/tracks/THE_APOLOGY_THAT_NEVER_CAME_V4/stems")

VALID_STEMS = ("drums", "fx", "lead", "atmos", "midbass", "sub", "vocals", "legacy")


def compute_section_boundaries(dna):
    """Calculate sample-accurate section start/end positions."""
    bar_dur = 60.0 / dna.bpm * 4
    total_bars = sum(s.bars for s in dna.arrangement)
    total_samples = round(total_bars * bar_dur * SAMPLE_RATE)

    starts = []
    cum_bars = 0
    for sec in dna.arrangement:
        starts.append(round(cum_bars * bar_dur * SAMPLE_RATE))
        cum_bars += sec.bars
    starts.append(total_samples)
    return starts, total_samples


def stitch_pipeline_sections(pipeline_sections, section_starts, total_samples):
    """Stitch per-section pipeline output into continuous stereo arrays."""
    left = np.zeros(total_samples)
    right = np.zeros(total_samples)

    for i in range(len(pipeline_sections)):
        s = section_starts[i]
        e = section_starts[i + 1]
        sec_len = e - s
        data = pipeline_sections[i]
        b_left = data["left"]
        b_right = data["right"]
        b_len = min(len(b_left), sec_len)
        left[s:s + b_len] += b_left[:b_len]
        right[s:s + b_len] += b_right[:b_len]

    return left, right


def render_stem_drums(dna, section_starts, total_samples):
    """Render drum pipeline stem (kick, snare, hats)."""
    from engine.drum_pipeline import DrumPipeline

    print("  ═══ DRUM PIPELINE (6-stage) ═══")
    pipeline = DrumPipeline()
    sections = pipeline.render_full_drums(dna)
    print("  ═══ DRUM PIPELINE COMPLETE ═══")

    left, right = stitch_pipeline_sections(sections, section_starts, total_samples)

    # Free pipeline memory
    del pipeline, sections
    gc.collect()

    return left, right


def render_stem_fx(dna, section_starts, total_samples):
    """Render FX pipeline stem (risers, impacts, glitch)."""
    from engine.fx_pipeline import FxPipeline

    print("  ═══ FX PIPELINE (6-stage) ═══")
    pipeline = FxPipeline()
    sections = pipeline.render_full_fx(dna)
    print("  ═══ FX PIPELINE COMPLETE ═══")

    left, right = stitch_pipeline_sections(sections, section_starts, total_samples)

    del pipeline, sections
    gc.collect()

    return left, right


def render_stem_lead(dna, section_starts, total_samples):
    """Render lead pipeline stem (melodies, supersaws)."""
    from engine.lead_pipeline import LeadPipeline

    print("  ═══ LEAD PIPELINE (6-stage) ═══")
    pipeline = LeadPipeline()
    sections = pipeline.render_full_leads(dna)
    print("  ═══ LEAD PIPELINE COMPLETE ═══")

    left, right = stitch_pipeline_sections(sections, section_starts, total_samples)

    del pipeline, sections
    gc.collect()

    return left, right


def render_stem_atmos(dna, section_starts, total_samples):
    """Render atmosphere pipeline stem (pads, drones, noise beds)."""
    from engine.atmos_pipeline import AtmosPipeline

    print("  ═══ ATMOS PIPELINE (6-stage) ═══")
    pipeline = AtmosPipeline()
    sections = pipeline.render_full_atmos(dna)
    print("  ═══ ATMOS PIPELINE COMPLETE ═══")

    left, right = stitch_pipeline_sections(sections, section_starts, total_samples)

    del pipeline, sections
    gc.collect()

    return left, right


def render_stem_midbass(dna, section_starts, total_samples):
    """Render mid-bass pipeline stem (growl, neuro, FM bass)."""
    from engine.midbass_pipeline import MidBassPipeline

    print("  ═══ MID-BASS PIPELINE (6-stage) ═══")
    pipeline = MidBassPipeline()
    sections = pipeline.render_full_midbass(dna)
    print("  ═══ MID-BASS PIPELINE COMPLETE ═══")

    left, right = stitch_pipeline_sections(sections, section_starts, total_samples)

    del pipeline, sections
    gc.collect()

    return left, right


def render_stem_sub(dna, section_starts, total_samples):
    """Render sub-bass pipeline stem (sub sine, sub weight)."""
    from engine.sub_pipeline import SubBassPipeline

    print("  ═══ SUB-BASS PIPELINE (6-stage) ═══")
    pipeline = SubBassPipeline()
    sections = pipeline.render_full_sub(dna)
    print("  ═══ SUB-BASS PIPELINE COMPLETE ═══")

    left, right = stitch_pipeline_sections(sections, section_starts, total_samples)

    del pipeline, sections
    gc.collect()

    return left, right


def render_stem_vocals(dna, section_starts, total_samples):
    """Render vocal chops stem (female formant shifted chops)."""
    from make_full_track import render_vocal_chops, stereo_place

    print("  ═══ VOCAL CHOPS (legacy renderer) ═══")

    left = np.zeros(total_samples)
    right = np.zeros(total_samples)

    for i, sec in enumerate(dna.arrangement):
        if "chops" not in sec.elements:
            continue

        s = section_starts[i]
        e = section_starts[i + 1]
        sec_len = e - s

        chops_mono = render_vocal_chops(dna, sec.bars, sec.energy)
        mix_len = min(len(chops_mono), sec_len)

        # Stereo place with slight width
        ch_left, ch_right = stereo_place(chops_mono[:mix_len], width=0.15)
        left[s:s + mix_len] += ch_left
        right[s:s + mix_len] += ch_right

        print(f"    ✓ vocals [{sec.name}]: {mix_len / SAMPLE_RATE:.1f}s")

    print("  ═══ VOCAL CHOPS COMPLETE ═══")

    gc.collect()

    return left, right


def render_stem_legacy(dna, section_starts, total_samples):
    """Render legacy fallback elements that pipelines skip.

    Pipelines skip certain sections (e.g., lead pipeline skips verses,
    atmos pipeline skips verses/builds). This stem catches those gaps
    using the legacy renderers: pad, lead melody, drone, bass, noise bed.
    """
    from engine.atmos_pipeline import AtmosPipeline
    from engine.lead_pipeline import LeadPipeline
    from engine.midbass_pipeline import MidBassPipeline
    from make_full_track import (
        render_bass_drop,
        render_drone,
        render_lead_melody,
        render_noise_bed,
        render_pad,
        render_riser,
        sidechain_duck,
        stereo_place,
    )

    print("  ═══ LEGACY FALLBACK RENDERER ═══")
    print("  Filling gaps left by pipeline-skipped sections")

    # First, detect which sections each pipeline ACTUALLY renders
    # by doing a quick render and checking for silence
    lead_pipe = LeadPipeline()
    lead_secs = lead_pipe.render_full_leads(dna)
    atmos_pipe = AtmosPipeline()
    atmos_secs = atmos_pipe.render_full_atmos(dna)
    midbass_pipe = MidBassPipeline()
    midbass_secs = midbass_pipe.render_full_midbass(dna)

    left = np.zeros(total_samples)
    right = np.zeros(total_samples)

    element_gains = {
        "lead": 1.10, "pad": 0.35, "drone": 0.30,
        "bass": 0.90, "noise_bed": 0.20, "riser": 0.30,
        "chords": 0.40,
    }
    element_widths = {
        "lead": 0.18, "pad": 0.3, "drone": 0.3,
        "bass": 0.15, "noise_bed": 0.2, "riser": 0.2,
        "chords": 0.25,
    }

    for i, sec in enumerate(dna.arrangement):
        s = section_starts[i]
        e = section_starts[i + 1]
        sec_len = e - s
        elements = set(sec.elements)

        has_lead = (i < len(lead_secs) and
                    np.max(np.abs(lead_secs[i]["left"])) > 1e-6)
        has_atmos = (i < len(atmos_secs) and
                     np.max(np.abs(atmos_secs[i]["left"])) > 1e-6)
        has_midbass = (i < len(midbass_secs) and
                       np.max(np.abs(midbass_secs[i]["left"])) > 1e-6)

        renders = {}

        # Lead fallback
        if not has_lead and "lead" in elements:
            renders["lead"] = render_lead_melody(dna, sec.bars, sec.energy)

        # Atmos fallback (pad, drone, noise_bed)
        if not has_atmos:
            if any(e in elements for e in ("pad", "pad_fade", "plucks")):
                e_factor = 0.3 if "pad_fade" in elements else 1.0
                renders["pad"] = render_pad(dna, sec.bars, sec.energy * e_factor)
            if any(e in elements for e in ("drone", "texture")):
                renders["drone"] = render_drone(dna, sec.bars, sec.energy)
            if "noise_bed" in elements:
                renders["noise_bed"] = render_noise_bed(dna, sec.bars, sec.energy)

        # Bass fallback
        if not has_midbass:
            if any(e in elements for e in ("bass", "bass_alt", "extra_bass")):
                renders["bass"] = render_bass_drop(dna, sec.bars, sec.energy)

        # Chords (always legacy — no chord pipeline)
        if "chords" in elements and not has_atmos:
            renders["chords"] = render_pad(dna, sec.bars, sec.energy * 0.7)

        # Riser/swell (only if FX pipeline missed them)
        if "riser" in elements or "swell" in elements:
            renders["riser"] = render_riser(dna, sec.bars)

        if not renders:
            continue

        is_drop = "drop" in sec.name.lower()

        for name, audio in renders.items():
            audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)

            if is_drop and name not in ("riser",):
                audio = sidechain_duck(audio, dna.bpm, sec.bars,
                                       depth=0.85, release_ms=180.0)

            gain = element_gains.get(name, 0.6)
            mix_len = min(len(audio), sec_len)
            mono = audio[:mix_len] * gain
            width = element_widths.get(name, 0.0)
            l, r = stereo_place(mono, width)
            left[s:s + mix_len] += l
            right[s:s + mix_len] += r

            print(f"    ✓ legacy/{name} [{sec.name}]: {mix_len / SAMPLE_RATE:.1f}s "
                  f"(gain={gain:.2f})")

    print("  ═══ LEGACY FALLBACK COMPLETE ═══")

    del lead_pipe, lead_secs, atmos_pipe, atmos_secs, midbass_pipe, midbass_secs
    gc.collect()

    return left, right


RENDERERS = {
    "drums": render_stem_drums,
    "fx": render_stem_fx,
    "lead": render_stem_lead,
    "atmos": render_stem_atmos,
    "midbass": render_stem_midbass,
    "sub": render_stem_sub,
    "vocals": render_stem_vocals,
    "legacy": render_stem_legacy,
}


def main():
    parser = argparse.ArgumentParser(description="Render single stem to WAV")
    parser.add_argument("--stem", required=True, choices=VALID_STEMS,
                        help="Which stem to render")
    args = parser.parse_args()

    t0 = time.time()
    stem_name = args.stem

    print(f"\n{'=' * 60}")
    print(f"  DUBFORGE STEM RENDER — {stem_name.upper()}")
    print(f"  Isolated process — maximum RAM for this stem")
    print(f"{'=' * 60}")

    # Build DNA (deterministic — same every time)
    print("\n  Building DNA...")
    dna = build_apology_v3_dna()
    kill_noise_sources()
    set_female_vocal_chops()
    print(f"  DNA: {dna.total_bars} bars, {dna.key} {dna.scale} @ {dna.bpm} BPM")

    # Compute section boundaries
    section_starts, total_samples = compute_section_boundaries(dna)
    duration_s = total_samples / SAMPLE_RATE
    print(f"  Duration: {duration_s:.1f}s ({total_samples} samples)")

    # Render the stem
    print(f"\n  Rendering {stem_name}...")
    renderer = RENDERERS[stem_name]
    stem_l, stem_r = renderer(dna, section_starts, total_samples)

    # Clean signal
    for ch in [stem_l, stem_r]:
        ch[:] = np.nan_to_num(ch, nan=0.0, posinf=0.0, neginf=0.0)

    # Stats
    peak_l = np.max(np.abs(stem_l))
    peak_r = np.max(np.abs(stem_r))
    peak = max(peak_l, peak_r)
    rms = np.sqrt(np.mean(stem_l ** 2))
    print(f"\n  Stats — {stem_name}:")
    print(f"    Peak: {peak:.4f} ({20 * np.log10(peak + 1e-12):.1f} dBFS)")
    print(f"    RMS:  {rms:.4f} ({20 * np.log10(rms + 1e-12):.1f} dBFS)")

    # Write WAV
    STEM_DIR.mkdir(parents=True, exist_ok=True)
    out_path = STEM_DIR / f"{stem_name}_stem.wav"
    write_wav_stereo(str(out_path), stem_l, stem_r)

    elapsed = time.time() - t0
    print(f"\n  ✓ Written: {out_path}")
    print(f"  ✓ Duration: {duration_s:.1f}s | Time: {elapsed:.0f}s")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
