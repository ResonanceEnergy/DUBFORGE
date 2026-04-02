"""DUBFORGE — Sub-Bass Pipeline.

6-stage pipeline: Sub Synth → Clean Filter → Mono Collapse → DC-block → LP 100Hz → Limiter.
"""
from __future__ import annotations

import numpy as np

from engine.config_loader import PHI
from engine.dsp_core import SAMPLE_RATE, dc_block, svf_lowpass, osc_saw
from engine.log import get_logger

log = get_logger(__name__)


def _import_engine(name):
    import importlib
    try:
        return importlib.import_module(f"engine.{name}")
    except ImportError:
        return None


def _note_freq(dna, degree: int, octave: int = 1) -> float:
    semitones = [0, 2, 3, 5, 7, 8, 10]
    return dna.root_freq * (2.0 ** (octave - 1)) * (2.0 ** (semitones[degree % 7] / 12.0))


class SubBassPipeline:
    """6-stage sub-bass rendering pipeline.

    Sub must be:
    - Pure sine / triangle (minimal harmonics)
    - MONO below 100Hz
    - Clean (no distortion)
    - LP filtered at 100Hz
    """

    def render_full_sub(self, dna) -> list[dict[str, np.ndarray]]:
        sections = []
        for sec in dna.arrangement:
            log.info(f"  SubBassPipeline: {sec.name} ({sec.bars} bars, e={sec.energy:.2f})")
            result = self._render_section(dna, sec)
            sections.append(result)
        return sections

    def _render_section(self, dna, sec) -> dict[str, np.ndarray]:
        bpm = dna.bpm
        bar_dur = 4 * 60.0 / bpm
        beat_dur = 60.0 / bpm
        n_samples = round(sec.bars * bar_dur * SAMPLE_RATE)

        if "sub" not in sec.elements:
            return {"left": np.zeros(n_samples), "right": np.zeros(n_samples)}

        buf = np.zeros(n_samples, dtype=np.float64)

        # Get bass riff (sub follows same rhythm as midbass)
        riff = getattr(dna.bass, "bass_riff", [
            [(0, 0.0, 1.0), (0, 1.0, 1.0), (6, 2.0, 0.5), (0, 3.0, 1.0)],
        ])

        # Stage 1: Pure sine sub synthesis
        for bar_idx in range(sec.bars):
            pattern = riff[bar_idx % len(riff)]
            for degree, beat_pos, dur_beats in pattern:
                freq = _note_freq(dna, degree, octave=1)
                dur_s = dur_beats * beat_dur
                n_note = int(dur_s * SAMPLE_RATE)

                t = np.arange(n_note) / SAMPLE_RATE
                # Clean sine sub
                note = np.sin(2 * np.pi * freq * t)

                # Gentle attack/release to avoid clicks
                attack = min(int(0.005 * SAMPLE_RATE), n_note // 4)
                release = min(int(0.015 * SAMPLE_RATE), n_note // 4)
                if attack > 0:
                    note[:attack] *= np.linspace(0, 1, attack)
                if release > 0:
                    note[-release:] *= np.linspace(1, 0, release)

                offset = int((bar_idx * 4 + beat_pos) * beat_dur * SAMPLE_RATE)
                end = min(offset + len(note), n_samples)
                buf[offset:end] += note[:end - offset]

        # Stage 2: Clean filter — remove any harmonics above sub range
        buf = svf_lowpass(buf, 120.0, resonance=0.0)

        # Stage 3: Mono collapse — sub MUST be pure mono
        # (already mono since we're working with a single array)

        # Stage 4: DC-block
        buf = dc_block(buf)

        # Stage 5: Hard LP at 100Hz (brick-wall sub)
        buf = svf_lowpass(buf, 100.0, resonance=0.0)

        # Stage 6: Soft limiter to prevent sub peaks
        peak = np.max(np.abs(buf))
        if peak > 0.95:
            buf = np.tanh(buf * (0.95 / peak)) * 0.95

        # Sub is mono: identical L/R
        mono = buf * sec.energy * dna.bass.sub_weight
        return {"left": mono.copy(), "right": mono.copy()}
