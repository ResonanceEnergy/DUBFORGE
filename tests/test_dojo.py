"""Tests for engine.dojo — Producer Dojo / ill.Gates methodology engine."""
from engine.dojo import (
    ARTIST_PROFILE,
    BELT_SYSTEM,
    DOJO_PLATFORM,
    DOJO_TECHNIQUES,
    THE_APPROACH,
    ApproachPhase,
    BeltRank,
    RackCategory,
    RackZone,
    TechniqueType,
    build_128_rack,
    build_dojo_session_template,
    phi_approach_timing,
    phi_belt_progression,
    phi_mudpie_recipe,
)

# ── Constants ────────────────────────────────────────────────────

class TestConstants:
    def test_belt_system(self):
        assert isinstance(BELT_SYSTEM, list)
        assert len(BELT_SYSTEM) == 7

    def test_the_approach(self):
        assert isinstance(THE_APPROACH, list)
        assert len(THE_APPROACH) == 7

    def test_dojo_techniques(self):
        assert isinstance(DOJO_TECHNIQUES, list)
        assert len(DOJO_TECHNIQUES) == 8

    def test_artist_profile(self):
        assert isinstance(ARTIST_PROFILE, dict)
        assert "name" in ARTIST_PROFILE or "artist" in ARTIST_PROFILE or len(ARTIST_PROFILE) > 0

    def test_dojo_platform(self):
        assert isinstance(DOJO_PLATFORM, dict)


# ── Enums ────────────────────────────────────────────────────────

class TestEnums:
    def test_belt_ranks(self):
        assert len(BeltRank) == 7
        assert BeltRank.WHITE is not None
        assert BeltRank.BLACK is not None

    def test_approach_phases(self):
        assert len(ApproachPhase) == 7
        assert ApproachPhase.COLLECT is not None
        assert ApproachPhase.RELEASE is not None

    def test_technique_types(self):
        assert len(TechniqueType) == 6


# ── Dataclasses ──────────────────────────────────────────────────

class TestRackZone:
    def test_defaults(self):
        z = RackZone(note_start=0, note_end=8, category="bass", sample_slot=1)
        assert z.velocity_low == 0
        assert z.velocity_high == 127
        assert z.label == ""


class TestRackCategory:
    def test_fields(self):
        c = RackCategory(
            name="Bass", zone_count=16, note_range_start=0,
            note_range_end=15, color="blue", description="Bass sounds",
        )
        assert c.name == "Bass"
        assert c.zone_count == 16


# ── build_128_rack ───────────────────────────────────────────────

class TestBuild128Rack:
    def test_returns_dict(self):
        rack = build_128_rack()
        assert isinstance(rack, dict)

    def test_has_128_zones(self):
        rack = build_128_rack()
        assert rack["total_zones"] == 128
        assert len(rack["zones"]) == 128

    def test_has_categories(self):
        rack = build_128_rack()
        assert len(rack["categories"]) >= 10

    def test_has_fibonacci_distribution(self):
        rack = build_128_rack()
        assert "fibonacci_distribution" in rack

    def test_has_dubforge_preload(self):
        rack = build_128_rack()
        assert "dubforge_preload" in rack


# ── build_dojo_session_template ──────────────────────────────────

class TestBuildDojoSessionTemplate:
    def test_returns_dict(self):
        session = build_dojo_session_template()
        assert isinstance(session, dict)

    def test_has_tracks(self):
        session = build_dojo_session_template()
        assert "tracks" in session
        assert len(session["tracks"]) >= 8

    def test_has_scenes(self):
        session = build_dojo_session_template()
        assert "scenes" in session
        assert len(session["scenes"]) == 7

    def test_golden_section(self):
        session = build_dojo_session_template()
        assert "golden_section_bar" in session
        assert session["golden_section_bar"] > 0


# ── phi_belt_progression ─────────────────────────────────────────

class TestPhiBeltProgression:
    def test_returns_dict(self):
        prog = phi_belt_progression()
        assert isinstance(prog, dict)

    def test_has_7_belts(self):
        prog = phi_belt_progression()
        assert len(prog["belt_progression"]) == 7

    def test_total_tracks(self):
        prog = phi_belt_progression()
        assert prog["total_tracks_to_black_belt"] == 85

    def test_fibonacci_track_counts(self):
        prog = phi_belt_progression()
        assert "fibonacci_track_counts" in prog


# ── phi_approach_timing ──────────────────────────────────────────

class TestPhiApproachTiming:
    def test_returns_dict(self):
        timing = phi_approach_timing()
        assert isinstance(timing, dict)

    def test_default_hours(self):
        timing = phi_approach_timing()
        assert timing["total_session_hours"] == 8.0

    def test_custom_hours(self):
        timing = phi_approach_timing(total_hours=4.0)
        assert timing["total_session_hours"] == 4.0

    def test_has_7_phases(self):
        timing = phi_approach_timing()
        assert len(timing["phase_allocation"]) == 7

    def test_golden_checkpoint(self):
        timing = phi_approach_timing()
        assert "golden_checkpoint" in timing
        # Checkpoint is present (may be a time string or numeric)
        assert timing["golden_checkpoint"] is not None


# ── phi_mudpie_recipe ────────────────────────────────────────────

class TestPhiMudpieRecipe:
    def test_returns_dict(self):
        recipe = phi_mudpie_recipe()
        assert isinstance(recipe, dict)

    def test_default_sources(self):
        recipe = phi_mudpie_recipe()
        assert recipe["source_count"] == 8

    def test_custom_sources(self):
        recipe = phi_mudpie_recipe(num_sources=5)
        assert recipe["source_count"] == 5

    def test_has_fx_chain(self):
        recipe = phi_mudpie_recipe()
        assert "fx_chain" in recipe
        assert len(recipe["fx_chain"]) == 5

    def test_has_sources(self):
        recipe = phi_mudpie_recipe()
        assert "sources" in recipe
        assert len(recipe["sources"]) == 8
