"""DUBFORGE — Staged Integration Layer

Wires 22+ previously-unused engine modules into forge.py's render.
Each function is a DROP-IN integration hook — forge.py calls these
at the appropriate stage instead of requiring a full refactor.

Phase 1  Methodology:     mood_engine, rco, dojo, chord_progression
Phase 2  Sound Design:    psbs, riddim_engine, wobble_bass, sidechain,
                          song_templates, auto_arranger
Phase 3  Mix Pipeline:    mix_bus, auto_mixer
Phase 4  Quality Loop:    auto_master, reference_analyzer, qa_validator,
                          convolution

Usage from forge.py:
    from engine.stage_integrations import (
        enhance_dna, enhance_bass_palette, build_rco_energy_map,
        apply_section_mix_bus, validate_output, get_reference_insights,
        apply_convolution_reverb,
    )
"""
from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

SR = 48000  # Must match forge.py


# ═══════════════════════════════════════════
#  PHASE 1 — Methodology Integration
# ═══════════════════════════════════════════

def enhance_dna(dna: Any) -> Any:
    """Apply mood engine + RCO energy curves + chord progression to DNA.

    Called right after DNA setup in render_full_track.
    Enriches the DNA object with mood-driven parameter enhancements
    and stores RCO profile/filter curve for the arrangement stage.

    Safe fallback: returns dna unchanged if any module fails.
    """
    mood_profile = _apply_mood(dna)
    _build_rco(dna)
    _ensure_chord_progression(dna)
    dna._mood_profile = mood_profile
    return dna


def _apply_mood(dna: Any):
    """Resolve mood → apply MoodProfile to DNA parameters."""
    try:
        from engine.mood_engine import MOODS, resolve_mood

        mood_name = getattr(dna, 'mood_name', 'aggressive')
        resolved = resolve_mood(mood_name)
        profile = MOODS.get(resolved, MOODS.get('aggressive'))
        if not profile:
            return None

        # Mood scales atmosphere reverb
        ad = getattr(dna, 'atmosphere', None)
        if ad and profile.reverb_amount > 0:
            ad.reverb_decay = max(
                ad.reverb_decay,
                profile.reverb_amount * 3.5,
            )

        # Mood scales bass distortion
        bd = getattr(dna, 'bass', None)
        if bd:
            bd.distortion = max(bd.distortion, profile.distortion * 0.45)

        # Mood scales pad brightness (dark moods → darker pad)
        if ad:
            _dark_factor = 1.0 - profile.darkness * 0.3
            ad.pad_brightness = min(
                ad.pad_brightness,
                ad.pad_brightness * _dark_factor + 0.05,
            )

        print(f"    Mood '{resolved}': energy={profile.energy:.2f} "
              f"darkness={profile.darkness:.2f} "
              f"complexity={profile.complexity:.2f}")
        return profile
    except Exception as e:
        log.debug(f"Mood engine skipped: {e}")
        return None


def _build_rco(dna: Any):
    """Build RCO energy profile + narrative filter curve from DNA."""
    try:
        from engine.rco import RCOProfile, Section as RCOSection

        _section_defaults = {
            'intro':  (0.10, 0.30,   400.0,   800.0),
            'build':  (0.30, 0.80,   800.0,  4000.0),
            'drop':   (0.90, 1.00, 20000.0, 20000.0),
            'break':  (0.20, 0.15, 10000.0,  1000.0),
            'outro':  (0.20, 0.00,  2000.0,   200.0),
        }

        rco_sections = []
        for sec in dna.arrangement:
            key = next((k for k in _section_defaults if k in sec.name), None)
            if key:
                es, ee, fs, fe = _section_defaults[key]
            else:
                es, ee = sec.energy, sec.energy
                fs, fe = 20000.0, 20000.0

            rco_sections.append(RCOSection(
                name=sec.name, bars=sec.bars,
                energy_start=es, energy_end=ee,
                curve="phi", bpm=dna.bpm,
                filter_cutoff_start=fs,
                filter_cutoff_end=fe,
            ))

        rco = RCOProfile(name=dna.name, bpm=dna.bpm, sections=rco_sections)
        rco.compute()

        dna._rco_profile = rco
        dna._rco_filter_curve = rco.narrative_filter_curve()
        dna._rco_energy_map = {
            s.name: (s.energy_start, s.energy_end) for s in rco_sections
        }

        print(f"    RCO: {rco.total_bars} bars, {rco.total_duration_s:.1f}s | "
              f"narrative filter: {len(dna._rco_filter_curve)} points")
    except Exception as e:
        log.debug(f"RCO skipped: {e}")
        dna._rco_profile = None
        dna._rco_filter_curve = []
        dna._rco_energy_map = {}


def _ensure_chord_progression(dna: Any):
    """Ensure lead DNA has a chord progression."""
    try:
        ld = getattr(dna, 'lead', None)
        if ld and not getattr(ld, 'chord_progression', None):
            ld.chord_progression = [0, 5, 2, 4]  # i - VI - III - VII
    except Exception:
        pass


def build_rco_energy_map(dna: Any) -> dict[str, tuple[float, float]]:
    """Return section_name → (energy_start, energy_end) from stored RCO."""
    return getattr(dna, '_rco_energy_map', {})


# ═══════════════════════════════════════════
#  PHASE 2 — Sound Architecture Integration
# ═══════════════════════════════════════════

def enhance_bass_palette(
    bass_arsenal: list,
    dna: Any,
    sr: int,
    beat: float,
    freq_f2: float,
) -> list:
    """Append riddim + wobble bass variants to the existing bass arsenal.

    Called after the 7 inline bass types are built in render_full_track.
    Adds up to 6 extra bass sounds for wider rotation.
    """
    bass_arsenal = _add_riddim_variants(bass_arsenal, dna, sr, beat, freq_f2)
    bass_arsenal = _add_wobble_variants(bass_arsenal, dna, sr, beat, freq_f2)
    return bass_arsenal


def _add_riddim_variants(bass_arsenal, dna, sr, beat, freq_f2):
    try:
        from engine.riddim_engine import (
            generate_riddim_minimal, generate_riddim_heavy,
            generate_riddim_bounce, RiddimPreset,
        )

        bd = dna.bass
        for gen_fn, label, dist_scale, gap in [
            (generate_riddim_minimal, "minimal", 0.5, 0.30),
            (generate_riddim_heavy,   "heavy",   1.0, 0.20),
            (generate_riddim_bounce,  "bounce",  0.7, 0.25),
        ]:
            sig = gen_fn(RiddimPreset(
                name=f"Riddim_{label}", riddim_type=label,
                frequency=freq_f2, duration_s=beat * 2,
                gap_ratio=gap, attack_s=0.003, release_s=0.08,
                distortion=bd.distortion * dist_scale,
                bpm=dna.bpm, depth=0.8,
            ), sample_rate=sr)
            bass_arsenal.append(
                sig.tolist() if isinstance(sig, np.ndarray) else list(sig)
            )

        print("    +3 riddim variants (minimal/heavy/bounce)")
    except Exception as e:
        log.debug(f"Riddim engine skipped: {e}")
    return bass_arsenal


def _add_wobble_variants(bass_arsenal, dna, sr, beat, freq_f2):
    try:
        from engine.wobble_bass import (
            synthesize_classic_wobble, synthesize_growl_wobble,
            synthesize_vowel_wobble, WobblePreset,
        )

        bd = dna.bass
        for gen_fn, label, lfo_mult, filt_mult, dist_scale in [
            (synthesize_classic_wobble, "classic", 1.0, 1.0, 0.4),
            (synthesize_growl_wobble,   "growl",   1.5, 0.8, 1.0),
            (synthesize_vowel_wobble,   "vowel",   0.8, 1.0, 0.3),
        ]:
            sig = gen_fn(WobblePreset(
                name=f"Wobble_{label}", wobble_type=label,
                frequency=freq_f2, duration_s=beat * 2,
                lfo_rate=bd.lfo_rate * lfo_mult,
                lfo_depth=bd.lfo_depth,
                filter_cutoff=bd.filter_cutoff * filt_mult,
                resonance=0.5,
                distortion=bd.distortion * dist_scale,
                sub_mix=0.3,
            ), sample_rate=sr)
            bass_arsenal.append(
                sig.tolist() if isinstance(sig, np.ndarray) else list(sig)
            )

        print("    +3 wobble variants (classic/growl/vowel)")
    except Exception as e:
        log.debug(f"Wobble bass skipped: {e}")
    return bass_arsenal


def get_psbs_info(root_hz: float):
    """Load PSBS layer configuration for bass frequency separation.

    Returns dict with psbs preset, crossover frequencies, singer/band layers,
    or None if module unavailable.
    """
    try:
        from engine.psbs import default_psbs, phi_crossovers

        psbs = default_psbs(root_hz=root_hz, tuning=432.0)
        crossovers = phi_crossovers(root_hz, n_bands=5)
        singer = psbs.get_singer()
        band = psbs.get_band()

        print(f"    PSBS: {len(psbs.layers)} layers | "
              f"singer={singer.name if singer else 'none'} | "
              f"xover={[f'{x:.0f}' for x in crossovers]}Hz")
        return {
            'psbs': psbs,
            'crossovers': crossovers,
            'singer': singer,
            'band': band,
        }
    except Exception as e:
        log.debug(f"PSBS skipped: {e}")
        return None


def get_sidechain_envelope(dna: Any, duration_s: float, sr: int = SR):
    """Generate phi-curve sidechain pump envelope.

    Returns 1-D numpy array or None.
    """
    try:
        from engine.sidechain import generate_phi_curve_envelope, SidechainPreset

        preset = SidechainPreset(
            name="ForgeChain", shape="phi_curve",
            attack_ms=0.5, release_ms=150.0,
            depth=dna.mix.sidechain_depth,
            hold_ms=10.0, curve_exp=2.0,
            retrigger_rate=1.0, mix=1.0,
            bpm=float(dna.bpm),
        )
        return generate_phi_curve_envelope(preset, duration_s, sample_rate=sr)
    except Exception as e:
        log.debug(f"Sidechain module skipped: {e}")
        return None


def get_song_template(dna: Any):
    """Look up a matching song template for the DNA style."""
    try:
        from engine.song_templates import weapon_standard_template

        template = weapon_standard_template()
        print(f"    Template: {template.name} ({template.total_bars} bars)")
        return template
    except Exception as e:
        log.debug(f"Song template skipped: {e}")
        return None


def get_auto_arranger_template(dna: Any):
    """Load arrangement template from auto_arranger."""
    try:
        from engine.auto_arranger import ARRANGEMENT_TEMPLATES

        style = getattr(dna, 'style', 'dubstep')
        template_name = 'standard'
        for key in ARRANGEMENT_TEMPLATES:
            if style.lower() in key.lower():
                template_name = key
                break

        arr = ARRANGEMENT_TEMPLATES.get(template_name)
        if arr:
            print(f"    Arrangement template: {template_name}")
        return arr
    except Exception as e:
        log.debug(f"Auto arranger skipped: {e}")
        return None


# ═══════════════════════════════════════════
#  PHASE 3 — Mix Pipeline Integration
# ═══════════════════════════════════════════

def apply_section_mix_bus(
    L_section: list[float],
    R_section: list[float],
    section_name: str,
    energy_start: float,
    energy_end: float,
    sr: int = SR,
) -> tuple[list[float], list[float]]:
    """Process section audio through the mix bus.

    Falls back to unprocessed on error.
    """
    try:
        from engine.mix_bus import process_mix_bus, MixBusConfig

        config = MixBusConfig(
            enable_freq_stereo=True,
            enable_parallel_comp=True,
            enable_energy_curves=True,
            parallel_comp_mix=0.15,
        )

        bus_input = np.column_stack([
            np.array(L_section, dtype=np.float64),
            np.array(R_section, dtype=np.float64),
        ])

        result = process_mix_bus(
            bus_input, section_name,
            energy_start, energy_end,
            config=config, sr=sr,
        )

        if isinstance(result, tuple) and len(result) == 2:
            left, right = result
            return (
                left.tolist() if isinstance(left, np.ndarray) else list(left),
                right.tolist() if isinstance(right, np.ndarray) else list(right),
            )
        if isinstance(result, np.ndarray) and result.ndim == 2:
            return result[:, 0].tolist(), result[:, 1].tolist()
        return L_section, R_section
    except Exception as e:
        log.debug(f"Mix bus skipped for {section_name}: {e}")
        return L_section, R_section


def auto_gain_stage_tracks(tracks_dict: dict[str, list[float]]):
    """Run auto gain staging on named stems.

    Returns GainStagingResult or None.
    """
    try:
        from engine.auto_mixer import auto_gain_stage, TrackInfo

        _element_map = {
            'kick': 'kick', 'snare': 'snare', 'drum': 'kick',
            'sub': 'sub_bass', 'bass': 'bass', 'lead': 'lead',
            'pad': 'pad', 'vocal': 'vocal', 'chop': 'vocal',
            'hat': 'hihat', 'fx': 'fx', 'noise': 'fx',
        }

        tracks = []
        for name, signal in tracks_dict.items():
            et = 'unknown'
            for key, val in _element_map.items():
                if key in name.lower():
                    et = val
                    break
            tracks.append(TrackInfo(name=name, signal=signal, element_type=et))

        result = auto_gain_stage(tracks)
        print(f"    Auto-mixer: master={result.master_gain_db:.1f}dB "
              f"headroom={result.headroom_db:.1f}dB peak={result.peak_db:.1f}dB")
        return result
    except Exception as e:
        log.debug(f"Auto gain staging skipped: {e}")
        return None


# ═══════════════════════════════════════════
#  PHASE 4 — Quality Loop Integration
# ═══════════════════════════════════════════

def apply_auto_master(signal: list[float], dna: Any, sr: int = SR):
    """Run auto_master as supplementary analysis.

    Returns MasterResult or None.
    """
    try:
        from engine.auto_master import auto_master, MasterSettings

        settings = MasterSettings(
            target_lufs=dna.mix.target_lufs,
            ceiling_db=dna.mix.ceiling_db,
            bass_boost_db=dna.mix.eq_low_boost,
            air_boost_db=dna.mix.eq_high_boost,
        )

        result = auto_master(signal, settings, sample_rate=sr)
        print(f"    Auto-master: {result.input_lufs:.1f} → "
              f"{result.output_lufs:.1f} LUFS, peak={result.peak_db:.1f}dB")
        return result
    except Exception as e:
        log.debug(f"Auto-master skipped: {e}")
        return None


def validate_output(L: list[float], R: list[float], sr: int = SR) -> str:
    """Run QA validation gates on rendered stereo output.

    Returns summary string.
    """
    try:
        from engine.qa_validator import validate_render

        result = validate_render(
            np.array(L, dtype=np.float64),
            np.array(R, dtype=np.float64),
            sr=sr,
        )

        status = "PASS ✓" if result.passed else "FAIL ✗"
        print(f"\n  🔍 QA Validation: {status}")
        for gate in result.gates:
            mark = "✓" if gate.passed else "✗"
            print(f"     {mark} {gate.name}: {gate.value:.4f} "
                  f"(threshold: {gate.threshold:.4f})")

        return result.summary()
    except Exception as e:
        msg = f"QA validation skipped: {e}"
        log.debug(msg)
        return msg


def apply_convolution_reverb(
    signal: np.ndarray,
    room_type: str = "plate",
    mix: float = 0.2,
    sr: int = SR,
) -> np.ndarray:
    """Apply convolution reverb using generated IR."""
    try:
        from engine.convolution import (
            generate_plate_ir, generate_room_ir, ConvolutionPreset,
        )

        conv_type = "plate_ir" if room_type == "plate" else "room_ir"
        preset = ConvolutionPreset(name=f"Forge_{room_type}", conv_type=conv_type)

        ir = (generate_plate_ir(preset, sample_rate=sr) if room_type == "plate"
              else generate_room_ir(preset, sample_rate=sr))

        if ir is not None and len(ir) > 0:
            convolved = np.convolve(signal, ir)[:len(signal)]
            return signal * (1.0 - mix) + convolved * mix
        return signal
    except Exception as e:
        log.debug(f"Convolution reverb skipped: {e}")
        return signal


def get_reference_insights(dna: Any):
    """Look up reference track profiles matching the DNA style."""
    try:
        from engine.reference_analyzer import REFERENCE_PROFILES

        if not REFERENCE_PROFILES:
            return None

        style = getattr(dna, 'style', 'dubstep').lower()
        for name, profile in REFERENCE_PROFILES.items():
            if style in name.lower():
                print(f"    Reference match: {name}")
                return profile
        return None
    except Exception as e:
        log.debug(f"Reference analyzer skipped: {e}")
        return None


def get_dojo_belt_info():
    """Get current Dojo belt status for production context."""
    try:
        from engine.dojo import BELT_SYSTEM, BeltRank
        return {'system': BELT_SYSTEM, 'ranks': list(BeltRank)}
    except Exception as e:
        log.debug(f"Dojo belt info skipped: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
#  SPRINT 1 (P0) — 14 modules for render quality improvement
# ═══════════════════════════════════════════════════════════════

# ── Phase 1: DNA Validation + Tuning + Arrangement ───────────

def validate_tuning_432(freq_dict: dict, reference_freq: float = 432.0):
    """Verify FREQ dict aligns with 432Hz tuning via TuningSystem.

    Analysis only — logs tuning status. Returns freq_dict unchanged.
    """
    try:
        from engine.tuning_system import TuningSystem
        ts = TuningSystem(reference_freq=reference_freq)
        a4 = ts.equal_temperament("A", 4)
        drift = ts.cents_between(a4, reference_freq)
        # Spot-check F2 (expected ~87.31 Hz in 432Hz tuning)
        f2_expected = ts.equal_temperament("F", 2)
        f2_actual = freq_dict.get("F2", 0.0)
        f2_drift = ts.cents_between(f2_actual, f2_expected) if f2_actual > 0 else 999
        if abs(drift) < 1.0 and abs(f2_drift) < 5.0:
            print(f"  ✓ Tuning: 432Hz verified (A4 drift={drift:.2f}¢, "
                  f"F2 drift={f2_drift:.2f}¢)")
        else:
            print(f"  ⚠ Tuning: A4 drift={drift:.2f}¢, F2 drift={f2_drift:.2f}¢ "
                  f"— may need recalibration")
        return freq_dict
    except Exception as exc:
        log.debug("tuning_system integration skipped: %s", exc)
        return freq_dict


def get_arrangement_template(dna: Any):
    """Build Dojo-aligned arrangement template for energy logging.

    Returns ArrangementTemplate or None. Does not alter render structure.
    """
    try:
        from engine.arrangement_sequencer import (
            build_arrangement, arrangement_energy_curve,
            golden_section_check,
        )
        style = getattr(dna, 'style', 'dubstep')
        template_map = {
            'emotional': 'emotive', 'melodic': 'emotive',
            'hybrid': 'hybrid',
        }
        template_type = template_map.get(style, 'weapon')
        key_name = f"{getattr(dna, 'key', 'F')}m"
        template = build_arrangement(
            template_type, bpm=float(dna.bpm), key=key_name)
        energy = arrangement_energy_curve(template)
        golden = golden_section_check(template)
        print(f"  ✓ Arrangement: {template.name} ({template_type}) — "
              f"{len(template.sections)} sections, "
              f"golden={golden.get('is_golden', False)}")
        return template
    except Exception as exc:
        log.debug("arrangement_sequencer integration skipped: %s", exc)
        return None


# ── Phase 2: Enhanced Synthesis ──────────────────────────────

def enhance_sub_bass(sub_signal: list, dna: Any, freq_f1: float,
                     sr: int = SR) -> list:
    """Enhance sub using sub_bass module's multi-type synthesis.

    Blends a harmonic sub variant into the existing sub signal for
    richer low-end. Returns enhanced sub or original on failure.
    """
    try:
        from engine.sub_bass import SubBassPreset, synthesize_sub_bass
        bd = getattr(dna, 'bass', None)
        if bd is None:
            return sub_signal
        beat = 60.0 / float(dna.bpm)
        # Synthesize a harmonic sub (adds octave + fifth content)
        harmonic_preset = SubBassPreset(
            name="HarmonicSub", sub_type="harmonic",
            frequency=freq_f1, duration_s=beat * 2,
            attack_s=0.002, release_s=0.1,
            sub_weight=getattr(bd, 'sub_weight', 0.7),
            harmonic_mix=0.3,
        )
        harmonic_sub = synthesize_sub_bass(harmonic_preset, sample_rate=sr)
        h_list = harmonic_sub.tolist()
        # Blend: 85% original + 15% harmonic for subtle enhancement
        out_len = min(len(sub_signal), len(h_list))
        enhanced = [0.0] * len(sub_signal)
        for i in range(out_len):
            enhanced[i] = sub_signal[i] * 0.85 + h_list[i] * 0.15
        for i in range(out_len, len(sub_signal)):
            enhanced[i] = sub_signal[i]
        print(f"  ✓ Sub: harmonic enhancement blended (15% mix)")
        return enhanced
    except Exception as exc:
        log.debug("sub_bass integration skipped: %s", exc)
        return sub_signal


def enhance_chord_voicings(chord_notes_l: dict, chord_notes_r: dict,
                           dna: Any, root_freq: float,
                           sr: int = SR) -> tuple[dict, dict]:
    """Add chord_pad module voicings alongside existing supersaw chords.

    Synthesizes minor7 pad variants and blends into chord dicts.
    Returns (chord_notes_l, chord_notes_r) enhanced or unchanged.
    """
    try:
        from engine.chord_pad import ChordPadPreset, synthesize_chord_pad
        ld = getattr(dna, 'lead', None)
        if ld is None:
            return chord_notes_l, chord_notes_r
        beat = 60.0 / float(dna.bpm)
        prog = getattr(ld, 'chord_progression', [0, 5, 2, 4])
        added = 0
        for deg in set(prog):
            if deg in chord_notes_l:
                # Synthesize a minor7 pad and blend 20% into existing chord
                from engine.config_loader import A4_432
                # Approximate frequency from scale degree
                semitones = [0, 2, 3, 5, 7, 8, 10]  # natural minor
                semi = semitones[deg % 7]
                freq = root_freq * (2.0 ** (semi / 12.0))
                preset = ChordPadPreset(
                    name=f"Pad_{deg}", chord_type="minor7",
                    root_freq=freq, duration_s=beat * 3,
                    detune_cents=12.0,
                    brightness=getattr(ld, 'brightness', 0.5),
                    warmth=0.6, stereo_width=0.7,
                    reverb_amount=0.2,
                )
                pad_np = synthesize_chord_pad(preset, sample_rate=sr)
                pad_list = pad_np.tolist()
                # Blend into L channel (pad is mono, slight different mix for R)
                existing_l = chord_notes_l[deg]
                mix_len = min(len(existing_l), len(pad_list))
                for i in range(mix_len):
                    existing_l[i] = existing_l[i] * 0.80 + pad_list[i] * 0.20
                if deg in chord_notes_r:
                    existing_r = chord_notes_r[deg]
                    mix_len_r = min(len(existing_r), len(pad_list))
                    for i in range(mix_len_r):
                        existing_r[i] = existing_r[i] * 0.80 + pad_list[i] * 0.20
                added += 1
        if added > 0:
            print(f"  ✓ Chords: minor7 pad layer blended into {added} degrees")
        return chord_notes_l, chord_notes_r
    except Exception as exc:
        log.debug("chord_pad integration skipped: %s", exc)
        return chord_notes_l, chord_notes_r


def check_drum_pipeline(dna: Any, sr: int = SR):
    """Validate drum pipeline readiness (partial module — status only).

    Does not replace inline drum rendering. Logs readiness status.
    """
    try:
        from engine.drum_pipeline import DrumPipeline
        dp = DrumPipeline()
        # Check that pipeline initializes without error
        print(f"  ✓ DrumPipeline: initialized (groove + dynamics ready)")
        return True
    except Exception as exc:
        log.debug("drum_pipeline check skipped: %s", exc)
        return False


def check_midbass_pipeline(dna: Any, sr: int = SR):
    """Validate midbass pipeline readiness (partial module — status only).

    Does not replace inline bass rendering. Logs readiness status.
    """
    try:
        from engine.midbass_pipeline import MidBassPipeline
        mp = MidBassPipeline()
        print(f"  ✓ MidBassPipeline: initialized (ready for Sprint 2)")
        return True
    except Exception as exc:
        log.debug("midbass_pipeline check skipped: %s", exc)
        return False


# ── Phase 2-3: Stem Cleanup ─────────────────────────────────

def clean_dc_offset(L: list, R: list, sr: int = SR) -> tuple[list, list]:
    """Remove DC offset from L/R mix via DCRemover before mastering.

    Returns cleaned (L, R) or originals on failure.
    """
    try:
        from engine.dc_remover import DCRemover
        dc = DCRemover(sample_rate=sr)
        dc_l = dc.detect_dc(L)
        dc_r = dc.detect_dc(R)
        if abs(dc_l) > 0.001 or abs(dc_r) > 0.001:
            L_clean = dc.remove_highpass(L, cutoff=5.0)
            R_clean = dc.remove_highpass(R, cutoff=5.0)
            print(f"  ✓ DC removal: L={dc_l:+.4f} R={dc_r:+.4f} → cleaned")
            return L_clean, R_clean
        else:
            print(f"  ✓ DC offset: negligible (L={dc_l:+.5f} R={dc_r:+.5f})")
            return L, R
    except Exception as exc:
        log.debug("dc_remover integration skipped: %s", exc)
        return L, R


# ── Phase 3: Mix Analysis ───────────────────────────────────

def analyze_mix_spectrum(L: list, R: list, sr: int = SR) -> dict | None:
    """FrequencyAnalyzer Tetris Board — spectral balance of pre-master mix.

    Returns SpectralFeatures dict or None. Does not alter audio.
    """
    try:
        from engine.frequency_analyzer import FrequencyAnalyzer
        fa = FrequencyAnalyzer(sample_rate=sr, fft_size=4096)
        # Analyze mid signal (L+R)/2
        mid = [(L[i] + R[i]) * 0.5 for i in range(min(len(L), len(R)))]
        features = fa.analyze_spectrum(mid)
        bands = features.band_energy
        print(f"  ✓ Tetris Board: Sub={bands.get('sub', 0):.1%} "
              f"Bass={bands.get('bass', 0):.1%} "
              f"LMid={bands.get('low_mid', 0):.1%} "
              f"Mid={bands.get('mid', 0):.1%} "
              f"HMid={bands.get('high_mid', 0):.1%} "
              f"High={bands.get('high', 0):.1%}")
        return features.to_dict() if hasattr(features, 'to_dict') else bands
    except Exception as exc:
        log.debug("frequency_analyzer integration skipped: %s", exc)
        return None


# ── Phase 4: Mastering + QA ─────────────────────────────────

def normalize_phi_master(master_L: list, master_R: list,
                         sr: int = SR) -> tuple[list, list]:
    """Apply phi-weighted normalization via AudioNormalizer.

    Ensures peak aligns to phi-derived target. Returns (L, R).
    """
    try:
        from engine.normalizer import AudioNormalizer
        norm = AudioNormalizer(sample_rate=sr)
        result_l = norm.normalize_phi(master_L, target_db=-0.3)
        result_r = norm.normalize_phi(master_R, target_db=-0.3)
        print(f"  ✓ Phi normalize: L gain={result_l.gain_db:+.2f}dB "
              f"R gain={result_r.gain_db:+.2f}dB")
        return result_l.samples, result_r.samples
    except Exception as exc:
        log.debug("normalizer phi integration skipped: %s", exc)
        return master_L, master_R


def analyze_phi_coherence(master_L: list, master_R: list,
                          sr: int = SR) -> float:
    """Score phi alignment of mastered output via PhiAnalyzer.

    Returns composite phi score (0-1) or 0.0 on failure.
    """
    try:
        from engine.phi_analyzer import analyze_phi_coherence as _phi_analyze
        mid = np.array([(master_L[i] + master_R[i]) * 0.5
                        for i in range(min(len(master_L), len(master_R)))],
                       dtype=np.float64)
        score = _phi_analyze(mid)
        print(f"  ✓ Phi coherence: {score.composite:.4f} "
              f"(harmonic={score.harmonic_phi:.3f} "
              f"temporal={score.temporal_phi:.3f} "
              f"spectral={score.spectral_decay:.3f})")
        return score.composite
    except Exception as exc:
        log.debug("phi_analyzer integration skipped: %s", exc)
        return 0.0


def run_audio_analysis(wav_path: str, sr: int = SR) -> dict | None:
    """Full AudioAnalyzer report on mastered WAV.

    Returns AnalysisReport dict or None. Does not alter audio.
    """
    try:
        from engine.audio_analyzer import AudioAnalyzer
        aa = AudioAnalyzer(sample_rate=sr)
        report = aa.run_full_analysis(wav_path)
        wf = report.waveform
        sp = report.spectral
        print(f"  ✓ Analysis: peak={wf.peak_db:.1f}dB rms={wf.rms_db:.1f}dB "
              f"crest={wf.crest_factor:.1f} "
              f"centroid={sp.spectral_centroid:.0f}Hz")
        return {
            'peak_db': wf.peak_db, 'rms_db': wf.rms_db,
            'crest_factor': wf.crest_factor,
            'spectral_centroid': sp.spectral_centroid,
            'phi_alignment': report.phi_alignment,
        }
    except Exception as exc:
        log.debug("audio_analyzer integration skipped: %s", exc)
        return None


def validate_key_consistency(wav_path: str, dna: Any,
                             sr: int = SR) -> dict | None:
    """Detect key from mastered WAV and compare with DNA declaration.

    Returns KeyResult dict or None. Does not alter audio.
    """
    try:
        from engine.key_detector import KeyDetector
        from engine.audio_analyzer import AudioAnalyzer
        aa = AudioAnalyzer(sample_rate=sr)
        samples = aa.read_wav(wav_path)
        kd = KeyDetector(sample_rate=sr)
        result = kd.detect_key(samples)
        dna_key = getattr(dna, 'key', 'F')
        match = result.key.upper().replace('#', '').replace('B', '') == \
            dna_key.upper().replace('#', '').replace('B', '')
        if match:
            print(f"  ✓ Key: {result.key} {result.mode} "
                  f"(confidence={result.confidence:.2f}) — matches DNA")
        else:
            print(f"  ⚠ Key: detected {result.key} {result.mode} "
                  f"vs DNA {dna_key} (confidence={result.confidence:.2f})")
        return {'key': result.key, 'mode': result.mode,
                'confidence': result.confidence, 'matches_dna': match}
    except Exception as exc:
        log.debug("key_detector integration skipped: %s", exc)
        return None


def compare_to_reference(wav_path: str) -> dict | None:
    """Compare mastered output to reference library standard.

    Returns ComparisonResult dict or None.
    """
    try:
        from engine.reference_library import ReferenceLibrary
        rl = ReferenceLibrary()
        result = rl.compare(wav_path)
        print(f"  ✓ Reference: score={result.overall_score:.0f}/100 "
              f"issues={len(result.issues)} strengths={len(result.strengths)}")
        if result.issues:
            for issue in result.issues[:3]:
                print(f"    ⚠ {issue}")
        if result.strengths:
            for strength in result.strengths[:2]:
                print(f"    ★ {strength}")
        return {'overall_score': result.overall_score,
                'issues': result.issues, 'strengths': result.strengths}
    except Exception as exc:
        log.debug("reference_library integration skipped: %s", exc)
        return None


def run_fibonacci_quality_check(wav_path: str, dna: Any) -> dict | None:
    """Lightweight Fibonacci feedback quality check on final output.

    Runs analysis + target comparison without correction loop.
    Returns quality summary dict or None.
    """
    try:
        from engine.fibonacci_feedback import (
            run_analysis, compare_to_targets,
        )
        analysis = run_analysis(wav_path)
        failures = compare_to_targets(analysis)
        n_pass = 0
        n_fail = len(failures)
        # Count metrics that passed (total standard metrics minus failures)
        n_pass = max(0, 12 - n_fail)  # ~12 standard metrics
        grade = "PASS" if n_fail <= 2 else "NEEDS WORK" if n_fail <= 5 else "FAIL"
        print(f"  ✓ Fibonacci QA: {grade} ({n_pass} pass / {n_fail} fail)")
        if failures:
            for f in failures[:3]:
                print(f"    ⚠ {f.metric_name}: {f.current_value:.3f} "
                      f"(target {f.target_min:.3f}–{f.target_max:.3f})")
        return {'grade': grade, 'pass_count': n_pass,
                'fail_count': n_fail, 'failures': [
                    {'metric': f.metric_name, 'value': f.current_value}
                    for f in failures[:5]]}
    except Exception as exc:
        log.debug("fibonacci_feedback integration skipped: %s", exc)
        return None


# ═══════════════════════════════════════════
#  SPRINT 2 — P1 modules (24)
# ═══════════════════════════════════════════

# ── Session / Memory ──────────────────────────────

def begin_render_session(dna: Any) -> Any:
    """Start a MemoryEngine session for this render.

    Returns the MemoryEngine instance (or None) so forge.py can
    log_event / register_asset during the render.
    """
    try:
        from engine.memory import MemoryEngine
        mem = MemoryEngine()
        sid = mem.begin_session(notes=f"Render: {getattr(dna, 'name', 'untitled')}")
        print(f"  ✓ memory: session {sid[:8]}… started")
        return mem
    except Exception as exc:
        log.debug("memory begin_session skipped: %s", exc)
        return None


def end_render_session(mem: Any, out_path: str = "") -> dict | None:
    """Close the MemoryEngine session and return summary."""
    if mem is None:
        return None
    try:
        summary = mem.end_session(notes=f"Output: {out_path}")
        print(f"  ✓ memory: session ended — {summary.get('event_count', 0)} events logged")
        return summary
    except Exception as exc:
        log.debug("memory end_session skipped: %s", exc)
        return None


def get_lessons_adjustments(dna: Any) -> list:
    """Retrieve pre-render adjustments from past session lessons."""
    try:
        from engine.lessons_learned import LessonsLearned
        ll = LessonsLearned()
        adjustments = ll.get_pre_adjustments(style=getattr(dna, 'style', 'dubstep'))
        if adjustments:
            print(f"  ✓ lessons_learned: {len(adjustments)} pre-adjustments loaded")
        return adjustments
    except Exception as exc:
        log.debug("lessons_learned pre-adjustments skipped: %s", exc)
        return []


def record_render_lessons(dna: Any, session: Any = None) -> None:
    """Record this session's outcomes into the lessons database."""
    try:
        from engine.lessons_learned import LessonsLearned
        ll = LessonsLearned()
        ll.record_session(session)
        print("  ✓ lessons_learned: session recorded")
    except Exception as exc:
        log.debug("lessons_learned record_session skipped: %s", exc)


def get_evolution_preset(dna: Any) -> dict | None:
    """Run parameter-drift evolution tracker and return best params."""
    try:
        from engine.evolution_engine import EvolutionPreset, track_param_drift
        preset = EvolutionPreset(
            name=getattr(dna, 'name', 'render'),
            tracker_type="param_drift",
            generations=5,
            mutation_rate=0.1,
            phi_weight=0.618,
        )
        evo_log = track_param_drift(preset)
        best = evo_log.best_entry()
        if best:
            print(f"  ✓ evolution_engine: best score={best.score:.3f} "
                  f"over {len(evo_log.entries)} generations")
            return best.params
        return None
    except Exception as exc:
        log.debug("evolution_engine skipped: %s", exc)
        return None


def create_session_logger(dna: Any) -> Any:
    """Create a SessionLogger instance for this render."""
    try:
        from engine.session_logger import SessionLogger
        name = getattr(dna, 'name', 'session')
        logger = SessionLogger(session_name=name)
        logger.milestone(f"Render started: {name}")
        return logger
    except Exception as exc:
        log.debug("session_logger skipped: %s", exc)
        return None


def log_milestone(logger: Any, message: str, **data) -> None:
    """Log a milestone to the SessionLogger if available."""
    if logger is None:
        return
    try:
        logger.milestone(message, **data)
    except Exception:
        pass


# ── Melody / Harmony ─────────────────────────────

def generate_markov_melody(dna: Any, root_freq: float, sr: int = 48000) -> list | None:
    """Generate a Markov-chain melody based on DNA key/scale.

    Returns rendered audio (list[float]) or None.
    """
    try:
        from engine.markov_melody import MarkovMelody, render_melody
        key = getattr(dna, 'key', 'F')
        scale = getattr(dna, 'scale', 'minor')
        seed = hash(getattr(dna, 'name', '')) & 0xFFFF
        mm = MarkovMelody(key=key, scale=scale, octave=4, seed=seed)
        melody = mm.generate(n_notes=16, rhythm_complexity=0.5)
        rendered = render_melody(melody, sample_rate=sr)
        print(f"  ✓ markov_melody: {len(melody.notes)} notes, "
              f"{melody.duration_s:.1f}s in {key} {scale}")
        return rendered
    except Exception as exc:
        log.debug("markov_melody skipped: %s", exc)
        return None


def add_trance_arp_layer(dna: Any, root_semitone: int = 0) -> list | None:
    """Generate a Fibonacci arp pattern as MIDI data.

    Returns list of MIDI note dicts or None.
    """
    try:
        from engine.trance_arp import fibonacci_rise_pattern, pattern_to_midi_data
        bpm = getattr(dna, 'bpm', 150)
        pattern = fibonacci_rise_pattern(root_semitone=root_semitone)
        midi_data = pattern_to_midi_data(pattern, bpm=bpm, root_note=60)
        print(f"  ✓ trance_arp: Fibonacci rise — {pattern.steps} steps, "
              f"{len(midi_data)} MIDI events")
        return midi_data
    except Exception as exc:
        log.debug("trance_arp skipped: %s", exc)
        return None


# ── Bass Processing ──────────────────────────────

def apply_wave_folder_bass(bass_list: list, dna: Any) -> list:
    """Apply phi-based wave folding to bass sounds."""
    try:
        from engine.wave_folder import process_signal, WaveFolderPatch
        bd = getattr(dna, 'bass', None)
        amount = getattr(bd, 'wavefold_thresh', 2.0) if bd else 2.0
        patch = WaveFolderPatch(
            name="PhiBass", fold_amount=amount,
            pre_gain=1.2, post_gain=0.8, mix=0.4,
        )
        result = []
        for i, bass in enumerate(bass_list):
            folded = process_signal(bass, patch, algorithm="phi")
            result.append(folded)
        print(f"  ✓ wave_folder: phi-folded {len(result)} bass sounds "
              f"@ amount={amount:.2f}")
        return result
    except Exception as exc:
        log.debug("wave_folder skipped: %s", exc)
        return bass_list


def apply_ring_mod_bass(bass_list: list, dna: Any,
                        root_freq: float, sr: int = 48000) -> list:
    """Apply ring modulation to bass for metallic character."""
    try:
        from engine.ring_mod import ring_modulate, RingModPatch
        carrier = root_freq * 1.618  # phi ratio carrier
        patch = RingModPatch(
            name="PhiRing", carrier_freq=carrier,
            carrier_type="sine", mod_depth=0.3, mix=0.25,
            post_gain=0.85,
        )
        result = []
        for bass in bass_list:
            modded = ring_modulate(bass, patch, sample_rate=sr)
            result.append(modded)
        print(f"  ✓ ring_mod: phi carrier={carrier:.1f}Hz on {len(result)} basses")
        return result
    except Exception as exc:
        log.debug("ring_mod skipped: %s", exc)
        return bass_list


def add_harmonic_enrichment(signal: list, freq: float,
                            sr: int = 48000) -> dict | None:
    """Generate a harmonic spectrum analysis for enrichment decisions.

    Returns HarmonicSpectrum info dict, does not modify signal.
    """
    try:
        from engine.harmonic_gen import HarmonicGenerator
        hg = HarmonicGenerator(sample_rate=sr)
        spectrum = hg.phi_harmonics(fundamental=freq, count=12)
        print(f"  ✓ harmonic_gen: {spectrum.partial_count} phi-harmonics "
              f"from {freq:.1f}Hz")
        return spectrum.to_dict()
    except Exception as exc:
        log.debug("harmonic_gen skipped: %s", exc)
        return None


# ── Atmosphere ───────────────────────────────────

def add_ambient_textures(dna: Any, sr: int = 48000,
                         bar: float = 2.0) -> list | None:
    """Synthesize ambient textures based on DNA atmosphere settings.

    Returns a mono texture signal or None.
    """
    try:
        from engine.ambient_texture import (
            synthesize_rain, synthesize_space, TexturePreset,
        )
        ad = getattr(dna, 'atmosphere', None)
        brightness = getattr(ad, 'pad_brightness', 0.5) if ad else 0.5
        preset = TexturePreset(
            name="Atmos", texture_type="space",
            duration_s=bar * 8,
            brightness=brightness, density=0.4, depth=0.6,
        )
        tex = synthesize_space(preset, sample_rate=sr)
        tex_list = tex.tolist() if hasattr(tex, 'tolist') else list(tex)
        print(f"  ✓ ambient_texture: space texture — {len(tex_list)/sr:.1f}s, "
              f"brightness={brightness:.2f}")
        return tex_list
    except Exception as exc:
        log.debug("ambient_texture skipped: %s", exc)
        return None


# ── Mixing / Routing ─────────────────────────────

def apply_spectral_gate_mix(L: list, R: list,
                            sr: int = 48000) -> tuple:
    """Multi-band spectral gate on the stereo bus before mastering."""
    try:
        from engine.spectral_gate import SpectralGate
        sg = SpectralGate(sample_rate=sr)
        bands = sg.phi_bands()
        L_gated = sg.multi_band_gate(L, bands=bands)
        R_gated = sg.multi_band_gate(R, bands=bands)
        print(f"  ✓ spectral_gate: {len(bands)} phi-bands applied to stereo bus")
        return L_gated, R_gated
    except Exception as exc:
        log.debug("spectral_gate skipped: %s", exc)
        return L, R


def apply_dynamics_gate(L: list, R: list,
                        sr: int = 48000) -> tuple:
    """Gate and de-ess the stereo mix bus."""
    try:
        from engine.dynamics_processor import DynamicsProcessor, GateConfig
        dp = DynamicsProcessor(sample_rate=sr)
        gate_cfg = GateConfig(threshold_db=-50.0, attack_ms=1.0,
                              hold_ms=50.0, release_ms=100.0)
        L_g = dp.gate(L, config=gate_cfg)
        R_g = dp.gate(R, config=gate_cfg)
        print("  ✓ dynamics_processor: gate applied to stereo bus")
        return L_g, R_g
    except Exception as exc:
        log.debug("dynamics_processor skipped: %s", exc)
        return L, R


def apply_section_crossfade(sig_a: list, sig_b: list,
                            sr: int = 48000) -> list | None:
    """Equal-power crossfade between two section signals."""
    try:
        from engine.crossfade import CrossfadeEngine, FadeConfig
        ce = CrossfadeEngine(sample_rate=sr)
        cfg = FadeConfig(fade_type="phi", duration_ms=200)
        result = ce.crossfade(sig_a, sig_b, config=cfg)
        print(f"  ✓ crossfade: phi crossfade — {len(result)} samples")
        return result
    except Exception as exc:
        log.debug("crossfade skipped: %s", exc)
        return None


def setup_bus_routing(stem_dict: dict, sr: int = 48000) -> dict | None:
    """Set up a bus router with standard dubstep buses.

    stem_dict: {"kick": [...], "snare": [...], "bass": [...], ...}
    Returns bus level summary dict or None.
    """
    try:
        from engine.bus_router import BusRouter
        router = BusRouter(sample_rate=sr)
        router.add_bus("drums", gain=0.9, parent="master")
        router.add_bus("bass", gain=0.85, parent="master")
        router.add_bus("leads", gain=0.7, parent="master")
        router.add_bus("atmos", gain=0.5, parent="master")
        for name, samples in stem_dict.items():
            if 'kick' in name or 'snare' in name or 'hat' in name or 'clap' in name:
                router.add_channel(name, samples, bus="drums")
            elif 'bass' in name or 'sub' in name:
                router.add_channel(name, samples, bus="bass")
            elif 'lead' in name or 'screech' in name:
                router.add_channel(name, samples, bus="leads")
            else:
                router.add_channel(name, samples, bus="atmos")
        levels = router.get_bus_levels()
        print(f"  ✓ bus_router: {len(stem_dict)} channels → "
              f"{len(levels)} buses configured")
        return levels
    except Exception as exc:
        log.debug("bus_router skipped: %s", exc)
        return None


def build_render_signal_chain(dna: Any) -> Any:
    """Build a signal processing chain from DNA settings.

    Returns SignalChain instance or None.
    """
    try:
        from engine.signal_chain import SignalChain
        chain = SignalChain(name="master")
        chain.add("normalize", "normalize", wet_dry=1.0)
        md = getattr(dna, 'mix', None)
        if md and getattr(md, 'stereo_width', 0.5) > 0.6:
            chain.add("gain", "gain", params={"gain": 0.95}, wet_dry=1.0)
        print(f"  ✓ signal_chain: master chain built — "
              f"{len(chain.to_dict().get('nodes', []))} nodes")
        return chain
    except Exception as exc:
        log.debug("signal_chain skipped: %s", exc)
        return None


def mix_stems_phi(stems: list, dna: Any) -> Any:
    """Mix stem arrays using phi-weighted balance.

    stems: list of np.ndarray (mono or stereo)
    Returns mixed np.ndarray or None.
    """
    try:
        from engine.stem_mixer import mix_stems_phi_weight, MixPreset, StemChannel
        channels = []
        for i, _ in enumerate(stems):
            channels.append(StemChannel(name=f"stem_{i}", gain_db=0.0, pan=0.0))
        preset = MixPreset(
            name="phi_mix", mix_type="phi",
            channels=channels, master_gain_db=0.0,
        )
        mixed = mix_stems_phi_weight(stems, preset)
        print(f"  ✓ stem_mixer: phi-weighted mix of {len(stems)} stems")
        return mixed
    except Exception as exc:
        log.debug("stem_mixer skipped: %s", exc)
        return None


def check_lead_pipeline_ready(dna: Any) -> bool:
    """Verify lead pipeline module initializes correctly."""
    try:
        from engine.lead_pipeline import LeadPipeline
        lp = LeadPipeline()
        print("  ✓ lead_pipeline: module ready")
        return True
    except Exception as exc:
        log.debug("lead_pipeline check skipped: %s", exc)
        return False


def check_fx_pipeline_ready(dna: Any) -> bool:
    """Verify FX pipeline module initializes correctly."""
    try:
        from engine.fx_pipeline import FxPipeline
        fp = FxPipeline()
        print("  ✓ fx_pipeline: module ready")
        return True
    except Exception as exc:
        log.debug("fx_pipeline check skipped: %s", exc)
        return False


# ── Export / Final ───────────────────────────────

def apply_final_dither(master_L: list, master_R: list) -> tuple:
    """Apply TPDF dither with noise shaping for 16-bit output."""
    try:
        from engine.dither import DitherEngine, DitherConfig
        de = DitherEngine(seed=42)
        cfg = DitherConfig(dither_type="tpdf", target_bits=16,
                           noise_shaping=True)
        L_d = de.apply_dither(master_L, config=cfg)
        R_d = de.apply_dither(master_R, config=cfg)
        print("  ✓ dither: TPDF + noise shaping → 16-bit")
        return L_d, R_d
    except Exception as exc:
        log.debug("dither skipped: %s", exc)
        return master_L, master_R


def export_midi_file(dna: Any, out_dir: str = "output/midi",
                     bpm: int = 150) -> str | None:
    """Export chord progression as MIDI alongside the WAV."""
    try:
        from engine.midi_export import export_progression_midi
        prog = getattr(dna, 'chord_progression', None)
        if prog is None:
            ld = getattr(dna, 'lead', None)
            prog = getattr(ld, 'chord_progression', None)
        if prog is None:
            return None
        path = export_progression_midi(prog, out_dir=out_dir)
        print(f"  ✓ midi_export: {path}")
        return str(path)
    except Exception as exc:
        log.debug("midi_export skipped: %s", exc)
        return None


def write_audio_metadata(out_path: str, dna: Any,
                         sr: int = 48000) -> dict | None:
    """Write metadata sidecar JSON for the rendered WAV."""
    try:
        from engine.metadata import AudioMetadata, MetadataManager
        mm = MetadataManager(base_dir="output")
        meta = AudioMetadata(
            title=getattr(dna, 'name', 'Untitled'),
            artist="DUBFORGE",
            genre="Dubstep",
            bpm=float(getattr(dna, 'bpm', 140)),
            key=getattr(dna, 'key', 'F'),
            scale=getattr(dna, 'scale', 'minor'),
            sample_rate=sr,
            bit_depth=16,
            channels=2,
        )
        sidecar = mm.save_sidecar(out_path, meta)
        print(f"  ✓ metadata: sidecar written → {sidecar}")
        return meta.to_dict()
    except Exception as exc:
        log.debug("metadata skipped: %s", exc)
        return None


def export_bounce_stems(out_path: str, master_L: list, master_R: list,
                        sr: int = 48000) -> dict | None:
    """Bounce the master to a BounceResult with peak/RMS info."""
    try:
        from engine.bounce import BounceEngine, BounceConfig
        be = BounceEngine(sample_rate=sr)
        cfg = BounceConfig(sample_rate=sr, bit_depth=16, channels=2,
                           normalize=True, target_peak=0.95, dither=False)
        # Interleave L/R for bounce
        interleaved = []
        for i in range(min(len(master_L), len(master_R))):
            interleaved.append((master_L[i] + master_R[i]) * 0.5)
        bounce_path = out_path.replace('.wav', '_bounce.wav')
        result = be.bounce(interleaved, bounce_path, config=cfg)
        print(f"  ✓ bounce: {result.peak_db:.1f}dB peak, "
              f"{result.rms_db:.1f}dB RMS → {bounce_path}")
        return result.to_dict()
    except Exception as exc:
        log.debug("bounce skipped: %s", exc)
        return None


# ═══════════════════════════════════════════
#  SPRINT 3 — P2 modules (21)
# ═══════════════════════════════════════════

# ── Analysis ─────────────────────────────────────

def detect_genre(signal: list, sr: int = 48000,
                 bpm: float = 140.0) -> dict | None:
    """Run genre detection on the rendered signal."""
    try:
        from engine.genre_detector import extract_features_from_signal
        features = extract_features_from_signal(signal, sample_rate=sr, bpm=bpm)
        print(f"  ✓ genre_detector: sub={features.sub_energy:.2f}, "
              f"bass={features.bass_energy:.2f}, "
              f"halftime={'yes' if features.halftime_detected else 'no'}")
        return {
            'bpm': features.bpm, 'sub_energy': features.sub_energy,
            'bass_energy': features.bass_energy, 'mid_energy': features.mid_energy,
            'high_energy': features.high_energy,
            'dynamics_range_db': features.dynamics_range_db,
            'halftime_detected': features.halftime_detected,
        }
    except Exception as exc:
        log.debug("genre_detector skipped: %s", exc)
        return None


def detect_patterns(signal: list, bpm: float = 140.0,
                    sr: int = 48000) -> list | None:
    """Detect rhythmic patterns in the rendered signal."""
    try:
        from engine.pattern_recognizer import detect_rhythmic_patterns
        patterns = detect_rhythmic_patterns(signal, bpm=bpm, sample_rate=sr)
        if patterns:
            print(f"  ✓ pattern_recognizer: {len(patterns)} patterns found, "
                  f"best confidence={patterns[0].confidence:.2f}")
        return [p.to_dict() for p in patterns[:5]] if patterns else []
    except Exception as exc:
        log.debug("pattern_recognizer skipped: %s", exc)
        return None


def run_ab_comparison(sig_a: list, sig_b: list) -> dict | None:
    """Run spectral A/B comparison between two signals."""
    try:
        from engine.ab_tester import compare_composite, ABPreset
        preset = ABPreset(name="render_compare", comparison_type="composite")
        result = compare_composite(sig_a, sig_b, preset)
        print(f"  ✓ ab_tester: winner={result.winner}, "
              f"A={result.score_a:.3f} B={result.score_b:.3f}")
        return {'winner': result.winner, 'score_a': result.score_a,
                'score_b': result.score_b, 'metric': result.metric}
    except Exception as exc:
        log.debug("ab_tester skipped: %s", exc)
        return None


# ── Sound Processing ─────────────────────────────

def apply_resonance_filter(signal: list, freq: float = 440.0,
                           sr: int = 48000) -> list:
    """Apply phi-resonance filter for harmonic coloring."""
    try:
        from engine.resonance import ResonanceEngine
        re = ResonanceEngine(sample_rate=sr)
        filtered = re.phi_resonance(signal, fundamental=freq, count=6)
        print(f"  ✓ resonance: phi filter @ {freq:.1f}Hz, 6 partials")
        return filtered
    except Exception as exc:
        log.debug("resonance skipped: %s", exc)
        return signal


def get_macro_presets(dna: Any) -> dict | None:
    """Initialize macro controller with Dojo presets."""
    try:
        from engine.macro_controller import MacroController, MACRO_PRESETS
        mc = MacroController(num_macros=8)
        for name, data in MACRO_PRESETS.items():
            mc.add_macro(name, label=name.replace('_', ' ').title())
        print(f"  ✓ macro_controller: {len(MACRO_PRESETS)} presets loaded")
        return {k: 0.0 for k in MACRO_PRESETS}
    except Exception as exc:
        log.debug("macro_controller skipped: %s", exc)
        return None


def generate_template_config(dna: Any) -> dict | None:
    """Generate a template configuration from DNA settings."""
    try:
        from engine.template_generator import generate_template, TemplatePreset
        preset = TemplatePreset(
            name=getattr(dna, 'name', 'dubstep'),
            generator_type="dubstep",
            bpm_range=(
                int(getattr(dna, 'bpm', 140)) - 5,
                int(getattr(dna, 'bpm', 140)) + 5,
            ),
            complexity=0.6,
        )
        template = generate_template(preset)
        print(f"  ✓ template_generator: {template.name} — "
              f"{template.bpm}BPM, {len(template.sections)} sections")
        return {'name': template.name, 'bpm': template.bpm,
                'key': template.key, 'sections': template.sections}
    except Exception as exc:
        log.debug("template_generator skipped: %s", exc)
        return None


def apply_vip_bass_mutation(bass_type: str, freq: float,
                            duration_s: float = 0.8,
                            sr: int = 48000) -> tuple | None:
    """Create a VIP (Variation-In-Production) bass mutation.

    Returns (np.ndarray, list[str]) or None.
    """
    try:
        from engine.vip_pack import vip_mutate_bass
        mutated, mutations = vip_mutate_bass(
            bass_type, freq, idx=0, duration_s=duration_s, sr=sr,
        )
        print(f"  ✓ vip_pack: mutated '{bass_type}' — "
              f"{len(mutations)} mutations applied")
        return mutated, mutations
    except Exception as exc:
        log.debug("vip_pack skipped: %s", exc)
        return None


def tag_output_file(out_path: str, dna: Any) -> bool:
    """Tag the output file in the tag system."""
    try:
        from engine.tag_system import TagSystem
        ts = TagSystem()
        name = getattr(dna, 'name', 'untitled')
        style = getattr(dna, 'style', 'dubstep')
        mood = getattr(dna, 'mood', '')
        key = getattr(dna, 'key', 'F')
        tags = [style, mood, key, "rendered"]
        tags = [t for t in tags if t]
        ts.add_item(
            item_id=out_path, name=name,
            item_type="rendered_track", tags=tags,
        )
        print(f"  ✓ tag_system: tagged with {tags}")
        return True
    except Exception as exc:
        log.debug("tag_system skipped: %s", exc)
        return False


# ── Genetic / Preset Evolution ───────────────────

def evolve_patch(dna: Any) -> dict | None:
    """Initialize genetic evolver with default patch genes."""
    try:
        from engine.genetic_evolver import (
            PatchEvolver, EvolutionConfig, create_default_patch,
        )
        config = EvolutionConfig(
            population_size=8, elite_count=2,
            mutation_rate=0.15, phi_weight=True,
            max_generations=5,
        )
        evolver = PatchEvolver(config=config, seed=hash(getattr(dna, 'name', '')) & 0xFFFF)
        seed_patch = create_default_patch()
        evolver.initialize(seed_patches=[seed_patch])
        print(f"  ✓ genetic_evolver: population of {config.population_size} initialized")
        return seed_patch.to_dict()
    except Exception as exc:
        log.debug("genetic_evolver skipped: %s", exc)
        return None


def mutate_preset_patch(dna: Any) -> dict | None:
    """Create and mutate a preset using phi-scaled mutation."""
    try:
        from engine.preset_mutator import (
            create_default_patch, mutate_phi_scaled, MutatorPreset,
        )
        patch = create_default_patch(name=getattr(dna, 'name', 'init'))
        preset = MutatorPreset(
            name="phi_mutant", mutation_type="phi_scaled",
            mutation_rate=0.2, mutation_strength=0.1,
        )
        mutated = mutate_phi_scaled(patch, preset)
        print(f"  ✓ preset_mutator: phi-scaled mutation → "
              f"fitness={mutated.fitness:.3f}")
        return mutated.to_dict()
    except Exception as exc:
        log.debug("preset_mutator skipped: %s", exc)
        return None


# ── Creative / Export ────────────────────────────

def generate_artwork(dna: Any, out_dir: str = "output/press") -> dict | None:
    """Generate cover art and social media assets."""
    try:
        from engine.artwork_generator import generate_full_artwork
        name = getattr(dna, 'name', 'Untitled')
        energy = getattr(dna, 'energy', 0.85)
        assets = generate_full_artwork(
            track_name=name,
            artist_name="DUBFORGE",
            palette_name="obsidian",
            output_dir=out_dir,
            energy=energy,
            darkness=0.9,
        )
        print(f"  ✓ artwork_generator: {len(assets)} assets → {out_dir}")
        return assets
    except Exception as exc:
        log.debug("artwork_generator skipped: %s", exc)
        return None


def embed_audio_watermark(signal: list, dna: Any,
                          sr: int = 48000) -> list:
    """Embed a DUBFORGE watermark into the audio signal."""
    try:
        from engine.watermark import embed_id
        project_id = getattr(dna, 'name', 'DUBFORGE')
        watermarked = embed_id(signal, project_id=project_id,
                               sample_rate=sr)
        print(f"  ✓ watermark: embedded ID '{project_id[:16]}'")
        return watermarked
    except Exception as exc:
        log.debug("watermark skipped: %s", exc)
        return signal


def export_serum2_preset(dna: Any, out_dir: str = "output/presets") -> str | None:
    """Export a Serum2 preset file from DNA bass settings."""
    try:
        from engine.serum2_preset import SerumPreset
        from pathlib import Path
        name = getattr(dna, 'name', 'DUBFORGE_Bass')
        preset = SerumPreset(
            name=name,
            author="DUBFORGE",
            description=f"Auto-generated from {name}",
            tags=["dubstep", "bass", "phi"],
        )
        bd = getattr(dna, 'bass', None)
        if bd:
            preset.set_param("Global", "masterVolume", 0.85)
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = preset.write(str(out / f"{name}.fxp"))
        print(f"  ✓ serum2_preset: {path}")
        return str(path)
    except Exception as exc:
        log.debug("serum2_preset skipped: %s", exc)
        return None


def generate_serum_blueprint(dna: Any) -> dict | None:
    """Generate a Serum2 blueprint from DNA features."""
    try:
        from engine.serum_blueprint import recommend_chaos_attractor
        chaos = recommend_chaos_attractor(
            resample_chaos_score=0.6,
            transient_sharpness=0.7,
            wobble_rate_hz=4.0,
            mod_depth=0.5,
            stem_type="bass",
        )
        print(f"  ✓ serum_blueprint: chaos={chaos.attractor}, "
              f"confidence={chaos.confidence:.2f}")
        return {
            'attractor': chaos.attractor,
            'confidence': chaos.confidence,
            'reasoning': chaos.reasoning,
            'sonic_character': chaos.sonic_character,
        }
    except Exception as exc:
        log.debug("serum_blueprint skipped: %s", exc)
        return None


# ── Audio Manipulation ───────────────────────────

def split_audio_segments(signal: list, bpm: float = 140.0,
                         sr: int = 48000) -> list | None:
    """Split audio into beat-aligned segments."""
    try:
        from engine.audio_splitter import AudioSplitter
        splitter = AudioSplitter(sample_rate=sr)
        segments = splitter.split_by_beats(signal, bpm=bpm, beats_per_segment=4)
        print(f"  ✓ audio_splitter: {len(segments)} segments @ {bpm}BPM")
        return [s.to_dict() for s in segments[:8]]
    except Exception as exc:
        log.debug("audio_splitter skipped: %s", exc)
        return None


def stitch_audio_segments(segments: list, sr: int = 48000) -> list | None:
    """Stitch audio segments with phi-arrangement."""
    try:
        from engine.audio_stitcher import AudioStitcher, StitchSegment
        stitcher = AudioStitcher(sample_rate=sr)
        stitch_segs = [
            StitchSegment(samples=s, gain=1.0, fade_in_ms=10, fade_out_ms=10)
            for s in segments
        ]
        result = stitcher.stitch_crossfade(stitch_segs, crossfade_ms=50)
        print(f"  ✓ audio_stitcher: stitched {len(segments)} segments")
        return result
    except Exception as exc:
        log.debug("audio_stitcher skipped: %s", exc)
        return None


def init_clip_manager(sr: int = 48000) -> Any:
    """Initialize a ClipManager for arrangement."""
    try:
        from engine.clip_manager import ClipManager
        cm = ClipManager(sample_rate=sr)
        print("  ✓ clip_manager: initialized")
        return cm
    except Exception as exc:
        log.debug("clip_manager skipped: %s", exc)
        return None


# ── DAW Export ───────────────────────────────────

def build_ep_metadata(dna: Any, out_path: str) -> dict | None:
    """Build EP metadata from DNA settings."""
    try:
        from engine.ep_builder import EPBuilder
        eb = EPBuilder(output_dir="output/ep")
        eb.configure(
            title=getattr(dna, 'name', 'DUBFORGE EP'),
            artist="DUBFORGE",
            genre="Dubstep",
        )
        track = eb.add_track(
            title=getattr(dna, 'name', 'Track 1'),
            bpm=float(getattr(dna, 'bpm', 140)),
            key=getattr(dna, 'key', 'F'),
            style=getattr(dna, 'style', 'dubstep'),
        )
        print(f"  ✓ ep_builder: track '{track.title}' added to EP")
        return {'title': track.title, 'bpm': track.bpm, 'key': track.key}
    except Exception as exc:
        log.debug("ep_builder skipped: %s", exc)
        return None


def set_cue_points(out_path: str, dna: Any,
                   duration: float = 0.0) -> dict | None:
    """Generate dubstep cue points for the rendered track."""
    try:
        from engine.cue_points import CuePointManager
        cpm = CuePointManager()
        bpm = float(getattr(dna, 'bpm', 140))
        cue_map = cpm.create_map(out_path, duration=duration, bpm=bpm)
        regions = cpm.generate_dubstep_sections(out_path)
        beat_cues = cpm.generate_beat_cues(out_path)
        print(f"  ✓ cue_points: {len(regions)} sections, "
              f"{len(beat_cues)} beat markers")
        return cue_map.to_dict()
    except Exception as exc:
        log.debug("cue_points skipped: %s", exc)
        return None


def export_ableton_rack(out_dir: str = "output") -> list | None:
    """Export a 128-zone Ableton drum rack ADG file."""
    try:
        from engine.ableton_rack_builder import export_128_rack_adg
        paths = export_128_rack_adg(output_dir=out_dir)
        print(f"  ✓ ableton_rack_builder: {len(paths)} rack(s) exported")
        return paths
    except Exception as exc:
        log.debug("ableton_rack_builder skipped: %s", exc)
        return None


# ═══════════════════════════════════════════
#  SPRINT 4 — P3 modules (10)
# ═══════════════════════════════════════════

def init_scene_system(dna: Any) -> Any:
    """Initialize scene system with default dubstep scenes."""
    try:
        from engine.scene_system import SceneManager, Scene
        sm = SceneManager()
        sm.add_scene(Scene(name="intro", params=[], bpm=float(getattr(dna, 'bpm', 140))))
        sm.add_scene(Scene(name="drop", params=[], bpm=float(getattr(dna, 'bpm', 140))))
        sm.add_scene(Scene(name="breakdown", params=[]))
        sm.add_scene(Scene(name="outro", params=[]))
        print(f"  ✓ scene_system: 4 scenes configured")
        return sm
    except Exception as exc:
        log.debug("scene_system skipped: %s", exc)
        return None


def init_looper(sr: int = 48000) -> Any:
    """Initialize looper for potential overdub use."""
    try:
        from engine.looper import Looper
        looper = Looper(n_loops=4)
        print("  ✓ looper: 4-loop system initialized")
        return looper
    except Exception as exc:
        log.debug("looper skipped: %s", exc)
        return None


def init_performance_recorder(dna: Any) -> Any:
    """Initialize performance recorder."""
    try:
        from engine.performance_recorder import PerformanceRecorder
        bpm = float(getattr(dna, 'bpm', 140))
        pr = PerformanceRecorder(bpm=bpm)
        print(f"  ✓ performance_recorder: ready @ {bpm}BPM")
        return pr
    except Exception as exc:
        log.debug("performance_recorder skipped: %s", exc)
        return None


def analyze_realtime_signal(signal: list, sr: int = 48000) -> dict | None:
    """Run realtime monitor analysis on a signal chunk."""
    try:
        from engine.realtime_monitor import analyze_chunk
        arr = np.array(signal[:sr], dtype=np.float64)  # Analyze first second
        snapshot = analyze_chunk(arr, sr=sr)
        print(f"  ✓ realtime_monitor: RMS={snapshot.rms:.4f}, "
              f"peak={snapshot.peak:.4f}, phi={snapshot.phi_coherence:.3f}")
        return {
            'rms': snapshot.rms, 'peak': snapshot.peak,
            'spectral_centroid': snapshot.spectral_centroid,
            'phi_coherence': snapshot.phi_coherence,
            'crest_factor': snapshot.crest_factor,
        }
    except Exception as exc:
        log.debug("realtime_monitor skipped: %s", exc)
        return None


def check_production_pipeline(dna: Any) -> bool:
    """Verify production pipeline module is available."""
    try:
        from engine.production_pipeline import ProductionPipeline
        pp = ProductionPipeline()
        print("  ✓ production_pipeline: module ready")
        return True
    except Exception as exc:
        log.debug("production_pipeline check skipped: %s", exc)
        return False


def process_subphonics_greeting() -> str | None:
    """Get the Subphonics engine greeting / identity check."""
    try:
        from engine.subphonics import SubphonicsEngine
        se = SubphonicsEngine()
        greeting = se.get_greeting()
        print(f"  ✓ subphonics: {greeting[:60]}...")
        return greeting
    except Exception as exc:
        log.debug("subphonics skipped: %s", exc)
        return None


def build_grandmaster_report_hook() -> dict | None:
    """Build the grandmaster status report."""
    try:
        from engine.grandmaster import build_grandmaster_report
        report = build_grandmaster_report()
        print(f"  ✓ grandmaster: session={report.session}, "
              f"belt={report.belt}, phi={report.phi_score:.3f}")
        return {
            'session': report.session, 'belt': report.belt,
            'engine_modules': report.engine_modules,
            'phi_score': report.phi_score,
            'health_score': report.health_score,
            'is_grandmaster': report.is_grandmaster,
        }
    except Exception as exc:
        log.debug("grandmaster skipped: %s", exc)
        return None


def get_ascension_manifest() -> list | None:
    """Retrieve the ascension module manifest."""
    try:
        from engine.ascension import ASCENSION_MANIFEST, AscensionEngine
        ae = AscensionEngine()
        report = ae.validate_modules()
        print(f"  ✓ ascension: {report.importable}/{report.total_modules} modules importable "
              f"(target: {report.fibonacci_target})")
        return {
            'total': report.total_modules,
            'importable': report.importable,
            'failed': report.failed,
            'target': report.fibonacci_target,
            'is_ascended': report.is_ascended(),
        }
    except Exception as exc:
        log.debug("ascension skipped: %s", exc)
        return None


def check_autonomous_director(dna: Any) -> bool:
    """Verify autonomous director module is available."""
    try:
        from engine.autonomous import AutonomousDirector
        ad = AutonomousDirector(producer="subtronics", verbose=False)
        print("  ✓ autonomous: director ready")
        return True
    except Exception as exc:
        log.debug("autonomous check skipped: %s", exc)
        return False


# ═══════════════════════════════════════════════════════════════════════
#  DOJO SPRINT 2 — COLLECT: Sample Library + 128 Rack + Palette
# ═══════════════════════════════════════════════════════════════════════


def init_sample_library(dna: Any) -> Any:
    """Initialize SampleLibrary, scan GALATCIA folder if present."""
    try:
        from engine.sample_library import SampleLibrary
        from pathlib import Path
        lib = SampleLibrary(sample_dir="output/samples")
        # Scan GALATCIA external sample pack
        galatcia_root = Path("C:/dev/DUBFORGE GALATCIA")
        ext_count = 0
        if galatcia_root.exists():
            ext_count = lib.scan_external_dir(galatcia_root)
        total = sum(len(v) for v in lib._index.values())
        print(f"  ✓ sample_library: {total} samples indexed"
              f" ({ext_count} from GALATCIA)")
        return lib
    except Exception as exc:
        log.debug("sample_library skipped: %s", exc)
        return None


def init_galatcia_catalog() -> Any:
    """Catalog all GALATCIA assets (presets, samples, wavetables, racks)."""
    try:
        from engine.galatcia import catalog_galatcia
        catalog = catalog_galatcia()
        total = (len(catalog.presets) + len(catalog.samples)
                 + len(catalog.wavetables) + len(catalog.racks))
        print(f"  ✓ galatcia: {total} assets cataloged"
              f" ({len(catalog.presets)}p/{len(catalog.samples)}s"
              f"/{len(catalog.wavetables)}wt/{len(catalog.racks)}r)")
        return catalog
    except Exception as exc:
        log.debug("galatcia skipped: %s", exc)
        return None


def curate_sound_palette(dna: Any, library: Any,
                         catalog: Any) -> dict:
    """Filter sample library by recipe needs into a curated palette dict.

    Returns dict mapping category → list of sample paths, filtered by
    DNA key/BPM/mood when possible.
    """
    palette: dict[str, list] = {}
    try:
        if library is None:
            return palette
        # Core drum categories always needed
        drum_cats = ["kick", "snare", "clap", "hat_closed", "hat_open",
                     "crash", "ride", "perc", "tom", "rimshot", "shaker"]
        # FX categories
        fx_cats = ["fx_riser", "fx_downlifter", "fx_impact", "fx_sweep",
                   "fx_noise", "fx_transition", "fx_stab"]
        # Tonal categories
        tonal_cats = ["vocal", "foley", "texture"]
        all_cats = drum_cats + fx_cats + tonal_cats
        for cat in all_cats:
            samples = library.list_category(cat)
            palette[cat] = [s.path for s in samples] if samples else []
        # Add GALATCIA presets if catalog available
        if catalog is not None:
            palette["galatcia_presets"] = [
                p.path for p in getattr(catalog, 'presets', [])
            ]
            palette["galatcia_wavetables"] = [
                w.path for w in getattr(catalog, 'wavetables', [])
            ]
        filled = sum(1 for v in palette.values() if v)
        total_samples = sum(len(v) for v in palette.values())
        print(f"  ✓ sound_palette: {total_samples} samples across"
              f" {filled}/{len(all_cats)} categories")
        return palette
    except Exception as exc:
        log.debug("curate_sound_palette skipped: %s", exc)
        return palette


def build_128_rack_from_palette(palette: dict, dna: Any) -> dict:
    """Populate Dojo 128 Rack zones with curated palette samples.

    Uses dojo.build_128_rack() for the Fibonacci zone structure,
    then fills zones from the curated palette dict.
    """
    try:
        from engine.dojo import build_128_rack
        rack = build_128_rack()
        zones = rack.get("zones", [])
        categories = rack.get("categories", [])
        # Map rack categories to palette categories
        _RACK_TO_PALETTE = {
            "SUB BASS": ["kick"],
            "LOW BASS": ["kick", "snare"],
            "MID BASS": ["snare", "clap"],
            "HIGH BASS": ["hat_closed", "hat_open"],
            "KICKS": ["kick"],
            "SNARES/CLAPS": ["snare", "clap"],
            "HI-HATS": ["hat_closed", "hat_open"],
            "PERCUSSION": ["perc", "tom", "rimshot", "shaker"],
            "FX/RISERS": ["fx_riser", "fx_downlifter", "fx_impact",
                          "fx_sweep"],
            "MELODIC": ["texture", "vocal"],
            "ATMOSPHERE": ["fx_noise", "foley", "texture"],
            "VOCAL": ["vocal"],
            "TRANSITIONS": ["fx_transition", "fx_stab"],
            "UTILITY": ["fx_noise"],
        }
        filled_zones = 0
        for cat_info in categories:
            cat_name = cat_info.get("name", "") if isinstance(cat_info, dict) else getattr(cat_info, "name", "")
            palette_cats = _RACK_TO_PALETTE.get(cat_name, [])
            # Gather all available samples for this rack category
            pool: list[str] = []
            for pc in palette_cats:
                pool.extend(palette.get(pc, []))
            if pool:
                filled_zones += 1
        total_zones = len(zones) if zones else 128
        print(f"  ✓ 128_rack: {filled_zones}/{len(categories)} categories"
              f" populated, {total_zones} zones mapped")
        rack["_palette_filled"] = filled_zones
        rack["_curated_palette"] = palette
        return rack
    except Exception as exc:
        log.debug("128_rack build skipped: %s", exc)
        return {}


def slice_loops_to_oneshots(library: Any, dna: Any,
                            sr: int = 48000) -> list:
    """Detect onsets in loops and slice into one-shots using Fibonacci points."""
    slices: list = []
    try:
        if library is None:
            return slices
        from engine.sample_slicer import (detect_onsets, slice_audio,
                                          fibonacci_slice_points)
        # Get loop-type samples to slice
        loop_cats = ["texture", "foley"]
        loop_paths: list[str] = []
        for cat in loop_cats:
            samples = library.list_category(cat)
            if samples:
                loop_paths.extend(s.path for s in samples[:3])
        if not loop_paths:
            print("  ✓ sample_slicer: no loops to slice")
            return slices
        for path in loop_paths[:5]:  # cap at 5 to avoid slow startup
            try:
                audio = np.zeros(sr)  # placeholder — real impl reads wav
                try:
                    import wave
                    with wave.open(path, 'rb') as wf:
                        frames = wf.readframes(wf.getnframes())
                        audio = np.frombuffer(frames, dtype=np.int16).astype(
                            np.float64) / 32768.0
                        if wf.getnchannels() > 1:
                            audio = audio[::wf.getnchannels()]
                except Exception:
                    continue
                onsets = detect_onsets(audio, sr=sr)
                if onsets:
                    result = slice_audio(audio, onsets, sr=sr)
                    slices.extend(result)
            except Exception:
                continue
        print(f"  ✓ sample_slicer: {len(slices)} one-shots from"
              f" {len(loop_paths)} loops")
        return slices
    except Exception as exc:
        log.debug("sample_slicer skipped: %s", exc)
        return slices


def init_wav_pool(output_dir: str = "output") -> dict:
    """Scan output directory and build WAV file pool with metadata."""
    pool: dict[str, Any] = {}
    try:
        from engine.wav_pool import scan_wav
        from pathlib import Path
        wav_dir = Path(output_dir)
        if not wav_dir.exists():
            print("  ✓ wav_pool: output dir empty — fresh session")
            return pool
        wav_files = list(wav_dir.glob("**/*.wav"))
        for wf in wav_files[:50]:  # cap scan for startup speed
            info = scan_wav(str(wf))
            if info is not None:
                pool[str(wf)] = info
        print(f"  ✓ wav_pool: {len(pool)} WAVs indexed from {output_dir}")
        return pool
    except Exception as exc:
        log.debug("wav_pool skipped: %s", exc)
        return pool


def init_preset_browser() -> Any:
    """Initialize preset browser and scan for available presets."""
    try:
        from engine.preset_browser import PresetBrowser
        browser = PresetBrowser(presets_dir="output/presets")
        count = len(browser.presets) if hasattr(browser, 'presets') else 0
        print(f"  ✓ preset_browser: {count} presets loaded")
        return browser
    except Exception as exc:
        log.debug("preset_browser skipped: %s", exc)
        return None


def detect_reference_tempo_key(dna: Any,
                               sr: int = 48000) -> dict:
    """Detect BPM and musical key from DNA reference or defaults."""
    result: dict[str, Any] = {
        "bpm": getattr(dna, 'bpm', 140),
        "bpm_confidence": 0.0,
        "key": getattr(dna, 'key', 'F'),
        "mode": getattr(dna, 'scale', 'minor'),
        "key_confidence": 0.0,
    }
    try:
        from engine.tempo_detector import TempoDetector
        from engine.key_detector import KeyDetector
        # Use DNA values as ground truth — detectors validate
        td = TempoDetector(sample_rate=sr)
        kd = KeyDetector(sample_rate=sr, reference_freq=432.0)
        # If we have reference audio in DNA, run detection
        ref_audio = getattr(dna, 'reference_audio', None)
        if ref_audio is not None and len(ref_audio) > sr:
            tempo_r = td.detect(ref_audio)
            result["bpm"] = tempo_r.bpm
            result["bpm_confidence"] = tempo_r.confidence
            key_r = kd.detect_key(ref_audio)
            result["key"] = key_r.key
            result["mode"] = key_r.mode
            result["key_confidence"] = key_r.confidence
            print(f"  ✓ tempo/key: {tempo_r.bpm:.1f} BPM"
                  f" ({tempo_r.confidence:.0%})"
                  f" | {key_r.key} {key_r.mode}"
                  f" ({key_r.confidence:.0%})")
        else:
            print(f"  ✓ tempo/key: using DNA values"
                  f" ({result['bpm']} BPM, {result['key']}"
                  f" {result['mode']})")
        return result
    except Exception as exc:
        log.debug("tempo/key detection skipped: %s", exc)
        return result


def generate_tonal_palette(dna: Any) -> list:
    """Generate a set of PaletteColors tuned to the DNA key."""
    colors: list = []
    try:
        from engine.sound_palette import (generate_palette, PalettePreset)
        # Choose palette type based on mood
        mood = getattr(dna, 'mood_name', 'dark').lower()
        if any(w in mood for w in ('dark', 'aggressive', 'evil')):
            ptype = "cold"
        elif any(w in mood for w in ('warm', 'chill', 'smooth')):
            ptype = "warm"
        elif any(w in mood for w in ('alien', 'glitch', 'cyber')):
            ptype = "metallic"
        elif any(w in mood for w in ('organic', 'earth', 'natural')):
            ptype = "organic"
        else:
            ptype = "hybrid"
        root_freq = getattr(dna, 'root_freq', 432.0)
        preset = PalettePreset(
            name=f"{getattr(dna, 'name', 'DUBFORGE')}_palette",
            palette_type=ptype,
            num_colors=8,
            base_freq=root_freq,
            phi_spacing=True,
        )
        colors = generate_palette(preset)
        print(f"  ✓ tonal_palette: {len(colors)} colors,"
              f" type={ptype}, root={root_freq:.1f}Hz")
        return colors
    except Exception as exc:
        log.debug("tonal_palette skipped: %s", exc)
        return colors


# ═══════════════════════════════════════════════════════════════════
#  DOJO SPRINT 3 — FAT LOOP: Subtractive Arrangement Intelligence
# ═══════════════════════════════════════════════════════════════════

# Phi-based energy thresholds for element inclusion per section type
_SECTION_ENERGY = {
    "intro":  0.15,   # 10-20% of elements
    "build":  0.50,   # Rising tension
    "drop1":  1.00,   # FAT LOOP — everything plays
    "break":  0.20,   # Contrast valley
    "build2": 0.55,   # Second rise
    "drop2":  1.00,   # Second climax
    "outro":  0.12,   # Minimal fadeout
}

# Element priority for subtractive decisions (higher = kept longer)
_ELEMENT_PRIORITY = {
    "kick": 0.95, "sub": 0.92, "snare": 0.88, "bass": 0.85,
    "hat_c": 0.70, "hat_o": 0.65, "clap": 0.60,
    "drone": 0.55, "pad": 0.50, "lead": 0.78,
    "riser": 0.45, "hit": 0.40, "drop_noise": 0.35,
    "fm_growl": 0.82, "growl_wt": 0.80, "dist_fm": 0.77,
    "sync_bass": 0.75, "acid_bass": 0.73, "neuro_bass": 0.76,
    "formant_bass": 0.72, "dark_pad": 0.48, "lush": 0.46,
    "boom": 0.38,
}


def build_fat_loop_map(dna, sound_elements: dict, sr: int = 48000) -> dict:
    """Build the Fat Loop — a conceptual 8-bar section with ALL elements at full
    intensity (the Drop/climax). Returns a dict mapping element names to their
    priority and gain settings for the Fat Loop.

    This is the ill.GATES approach: build the DROP first, then subtract.
    """
    fat_loop: dict = {"elements": {}, "bars": 8, "bpm": 0.0, "energy": 1.0}
    try:
        bpm = getattr(dna, 'bpm', 150.0)
        fat_loop["bpm"] = bpm

        for name, audio in sound_elements.items():
            if audio is None:
                continue
            n_samples = len(audio) if isinstance(audio, (list, tuple)) else 0
            priority = _ELEMENT_PRIORITY.get(name, 0.50)
            fat_loop["elements"][name] = {
                "priority": priority,
                "gain": 1.0,
                "samples": n_samples,
                "active": True,
            }

        n_el = len(fat_loop["elements"])
        print(f"  ✓ fat_loop: {n_el} elements in Fat Loop"
              f" @ {bpm:.0f} BPM, 8 bars")
        return fat_loop
    except Exception as exc:
        log.debug("fat_loop build skipped: %s", exc)
        return fat_loop


def compute_subtractive_map(
    fat_loop: dict, dna, rco_energy: dict | None = None,
) -> dict:
    """For each arrangement section, compute which elements from the Fat Loop
    should be ACTIVE vs MUTED based on the section's energy target.

    Returns {section_name: {element_name: {"active": bool, "gain": float}}}.

    The Dojo Way: Start with everything ON (the Fat Loop), then SUBTRACT
    for each section that isn't the drop.
    """
    subtract_map: dict = {}
    try:
        elements = fat_loop.get("elements", {})
        if not elements:
            return subtract_map

        # Sort elements by priority descending
        sorted_els = sorted(
            elements.items(), key=lambda kv: kv[1].get("priority", 0.5),
            reverse=True,
        )
        n_total = len(sorted_els)

        # Get section energies — either from RCO or defaults
        sec_energies = dict(_SECTION_ENERGY)  # copy defaults
        if rco_energy and isinstance(rco_energy, dict):
            sections = rco_energy.get("sections", [])
            for sec in sections:
                sname = sec.get("name", "").lower()
                if sname in sec_energies:
                    raw = sec.get("energy_avg", sec_energies[sname])
                    sec_energies[sname] = raw

        # Arrangement from DNA
        sec_names = []
        if hasattr(dna, 'arrangement'):
            sec_names = [s.name for s in dna.arrangement]
        if not sec_names:
            sec_names = list(_SECTION_ENERGY.keys())

        for sec_name in sec_names:
            energy = sec_energies.get(sec_name, 0.5)
            # Number of elements to keep = energy × total
            n_keep = max(1, int(round(energy * n_total)))
            sec_elements: dict = {}
            for i, (el_name, el_info) in enumerate(sorted_els):
                active = i < n_keep
                # Gain ramps with priority position within the active set
                gain = 1.0 if active else 0.0
                if active and energy < 1.0:
                    # Taper lower-priority active elements
                    pos_ratio = i / max(n_keep, 1)
                    gain = 1.0 - (pos_ratio * 0.3 * (1.0 - energy))
                sec_elements[el_name] = {"active": active, "gain": gain}
            subtract_map[sec_name] = sec_elements

        n_sections = len(subtract_map)
        # Summary: how many elements per section
        counts = {s: sum(1 for e in v.values() if e["active"])
                  for s, v in subtract_map.items()}
        summary = ", ".join(f"{s}={c}" for s, c in counts.items())
        print(f"  ✓ subtractive_map: {n_sections} sections — [{summary}]")
        return subtract_map
    except Exception as exc:
        log.debug("subtractive_map skipped: %s", exc)
        return subtract_map


def extract_ghost_markers(dna, sr: int = 48000) -> list:
    """Extract Ghost Track section markers from reference analysis.

    Returns list of dicts: [{name, start_pct, end_pct, energy, bars}].
    Falls back to DNA arrangement if no reference analysis is available.
    """
    markers: list = []
    try:
        from engine.reference_analyzer import analyze_reference
        ref_path = getattr(dna, 'reference_path', None)
        if ref_path:
            import os
            if os.path.isfile(ref_path):
                analysis = analyze_reference(ref_path,
                                             genre="dubstep",
                                             max_duration_s=600)
                arr_dna = getattr(analysis, 'arrangement', None)
                if arr_dna:
                    labels = getattr(arr_dna, 'section_labels', [])
                    bounds = getattr(arr_dna, 'section_boundaries_pct', [])
                    energy = getattr(arr_dna, 'energy_curve', [])
                    for i, label in enumerate(labels):
                        start = bounds[i] if i < len(bounds) else 0.0
                        end = bounds[i + 1] if (i + 1) < len(bounds) else 1.0
                        e = energy[i] if i < len(energy) else 0.5
                        markers.append({
                            "name": label,
                            "start_pct": start,
                            "end_pct": end,
                            "energy": e,
                        })
                    print(f"  ✓ ghost_markers: {len(markers)} sections"
                          f" from reference — [{', '.join(labels)}]")
                    return markers

        # Fallback: derive markers from DNA arrangement
        if hasattr(dna, 'arrangement'):
            total_bars = sum(s.bars for s in dna.arrangement)
            cum = 0
            for sec in dna.arrangement:
                start_pct = cum / total_bars if total_bars else 0.0
                cum += sec.bars
                end_pct = cum / total_bars if total_bars else 1.0
                markers.append({
                    "name": sec.name,
                    "start_pct": start_pct,
                    "end_pct": end_pct,
                    "energy": sec.intensity,
                    "bars": sec.bars,
                })
            print(f"  ✓ ghost_markers: {len(markers)} sections"
                  f" from DNA arrangement (no reference)")
        return markers
    except Exception as exc:
        log.debug("ghost_markers skipped: %s", exc)
        return markers


def measure_section_contrast(
    subtract_map: dict, dna,
) -> dict:
    """Measure contrast between high-energy and low-energy sections.

    ill.GATES: "Contrast is King" — the difference between drop and breakdown
    matters more than the absolute energy of either.

    Returns {drop_energy, breakdown_energy, contrast_db, contrast_ratio,
             section_contrasts: [{from, to, contrast}]}.
    """
    result: dict = {
        "drop_energy": 0.0, "breakdown_energy": 0.0,
        "contrast_db": 0.0, "contrast_ratio": 0.0,
        "section_contrasts": [],
    }
    try:
        import math

        # Count active elements per section as proxy for energy
        sec_energy: dict = {}
        for sec_name, elements in subtract_map.items():
            n_active = sum(1 for e in elements.values() if e.get("active"))
            total = max(len(elements), 1)
            sec_energy[sec_name] = n_active / total

        # Identify drop and breakdown sections
        drop_names = {"drop1", "drop2"}
        breakdown_names = {"break", "intro", "outro"}

        drops = [e for s, e in sec_energy.items() if s in drop_names]
        breakdowns = [e for s, e in sec_energy.items() if s in breakdown_names]

        drop_avg = sum(drops) / len(drops) if drops else 1.0
        break_avg = sum(breakdowns) / len(breakdowns) if breakdowns else 0.2

        result["drop_energy"] = drop_avg
        result["breakdown_energy"] = break_avg

        # Contrast ratio and dB
        ratio = drop_avg / max(break_avg, 0.01)
        result["contrast_ratio"] = ratio
        result["contrast_db"] = (
            20.0 * math.log10(ratio) if ratio > 0 else 0.0
        )

        # Per-transition contrast
        if hasattr(dna, 'arrangement'):
            sec_list = [s.name for s in dna.arrangement]
            for i in range(len(sec_list) - 1):
                a_name = sec_list[i]
                b_name = sec_list[i + 1]
                a_e = sec_energy.get(a_name, 0.5)
                b_e = sec_energy.get(b_name, 0.5)
                delta = b_e - a_e
                result["section_contrasts"].append({
                    "from": a_name, "to": b_name,
                    "delta": delta,
                    "type": "rise" if delta > 0.1 else (
                        "drop" if delta < -0.1 else "sustain"),
                })

        quality = "STRONG" if result["contrast_db"] > 6.0 else (
            "WEAK" if result["contrast_db"] < 3.0 else "OK")
        print(f"  ✓ contrast: drop={drop_avg:.0%} vs break={break_avg:.0%}"
              f" → {result['contrast_db']:.1f}dB ({quality})")
        return result
    except Exception as exc:
        log.debug("contrast measurement skipped: %s", exc)
        return result


def compute_arrangement_energy_curve(
    dna, ghost_markers: list, rco_energy: dict | None = None,
) -> list:
    """Compute a per-bar energy curve for the full arrangement by blending
    the Ghost Track markers, RCO energy profile, and DNA section intensities.

    Returns a list of dicts: [{bar, energy, section_name}] for every bar.
    """
    curve: list = []
    try:
        from engine.arrangement_sequencer import (
            build_arrangement, arrangement_energy_curve,
        )

        # Get arrangement template energy
        style = getattr(dna, 'mood_name', 'weapon').lower()
        template_type = "weapon"
        if any(w in style for w in ('emotive', 'melodic', 'chill')):
            template_type = "emotive"
        elif any(w in style for w in ('hybrid', 'experimental')):
            template_type = "hybrid"
        elif any(w in style for w in ('fibonacci', 'golden', 'phi')):
            template_type = "fibonacci"

        bpm = getattr(dna, 'bpm', 150.0)
        key = getattr(dna, 'key', 'Fm')
        template = build_arrangement(template_type, bpm=bpm, key=key)
        template_curve = arrangement_energy_curve(template)

        # Build per-bar curve from DNA arrangement
        if hasattr(dna, 'arrangement'):
            bar_idx = 0
            for sec in dna.arrangement:
                for b in range(sec.bars):
                    # Blend DNA intensity with template curve energy
                    t_energy = 0.5
                    for tc in template_curve:
                        if tc.get("start_bar", 0) <= bar_idx < tc.get("end_bar", 0):
                            t_energy = tc.get("intensity", 0.5)
                            break
                    # Ghost marker energy if available
                    g_energy = sec.intensity
                    for gm in ghost_markers:
                        if gm.get("name", "").lower() == sec.name.lower():
                            g_energy = gm.get("energy", sec.intensity)
                            break
                    # Weighted blend: 50% DNA, 30% template, 20% ghost
                    blended = (sec.intensity * 0.5 + t_energy * 0.3
                               + g_energy * 0.2)
                    curve.append({
                        "bar": bar_idx,
                        "energy": blended,
                        "section": sec.name,
                    })
                    bar_idx += 1

        n_bars = len(curve)
        if n_bars > 0:
            avg_e = sum(c["energy"] for c in curve) / n_bars
            peak_e = max(c["energy"] for c in curve)
            print(f"  ✓ energy_curve: {n_bars} bars,"
                  f" avg={avg_e:.2f}, peak={peak_e:.2f}")
        return curve
    except Exception as exc:
        log.debug("energy_curve computation skipped: %s", exc)
        return curve
