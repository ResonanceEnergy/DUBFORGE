"""Tests for engine.ableton_live — Ableton Live integration."""
from engine.ableton_live import (
    ABLETON_COLORS,
    LOM_REFERENCE,
    ArrangementTemplate,
    ClipTriggerQuantization,
    DeviceConfig,
    DeviceParam,
    DeviceType,
    LaunchMode,
    MIDIClip,
    MIDINote,
    SessionTemplate,
    TrackConfig,
    WarpMode,
    build_arrangement_template,
    build_dubstep_session_template,
    dubstep_master_chain,
    fibonacci_duration_pattern,
    generate_arp_clip,
    generate_chord_stab_clip,
    generate_m4l_control_script,
    generate_mid_bass_clip,
    generate_sub_bass_clip,
    golden_section_point,
    phi_timing_grid,
    phi_velocity_curve,
    psbs_device_chain,
    return_track_delay,
    return_track_reverb,
)
from engine.config_loader import PHI

# ── Constants ────────────────────────────────────────────────────

class TestConstants:
    def test_ableton_colors(self):
        assert isinstance(ABLETON_COLORS, dict)
        assert len(ABLETON_COLORS) >= 10

    def test_lom_reference(self):
        assert isinstance(LOM_REFERENCE, dict)


# ── Enums ────────────────────────────────────────────────────────

class TestEnums:
    def test_clip_trigger_quantization(self):
        assert ClipTriggerQuantization.NONE == 0

    def test_launch_mode(self):
        assert LaunchMode.TRIGGER == 0
        assert LaunchMode.GATE == 1

    def test_warp_mode(self):
        assert WarpMode.BEATS == 0

    def test_device_type(self):
        assert DeviceType.INSTRUMENT == 1
        assert DeviceType.AUDIO_EFFECT == 2


# ── Dataclasses ──────────────────────────────────────────────────

class TestMIDINote:
    def test_defaults(self):
        n = MIDINote(pitch=60, start_time=0.0, duration=1.0)
        assert n.velocity == 100.0
        assert n.mute is False
        assert n.probability == 1.0

    def test_to_dict(self):
        n = MIDINote(pitch=64, start_time=2.0, duration=0.5)
        d = n.to_dict()
        assert d["pitch"] == 64
        assert d["start_time"] == 2.0


class TestMIDIClip:
    def test_loop_end_defaults_to_length(self):
        c = MIDIClip(name="Test", length=8.0)
        assert c.loop_end == 8.0
        assert c.looping is True

    def test_to_dict(self):
        c = MIDIClip(name="Test", length=4.0)
        d = c.to_dict()
        assert d["name"] == "Test"


class TestDeviceConfig:
    def test_to_dict(self):
        p = DeviceParam(name="Freq", value=0.5)
        dc = DeviceConfig(class_name="Eq8", display_name="EQ Eight", parameters=[p])
        d = dc.to_dict()
        assert d["class_name"] == "Eq8"
        assert len(d["parameters"]) == 1


# ── Utility functions ────────────────────────────────────────────

class TestPhiVelocityCurve:
    def test_length(self):
        curve = phi_velocity_curve(8)
        assert len(curve) == 8

    def test_values_in_range(self):
        curve = phi_velocity_curve(13, base=60.0, peak=127.0)
        for v in curve:
            assert 1.0 <= v <= 127.0

    def test_single_note(self):
        curve = phi_velocity_curve(1)
        assert len(curve) == 1


class TestFibonacciDurationPattern:
    def test_sums_to_bars(self):
        pattern = fibonacci_duration_pattern(8)
        assert sum(pattern) == 8

    def test_returns_list(self):
        pattern = fibonacci_duration_pattern(16)
        assert isinstance(pattern, list)
        assert all(isinstance(d, int) for d in pattern)


class TestPhiTimingGrid:
    def test_length(self):
        grid = phi_timing_grid(16.0, 8)
        assert len(grid) == 8

    def test_values_positive(self):
        grid = phi_timing_grid(8.0, 5)
        for t in grid:
            assert t >= 0


class TestGoldenSectionPoint:
    def test_calculation(self):
        point = golden_section_point(100.0)
        assert abs(point - 100.0 / PHI) < 0.01


# ── Clip generators ──────────────────────────────────────────────

class TestGenerateSubBassClip:
    def test_returns_midi_clip(self):
        clip = generate_sub_bass_clip()
        assert isinstance(clip, MIDIClip)
        assert len(clip.notes) > 0

    def test_custom_params(self):
        clip = generate_sub_bass_clip(root_note=36, bars=4, bpm=140.0)
        assert isinstance(clip, MIDIClip)


class TestGenerateMidBassClip:
    def test_returns_midi_clip(self):
        clip = generate_mid_bass_clip()
        assert isinstance(clip, MIDIClip)
        assert len(clip.notes) > 0


class TestGenerateArpClip:
    def test_returns_midi_clip(self):
        clip = generate_arp_clip()
        assert isinstance(clip, MIDIClip)
        assert len(clip.notes) > 0

    def test_custom_scale(self):
        clip = generate_arp_clip(root_note=60, scale="minor", bars=8, octave_range=3)
        assert isinstance(clip, MIDIClip)


class TestGenerateChordStabClip:
    def test_returns_midi_clip(self):
        clip = generate_chord_stab_clip()
        assert isinstance(clip, MIDIClip)

    def test_custom_chord(self):
        clip = generate_chord_stab_clip(chord_notes=[60, 64, 67])
        assert isinstance(clip, MIDIClip)


# ── Device chains ────────────────────────────────────────────────

class TestPsbsDeviceChain:
    def test_returns_device_config(self):
        chain = psbs_device_chain()
        assert isinstance(chain, DeviceConfig)

    def test_has_rack_chains(self):
        chain = psbs_device_chain()
        d = chain.to_dict()
        assert len(d.get("chains", d.get("rack_chains", []))) == 5  # 5 PSBS layers


class TestDubstepMasterChain:
    def test_returns_list(self):
        chain = dubstep_master_chain()
        assert isinstance(chain, list)
        assert len(chain) == 4
        assert all(isinstance(d, DeviceConfig) for d in chain)


class TestReturnTracks:
    def test_reverb(self):
        track = return_track_reverb()
        assert isinstance(track, TrackConfig)

    def test_delay(self):
        track = return_track_delay()
        assert isinstance(track, TrackConfig)


# ── Session template ─────────────────────────────────────────────

class TestBuildDubstepSessionTemplate:
    def test_returns_session_template(self):
        session = build_dubstep_session_template()
        assert isinstance(session, SessionTemplate)
        assert session.bpm == 150.0

    def test_has_tracks(self):
        session = build_dubstep_session_template()
        assert len(session.tracks) >= 8

    def test_has_scenes(self):
        session = build_dubstep_session_template()
        assert len(session.scenes) >= 5

    def test_to_dict(self):
        session = build_dubstep_session_template()
        d = session.to_dict()
        assert isinstance(d, dict)
        assert "tracks" in d
        assert "bpm" in d

    def test_custom_params(self):
        session = build_dubstep_session_template(name="TEST", bpm=140.0)
        assert session.name == "TEST"
        assert session.bpm == 140.0


# ── Arrangement template ─────────────────────────────────────────

class TestBuildArrangementTemplate:
    def test_returns_arrangement(self):
        arr = build_arrangement_template()
        assert isinstance(arr, ArrangementTemplate)

    def test_has_sections(self):
        arr = build_arrangement_template()
        assert len(arr.sections) >= 5

    def test_has_cue_points(self):
        arr = build_arrangement_template()
        assert len(arr.cue_points) > 0

    def test_to_dict(self):
        arr = build_arrangement_template()
        d = arr.to_dict()
        assert isinstance(d, dict)
        assert "sections" in d


# ── M4L script generation ────────────────────────────────────────

class TestGenerateM4lControlScript:
    def test_returns_string(self):
        session = build_dubstep_session_template()
        script = generate_m4l_control_script(session)
        assert isinstance(script, str)
        assert len(script) > 100
        assert "import" in script or "Live" in script
