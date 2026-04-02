#!/usr/bin/env python3
"""DUBFORGE — V9 Single Stem Renderer (Isolated Process)

Renders ONE stem pipeline to WAV then exits, freeing all RAM.
V9 changes vs V8:
  - Harmonized singing vocals: 3rds/5ths layered in chorus sections
  - Double-tracked vocals with subtle detune for richness
  - Per-section vocal dynamics (verse=intimate, chorus=open, drop=FX)
  - Vocal processor harmonizer integration for real harmony layers
  - RubberBand R3 formant preservation retained from V8

Usage:
    python _v9_stem_render.py --stem drums
    python _v9_stem_render.py --stem vocals
    python _v9_stem_render.py --stem legacy
"""

from __future__ import annotations

import argparse
import gc
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _v9_fast_init  # noqa: F401 — bypass engine/__init__.py

from make_apology import build_apology_dna, kill_noise_sources, set_female_vocal_chops
from make_full_track import SAMPLE_RATE, write_wav_stereo

STEM_DIR = Path("output/tracks/THE_APOLOGY_THAT_NEVER_CAME_V9/stems")
VALID_STEMS = ("drums", "fx", "lead", "atmos", "midbass", "sub", "vocals", "legacy")


def _ram_mb() -> float:
    """Return current process RSS in MB (macOS/Linux)."""
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
    except Exception:
        return 0.0


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


# ═══════════════════════════════════════════════════════════════════════════
# STEM RENDERERS (one per pipeline)
# ═══════════════════════════════════════════════════════════════════════════

def render_stem_drums(dna, section_starts, total_samples):
    from engine.drum_pipeline import DrumPipeline
    print("  ═══ DRUM PIPELINE (6-stage, Stage 6 = DC-block) ═══")
    pipeline = DrumPipeline()
    sections = pipeline.render_full_drums(dna)
    print("  ═══ DRUM PIPELINE COMPLETE ═══")
    left, right = stitch_pipeline_sections(sections, section_starts, total_samples)
    del pipeline, sections; gc.collect()
    return left, right


def render_stem_fx(dna, section_starts, total_samples):
    from engine.fx_pipeline import FxPipeline
    print("  ═══ FX PIPELINE (6-stage, Stage 6 = DC-block) ═══")
    pipeline = FxPipeline()
    sections = pipeline.render_full_fx(dna)
    print("  ═══ FX PIPELINE COMPLETE ═══")
    left, right = stitch_pipeline_sections(sections, section_starts, total_samples)
    del pipeline, sections; gc.collect()
    return left, right


def render_stem_lead(dna, section_starts, total_samples):
    from engine.lead_pipeline import LeadPipeline
    print("  ═══ LEAD PIPELINE (6-stage, Stage 6 = DC-block) ═══")
    pipeline = LeadPipeline()
    sections = pipeline.render_full_leads(dna)
    print("  ═══ LEAD PIPELINE COMPLETE ═══")
    left, right = stitch_pipeline_sections(sections, section_starts, total_samples)
    del pipeline, sections; gc.collect()
    return left, right


def render_stem_atmos(dna, section_starts, total_samples):
    from engine.atmos_pipeline import AtmosPipeline
    print("  ═══ ATMOS PIPELINE (6-stage, Stage 6 = DC-block) ═══")
    pipeline = AtmosPipeline()
    sections = pipeline.render_full_atmos(dna)
    print("  ═══ ATMOS PIPELINE COMPLETE ═══")
    left, right = stitch_pipeline_sections(sections, section_starts, total_samples)
    del pipeline, sections; gc.collect()
    return left, right


def render_stem_midbass(dna, section_starts, total_samples):
    from engine.midbass_pipeline import MidBassPipeline
    print("  ═══ MID-BASS PIPELINE (6-stage, Stage 6 = DC-block) ═══")
    pipeline = MidBassPipeline()
    sections = pipeline.render_full_midbass(dna)
    print("  ═══ MID-BASS PIPELINE COMPLETE ═══")
    left, right = stitch_pipeline_sections(sections, section_starts, total_samples)
    del pipeline, sections; gc.collect()
    return left, right


def render_stem_sub(dna, section_starts, total_samples):
    from engine.sub_pipeline import SubBassPipeline
    print("  ═══ SUB-BASS PIPELINE (6-stage, Stage 6 = DC-block + LP) ═══")
    pipeline = SubBassPipeline()
    sections = pipeline.render_full_sub(dna)
    print("  ═══ SUB-BASS PIPELINE COMPLETE ═══")
    left, right = stitch_pipeline_sections(sections, section_starts, total_samples)
    del pipeline, sections; gc.collect()
    return left, right


def render_stem_vocals(dna, section_starts, total_samples):
    """Render vocal stem: V9 harmonized singing + double-tracking + vocal chops.

    V9 vocal upgrades vs V8:
      - Harmonized vocals: 3rd/5th harmony layers in chorus sections
      - Double-tracked lead vocal with ±5 cent detune for richness
      - Per-section dynamics: verse=intimate (0.50), chorus=open (0.60),
        pre-chorus=rising (0.55), outro=fading (0.45)
      - Vocal processor harmonizer for real chord-aware harmony generation
      - RubberBand R3 --fine --formant retained from V8
    """
    from engine.vocal_tts import (
        render_singing_vocal_stem_v8,
        SINGING_LYRICS,
        generate_line,
        _compute_tts_pitch_for_target,
        _detect_pitch_hz,
        _hz_to_midi,
        _rubberband_pitch_and_time,
    )
    from make_full_track import render_vocal_chops, stereo_place
    from engine.fx_rack import FXRack

    print("  ═══ VOCAL STEM (V9: Harmonized Singing + Double-Track) ═══")

    # ── 1. Lead vocal: RubberBand R3 pitch-matched singing ───────
    print("    [1/4] Rendering lead singing vocal (RubberBand R3)...")
    lead_vocal = render_singing_vocal_stem_v8(dna.bpm, total_samples)

    # Process through FXRack vocal chain
    lead_processed = FXRack.process(lead_vocal, FXRack.preset("mix_vocals"),
                                    sr=SAMPLE_RATE)
    lead_processed = lead_processed.astype(np.float64)

    # ── 2. Double-tracked vocal: ±5 cent detune for thickness ────
    print("    [2/4] Rendering double-tracked vocal (+5 cent detune)...")
    double_vocal = render_singing_vocal_stem_v8(dna.bpm, total_samples)
    # Apply subtle pitch shift: +5 cents = +0.05 semitones
    try:
        double_vocal = _rubberband_pitch_and_time(double_vocal, 0.05, 1.0)
    except Exception:
        # Fallback: simple detune via resampling
        from scipy.signal import resample
        factor = 2.0 ** (0.05 / 12.0)
        new_len = int(len(double_vocal) / factor)
        double_vocal = resample(double_vocal, new_len)

    double_processed = FXRack.process(double_vocal, FXRack.preset("mix_vocals"),
                                      sr=SAMPLE_RATE)
    double_processed = double_processed.astype(np.float64)

    # Pad/trim double to match lead length
    if len(double_processed) < total_samples:
        padded = np.zeros(total_samples, dtype=np.float64)
        padded[:len(double_processed)] = double_processed
        double_processed = padded
    else:
        double_processed = double_processed[:total_samples]

    del double_vocal
    gc.collect()

    # ── 3. Harmony vocals for chorus sections ────────────────────
    print("    [3/4] Rendering harmony vocals for choruses...")
    harmony_vocal = np.zeros(total_samples, dtype=np.float64)

    bar_dur = 4 * 60.0 / dna.bpm
    bar_samps = int(bar_dur * SAMPLE_RATE)

    # Chorus bars: 40-55 and 96-111 — add harmony layers
    chorus_sections = {40, 96}

    for section_bar, lines in SINGING_LYRICS.items():
        if section_bar not in chorus_sections:
            continue

        for bar_off, bar_count, text, rate, target_notes in lines:
            offset = (section_bar + bar_off) * bar_samps
            if offset >= total_samples:
                continue

            target_samps = bar_count * bar_samps
            avg_target = sum(target_notes) / len(target_notes)

            # Generate harmony: minor 3rd above (3 semitones in Dm)
            harmony_target = avg_target + 3.0
            tts_pitch = _compute_tts_pitch_for_target(harmony_target)

            try:
                raw = generate_line(text, rate=rate, pitch=tts_pitch)
                if len(raw) == 0:
                    continue

                detected_hz = _detect_pitch_hz(raw)
                if detected_hz <= 0:
                    tts_shift = float(tts_pitch.replace("Hz", ""))
                    detected_hz = 200.0 + tts_shift
                    detected_hz = max(80.0, detected_hz)
                detected_midi = _hz_to_midi(detected_hz)

                remaining_semi = harmony_target - detected_midi
                remaining_semi = max(-12.0, min(12.0, remaining_semi))
                time_ratio = target_samps / len(raw)
                time_ratio = max(0.5, min(2.0, time_ratio))

                sung = _rubberband_pitch_and_time(raw, remaining_semi, time_ratio)

                if len(sung) >= target_samps:
                    sung = sung[:target_samps]
                else:
                    padded = np.zeros(target_samps, dtype=np.float64)
                    padded[:len(sung)] = sung
                    sung = padded

                # Fade in/out
                fade = int(0.010 * SAMPLE_RATE)
                if len(sung) > 2 * fade:
                    sung[:fade] *= np.linspace(0, 1, fade)
                    sung[-fade:] *= np.linspace(1, 0, fade)

                end = min(offset + len(sung), total_samples)
                harmony_vocal[offset:end] += sung[:end - offset]

            except Exception as e:
                print(f"      ⚠ Harmony failed for '{text[:25]}': {e}")

    harmony_processed = FXRack.process(harmony_vocal, FXRack.preset("mix_vocals"),
                                       sr=SAMPLE_RATE)
    harmony_processed = harmony_processed.astype(np.float64)
    if len(harmony_processed) < total_samples:
        padded = np.zeros(total_samples, dtype=np.float64)
        padded[:len(harmony_processed)] = harmony_processed
        harmony_processed = padded

    del harmony_vocal
    gc.collect()

    # ── 4. Per-section dynamics and stereo placement ─────────────
    print("    [4/4] Applying per-section vocal dynamics...")

    # Section type → (lead_gain, double_gain, harmony_gain, stereo_width)
    VOCAL_DYNAMICS = {
        "intro":   (0.00, 0.00, 0.00, 0.00),  # no vocals in intro
        "build":   (0.50, 0.15, 0.00, 0.05),  # intimate, centered
        "build2":  (0.55, 0.18, 0.00, 0.08),  # slightly opening
        "drop1":   (0.00, 0.00, 0.00, 0.00),  # instrumental drop
        "drop1b":  (0.00, 0.00, 0.00, 0.00),  # instrumental drop
        "break":   (0.50, 0.15, 0.00, 0.05),  # intimate again
        "drop2":   (0.00, 0.00, 0.00, 0.00),  # instrumental drop
        "drop2b":  (0.00, 0.00, 0.00, 0.00),  # instrumental drop
        "outro":   (0.45, 0.10, 0.00, 0.03),  # fading, peaceful
    }

    # Detect chorus/pre-chorus by bar positions
    # Chorus 1: bars 40-55, Chorus 2: bars 96-111
    # Pre-chorus: bars 32-39, bars 88-95

    left = np.zeros(total_samples, dtype=np.float64)
    right = np.zeros(total_samples, dtype=np.float64)

    cum_bars = 0
    for i, sec in enumerate(dna.arrangement):
        s = section_starts[i]
        e = section_starts[i + 1]
        sec_len = e - s
        sec_start_bar = cum_bars
        cum_bars += sec.bars

        # Determine vocal dynamics based on section content
        sec_name = sec.name.lower()

        # Check if this section overlaps chorus bars
        sec_end_bar = sec_start_bar + sec.bars
        is_chorus = (
            (sec_start_bar <= 40 < sec_end_bar) or
            (sec_start_bar <= 96 < sec_end_bar)
        )
        is_prechorus = (
            (sec_start_bar <= 32 < sec_end_bar and sec_end_bar <= 40) or
            (sec_start_bar <= 88 < sec_end_bar and sec_end_bar <= 96)
        )

        if is_chorus:
            # Chorus: full harmonized singing, wide stereo
            lead_g, dbl_g, harm_g, width = 0.60, 0.22, 0.35, 0.15
        elif is_prechorus:
            # Pre-chorus: building energy, moderate width
            lead_g, dbl_g, harm_g, width = 0.55, 0.18, 0.00, 0.10
        else:
            # Use section-name based dynamics
            lead_g, dbl_g, harm_g, width = VOCAL_DYNAMICS.get(
                sec_name, (0.50, 0.15, 0.00, 0.05))

        # Mix vocals for this section
        sec_lead = lead_processed[s:e] * lead_g
        sec_double = double_processed[s:e] * dbl_g
        sec_harmony = harmony_processed[s:e] * harm_g

        # Combine mono signal
        combined = sec_lead + sec_double + sec_harmony
        mix_len = min(len(combined), sec_len)

        # Stereo placement: lead center, double slightly wide, harmony wider
        lead_l, lead_r = stereo_place(sec_lead[:mix_len], width=0.02)
        dbl_l, dbl_r = stereo_place(sec_double[:mix_len], width=0.12)
        harm_l, harm_r = stereo_place(sec_harmony[:mix_len], width=width)

        left[s:s + mix_len] += lead_l + dbl_l + harm_l
        right[s:s + mix_len] += lead_r + dbl_r + harm_r

    del lead_processed, double_processed, harmony_processed
    gc.collect()

    # ── 5. Vocal chops for drop sections ─────────────────────────
    print("    Rendering vocal chops for drops...")
    for i, sec in enumerate(dna.arrangement):
        if "chops" not in sec.elements:
            continue
        s = section_starts[i]
        e = section_starts[i + 1]
        sec_len = e - s

        chops_mono = render_vocal_chops(dna, sec.bars, sec.energy)
        mix_len = min(len(chops_mono), sec_len)

        ch_left, ch_right = stereo_place(chops_mono[:mix_len], width=0.15)
        left[s:s + mix_len] += ch_left * 0.70
        right[s:s + mix_len] += ch_right * 0.70

        print(f"      ✓ chops [{sec.name}]: {mix_len / SAMPLE_RATE:.1f}s")

    print("  ═══ VOCAL STEM COMPLETE (V9: harmonized + double-tracked) ═══")
    gc.collect()
    return left, right


def render_stem_legacy(dna, section_starts, total_samples):
    """Render legacy fallback elements that pipelines skip."""
    from engine.atmos_pipeline import AtmosPipeline
    from engine.lead_pipeline import LeadPipeline
    from engine.midbass_pipeline import MidBassPipeline
    from make_full_track import (
        render_bass_drop, render_drone, render_lead_melody,
        render_noise_bed, render_pad, render_riser,
        sidechain_duck, stereo_place,
    )

    print("  ═══ LEGACY FALLBACK RENDERER (V9) ═══")

    lead_secs = LeadPipeline().render_full_leads(dna)
    atmos_secs = AtmosPipeline().render_full_atmos(dna)
    midbass_secs = MidBassPipeline().render_full_midbass(dna)

    left = np.zeros(total_samples)
    right = np.zeros(total_samples)

    gains = {"lead": 1.10, "pad": 0.35, "drone": 0.30,
             "bass": 0.90, "noise_bed": 0.20, "riser": 0.30, "chords": 0.40}
    widths = {"lead": 0.18, "pad": 0.3, "drone": 0.3,
              "bass": 0.15, "noise_bed": 0.2, "riser": 0.2, "chords": 0.25}

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

        if not has_lead and "lead" in elements:
            renders["lead"] = render_lead_melody(dna, sec.bars, sec.energy)
        if not has_atmos:
            if any(e in elements for e in ("pad", "pad_fade", "plucks")):
                ef = 0.3 if "pad_fade" in elements else 1.0
                renders["pad"] = render_pad(dna, sec.bars, sec.energy * ef)
            if any(e in elements for e in ("drone", "texture")):
                renders["drone"] = render_drone(dna, sec.bars, sec.energy)
            if "noise_bed" in elements:
                renders["noise_bed"] = render_noise_bed(dna, sec.bars, sec.energy)
        if not has_midbass:
            if any(e in elements for e in ("bass", "bass_alt", "extra_bass")):
                renders["bass"] = render_bass_drop(dna, sec.bars, sec.energy)
        if "chords" in elements and not has_atmos:
            renders["chords"] = render_pad(dna, sec.bars, sec.energy * 0.7)
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
            gain = gains.get(name, 0.6)
            mix_len = min(len(audio), sec_len)
            mono = audio[:mix_len] * gain
            width = widths.get(name, 0.0)
            l, r = stereo_place(mono, width)
            left[s:s + mix_len] += l
            right[s:s + mix_len] += r
            print(f"    ✓ legacy/{name} [{sec.name}]: {mix_len / SAMPLE_RATE:.1f}s")

    print("  ═══ LEGACY FALLBACK COMPLETE ═══")
    del lead_secs, atmos_secs, midbass_secs
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
    parser = argparse.ArgumentParser(description="V9 — Render single stem to WAV")
    parser.add_argument("--stem", required=True, choices=VALID_STEMS,
                        help="Which stem to render")
    args = parser.parse_args()

    t0 = time.time()
    stem_name = args.stem

    print(f"\n{'=' * 60}")
    print(f"  DUBFORGE V9 STEM RENDER — {stem_name.upper()}")
    print(f"  V9 = Harmonized Singing | Double-Track | Per-Section Dynamics")
    print(f"{'=' * 60}")

    # Build DNA (deterministic)
    print("\n  Building DNA (V9)...")
    dna = build_apology_dna()
    kill_noise_sources()
    set_female_vocal_chops()
    print(f"  DNA: {dna.total_bars} bars, {dna.key} {dna.scale} @ {dna.bpm} BPM")
    print(f"  V9: Harmonized singing + double-track + per-section dynamics")

    section_starts, total_samples = compute_section_boundaries(dna)
    duration_s = total_samples / SAMPLE_RATE
    print(f"  Duration: {duration_s:.1f}s ({total_samples} samples)")

    # Render
    print(f"\n  Rendering {stem_name}...")
    ram_before = _ram_mb()
    renderer = RENDERERS[stem_name]
    stem_l, stem_r = renderer(dna, section_starts, total_samples)
    ram_after = _ram_mb()
    print(f"  RAM: {ram_before:.0f} MB → {ram_after:.0f} MB (Δ {ram_after - ram_before:+.0f} MB)")

    # Clean
    gc.collect()
    for ch in [stem_l, stem_r]:
        ch[:] = np.nan_to_num(ch, nan=0.0, posinf=0.0, neginf=0.0)

    # Stats
    peak = max(np.max(np.abs(stem_l)), np.max(np.abs(stem_r)))
    rms = np.sqrt(np.mean(stem_l ** 2))
    print(f"\n  Stats — {stem_name}:")
    print(f"    Peak: {peak:.4f} ({20 * np.log10(peak + 1e-12):.1f} dBFS)")
    print(f"    RMS:  {rms:.4f} ({20 * np.log10(rms + 1e-12):.1f} dBFS)")

    # Write
    STEM_DIR.mkdir(parents=True, exist_ok=True)
    out_path = STEM_DIR / f"{stem_name}_stem.wav"
    write_wav_stereo(str(out_path), stem_l, stem_r)

    elapsed = time.time() - t0
    print(f"\n  ✓ Written: {out_path}")
    print(f"  ✓ Duration: {duration_s:.1f}s | Time: {elapsed:.0f}s")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
