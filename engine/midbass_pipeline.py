"""DUBFORGE — Mid-Bass Pipeline.

6-stage pipeline: Bass Synth → Growl Resample → PSBS Separation → Distortion → Variation → DC-block.
"""
from __future__ import annotations

import numpy as np

from engine.config_loader import PHI
from engine.dsp_core import (
    SAMPLE_RATE, dc_block, svf_lowpass, svf_highpass,
    osc_saw, osc_square, distort_foldback, saturate_aggressive,
)
from engine.log import get_logger

log = get_logger(__name__)


def _import_engine(name):
    import importlib
    try:
        return importlib.import_module(f"engine.{name}")
    except ImportError:
        return None


def _note_freq(dna, degree: int, octave: int = 2) -> float:
    semitones = [0, 2, 3, 5, 7, 8, 10]
    return dna.root_freq * (2.0 ** (octave - 1)) * (2.0 ** (semitones[degree % 7] / 12.0))


class MidBassPipeline:
    """6-stage mid-bass rendering pipeline.

    Handles both the clean sub layer and the aggressive mid-range growl.
    """

    def render_full_midbass(self, dna) -> list[dict[str, np.ndarray]]:
        sections = []
        for sec in dna.arrangement:
            log.info(f"  MidBassPipeline: {sec.name} ({sec.bars} bars, e={sec.energy:.2f})")
            result = self._render_section(dna, sec)
            sections.append(result)
        return sections

    def _render_section(self, dna, sec) -> dict[str, np.ndarray]:
        bpm = dna.bpm
        bar_dur = 4 * 60.0 / bpm
        beat_dur = 60.0 / bpm
        n_samples = round(sec.bars * bar_dur * SAMPLE_RATE)

        if "midbass" not in sec.elements and "bass" not in sec.elements:
            return {"left": np.zeros(n_samples), "right": np.zeros(n_samples)}

        buf = np.zeros(n_samples, dtype=np.float64)

        # Get bass riff pattern
        riff = getattr(dna.bass, "bass_riff", [
            [(0, 0.0, 1.0), (0, 1.0, 1.0), (6, 2.0, 0.5), (0, 3.0, 1.0)],
        ])

        # Stage 1: Synthesize raw bass notes
        bass_mod = _import_engine("bass_oneshot")

        for bar_idx in range(sec.bars):
            pattern = riff[bar_idx % len(riff)]
            for degree, beat_pos, dur_beats in pattern:
                freq = _note_freq(dna, degree, octave=2)
                dur_s = dur_beats * beat_dur

                note = self._synth_bass(bass_mod, dna, freq, dur_s)

                offset = int((bar_idx * 4 + beat_pos) * beat_dur * SAMPLE_RATE)
                end = min(offset + len(note), n_samples)
                buf[offset:end] += note[:end - offset]

        # Stage 2: Growl resampler (mid-range aggression)
        growl_mod = _import_engine("growl_resampler")
        if growl_mod and hasattr(growl_mod, "GrowlResampler") and sec.energy > 0.5:
            try:
                gr = growl_mod.GrowlResampler()
                # Extract mid-range for growl processing
                mid = svf_highpass(svf_lowpass(buf, 2000.0), 200.0)
                # Apply growl processing (no bit reduction!)
                mid_growl = gr.process(mid, intensity=sec.energy * 0.7)
                # Mix back
                sub = svf_lowpass(buf, 200.0)
                buf = sub + mid_growl
            except Exception:
                pass

        # Stage 3: PSBS frequency separation
        psbs_mod = _import_engine("psbs")
        if psbs_mod and hasattr(psbs_mod, "PSBSSplitter"):
            try:
                splitter = psbs_mod.PSBSSplitter()
                bands = splitter.split(buf, crossovers=[89, 233, 610])
                # Process each band independently
                if len(bands) >= 4:
                    # Sub: clean
                    bands[0] = bands[0] * 1.0
                    # Low: light saturation
                    bands[1] = saturate_aggressive(bands[1], drive=1.2)
                    # Mid: heavy distortion
                    bands[2] = distort_foldback(bands[2], threshold=0.6)
                    # High: presence
                    bands[3] = bands[3] * 0.8
                buf = sum(bands)
            except Exception:
                pass

        # Stage 4: Additional distortion for drops
        if sec.energy > 0.7:
            # Parallel distortion: mix dry + wet
            wet = saturate_aggressive(buf, drive=2.0 + sec.energy)
            buf = buf * 0.6 + wet * 0.4

        # Stage 5: Variation
        var_mod = _import_engine("variation_engine")
        if var_mod and hasattr(var_mod, "VariationEngine"):
            try:
                ve = var_mod.VariationEngine()
                buf = ve.apply(buf, amount=0.2 * sec.energy)
            except Exception:
                pass

        # Stage 6: DC-block
        buf = dc_block(buf)

        # Mid-bass stereo: sub mono, mid slightly wide
        sub = svf_lowpass(buf, 100.0)
        mid = buf - sub

        left = sub + mid * 1.05
        right = sub + mid * 0.95

        left *= sec.energy * 0.85
        right *= sec.energy * 0.85

        return {"left": left, "right": right}

    def _synth_bass(self, bass_mod, dna, freq, dur_s):
        """Synthesize a single bass note."""
        if bass_mod and hasattr(bass_mod, "BassPreset"):
            try:
                preset = bass_mod.BassPreset(
                    freq=freq, duration=dur_s, style="sub_bass",
                    drive=dna.bass.distortion, sub_weight=dna.bass.sub_weight,
                )
                return bass_mod.synthesize_bass(preset, sample_rate=SAMPLE_RATE).astype(np.float64)
            except Exception:
                pass

        # Fallback: detuned saw + sub sine
        n = int(dur_s * SAMPLE_RATE)
        t = np.arange(n) / SAMPLE_RATE
        sub = np.sin(2 * np.pi * freq * t) * 0.7
        mid = osc_saw(freq * 2, dur_s, SAMPLE_RATE)
        if len(mid) > n:
            mid = mid[:n]
        elif len(mid) < n:
            padded = np.zeros(n)
            padded[:len(mid)] = mid
            mid = padded
        note = sub + mid * 0.3

        # Envelope
        attack = min(int(0.003 * SAMPLE_RATE), n // 4)
        release = min(int(0.02 * SAMPLE_RATE), n // 4)
        if attack > 0:
            note[:attack] *= np.linspace(0, 1, attack)
        if release > 0:
            note[-release:] *= np.linspace(1, 0, release)
        return note
