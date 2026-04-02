"""DUBFORGE — Lead Pipeline.

6-stage pipeline: Melody Gen → Synthesis → Distortion/FX → Variation → Mix → DC-block.
"""
from __future__ import annotations

import numpy as np

from engine.config_loader import PHI
from engine.dsp_core import (
    SAMPLE_RATE, dc_block, svf_lowpass, osc_saw, osc_square,
    distort_foldback, saturate_aggressive,
)
from engine.log import get_logger

log = get_logger(__name__)


def _import_engine(name):
    import importlib
    try:
        return importlib.import_module(f"engine.{name}")
    except ImportError:
        return None


def _note_freq(dna, degree: int, octave: int = 4) -> float:
    """Get frequency of a scale degree in the song key."""
    semitones = [0, 2, 3, 5, 7, 8, 10]  # natural minor
    return dna.root_freq * (2.0 ** (octave - 1)) * (2.0 ** (semitones[degree % 7] / 12.0))


class LeadPipeline:
    """6-stage lead rendering pipeline."""

    def render_full_leads(self, dna) -> list[dict[str, np.ndarray]]:
        sections = []
        for sec in dna.arrangement:
            log.info(f"  LeadPipeline: {sec.name} ({sec.bars} bars, e={sec.energy:.2f})")
            result = self._render_section(dna, sec)
            sections.append(result)
        return sections

    def _render_section(self, dna, sec) -> dict[str, np.ndarray]:
        bpm = dna.bpm
        bar_dur = 4 * 60.0 / bpm
        n_samples = round(sec.bars * bar_dur * SAMPLE_RATE)

        if "lead" not in sec.elements:
            return {"left": np.zeros(n_samples), "right": np.zeros(n_samples)}

        beat_dur = 60.0 / bpm
        buf = np.zeros(n_samples, dtype=np.float64)

        # Stage 1: Generate melody pattern
        patterns = getattr(dna.lead, "melody_patterns", None)
        if patterns is None:
            patterns = [
                [(0, 0.0, 0.5, 1.0), (6, 1.0, 0.5, 0.9),
                 (4, 2.0, 0.75, 0.85), (2, 3.0, 0.5, 0.8)],
            ]

        # Stage 2: Synthesize each note
        lead_mod = _import_engine("lead_synth")

        for bar_idx in range(sec.bars):
            pattern = patterns[bar_idx % len(patterns)]
            for degree, beat_pos, dur_beats, velocity in pattern:
                if degree < 0:
                    continue
                freq = _note_freq(dna, degree, octave=4)
                dur_s = dur_beats * beat_dur
                dur_samps = int(dur_s * SAMPLE_RATE)

                # Try engine lead synth
                note = self._synth_note(lead_mod, dna, freq, dur_s)

                # Stage 3: Distortion/FX
                if sec.energy > 0.6:
                    note = distort_foldback(note, threshold=0.7)
                    note = saturate_aggressive(note, drive=1.5 + sec.energy)

                note *= velocity
                offset = int((bar_idx * 4 + beat_pos) * beat_dur * SAMPLE_RATE)
                end = min(offset + len(note), n_samples)
                buf[offset:end] += note[:end - offset]

        # Stage 4: Variation
        var_mod = _import_engine("variation_engine")
        if var_mod and hasattr(var_mod, "VariationEngine"):
            try:
                ve = var_mod.VariationEngine()
                buf = ve.apply(buf, amount=0.15 * sec.energy)
            except Exception:
                pass

        # Stage 5: Stereo placement — leads slightly wide
        width = 0.18
        shift = max(1, int(width * 0.002 * SAMPLE_RATE))
        left = buf.copy()
        right = np.zeros_like(buf)
        right[shift:] = buf[:-shift] if shift < len(buf) else 0.0

        # Apply brightness filter
        cutoff = 2000 + 8000 * dna.lead.brightness
        left = svf_lowpass(left, cutoff)
        right = svf_lowpass(right, cutoff)

        # Stage 6: DC-block
        left = dc_block(left) * sec.energy * 0.65
        right = dc_block(right) * sec.energy * 0.65

        return {"left": left, "right": right}

    def _synth_note(self, lead_mod, dna, freq, dur_s):
        """Synthesize one lead note."""
        dur_samps = int(dur_s * SAMPLE_RATE)

        if lead_mod and hasattr(lead_mod, "LeadPreset"):
            try:
                preset = lead_mod.LeadPreset(
                    freq=freq,
                    duration=dur_s,
                    style="screech",
                    brightness=dna.lead.brightness,
                    reverb=dna.lead.reverb_decay,
                )
                note = lead_mod.synthesize_screech_lead(preset, sample_rate=SAMPLE_RATE)
                return note.astype(np.float64)
            except Exception:
                pass

        # Fallback: detuned sawtooth
        saw1 = osc_saw(freq, dur_s, SAMPLE_RATE)
        saw2 = osc_saw(freq * 1.005, dur_s, SAMPLE_RATE)  # +5 cent detune
        saw3 = osc_saw(freq * 0.995, dur_s, SAMPLE_RATE)  # -5 cent detune
        note = (saw1 + saw2 * 0.7 + saw3 * 0.7) / 2.4

        # Apply amplitude envelope
        attack = min(int(0.005 * SAMPLE_RATE), len(note) // 4)
        release = min(int(0.05 * SAMPLE_RATE), len(note) // 4)
        if attack > 0:
            note[:attack] *= np.linspace(0, 1, attack)
        if release > 0:
            note[-release:] *= np.linspace(1, 0, release)

        return note
