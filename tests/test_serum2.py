"""Tests for engine.serum2 — Serum 2 synthesizer engine (v2.0.18 model)."""
from engine.config_loader import PHI
from engine.serum2 import (
    MODULATION_DESTINATIONS,
    SERUM2_ARCHITECTURE,
    SERUM_FRAME_SIZE,
    SERUM_MAX_FRAMES,
    WAVETABLE_MAP,
    ArpPatternMode,
    ArpShape,
    ClipSequencerConfig,
    CompressorMode,
    DelayMode,
    DistortionMode,
    EffectSlot,
    EffectType,
    EnvelopeConfig,
    FilterConfig,
    FilterType,
    FMSubMode,
    FXRack,
    LFOConfig,
    LFODirection,
    LFOMode,
    LFOShape,
    LFOType,
    MacroConfig,
    ModulationRoute,
    NitrousMode,
    NoiseColor,
    NoiseOscillator,
    OscillatorConfig,
    OscillatorType,
    ReverbType,
    Serum2Patch,
    SubOscillator,
    SubOscWaveform,
    UnisonMode,
    UnisonStack,
    VoiceStealPriority,
    VoicingConfig,
    VoicingMode,
    WarpMode,
    WavetableSlot,
    build_dubstep_patches,
    build_init_template,
    fibonacci_lfo_rates,
    fibonacci_wavetable_frames,
    phi_effect_mix,
    phi_envelope,
    phi_filter_cutoff,
    phi_fm_ratio,
    phi_macro_scaling,
    phi_unison_detune,
)

# ── Constants ────────────────────────────────────────────────────

class TestConstants:
    def test_frame_size(self):
        assert SERUM_FRAME_SIZE == 2048

    def test_max_frames(self):
        assert SERUM_MAX_FRAMES == 256

    def test_architecture(self):
        assert isinstance(SERUM2_ARCHITECTURE, dict)

    def test_wavetable_map(self):
        assert isinstance(WAVETABLE_MAP, dict)


# ── Enums — Oscillator Types ────────────────────────────────────

class TestOscillatorType:
    def test_five_types(self):
        assert len(OscillatorType) == 5

    def test_wavetable(self):
        assert OscillatorType.WAVETABLE.value == "wavetable"

    def test_all_types(self):
        expected = {"wavetable", "multisample", "sample", "granular", "spectral"}
        assert {t.value for t in OscillatorType} == expected


# ── Enums — Warp Modes ──────────────────────────────────────────

class TestWarpMode:
    def test_has_off(self):
        assert WarpMode.OFF.value == "Off"

    def test_has_sync(self):
        assert WarpMode.SYNC.value == "Sync"

    def test_alt_warp_count(self):
        alt_warps = [w for w in WarpMode
                     if w.value in ("Bend +", "Bend -", "Bend +/-", "PWM",
                                    "Asym +", "Asym -", "Asym +/-", "Flip", "Mirror",
                                    "Remap 1", "Remap 2", "Remap 3", "Remap 4",
                                    "Quantize", "Odd/Even")]
        assert len(alt_warps) == 15

    def test_odd_even_new(self):
        """Odd/Even is a new Alt Warp in Serum 2."""
        assert WarpMode.ODD_EVEN.value == "Odd/Even"

    def test_filter_warps(self):
        assert WarpMode.WARP_LPF.value == "LPF"
        assert WarpMode.WARP_HPF.value == "HPF"

    def test_distortion_warps(self):
        dist_warps = [w for w in WarpMode if w.name.startswith("DIST_")]
        assert len(dist_warps) == 14

    def test_fm_warps(self):
        fm_warps = [w for w in WarpMode if w.name.startswith("FM_")]
        assert len(fm_warps) == 6

    def test_pd_warps(self):
        pd_warps = [w for w in WarpMode if w.name.startswith("PD_")]
        assert len(pd_warps) == 7

    def test_am_warps(self):
        am_warps = [w for w in WarpMode if w.name.startswith("AM_")]
        assert len(am_warps) == 6

    def test_rm_warps(self):
        rm_warps = [w for w in WarpMode if w.name.startswith("RM_")]
        assert len(rm_warps) == 6

    def test_total_warp_modes(self):
        assert len(WarpMode) == 58

    def test_fm_sub_modes(self):
        assert len(FMSubMode) == 3
        assert FMSubMode.THRU_ZERO.value == "Thru-Zero"


# ── Enums — Filter Types ────────────────────────────────────────

class TestFilterType:
    def test_normal_mg_low_slopes(self):
        """MG Low should have 6/12/18/24 dB slopes."""
        mg_lows = [f for f in FilterType if f.value.startswith("MG Low")]
        assert len(mg_lows) == 4

    def test_normal_low_slopes(self):
        lows = [f for f in FilterType if f.value.startswith("Low ") and "EQ" not in f.value]
        assert len(lows) == 4

    def test_multi_filters(self):
        multis = [f for f in FilterType if f.name.startswith("MULTI_")]
        assert len(multis) == 16

    def test_flanges_filters(self):
        flanges = [f for f in FilterType
                   if any(f.value.startswith(p) for p in ("Cmb", "Flg", "Phs"))]
        assert len(flanges) == 9

    def test_serum2_new_filters(self):
        new = {"Wsp", "DJ Mixer", "Diffusor", "MG Ladder", "Acid Ladder",
               "EMS Ladder", "MG Dirty", "PZ SVF", "Comb 2", "Exp MM", "Exp BPF"}
        actual = {f.value for f in FilterType if f.name in (
            "WSP", "DJ_MIXER", "DIFFUSOR", "MG_LADDER", "ACID_LADDER",
            "EMS_LADDER", "MG_DIRTY", "PZ_SVF", "COMB_2", "EXP_MM", "EXP_BPF"
        )}
        assert actual == new

    def test_total_filter_types(self):
        assert len(FilterType) == 80


# ── Enums — Effects ──────────────────────────────────────────────

class TestEffectType:
    def test_no_ott(self):
        """OTT does not exist as a standalone effect in Serum 2."""
        names = {e.name for e in EffectType}
        assert "OTT" not in names

    def test_no_bitcrusher(self):
        names = {e.name for e in EffectType}
        assert "BITCRUSHER" not in names

    def test_bode_new(self):
        assert EffectType.BODE.value == "Bode"

    def test_convolve_new(self):
        assert EffectType.CONVOLVE.value == "Convolve"

    def test_utility_new(self):
        assert EffectType.UTILITY.value == "Utility"

    def test_splitters(self):
        splitters = [e for e in EffectType if "Splitter" in e.value]
        assert len(splitters) == 3

    def test_total_fx_types(self):
        assert len(EffectType) == 16  # 13 FX + 3 splitters

    def test_fx_racks(self):
        assert len(FXRack) == 3


class TestDistortionMode:
    def test_count(self):
        assert len(DistortionMode) == 15

    def test_overdrive_new(self):
        assert DistortionMode.OVERDRIVE.value == "Overdrive"

    def test_x_shaper(self):
        assert DistortionMode.X_SHAPER.value == "X-Shaper"
        assert DistortionMode.X_SHAPER_ASYM.value == "X-Shaper (Asym)"

    def test_sine_shaper(self):
        assert DistortionMode.SINE_SHAPER.value == "Sine Shaper"


class TestReverbType:
    def test_count(self):
        assert len(ReverbType) == 5

    def test_new_types(self):
        new = {"Vintage", "Nitrous", "Basin"}
        actual = {r.value for r in ReverbType if r.value in new}
        assert actual == new

    def test_nitrous_modes(self):
        assert len(NitrousMode) == 5

    def test_compressor_modes(self):
        assert len(CompressorMode) == 2

    def test_delay_modes(self):
        assert len(DelayMode) == 3


# ── Enums — Unison ───────────────────────────────────────────────

class TestUnisonMode:
    def test_count(self):
        assert len(UnisonMode) == 5

    def test_modes(self):
        expected = {"Linear", "Super", "Exp", "Inv", "Random"}
        assert {u.value for u in UnisonMode} == expected

    def test_no_classic(self):
        names = {u.name for u in UnisonMode}
        assert "CLASSIC" not in names

    def test_stack_options(self):
        assert len(UnisonStack) == 9


# ── Enums — LFO ─────────────────────────────────────────────────

class TestLFOEnums:
    def test_lfo_types(self):
        assert len(LFOType) == 5
        assert LFOType.CHAOS_LORENZ.value == "Chaos: Lorenz"
        assert LFOType.CHAOS_ROSSLER.value == "Chaos: Rossler"

    def test_lfo_shapes(self):
        assert len(LFOShape) == 6

    def test_lfo_modes(self):
        assert len(LFOMode) == 3
        assert LFOMode.RETRIG.value == "Retrig"

    def test_lfo_directions(self):
        assert len(LFODirection) == 3


# ── Enums — Voicing ──────────────────────────────────────────────

class TestVoicingEnums:
    def test_voicing_modes(self):
        assert len(VoicingMode) == 3
        expected = {"Poly", "Mono", "Legato"}
        assert {v.value for v in VoicingMode} == expected

    def test_no_mono_retrig(self):
        names = {v.name for v in VoicingMode}
        assert "MONO_RETRIG" not in names

    def test_steal_priorities(self):
        assert len(VoiceStealPriority) == 5


# ── Enums — Arp ──────────────────────────────────────────────────

class TestArpEnums:
    def test_arp_shapes(self):
        assert len(ArpShape) >= 19

    def test_pattern_modes(self):
        assert len(ArpPatternMode) == 8


# ── Enums — Sub / Noise ─────────────────────────────────────────

class TestSubNoiseEnums:
    def test_sub_waveforms(self):
        assert len(SubOscWaveform) == 6
        assert SubOscWaveform.ROUNDED_RECT.value == "Rounded Rect"

    def test_noise_colors(self):
        assert len(NoiseColor) == 4
        assert NoiseColor.GEIGER.value == "Geiger"


# ── Dataclasses ──────────────────────────────────────────────────

class TestWavetableSlot:
    def test_defaults(self):
        wt = WavetableSlot()
        assert wt.name == "Default"
        assert wt.frames == 256
        assert wt.frame_size == 2048


class TestOscillatorConfig:
    def test_defaults(self):
        osc = OscillatorConfig()
        assert osc.enabled is True
        assert osc.level == 0.80
        assert osc.unison_voices == 1
        assert osc.warp_1 == "Off"
        assert osc.warp_2 == "Off"

    def test_unison_blend_default(self):
        """Serum 2 default blend is 75%."""
        osc = OscillatorConfig()
        assert osc.unison_blend == 0.75

    def test_phase_fields(self):
        osc = OscillatorConfig()
        assert osc.phase_memory is False
        assert osc.contiguous_phase is False


class TestSubOscillator:
    def test_defaults(self):
        sub = SubOscillator()
        assert sub.enabled is False
        assert sub.waveform == "Sine"
        assert sub.octave == -1
        assert sub.coarse == 0.0


class TestNoiseOscillator:
    def test_defaults(self):
        noise = NoiseOscillator()
        assert noise.enabled is False
        assert noise.color_mode is None


class TestFilterConfig:
    def test_defaults(self):
        f = FilterConfig()
        assert f.filter_type == "MG Low 24"
        assert f.enabled is True

    def test_serum2_fields(self):
        """Filter should have VAR, PAN, MIX, and drive_clean."""
        f = FilterConfig()
        assert hasattr(f, "var")
        assert hasattr(f, "pan")
        assert hasattr(f, "mix")
        assert hasattr(f, "drive_clean")


class TestEnvelopeConfig:
    def test_defaults(self):
        env = EnvelopeConfig()
        assert env.attack_ms == 1.0
        assert env.sustain == 0.75
        assert env.release_ms == 100.0

    def test_hold_segment(self):
        """Serum 2 envelopes have HOLD (AHDSR)."""
        env = EnvelopeConfig()
        assert hasattr(env, "hold_ms")
        assert env.hold_ms == 0.0

    def test_bpm_sync(self):
        env = EnvelopeConfig()
        assert hasattr(env, "bpm_sync")

    def test_legato_inverted(self):
        env = EnvelopeConfig()
        assert hasattr(env, "legato_inverted")


class TestLFOConfig:
    def test_defaults(self):
        lfo = LFOConfig()
        assert lfo.lfo_type == "Normal"
        assert lfo.mode == "Retrig"
        assert lfo.direction == "Forward"

    def test_rate_10x(self):
        lfo = LFOConfig()
        assert hasattr(lfo, "rate_10x")

    def test_swing(self):
        lfo = LFOConfig()
        assert hasattr(lfo, "swing")


class TestModulationRoute:
    def test_defaults(self):
        mod = ModulationRoute()
        assert mod.source == "LFO 1"
        assert mod.polarity_bipolar is True

    def test_curve_field(self):
        mod = ModulationRoute()
        assert hasattr(mod, "curve")
        assert hasattr(mod, "aux_curve")
        assert hasattr(mod, "output_scale")


class TestEffectSlot:
    def test_defaults(self):
        fx = EffectSlot()
        assert fx.rack == "Main"

    def test_reverb_type_field(self):
        fx = EffectSlot()
        assert hasattr(fx, "reverb_type")
        assert hasattr(fx, "nitrous_mode")

    def test_delay_hq(self):
        fx = EffectSlot()
        assert fx.delay_hq is True


class TestMacroConfig:
    def test_defaults(self):
        m = MacroConfig()
        assert m.label == "Macro 1"


class TestClipSequencer:
    def test_defaults(self):
        clip = ClipSequencerConfig()
        assert clip.enabled is False
        assert clip.active_slot == 1


class TestVoicingConfig:
    def test_defaults(self):
        v = VoicingConfig()
        assert v.mode == "Poly"
        assert v.steal_priority == "Newest"

    def test_portamento_options(self):
        v = VoicingConfig()
        assert hasattr(v, "portamento_curve")
        assert hasattr(v, "portamento_always")
        assert hasattr(v, "portamento_scaled")

    def test_mpe(self):
        v = VoicingConfig()
        assert hasattr(v, "mpe_enabled")


# ── Serum2Patch ──────────────────────────────────────────────────

class TestSerum2Patch:
    def test_has_osc_c(self):
        """Serum 2 has 3 oscillators."""
        patch = Serum2Patch()
        assert hasattr(patch, "osc_c")
        assert patch.osc_c.enabled is False

    def test_has_sub_oscillator(self):
        patch = Serum2Patch()
        assert hasattr(patch, "sub")
        assert isinstance(patch.sub, SubOscillator)

    def test_has_4_envelopes(self):
        patch = Serum2Patch()
        assert hasattr(patch, "env_4")
        assert isinstance(patch.env_4, EnvelopeConfig)

    def test_has_10_lfos(self):
        patch = Serum2Patch()
        assert hasattr(patch, "lfo_10")
        assert isinstance(patch.lfo_10, LFOConfig)

    def test_has_8_macros(self):
        patch = Serum2Patch()
        assert hasattr(patch, "macro_8")
        assert isinstance(patch.macro_8, MacroConfig)

    def test_has_clip_sequencer(self):
        patch = Serum2Patch()
        assert hasattr(patch, "clip")
        assert isinstance(patch.clip, ClipSequencerConfig)

    def test_has_description(self):
        patch = Serum2Patch()
        assert hasattr(patch, "description")

    def test_s1_compatibility(self):
        patch = Serum2Patch()
        assert hasattr(patch, "s1_compatibility")
        assert patch.s1_compatibility is False


# ── Architecture Dict ────────────────────────────────────────────

class TestArchitecture:
    def test_version(self):
        assert SERUM2_ARCHITECTURE["version"] == "2.0.18"

    def test_3_oscillators(self):
        assert SERUM2_ARCHITECTURE["oscillators"]["primary_count"] == 3

    def test_4_envelopes(self):
        assert SERUM2_ARCHITECTURE["modulation"]["envelopes"]["count"] == 4

    def test_10_lfos(self):
        assert SERUM2_ARCHITECTURE["modulation"]["lfos"]["count"] == 10

    def test_64_mod_slots(self):
        assert SERUM2_ARCHITECTURE["modulation"]["matrix"]["max_slots"] == 64

    def test_49_mod_sources(self):
        assert SERUM2_ARCHITECTURE["modulation"]["matrix"]["total_sources"] == 49

    def test_8_macros(self):
        assert SERUM2_ARCHITECTURE["macros"]["count"] == 8

    def test_3_fx_racks(self):
        assert SERUM2_ARCHITECTURE["effects_rack"]["rack_count"] == 3

    def test_5_reverb_types(self):
        assert len(SERUM2_ARCHITECTURE["effects_rack"]["reverb_types"]) == 5

    def test_sub_osc_waveforms(self):
        assert len(SERUM2_ARCHITECTURE["sub_oscillator"]["waveforms"]) == 6

    def test_noise_color_modes(self):
        assert len(SERUM2_ARCHITECTURE["noise_oscillator"]["color_modes"]) == 4

    def test_granular_max_grains(self):
        assert SERUM2_ARCHITECTURE["oscillators"]["granular"]["max_grains"] == 256


# ── Modulation Destinations ─────────────────────────────────────

class TestModulationDestinations:
    def test_osc_c_destinations(self):
        osc_dests = MODULATION_DESTINATIONS["oscillators"]
        c_dests = [d for d in osc_dests if d.startswith("Osc C")]
        assert len(c_dests) >= 11

    def test_envelope_hold(self):
        env_dests = MODULATION_DESTINATIONS["envelopes"]
        holds = [d for d in env_dests if "Hold" in d]
        assert len(holds) == 4

    def test_lfo_10(self):
        lfo_dests = MODULATION_DESTINATIONS["lfos"]
        lfo10 = [d for d in lfo_dests if d.startswith("LFO 10")]
        assert len(lfo10) == 3

    def test_macros_as_destinations(self):
        assert "macros" in MODULATION_DESTINATIONS
        assert len(MODULATION_DESTINATIONS["macros"]) == 8

    def test_filter_var_pan_mix(self):
        filt_dests = MODULATION_DESTINATIONS["filters"]
        assert "Filter 1 Var" in filt_dests
        assert "Filter 1 Pan" in filt_dests
        assert "Filter 1 Mix" in filt_dests


# ── phi_unison_detune ────────────────────────────────────────────

class TestPhiUnisonDetune:
    def test_single_voice(self):
        result = phi_unison_detune(1)
        assert result == [0.0]

    def test_multiple_voices(self):
        result = phi_unison_detune(8)
        assert isinstance(result, list)
        assert len(result) == 8
        assert result == sorted(result)

    def test_symmetric(self):
        result = phi_unison_detune(5)
        assert abs(sum(result)) < 1.0

    def test_zero_voices(self):
        result = phi_unison_detune(0)
        assert result == [0.0]


# ── phi_envelope ─────────────────────────────────────────────────

class TestPhiEnvelope:
    def test_returns_envelope(self):
        env = phi_envelope()
        assert isinstance(env, EnvelopeConfig)

    def test_phi_relationships(self):
        env = phi_envelope(base_attack_ms=5.0)
        assert abs(env.decay_ms - 5.0 * PHI) < 0.1
        assert abs(env.sustain - (1.0 / PHI)) < 0.01

    def test_custom_attack(self):
        env = phi_envelope(base_attack_ms=10.0)
        assert env.attack_ms == 10.0
        assert abs(env.decay_ms - 10.0 * PHI) < 0.1

    def test_hold_zero(self):
        """phi_envelope sets hold to 0."""
        env = phi_envelope()
        assert env.hold_ms == 0.0


# ── phi_filter_cutoff ───────────────────────────────────────────

class TestPhiFilterCutoff:
    def test_returns_list(self):
        cutoffs = phi_filter_cutoff()
        assert isinstance(cutoffs, list)
        assert len(cutoffs) == 8

    def test_phi_ratio(self):
        cutoffs = phi_filter_cutoff(root_hz=100.0, n_steps=4)
        assert len(cutoffs) == 4
        for i in range(1, len(cutoffs)):
            ratio = cutoffs[i] / cutoffs[i - 1]
            assert abs(ratio - PHI) < 0.01

    def test_starts_at_root(self):
        cutoffs = phi_filter_cutoff(root_hz=55.0)
        assert abs(cutoffs[0] - 55.0) < 0.01


# ── fibonacci_lfo_rates ─────────────────────────────────────────

class TestFibonacciLfoRates:
    def test_returns_list(self):
        rates = fibonacci_lfo_rates()
        assert isinstance(rates, list)
        assert len(rates) == 9

    def test_contains_standard_rates(self):
        rates = fibonacci_lfo_rates()
        assert "1/1" in rates
        assert "1/8" in rates


# ── phi_macro_scaling ────────────────────────────────────────────

class TestPhiMacroScaling:
    def test_zero(self):
        assert phi_macro_scaling(0.0) == 0.0

    def test_one(self):
        assert abs(phi_macro_scaling(1.0) - 1.0) < 0.001

    def test_mid_value(self):
        result = phi_macro_scaling(0.5)
        assert 0.0 < result < 1.0
        assert abs(result - 0.5 ** (1.0 / PHI)) < 0.001


# ── phi_fm_ratio ─────────────────────────────────────────────────

class TestPhiFmRatio:
    def test_ratio(self):
        result = phi_fm_ratio(100.0)
        assert abs(result - 100.0 * PHI) < 0.01


# ── fibonacci_wavetable_frames ───────────────────────────────────

class TestFibonacciWavetableFrames:
    def test_returns_list(self):
        frames = fibonacci_wavetable_frames()
        assert isinstance(frames, list)
        assert 256 in frames

    def test_contains_fibonacci(self):
        frames = fibonacci_wavetable_frames()
        for fib in [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]:
            assert fib in frames


# ── phi_effect_mix ───────────────────────────────────────────────

class TestPhiEffectMix:
    def test_default(self):
        mix = phi_effect_mix()
        assert mix == 0.618

    def test_clamped(self):
        mix = phi_effect_mix(depth=2.0)
        assert mix == 1.0

    def test_custom(self):
        mix = phi_effect_mix(depth=0.3)
        assert abs(mix - 0.3) < 0.001


# ── build_dubstep_patches ────────────────────────────────────────

class TestBuildDubstepPatches:
    def test_returns_list(self):
        patches = build_dubstep_patches()
        assert isinstance(patches, list)
        assert len(patches) == 8

    def test_patch_structure(self):
        patches = build_dubstep_patches()
        for patch in patches:
            assert isinstance(patch, dict)
            assert "name" in patch
            assert "osc_a" in patch
            assert "osc_c" in patch
            assert "sub" in patch
            assert "filter_1" in patch
            assert "env_4" in patch
            assert "lfo_10" in patch
            assert "macro_8" in patch
            assert "clip" in patch

    def test_no_fake_effects(self):
        """No patches should reference OTT, Bitcrusher, or Wavefolder."""
        patches = build_dubstep_patches()
        for patch in patches:
            for fx in patch.get("effects", []):
                assert fx["fx_type"] != "OTT"
                assert fx["fx_type"] != "Bitcrusher"
                assert fx["fx_type"] != "Wavefolder"

    def test_weapon_uses_osc_c(self):
        """Weapon patch should use OSC C (3-osc power)."""
        patches = build_dubstep_patches()
        weapon = [p for p in patches if "Weapon" in p["name"]][0]
        assert weapon["osc_c"]["enabled"] is True


# ── build_init_template ─────────────────────────────────────────

class TestBuildInitTemplate:
    def test_returns_dict(self):
        template = build_init_template()
        assert isinstance(template, dict)
        assert "name" in template
        assert "DUBFORGE" in template["name"]

    def test_has_3_oscillators(self):
        template = build_init_template()
        assert "osc_a" in template
        assert "osc_b" in template
        assert "osc_c" in template

    def test_has_8_macros(self):
        template = build_init_template()
        assert "macro_8" in template

    def test_has_clip_sequencer(self):
        template = build_init_template()
        assert "clip" in template
