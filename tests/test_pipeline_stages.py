"""Stage-by-stage pipeline tests for Phase 1.

Each test class validates one stage's outputs are correct and complete
BEFORE the next stage would consume them.  Run a single stage with:

    pytest tests/test_pipeline_stages.py -k Stage1 -v
    pytest tests/test_pipeline_stages.py -k Stage2 -v
    ...etc
"""
import numpy as np
import pytest

from engine.phase_one import (
    SongMandate,
    SongBlueprint,
    DrumKit,
    DrumLoopKit,
    GalactiaFxSamples,
    MelodyKit,
    WobbleBassKit,
    RiddimBassKit,
    Rack128,
    RackMidiMap,
    AudioManifest,
    _oracle,
    _design_palette_intent,
    _build_recipes,
    _extract_sections,
    _build_arrangement_from_dna,
    _sections_from_arrangement,
    _build_audio_manifest,
    _build_chord_progression,
    _build_freq_table,
    _configure_stem_specs,
    _generate_midi_sequences,
    _collect_drums,
    _collect_fx_samples,
    _sketch_drums,
    _build_drum_loops,
    _build_128_rack,
    _build_rack_midi_map,
    _build_loop_midi_maps,
)
from engine.variation_engine import SongDNA


# ── Shared fixture: a fresh SongDNA via _oracle ──

@pytest.fixture(scope="module")
def dna() -> SongDNA:
    bp = SongBlueprint(name="Pipeline_Test", style="dubstep", bpm=150, key="F", scale="minor")
    return _oracle(bp, None, None)


# ═══════════════════════════════════════════════════════════════════════
# STAGE 1: IDENTITY — DNA → Palette → Recipe
# ═══════════════════════════════════════════════════════════════════════

class TestStage1Identity:
    """Stage 1 produces: dna, beat_s, bar_s, design_intent,
    groove_template, quality_targets, arrange_tasks."""

    def test_1b_dna_has_required_fields(self, dna: SongDNA):
        assert dna.name == "Pipeline_Test"
        assert dna.key == "F"
        assert dna.scale == "minor"
        assert dna.bpm == 150
        assert dna.root_freq > 0
        assert isinstance(dna.style, str)
        assert hasattr(dna, "bass")
        assert hasattr(dna, "lead")
        assert hasattr(dna, "drums")
        assert hasattr(dna, "atmosphere")
        assert hasattr(dna, "fx")

    def test_1b_timing_constants(self, dna: SongDNA):
        beat_s = 60.0 / dna.bpm
        bar_s = beat_s * 4
        assert beat_s == pytest.approx(0.4, abs=0.01)   # 150 BPM → 0.4s/beat
        assert bar_s == pytest.approx(1.6, abs=0.05)

    def test_1c_palette_intent_structure(self, dna: SongDNA):
        intent = _design_palette_intent(dna)
        for key in ("drums", "bass", "leads", "atmosphere", "fx", "vocals", "wavetables"):
            assert key in intent, f"Missing palette intent key: {key}"
        # Bass must have rotation + sub_weight
        assert "rotation" in intent["bass"] or "types_needed" in intent["bass"]
        # Leads must declare brightness
        assert "brightness" in intent["leads"]

    def test_1d_recipes_output(self, dna: SongDNA):
        intent = _design_palette_intent(dna)
        sections_raw = _extract_sections(dna)
        recipes = _build_recipes(dna, intent, sections_raw)

        assert "groove_template" in recipes
        assert isinstance(recipes["groove_template"], str)
        assert len(recipes["groove_template"]) > 0

        assert "quality_targets" in recipes
        qt = recipes["quality_targets"]
        assert isinstance(qt, dict)
        assert len(qt) >= 3  # at least LUFS, ceiling, DR

        assert "arrange_tasks" in recipes
        assert isinstance(recipes["arrange_tasks"], list)

    def test_1d_extract_sections(self, dna: SongDNA):
        sections = _extract_sections(dna)
        assert isinstance(sections, dict)
        assert len(sections) > 0
        for name, bars in sections.items():
            assert isinstance(name, str)
            assert isinstance(bars, int)
            assert bars > 0

    def test_stage1_phase_log_entry(self, dna: SongDNA):
        """Simulate full Stage 1 and check phase_log."""
        mandate = SongMandate()
        mandate.dna = dna
        mandate.beat_s = 60.0 / dna.bpm
        mandate.bar_s = mandate.beat_s * 4

        intent = _design_palette_intent(dna)
        mandate.design_intent = intent

        sections_raw = _extract_sections(dna)
        recipes = _build_recipes(dna, intent, sections_raw)
        mandate.groove_template = recipes["groove_template"]
        mandate.quality_targets = recipes["quality_targets"]
        mandate.arrange_tasks = recipes["arrange_tasks"]

        mandate.phase_log.append({"step": "identity", "status": "complete"})

        # Validate everything Stage 2 needs is present
        assert mandate.dna is not None
        assert mandate.beat_s > 0
        assert mandate.bar_s > 0
        assert mandate.design_intent is not None
        assert mandate.groove_template != ""
        assert len(mandate.quality_targets) > 0
        assert mandate.phase_log[-1]["step"] == "identity"


# ═══════════════════════════════════════════════════════════════════════
# STAGE 2: STRUCTURE — Arrangement → Sections → Manifest
# ═════════════════════════════════════════════════════════════════════

class TestStage2Structure:
    """Stage 2 produces: arrangement_template,
    sections, total_bars, total_samples, audio_manifest."""

    def test_2a_arrangement_from_dna(self, dna: SongDNA):
        arr = _build_arrangement_from_dna(dna)
        assert arr is not None
        assert hasattr(arr, "name")
        assert hasattr(arr, "sections")
        assert len(arr.sections) >= 3  # at least intro + drop + outro
        total_bars = sum(s.bars for s in arr.sections)
        assert total_bars > 0

    def test_2c_sections_from_arrangement(self, dna: SongDNA):
        arr = _build_arrangement_from_dna(dna)
        sections = _sections_from_arrangement(arr)
        assert isinstance(sections, dict)
        assert len(sections) > 0
        assert all(isinstance(v, int) and v > 0 for v in sections.values())

    def test_2c_total_bars_and_samples(self, dna: SongDNA):
        arr = _build_arrangement_from_dna(dna)
        sections = _sections_from_arrangement(arr)
        total_bars = sum(sections.values())
        beat_s = 60.0 / dna.bpm
        total_samples = int(total_bars * 4 * beat_s * 44100)
        assert total_bars >= 32  # minimum viable track length
        assert total_samples > 0

    def test_2d_audio_manifest(self, dna: SongDNA):
        arr = _build_arrangement_from_dna(dna)
        sections = _sections_from_arrangement(arr)
        manifest = _build_audio_manifest()
        assert isinstance(manifest, AudioManifest)
        assert manifest.total > 0
        assert len(manifest.files) > 0
        # Must have 4E stem entries (5E added at Stage 4F)
        stages = {f.stage for f in manifest.files}
        assert "4E" in stages

    def test_stage2_feeds_stage3(self, dna: SongDNA):
        """Verify Stage 2 output has everything Stage 3 needs."""
        arr = _build_arrangement_from_dna(dna)
        sections = _sections_from_arrangement(arr)
        manifest = _build_audio_manifest()

        # Stage 3 needs: dna (S1), sections (S2), arrangement_template (S2)
        assert arr is not None
        assert len(sections) > 0
        assert manifest is not None


# ═══════════════════════════════════════════════════════════════════════
# STAGE 3: HARMONIC BLUEPRINT — Chords → Freq table → MIDI
# ═══════════════════════════════════════════════════════════════════════

class TestStage3HarmonicBlueprint:
    """Stage 3 produces: chord_progression, freq_table, midi_sequences."""

    def test_3a_chord_progression(self, dna: SongDNA):
        chords = _build_chord_progression(dna)
        # May be None if module unavailable, but if present must have .chords
        if chords is not None:
            assert hasattr(chords, "chords")
            assert len(chords.chords) >= 2

    def test_3b_freq_table(self, dna: SongDNA):
        ft = _build_freq_table(dna)
        assert isinstance(ft, dict)
        assert len(ft) > 0
        # All values should be positive frequencies
        for note, freq in ft.items():
            assert isinstance(note, str)
            assert freq > 0

    def test_3c_midi_sequences(self, dna: SongDNA):
        """Full Stage 3C: configure stems + generate MIDI."""
        mandate = SongMandate()
        mandate.dna = dna
        mandate.beat_s = 60.0 / dna.bpm
        mandate.bar_s = mandate.beat_s * 4

        # Need S1 outputs
        mandate.design_intent = _design_palette_intent(dna)
        sections_raw = _extract_sections(dna)
        recipes = _build_recipes(dna, mandate.design_intent, sections_raw)
        mandate.groove_template = recipes["groove_template"]
        mandate.quality_targets = recipes["quality_targets"]
        mandate.arrange_tasks = recipes["arrange_tasks"]

        # Need S2 outputs
        mandate.arrangement_template = _build_arrangement_from_dna(dna)
        mandate.sections = _sections_from_arrangement(mandate.arrangement_template)
        mandate.total_bars = sum(mandate.sections.values())
        mandate.total_samples = int(mandate.total_bars * 4 * mandate.beat_s * 44100)

        # S3A + S3B
        mandate.chord_progression = _build_chord_progression(dna)
        mandate.freq_table = _build_freq_table(dna)

        # S3C: MIDI generation
        stem_configs = _configure_stem_specs(mandate)
        midi = _generate_midi_sequences(mandate, stem_configs)

        assert isinstance(midi, dict)
        assert len(midi) > 0
        total_notes = sum(len(v) for v in midi.values())
        assert total_notes > 0
        # Must have ghost_kick
        assert "ghost_kick" in midi
        assert len(midi["ghost_kick"]) > 0

    def test_stage3_no_synth_dependency(self, dna: SongDNA):
        """Stage 3 must NOT depend on wavetables, presets, or drums."""
        # This test ensures MIDI generation only needs DNA + structure
        mandate = SongMandate()
        mandate.dna = dna
        mandate.beat_s = 60.0 / dna.bpm
        mandate.bar_s = mandate.beat_s * 4
        mandate.design_intent = _design_palette_intent(dna)
        sections_raw = _extract_sections(dna)
        recipes = _build_recipes(dna, mandate.design_intent, sections_raw)
        mandate.groove_template = recipes["groove_template"]
        mandate.quality_targets = recipes["quality_targets"]
        mandate.arrange_tasks = recipes["arrange_tasks"]
        mandate.arrangement_template = _build_arrangement_from_dna(dna)
        mandate.sections = _sections_from_arrangement(mandate.arrangement_template)
        mandate.total_bars = sum(mandate.sections.values())
        mandate.total_samples = int(mandate.total_bars * 4 * mandate.beat_s * 44100)

        # These should all still be empty/default — proving S3 doesn't need them
        assert mandate.drums.kick is None, "Drums should not be populated before Stage 5"

        # But MIDI generation should still work
        stem_configs = _configure_stem_specs(mandate)
        midi = _generate_midi_sequences(mandate, stem_configs)
        assert sum(len(v) for v in midi.values()) > 0


# ═══════════════════════════════════════════════════════════════════════
# STAGE 4: SYNTH FACTORY — WT + Mod + FX + Presets + Synthesis + ALS
# ═══════════════════════════════════════════════════════════════════════

class TestStage4SynthFactory:
    """Stage 4 produces: wavetables, modulation_routes, fx_chains,
    serum2_presets, bass/leads/atmos/fx/vocals/melody/wobble/riddim/growl,
    stem_configs, render_als_path, audio_clips."""

    @pytest.fixture
    def stage3_mandate(self, dna: SongDNA) -> SongMandate:
        """Build mandate through Stage 3 completion."""
        mandate = SongMandate()
        mandate.dna = dna
        mandate.beat_s = 60.0 / dna.bpm
        mandate.bar_s = mandate.beat_s * 4
        mandate.design_intent = _design_palette_intent(dna)
        sections_raw = _extract_sections(dna)
        recipes = _build_recipes(dna, mandate.design_intent, sections_raw)
        mandate.groove_template = recipes["groove_template"]
        mandate.quality_targets = recipes["quality_targets"]
        mandate.arrange_tasks = recipes["arrange_tasks"]
        mandate.arrangement_template = _build_arrangement_from_dna(dna)
        mandate.sections = _sections_from_arrangement(mandate.arrangement_template)
        mandate.total_bars = sum(mandate.sections.values())
        mandate.total_samples = int(mandate.total_bars * 4 * mandate.beat_s * 44100)
        mandate.audio_manifest = _build_audio_manifest()
        mandate.chord_progression = _build_chord_progression(dna)
        mandate.freq_table = _build_freq_table(dna)
        stem_configs = _configure_stem_specs(mandate)
        mandate.midi_sequences = _generate_midi_sequences(mandate, stem_configs)
        return mandate

    def test_4g_synthesis_outputs(self, dna: SongDNA):
        """All 9 sketch functions produce non-empty results."""
        from engine.phase_one import (
            _sketch_bass, _sketch_leads, _sketch_atmosphere,
            _sketch_fx, _sketch_vocals, _sketch_melody,
            _sketch_wobble_bass, _sketch_riddim_bass, _sketch_growl_textures,
        )
        intent = _design_palette_intent(dna)
        chords = _build_chord_progression(dna)
        galactia_fx = _collect_fx_samples(intent)

        bass = _sketch_bass(dna, intent)
        assert len(bass.sounds) > 0

        leads = _sketch_leads(dna, intent)
        assert len(leads.screech) > 0

        atmos = _sketch_atmosphere(dna, intent)
        assert atmos is not None

        fx = _sketch_fx(dna, intent, galactia_fx)
        assert fx is not None

        vocals = _sketch_vocals(dna, intent)
        assert vocals is not None

        melody = _sketch_melody(dna, chords)
        assert melody is not None

        wobble = _sketch_wobble_bass(dna)
        assert len(wobble.patterns) > 0

        riddim = _sketch_riddim_bass(dna)
        assert len(riddim.patterns) > 0

        growl = _sketch_growl_textures(dna)
        assert len(growl.frames) > 0

    def test_4h_stem_configs(self, stage3_mandate: SongMandate):
        """Stem configs compile from S1-S3 data."""
        configs = _configure_stem_specs(stage3_mandate)
        assert isinstance(configs, dict)
        assert len(configs) > 0
        # Each stem config should have at minimum a name/type
        for name, cfg in configs.items():
            assert isinstance(name, str)
            assert cfg is not None

    def test_stage4_independent_of_drums(self, stage3_mandate: SongMandate):
        """Synth factory must not depend on drum data."""
        # drums should not be populated yet at Stage 4 entry
        assert stage3_mandate.drums is None or (
            stage3_mandate.drums.kick is None and
            stage3_mandate.drums.snare is None
        )


# ═══════════════════════════════════════════════════════════════════════
# STAGE 5: DRUM FACTORY — Samples, Rack, Loops (NO synth content)
# ═══════════════════════════════════════════════════════════════════════

class TestStage5DrumFactory:
    """Stage 5 produces: drums, galactia_fx, rack_128, rack_midi_map,
    drum_loops, loop_midi_maps, render_patterns.
    Must NOT contain synth content in rack."""

    def test_5a_drum_selection(self, dna: SongDNA):
        intent = _design_palette_intent(dna)
        drums = _collect_drums(dna, intent)
        assert isinstance(drums, DrumKit)
        assert drums.kick is not None
        assert drums.snare is not None
        assert drums.hat_closed is not None
        assert len(drums.kick) > 0

    def test_5b_fx_samples(self, dna: SongDNA):
        intent = _design_palette_intent(dna)
        fx = _collect_fx_samples(intent)
        assert isinstance(fx, GalactiaFxSamples)
        total = sum(len(v) for v in [
            fx.risers, fx.impacts, fx.reverses,
            fx.falling, fx.rising, fx.shepard, fx.buildups,
        ])
        assert total > 0

    def test_5c_drum_processing(self, dna: SongDNA):
        intent = _design_palette_intent(dna)
        drums = _collect_drums(dna, intent)
        processed = _sketch_drums(drums, dna)
        assert isinstance(processed, DrumKit)
        assert processed.kick is not None
        assert len(processed.kick) > 0

    def test_5d_rack_drums_only(self, dna: SongDNA):
        """128 rack must contain drums + FX, NOT synth content."""
        intent = _design_palette_intent(dna)
        drums = _collect_drums(dna, intent)
        drums = _sketch_drums(drums, dna)
        galactia_fx = _collect_fx_samples(intent)

        rack = _build_128_rack(drums, galactia_fx)
        assert isinstance(rack, Rack128)
        total = sum(rack.zone_counts.values())
        assert total > 0
        assert total <= 128

        # Verify drum zones are populated
        assert rack.zone_counts.get("kicks", 0) > 0
        assert rack.zone_counts.get("snares", 0) > 0
        assert rack.zone_counts.get("hats", 0) > 0

    def test_5d_rack_midi_map(self, dna: SongDNA):
        intent = _design_palette_intent(dna)
        drums = _collect_drums(dna, intent)
        drums = _sketch_drums(drums, dna)
        galactia_fx = _collect_fx_samples(intent)
        rack = _build_128_rack(drums, galactia_fx)
        midi_map = _build_rack_midi_map(rack)
        assert isinstance(midi_map, RackMidiMap)
        assert len(midi_map.note_map) > 0

    def test_5e_drum_loops(self, dna: SongDNA):
        intent = _design_palette_intent(dna)
        drums = _collect_drums(dna, intent)
        drums = _sketch_drums(drums, dna)
        arr = _build_arrangement_from_dna(dna)
        sections = _sections_from_arrangement(arr)

        loops = _build_drum_loops(drums, dna, sections)
        assert isinstance(loops, DrumLoopKit)
        assert len(loops.patterns) > 0

    def test_5e_loop_midi_maps(self, dna: SongDNA):
        intent = _design_palette_intent(dna)
        drums = _collect_drums(dna, intent)
        drums = _sketch_drums(drums, dna)
        galactia_fx = _collect_fx_samples(intent)
        arr = _build_arrangement_from_dna(dna)
        sections = _sections_from_arrangement(arr)

        loops = _build_drum_loops(drums, dna, sections)
        rack = _build_128_rack(drums, galactia_fx)
        midi_maps = _build_loop_midi_maps(loops, rack, dna)
        assert isinstance(midi_maps, list)
        assert len(midi_maps) > 0
        total_hits = sum(len(lm.hits) for lm in midi_maps)
        assert total_hits > 0

    def test_stage5_no_synth_in_rack(self, dna: SongDNA):
        """Hard check: rack built with empty synth kits has
        zero synth zone content."""
        intent = _design_palette_intent(dna)
        drums = _collect_drums(dna, intent)
        drums = _sketch_drums(drums, dna)
        galactia_fx = _collect_fx_samples(intent)

        rack = _build_128_rack(drums, galactia_fx)
        # Synth zones should always be 0 — rack is drums-only
        synth_zones = ["sub_bass", "low_bass", "mid_bass", "high_bass", "melodic"]
        synth_total = sum(rack.zone_counts.get(z, 0) for z in synth_zones)
        assert synth_total == 0, (
            f"Rack has {synth_total} synth samples in drum-only build! "
            f"Zones: {', '.join(f'{z}={rack.zone_counts.get(z, 0)}' for z in synth_zones)}"
        )
