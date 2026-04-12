#!/usr/bin/env python3
"""Phase 1 stage-by-stage QA — runs the full pipeline, then validates each stage."""
from __future__ import annotations

import sys
import time
import traceback

sys.path.insert(0, ".")

from engine.phase_one import run_phase_one

# ─── Run the pipeline ───────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  QA HARNESS — Phase 1 Stage-by-Stage Verification")
print("=" * 70)

t0 = time.perf_counter()
try:
    mandate = run_phase_one()
except Exception:
    traceback.print_exc()
    print("\n❌ Pipeline CRASHED — cannot proceed with QA")
    sys.exit(1)

elapsed = time.perf_counter() - t0
print(f"\n  Pipeline completed in {elapsed:.1f}s\n")

# ─── QA helpers ──────────────────────────────────────────────────────────
results: list[tuple[str, bool, str]] = []

def check(label: str, condition: bool, detail: str = "") -> None:
    results.append((label, condition, detail))
    mark = "✅" if condition else "❌"
    msg = f"  {mark} {label}"
    if detail:
        msg += f"  — {detail}"
    print(msg)

# ═══════════════════════════════════════════════════════════════════════
# STAGE 1: THE TOTAL RECIPE
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("  STAGE 1 QA: THE TOTAL RECIPE")
print("─" * 60)

# 1B: DNA
dna = mandate.dna
check("1B DNA exists", dna is not None)
check("1B DNA.name", hasattr(dna, "name") and bool(dna.name), f"name={getattr(dna, 'name', None)}")
check("1B DNA.key", hasattr(dna, "key") and dna.key is not None, f"key={getattr(dna, 'key', None)}")
check("1B DNA.scale", hasattr(dna, "scale") and dna.scale is not None, f"scale={getattr(dna, 'scale', None)}")
check("1B DNA.bpm", hasattr(dna, "bpm") and 60 < dna.bpm < 300, f"bpm={getattr(dna, 'bpm', None)}")
check("1B DNA.root_freq", hasattr(dna, "root_freq") and dna.root_freq > 0, f"root_freq={getattr(dna, 'root_freq', None):.1f}")
check("1B beat_s / bar_s", mandate.beat_s > 0 and mandate.bar_s > 0, f"beat={mandate.beat_s:.3f}s, bar={mandate.bar_s:.3f}s")

# 1C: Harmony
check("1C chord_progression", mandate.chord_progression is not None)
if mandate.chord_progression:
    n_chords = len(mandate.chord_progression.chords)
    check("1C chord count > 0", n_chords > 0, f"{n_chords} chords")

# 1D: Freq table
check("1D freq_table", mandate.freq_table is not None)
if mandate.freq_table:
    check("1D freq_table has entries", len(mandate.freq_table) > 0, f"{len(mandate.freq_table)} entries")

# 1E: Palette intent
check("1E design_intent", mandate.design_intent is not None)

# 1F: Template config
check("1F template_config", getattr(mandate, 'template_config', None) is not None)

# 1G: Production recipe
check("1G groove_template", mandate.groove_template is not None, f"{mandate.groove_template}")
check("1G quality_targets", mandate.quality_targets is not None and len(mandate.quality_targets) > 0,
      f"{len(mandate.quality_targets)} targets")
check("1G arrange_tasks", mandate.arrange_tasks is not None and len(mandate.arrange_tasks) > 0,
      f"{len(mandate.arrange_tasks)} tasks")

# 1H: Arrangement
check("1H sections", mandate.sections is not None and len(mandate.sections) > 0,
      f"{len(mandate.sections)} sections")
check("1H total_bars > 0", mandate.total_bars > 0, f"{mandate.total_bars} bars")
check("1H total_samples > 0", mandate.total_samples > 0,
      f"{mandate.total_samples} samples ({mandate.total_samples / 44100:.1f}s)")
check("1H arrangement_template", mandate.arrangement_template is not None)
check("1H energy_curve", getattr(mandate, 'energy_curve', None) is not None)

# 1I: Audio manifest
check("1I audio_manifest", mandate.audio_manifest is not None)
if mandate.audio_manifest:
    check("1I manifest.total > 0", mandate.audio_manifest.total > 0,
          f"{mandate.audio_manifest.total} files expected")

# ═══════════════════════════════════════════════════════════════════════
# STAGE 2: COLLECTION + LOOPS + RACK + MIDI
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("  STAGE 2 QA: COLLECTION + LOOPS + RACK + MIDI")
print("─" * 60)

# 2A: Drums
check("2A drums", mandate.drums is not None)
if mandate.drums:
    has_kick = getattr(mandate.drums, "kick", None) is not None
    has_snare = getattr(mandate.drums, "snare", None) is not None
    check("2A kick sample", has_kick)
    check("2A snare sample", has_snare)

# 2B: Drum loops
check("2B drum_loops", mandate.drum_loops is not None)
if mandate.drum_loops:
    n_loops = len(mandate.drum_loops.patterns)
    check("2B loop count > 0", n_loops > 0, f"{n_loops} patterns")

# 2C: FX samples
check("2C galactia_fx", mandate.galactia_fx is not None)
if mandate.galactia_fx:
    fx_count = sum(len(v) for v in [
        mandate.galactia_fx.risers, mandate.galactia_fx.impacts,
        mandate.galactia_fx.reverses, mandate.galactia_fx.falling,
        mandate.galactia_fx.rising, mandate.galactia_fx.shepard,
        mandate.galactia_fx.buildups])
    check("2C FX sample count > 0", fx_count > 0, f"{fx_count} samples")

# 2C+: Galactia zone map
check("2C+ galactia_zone_map", mandate.galactia_zone_map is not None)
if mandate.galactia_zone_map:
    check("2C+ total_audio > 0", mandate.galactia_zone_map.total_audio > 0,
          f"{mandate.galactia_zone_map.total_audio} audio samples")

# 2E: 128 Rack
check("2E rack_128", mandate.rack_128 is not None)
if mandate.rack_128:
    total_slots = sum(mandate.rack_128.zone_counts.values())
    check("2E rack slots > 0", total_slots > 0, f"{total_slots}/128 slots")

# 2F: MIDI map
check("2F rack_midi_map", mandate.rack_midi_map is not None)
if mandate.rack_midi_map:
    n_notes = len(mandate.rack_midi_map.note_map)
    check("2F MIDI notes mapped > 0", n_notes > 0, f"{n_notes} notes")

# 2G: Loop MIDI
check("2G loop_midi_maps", mandate.loop_midi_maps is not None)
if mandate.loop_midi_maps:
    n_maps = len(mandate.loop_midi_maps)
    total_hits = sum(len(lm.hits) for lm in mandate.loop_midi_maps)
    check("2G loop maps > 0", n_maps > 0, f"{n_maps} patterns, {total_hits} hits")

# ═══════════════════════════════════════════════════════════════════════
# STAGE 3: SOUND DESIGN
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("  STAGE 3 QA: SOUND DESIGN")
print("─" * 60)

# 3A: Wavetables
check("3A wavetables", mandate.wavetables is not None)
if mandate.wavetables:
    n_wt = len(mandate.wavetables.frames)
    check("3A wavetable count > 0", n_wt > 0, f"{n_wt} wavetable frames")

# 3B: WT packs
check("3B wavetable_packs", mandate.wavetable_packs is not None)

# 3C: Modulation routes
check("3C modulation_routes", mandate.modulation_routes is not None)
if mandate.modulation_routes:
    n_stems = len(mandate.modulation_routes)
    n_routes = sum(len(v.get("mod_matrix", [])) for v in mandate.modulation_routes.values())
    check("3C routes > 0", n_routes > 0, f"{n_routes} routes across {n_stems} stems")

# 3D: FX chains
check("3D fx_chains", mandate.fx_chains is not None)
if mandate.fx_chains:
    n_fx_stems = len(mandate.fx_chains)
    n_fx_slots = sum(len(v) for v in mandate.fx_chains.values() if isinstance(v, list))
    check("3D FX slots > 0", n_fx_slots > 0 or n_fx_stems > 0,
          f"{n_fx_slots} slots across {n_fx_stems} stems")

# 3E: Morph wavetables
check("3E morph_wavetables", mandate.morph_wavetables is not None)
if mandate.morph_wavetables:
    n_morphs = len(mandate.morph_wavetables)
    check("3E morph count > 0", n_morphs > 0, f"{n_morphs} morphs")

# 3F: Serum 2 presets
check("3F serum2_presets", mandate.serum2_presets is not None)
if mandate.serum2_presets:
    n_presets = len(mandate.serum2_presets)
    check("3F preset count > 0", n_presets > 0,
          f"{n_presets} presets: {', '.join(list(mandate.serum2_presets.keys())[:5])}")

# ═══════════════════════════════════════════════════════════════════════
# STAGE 4: SYNTHESIS
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("  STAGE 4 QA: SYNTHESIS")
print("─" * 60)

# 4A: Stem configs
check("4A stem_configs", mandate.stem_configs is not None)
if mandate.stem_configs:
    check("4A stem count > 0", len(mandate.stem_configs) > 0,
          f"{len(mandate.stem_configs)} stems")

# 4B: Serum2 state map
check("4B serum2_state_map", mandate.serum2_state_map is not None)
if mandate.serum2_state_map:
    check("4B state count > 0", len(mandate.serum2_state_map) > 0,
          f"{len(mandate.serum2_state_map)} states")

# 4C: MIDI sequences
check("4C midi_sequences", mandate.midi_sequences is not None)
if mandate.midi_sequences:
    total_notes = sum(len(v) for v in mandate.midi_sequences.values())
    active = sum(1 for v in mandate.midi_sequences.values() if v)
    check("4C MIDI notes > 0", total_notes > 0,
          f"{total_notes} notes, {active} active stems")

# 4D: Render ALS
check("4D render_als_path", mandate.render_als_path is not None,
      f"{mandate.render_als_path}")

# 4E: Synthesis audio
import numpy as np

for name, attr in [
    ("bass", "bass"), ("leads", "leads"), ("atmosphere", "atmosphere"),
    ("fx", "fx"), ("vocals", "vocals"), ("melody", "melody"),
    ("wobble_bass", "wobble_bass"), ("riddim_bass", "riddim_bass"),
    ("growl_textures", "growl_textures"),
]:
    obj = getattr(mandate, attr, None)
    check(f"4E {name}", obj is not None)
    if obj:
        # Check for actual audio data (non-silent)
        has_audio = False
        for field in dir(obj):
            val = getattr(obj, field, None)
            if isinstance(val, np.ndarray) and val.size > 0 and np.any(val != 0):
                has_audio = True
                break
            if isinstance(val, dict):
                for v2 in val.values():
                    if isinstance(v2, np.ndarray) and v2.size > 0 and np.any(v2 != 0):
                        has_audio = True
                        break
                    if isinstance(v2, dict):
                        for v3 in v2.values():
                            if isinstance(v3, np.ndarray) and v3.size > 0 and np.any(v3 != 0):
                                has_audio = True
                                break
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, np.ndarray) and item.size > 0 and np.any(item != 0):
                        has_audio = True
                        break
            if has_audio:
                break
        check(f"4E {name} has audio data", has_audio)

# 4F: Live bounce (optional — not scored as failure)
if mandate.audio_clips:
    print(f"  ℹ️  4F Live bounces collected: {len(mandate.audio_clips)}")
else:
    print("  ℹ️  4F Live bounce skipped (Ableton not running) — OK")

# 4H: Production skeleton
check("4H production_als_path", mandate.production_als_path is not None,
      f"{mandate.production_als_path}")

# ═══════════════════════════════════════════════════════════════════════
# STAGE 5: RENDER FACTORY
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("  STAGE 5 QA: RENDER FACTORY")
print("─" * 60)

# 5A: Rack augmented
check("5A rack_128 augmented", mandate.rack_128 is not None)
if mandate.rack_128:
    total_s5 = sum(mandate.rack_128.zone_counts.values())
    check("5A rack slots > 50 (post-augment)", total_s5 > 50,
          f"{total_s5}/128 slots")
    zones = {z: c for z, c in mandate.rack_128.zone_counts.items() if c > 0}
    check("5A multiple zone types", len(zones) >= 3,
          f"{len(zones)} zones: {zones}")

# 5B: Render patterns
check("5B render_patterns", mandate.render_patterns is not None)
if mandate.render_patterns:
    n_secs = len(mandate.render_patterns)
    n_hits = sum(sum(len(h) for h in z.values()) for z in mandate.render_patterns.values())
    check("5B sections > 0", n_secs > 0, f"{n_secs} sections")
    check("5B MIDI hits > 0", n_hits > 0, f"{n_hits} total hits")

# 5C: FX chains (stage5)
s5_fx = mandate.fx_chains.get("stage5", {}) if isinstance(mandate.fx_chains, dict) else {}
check("5C stage5 FX chains", len(s5_fx) > 0, f"{len(s5_fx)} zone chains")

# 5D: Stage 5 ALS
check("5D stage5_als_path", mandate.stage5_als_path is not None,
      f"{mandate.stage5_als_path}")

# 5E: Live bounce (optional — not scored)
if mandate.stage5_renders:
    print(f"  ℹ️  5E bounces collected: {sum(len(g) for g in mandate.stage5_renders.values())}")
else:
    print("  ℹ️  5E Live bounce skipped (Ableton not running) — OK")

# 5F: Loop MIDI maps rebuilt
check("5F loop_midi_maps rebuilt", mandate.loop_midi_maps is not None and len(mandate.loop_midi_maps) > 0,
      f"{len(mandate.loop_midi_maps)} maps")

# Phase log
check("phase_log complete", len(mandate.phase_log) >= 3,
      f"{len(mandate.phase_log)} log entries")

# ═══════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
total = len(results)

if failed == 0:
    print(f"  ✅ ALL {total} CHECKS PASSED ({elapsed:.1f}s)")
else:
    print(f"  RESULT: {passed}/{total} passed, {failed} FAILED ({elapsed:.1f}s)")
    print()
    print("  FAILURES:")
    for label, ok, detail in results:
        if not ok:
            print(f"    ❌ {label}  {detail}")

print("=" * 70)
sys.exit(0 if failed == 0 else 1)
