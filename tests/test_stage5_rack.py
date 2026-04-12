"""Tests for Phase 1 Stage 5: DRUM FACTORY — Rack + MIDI map.

Covers:
- _rack_add (shared slot insertion)
- _fill_synth_zones (standalone zone-filling utility)
- _build_128_rack (drums + FX only rack build)
- _build_rack_midi_map (MIDI note mapping)
- Zone layout constants (_ZONE_IDX, _ZONE_MAX, _ZONE_RANGES)
"""
import numpy as np
import pytest

from engine.phase_one import (
    AtmosphereKit,
    BassArsenal,
    DrumKit,
    FxKit,
    GalactiaFxSamples,
    GrowlKit,
    LeadPalette,
    MelodyKit,
    Rack128,
    RiddimBassKit,
    VocalKit,
    WavetableKit,
    WobbleBassKit,
    _ZONE_IDX,
    _ZONE_MAX,
    _ZONE_RANGES,
    _build_128_rack,
    _build_rack_midi_map,
    _fill_synth_zones,
    _rack_add,
)

SR = 48000
_TONE = np.sin(2 * np.pi * 440 * np.arange(SR) / SR)  # 1 s @ 440 Hz


def _short(n: int = 2048) -> np.ndarray:
    return _TONE[:n].copy()


# ═══════════════════════════════════════════════════════════════════
#  Zone layout constants
# ═══════════════════════════════════════════════════════════════════

class TestZoneConstants:
    def test_zone_idx_has_14_categories(self):
        assert len(_ZONE_IDX) == 14

    def test_zone_max_has_14_categories(self):
        assert len(_ZONE_MAX) == 14

    def test_zone_ranges_has_14_categories(self):
        assert len(_ZONE_RANGES) == 14

    def test_total_capacity_is_128(self):
        assert sum(_ZONE_MAX.values()) == 128

    def test_zone_idx_matches_ranges(self):
        for zone, start in _ZONE_IDX.items():
            assert _ZONE_RANGES[zone][0] == start

    def test_zone_max_matches_ranges(self):
        for zone, cap in _ZONE_MAX.items():
            lo, hi = _ZONE_RANGES[zone]
            assert cap == hi - lo + 1

    def test_zones_are_contiguous(self):
        sorted_zones = sorted(_ZONE_IDX.items(), key=lambda x: x[1])
        for i in range(len(sorted_zones) - 1):
            z_name, z_start = sorted_zones[i]
            next_start = sorted_zones[i + 1][1]
            assert z_start + _ZONE_MAX[z_name] == next_start

    def test_fibonacci_sizes(self):
        fib = {5, 8, 13}
        for cap in _ZONE_MAX.values():
            assert cap in fib


# ═══════════════════════════════════════════════════════════════════
#  _rack_add
# ═══════════════════════════════════════════════════════════════════

class TestRackAdd:
    def test_adds_slot(self):
        rack = Rack128()
        counts = {z: 0 for z in _ZONE_IDX}
        _rack_add(rack, counts, "kicks", "test_kick", _short(), "synth")
        assert "test_kick" in rack.slots
        assert counts["kicks"] == 1
        assert rack.slots["test_kick"]["zone_num"] == _ZONE_IDX["kicks"]

    def test_skips_none_audio(self):
        rack = Rack128()
        counts = {z: 0 for z in _ZONE_IDX}
        _rack_add(rack, counts, "kicks", "null_kick", None, "synth")
        assert "null_kick" not in rack.slots
        assert counts["kicks"] == 0

    def test_respects_zone_capacity(self):
        rack = Rack128()
        counts = {z: 0 for z in _ZONE_IDX}
        counts["vocal"] = _ZONE_MAX["vocal"]  # Pre-fill to max
        _rack_add(rack, counts, "vocal", "overflow", _short(), "synth")
        assert "overflow" not in rack.slots

    def test_dedup_skips_existing(self):
        rack = Rack128()
        counts = {z: 0 for z in _ZONE_IDX}
        _rack_add(rack, counts, "kicks", "kick_a", _short(), "src1")
        _rack_add(rack, counts, "kicks", "kick_a", _short(), "src2", dedup=True)
        assert counts["kicks"] == 1
        assert rack.slots["kick_a"]["source"] == "src1"

    def test_no_dedup_overwrites(self):
        rack = Rack128()
        counts = {z: 0 for z in _ZONE_IDX}
        _rack_add(rack, counts, "kicks", "kick_a", _short(), "src1")
        _rack_add(rack, counts, "kicks", "kick_a", _short(), "src2", dedup=False)
        # Without dedup, a second add with same name increments count
        assert counts["kicks"] == 2

    def test_appends_manifest(self):
        rack = Rack128()
        counts = {z: 0 for z in _ZONE_IDX}
        _rack_add(rack, counts, "fx", "riser_1", _short(), "galactia")
        assert len(rack.source_manifest) == 1
        assert rack.source_manifest[0]["slot"] == "riser_1"

    def test_zone_num_increments(self):
        rack = Rack128()
        counts = {z: 0 for z in _ZONE_IDX}
        _rack_add(rack, counts, "snares", "snare_1", _short(), "s1")
        _rack_add(rack, counts, "snares", "snare_2", _short(), "s2")
        assert rack.slots["snare_1"]["zone_num"] == _ZONE_IDX["snares"]
        assert rack.slots["snare_2"]["zone_num"] == _ZONE_IDX["snares"] + 1


# ═══════════════════════════════════════════════════════════════════
#  _fill_synth_zones
# ═══════════════════════════════════════════════════════════════════

class TestFillSynthZones:
    def test_fills_bass(self):
        rack = Rack128()
        counts = {z: 0 for z in _ZONE_IDX}
        bass = BassArsenal(
            sub=_short(), reese=_short(),
            sounds={"dist_fm": _short(), "sub_growl": _short()},
            sources={"sub": "synth", "reese": "synth", "dist_fm": "synth", "sub_growl": "synth"},
        )
        _fill_synth_zones(rack, counts, bass=bass)
        assert counts["sub_bass"] >= 2  # sub_sine + sub_growl
        assert counts["low_bass"] >= 2  # bass_reese + bass_dist_fm

    def test_fills_atmosphere(self):
        rack = Rack128()
        counts = {z: 0 for z in _ZONE_IDX}
        atmos = AtmosphereKit(
            dark_pad=_short(), lush_pad=_short(),
            drone=_short(), noise_bed=_short(),
        )
        _fill_synth_zones(rack, counts, atmosphere=atmos)
        assert counts["atmos"] == 4

    def test_fills_vocals(self):
        rack = Rack128()
        counts = {z: 0 for z in _ZONE_IDX}
        vox = VocalKit(chops={"ee": _short(), "ah": _short(), "oh": _short()})
        _fill_synth_zones(rack, counts, vocals=vox)
        assert counts["vocal"] == 3

    def test_fills_transitions(self):
        rack = Rack128()
        counts = {z: 0 for z in _ZONE_IDX}
        fx = FxKit(tape_stop=_short(), pitch_dive=_short(), gate_chop=_short())
        _fill_synth_zones(rack, counts, fx=fx)
        assert counts["transitions"] >= 3

    def test_fills_utility_wavetables(self):
        rack = Rack128()
        counts = {z: 0 for z in _ZONE_IDX}
        wt = WavetableKit(frames={"fm_pack": [_short()], "growl_pack": [_short()]})
        _fill_synth_zones(rack, counts, wavetables=wt)
        assert counts["utility"] == 2

    def test_dedup_skips_existing_slots(self):
        rack = Rack128()
        counts = {z: 0 for z in _ZONE_IDX}
        atmos = AtmosphereKit(dark_pad=_short())
        _fill_synth_zones(rack, counts, atmosphere=atmos)
        before = counts["atmos"]
        _fill_synth_zones(rack, counts, atmosphere=atmos, dedup=True)
        assert counts["atmos"] == before  # No change

    def test_growl_frames_capped(self):
        rack = Rack128()
        counts = {z: 0 for z in _ZONE_IDX}
        growl = GrowlKit(frames=[_short() for _ in range(20)])
        _fill_synth_zones(rack, counts, growl=growl)
        assert counts["high_bass"] == _ZONE_MAX["high_bass"]

    def test_melodic_zone(self):
        rack = Rack128()
        counts = {z: 0 for z in _ZONE_IDX}
        leads = LeadPalette(
            screech={440.0: _short(), 880.0: _short()},
            pluck={440.0: _short()},
            chord_l=_short(),
        )
        melody = MelodyKit(
            lead_melody=_short(),
            arp_patterns={"fib": _short()},
        )
        _fill_synth_zones(rack, counts, leads=leads, melody=melody)
        # 2 screech + 1 pluck + 1 chord_L + 1 lead_melody + 1 arp = 6
        assert counts["melodic"] == 6


# ═══════════════════════════════════════════════════════════════════
#  _build_128_rack (Stage 2E)
# ═══════════════════════════════════════════════════════════════════

def _make_drum_kit() -> DrumKit:
    return DrumKit(
        kick=_short(), snare=_short(), hat_closed=_short(),
        hat_open=_short(), clap=_short(), crash=_short(),
        kick_source="synth", snare_source="synth",
        hat_closed_source="synth", hat_open_source="synth",
        clap_source="synth", crash_source="synth",
    )


def _make_empty_gfx():
    return GalactiaFxSamples()


class TestBuild128Rack:
    def test_returns_rack128(self):
        drums = _make_drum_kit()
        rack = _build_128_rack(drums, _make_empty_gfx())
        assert isinstance(rack, Rack128)

    def test_drums_placed_in_correct_zones(self):
        drums = _make_drum_kit()
        rack = _build_128_rack(drums, _make_empty_gfx())
        assert rack.slots["drum_kick"]["zone"] == "kicks"
        assert rack.slots["drum_snare"]["zone"] == "snares"
        assert rack.slots["drum_hat_closed"]["zone"] == "hats"
        assert rack.slots["drum_crash"]["zone"] == "perc"

    def test_zone_counts_populated(self):
        drums = _make_drum_kit()
        rack = _build_128_rack(drums, _make_empty_gfx())
        assert rack.zone_counts["kicks"] == 1
        assert rack.zone_counts["snares"] == 2  # snare + clap
        assert rack.zone_counts["hats"] == 2    # closed + open
        assert rack.zone_counts["perc"] == 1    # crash

    def test_no_synth_zones(self):
        drums = _make_drum_kit()
        rack = _build_128_rack(drums, _make_empty_gfx())
        assert rack.zone_counts.get("sub_bass", 0) == 0
        assert rack.zone_counts.get("melodic", 0) == 0
        assert rack.zone_counts.get("atmos", 0) == 0

    def test_galactia_fx_in_rack(self):
        drums = _make_drum_kit()
        gfx = GalactiaFxSamples(
            risers=[_short()],
            impacts=[_short()],
            buildups=[_short()],
        )
        rack = _build_128_rack(drums, gfx)
        total = sum(rack.zone_counts.values())
        # drums(6) + riser(1) + impact(1) + buildup(1) = 9
        assert total >= 9
        assert rack.zone_counts.get("fx", 0) >= 2
        assert rack.zone_counts.get("transitions", 0) >= 1

    def test_manifest_tracks_sources(self):
        drums = _make_drum_kit()
        rack = _build_128_rack(drums, _make_empty_gfx())
        assert len(rack.source_manifest) == sum(rack.zone_counts.values())


# ═══════════════════════════════════════════════════════════════════
#  _build_rack_midi_map (Stage 5 refresh)
# ═══════════════════════════════════════════════════════════════════

class TestBuildRackMidiMap:
    def test_returns_rack_midi_map(self):
        drums = _make_drum_kit()
        rack = _build_128_rack(drums, _make_empty_gfx())
        midi_map = _build_rack_midi_map(rack)
        from engine.phase_one import RackMidiMap
        assert isinstance(midi_map, RackMidiMap)

    def test_note_count_matches_slots(self):
        drums = _make_drum_kit()
        rack = _build_128_rack(drums, _make_empty_gfx())
        midi_map = _build_rack_midi_map(rack)
        assert len(midi_map.note_map) == len(rack.slots)

    def test_kick_at_zone_37(self):
        drums = _make_drum_kit()
        rack = _build_128_rack(drums, _make_empty_gfx())
        midi_map = _build_rack_midi_map(rack)
        assert 37 in midi_map.note_map
        assert midi_map.note_map[37]["name"] == "drum_kick"

    def test_zone_ranges_present(self):
        drums = _make_drum_kit()
        rack = _build_128_rack(drums, _make_empty_gfx())
        midi_map = _build_rack_midi_map(rack)
        assert len(midi_map.zone_ranges) == 14

    def test_all_notes_within_0_127(self):
        drums = _make_drum_kit()
        gfx = GalactiaFxSamples(risers=[_short()], impacts=[_short()])
        rack = _build_128_rack(drums, gfx)
        midi_map = _build_rack_midi_map(rack)
        for note in midi_map.note_map:
            assert 0 <= note <= 127
