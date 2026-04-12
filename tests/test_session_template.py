"""Tests for session_template and phase_two_setup modules."""

from __future__ import annotations

import pytest
import numpy as np


class TestSessionTemplate:
    """Validate the canonical session template builder."""

    def test_build_dubstep_session_track_count(self):
        from engine.session_template import build_dubstep_session
        layout = build_dubstep_session()
        assert len(layout.tracks) == 19
        assert len(layout.returns) == 3
        assert len(layout.scenes) == 9

    def test_bus_groups(self):
        from engine.session_template import build_dubstep_session
        layout = build_dubstep_session()
        bus_names = sorted(set(t.bus for t in layout.tracks))
        assert bus_names == ["bass", "drums", "fx", "melodics"]

    def test_drums_bus_tracks(self):
        from engine.session_template import build_dubstep_session
        layout = build_dubstep_session()
        drums = [t.name for t in layout.tracks if t.bus == "drums"]
        assert "Kick" in drums
        assert "Snare" in drums
        assert "Hi-Hats" in drums
        assert "Percussion" in drums
        assert "SC Trigger" in drums

    def test_bass_bus_tracks(self):
        from engine.session_template import build_dubstep_session
        layout = build_dubstep_session()
        bass = [t.name for t in layout.tracks if t.bus == "bass"]
        assert "Sub" in bass
        assert "Mid Bass" in bass
        assert "Growl" in bass
        assert "Riddim" in bass
        assert "Formant" in bass

    def test_melodics_bus_tracks(self):
        from engine.session_template import build_dubstep_session
        layout = build_dubstep_session()
        mel = [t.name for t in layout.tracks if t.bus == "melodics"]
        assert "Lead" in mel
        assert "Pad" in mel
        assert "Arp" in mel
        assert "Chords" in mel
        assert "Vocal" in mel

    def test_fx_bus_tracks(self):
        from engine.session_template import build_dubstep_session
        layout = build_dubstep_session()
        fx = [t.name for t in layout.tracks if t.bus == "fx"]
        assert "Risers" in fx
        assert "Impacts" in fx
        assert "Transitions" in fx
        assert "Atmos" in fx

    def test_returns(self):
        from engine.session_template import build_dubstep_session
        layout = build_dubstep_session()
        names = [r.name for r in layout.returns]
        assert names == ["Reverb", "Delay", "Parallel Comp"]

    def test_scenes_total_bars(self):
        from engine.session_template import build_dubstep_session
        layout = build_dubstep_session()
        total = sum(s.bars for s in layout.scenes)
        assert total == 112
        assert layout.scenes[0].name == "INTRO"
        assert layout.scenes[-1].name == "OUTRO"

    def test_sc_trigger_is_muted(self):
        from engine.session_template import build_dubstep_session
        layout = build_dubstep_session()
        sc = next(t for t in layout.tracks if t.name == "SC Trigger")
        assert sc.mute is True
        assert sc.volume == 0.0

    def test_sub_is_mono(self):
        from engine.session_template import build_dubstep_session
        layout = build_dubstep_session()
        sub = next(t for t in layout.tracks if t.name == "Sub")
        assert sub.mono is True

    def test_sidechain_pairs(self):
        from engine.session_template import build_dubstep_session
        layout = build_dubstep_session()
        sidechained = [t.name for t in layout.tracks if t.sidechain_from]
        assert "Sub" in sidechained
        assert "Mid Bass" in sidechained
        assert "Growl" in sidechained

    def test_template_requirements(self):
        from engine.session_template import get_template_requirements
        reqs = get_template_requirements()
        assert len(reqs.required_stems) > 0
        assert len(reqs.required_instruments) > 0
        assert len(reqs.bus_names) == 4
        assert len(reqs.return_names) == 3
        assert reqs.total_bars == 112
        assert len(reqs.sidechain_pairs) == 5

    def test_mandate_to_track_mapping(self):
        from engine.session_template import MANDATE_TO_TRACK
        assert MANDATE_TO_TRACK["drums.kick"] == "Kick"
        assert MANDATE_TO_TRACK["bass.sub"] == "Sub"
        assert MANDATE_TO_TRACK["leads.screech"] == "Lead"
        assert MANDATE_TO_TRACK["fx.riser"] == "Risers"
        assert MANDATE_TO_TRACK["fx.boom"] == "Impacts"

    def test_track_modules_coverage(self):
        from engine.session_template import TRACK_MODULES, build_dubstep_session
        layout = build_dubstep_session()
        all_names = {t.name for t in layout.tracks} | {r.name for r in layout.returns}
        for track_name in TRACK_MODULES:
            assert track_name in all_names, f"Module wiring for '{track_name}' not in template"

    def test_gap_module_tracks(self):
        from engine.session_template import GAP_MODULE_TRACKS
        assert "resample_feedback" in GAP_MODULE_TRACKS
        assert "wavetable_export" in GAP_MODULE_TRACKS
        assert "granular_depth" in GAP_MODULE_TRACKS
        assert "guitar_synth" in GAP_MODULE_TRACKS
        assert "vocal_mangle" in GAP_MODULE_TRACKS
        assert "serum_lfo_shapes" in GAP_MODULE_TRACKS
        assert "ab_workflow" in GAP_MODULE_TRACKS
        assert "vip_generator" in GAP_MODULE_TRACKS


class TestPhaseTwoSetup:
    """Validate the Phase 2 Setup module."""

    def test_resolve_mandate_stems_empty(self):
        from engine.session_template import build_dubstep_session
        from engine.phase_two_setup import resolve_mandate_stems

        class FakeMandate:
            pass

        layout = build_dubstep_session()
        stems = resolve_mandate_stems(FakeMandate(), layout)
        assert len(stems) == 19
        assert all(v is None for v in stems.values())

    def test_build_scene_map_from_layout(self):
        from engine.session_template import build_dubstep_session
        from engine.phase_two_setup import build_scene_map

        class FakeMandate:
            arrangement_template = None

        layout = build_dubstep_session()
        scene_map = build_scene_map(FakeMandate(), layout)
        assert "INTRO" in scene_map
        assert "OUTRO" in scene_map
        assert scene_map["INTRO"] == 0

    def test_build_energy_curve(self):
        from engine.phase_two_setup import build_energy_curve

        class FakeMandate:
            arrangement_template = None
            dna = None

        curve = build_energy_curve(FakeMandate(), 48000)
        assert len(curve) == 48000
        assert np.allclose(curve, 0.5)

    def test_session_arrangement_dataclass(self):
        from engine.phase_two_setup import SessionArrangement
        sa = SessionArrangement()
        assert sa.buses == {}
        assert sa.returns == {}
        assert sa.bpm == 150.0
        assert sa.total_bars == 0

    def test_to_ableton_live_template(self):
        from engine.session_template import build_dubstep_session, to_ableton_live_template
        layout = build_dubstep_session()
        template = to_ableton_live_template(layout)
        assert template.name == "DUBFORGE Subtronics Template"
        assert len(template.tracks) == 19
        assert len(template.return_tracks) == 3
        assert len(template.scenes) == 9
