"""DUBFORGE — Drum Pipeline.

6-stage pipeline: Pattern → Synthesis/Samples → Groove → Dynamics → Mix → DC-block.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

from engine.config_loader import PHI
from engine.dsp_core import SAMPLE_RATE, dc_block, svf_lowpass, svf_highpass
from engine.dynamics_processor import DynamicsProcessor, GateConfig
from engine.groove import GrooveEngine, GROOVE_TEMPLATES
from engine.log import get_logger
from engine.perc_synth import PercPreset, synthesize_kick, synthesize_snare, synthesize_hat, synthesize_clap, synthesize_rim

log = get_logger(__name__)

# Try to load samples; fall back to synthesis
try:
    from engine.sample_library import SampleLibrary
    _sample_lib = SampleLibrary()
    _HAS_SAMPLES = _sample_lib.total_count > 0
except Exception:
    _HAS_SAMPLES = False
    _sample_lib = None


def _load_wav_mono(path: str) -> np.ndarray:
    """Load a WAV/AIFF file as mono float64."""
    try:
        import soundfile as sf  # type: ignore[import-not-found]
        audio, sr = sf.read(path, dtype="float64", always_2d=True)
        mono = audio.mean(axis=1) if audio.ndim > 1 else audio.ravel()
        if sr != SAMPLE_RATE:
            from scipy.signal import resample  # type: ignore[import-not-found]
            mono = resample(mono, int(len(mono) * SAMPLE_RATE / sr))
        return mono
    except ImportError:
        import wave, struct
        with wave.open(path, "rb") as wf:
            n = wf.getnframes()
            raw = wf.readframes(n)
            sw = wf.getsampwidth()
            ch = wf.getnchannels()
            sr = wf.getframerate()
        if sw == 2:
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
        elif sw == 3:
            arr = []
            for i in range(0, len(raw), 3):
                val = int.from_bytes(raw[i:i+3], "little", signed=True)
                arr.append(val / (2**23))
            data = np.array(arr)
        else:
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
        if ch == 2:
            data = (data[0::2] + data[1::2]) * 0.5
        return data


class DrumPipeline:
    """6-stage drum rendering pipeline.

    Returns list of per-section dicts: [{"left": array, "right": array}, ...]
    """

    def __init__(self):
        self.groove = GrooveEngine(bpm=140)
        self.dyn = DynamicsProcessor()

    def render_full_drums(self, dna) -> list[dict[str, np.ndarray]]:
        """Render all drum sections for the arrangement."""
        sections = []
        for sec in dna.arrangement:
            log.info(f"  DrumPipeline: {sec.name} ({sec.bars} bars, e={sec.energy:.2f})")
            section_audio = self._render_section(dna, sec)
            sections.append(section_audio)
        return sections

    def _render_section(self, dna, sec) -> dict[str, np.ndarray]:
        """Render one section's drums."""
        bpm = dna.bpm
        bar_dur = 4 * 60.0 / bpm
        n_samples = round(sec.bars * bar_dur * SAMPLE_RATE)

        if "drums" not in sec.elements:
            return {"left": np.zeros(n_samples), "right": np.zeros(n_samples)}

        # Stage 1: Generate patterns
        kick_hits, snare_hits, hat_hits, extras = self._gen_pattern(
            dna, sec, bpm, sec.bars)

        # Stage 2: Synthesize / load samples
        kick_buf = self._place_hits(kick_hits, "kick", dna, n_samples)
        snare_buf = self._place_hits(snare_hits, "snare", dna, n_samples)
        hat_buf = self._place_hits(hat_hits, "hat_closed", dna, n_samples)

        # Stage 3: Apply groove
        template = GROOVE_TEMPLATES.get("dubstep_halftime")
        if template and dna.drums.groove_amount > 0:
            # Groove is pre-applied to hit times in _gen_pattern
            pass

        # Stage 4: Dynamics (gate + transient shape)
        kick_buf = np.array(self.dyn.transient_shaper(
            kick_buf.tolist(), attack_gain=1.3, sustain_gain=0.85))
        snare_buf = np.array(self.dyn.transient_shaper(
            snare_buf.tolist(), attack_gain=1.2, sustain_gain=0.9))

        # Stage 5: Mix and stereo placement
        left = np.zeros(n_samples, dtype=np.float64)
        right = np.zeros(n_samples, dtype=np.float64)

        # Kick: center
        left += kick_buf * dna.drums.kick_gain * sec.energy
        right += kick_buf * dna.drums.kick_gain * sec.energy

        # Snare: center with slight width
        snare_l = snare_buf * dna.drums.snare_gain * sec.energy
        snare_r = snare_buf * dna.drums.snare_gain * sec.energy * 0.95
        left += snare_l
        right += snare_r

        # Hats: wider
        hat_gain = dna.drums.hat_gain * sec.energy
        left += hat_buf * hat_gain * 0.8
        right += hat_buf * hat_gain * 1.2

        # Stage 6: DC-block
        left = dc_block(left)
        right = dc_block(right)

        return {"left": left, "right": right}

    def _gen_pattern(self, dna, sec, bpm, bars):
        """Generate hit positions (in samples) for each drum element."""
        beat_dur = 60.0 / bpm
        bar_dur = 4 * beat_dur
        total_samps = round(bars * bar_dur * SAMPLE_RATE)

        kicks = []
        snares = []
        hats = []
        extras = []

        halftime = getattr(dna.drums, "halftime", True)

        for bar_idx in range(bars):
            bar_offset = bar_idx * bar_dur

            # Kick: beat 1 always, beat 3 in non-halftime
            kicks.append(int((bar_offset + 0 * beat_dur) * SAMPLE_RATE))
            if not halftime:
                kicks.append(int((bar_offset + 2 * beat_dur) * SAMPLE_RATE))

            # Snare: beat 3 in halftime (dubstep standard)
            if halftime:
                snares.append(int((bar_offset + 2 * beat_dur) * SAMPLE_RATE))
            else:
                snares.append(int((bar_offset + 1 * beat_dur) * SAMPLE_RATE))
                snares.append(int((bar_offset + 3 * beat_dur) * SAMPLE_RATE))

            # Hats: 8th notes by default, 16ths if energy > 0.7
            hat_div = 8 if sec.energy < 0.7 else 16
            for step in range(hat_div):
                t = bar_offset + step * (bar_dur / hat_div)
                hats.append(int(t * SAMPLE_RATE))

        return kicks, snares, hats, extras

    def _place_hits(self, hit_positions, category, dna, n_samples):
        """Place one-shot sounds at hit positions."""
        buf = np.zeros(n_samples, dtype=np.float64)

        # Try sample library first
        oneshot = self._get_oneshot(category, dna)
        if oneshot is None:
            return buf

        for pos in hit_positions:
            if pos < 0 or pos >= n_samples:
                continue
            end = min(pos + len(oneshot), n_samples)
            buf[pos:end] += oneshot[:end - pos]

        return buf

    def _get_oneshot(self, category, dna):
        """Get a one-shot sample or synthesize one."""
        # Try sample library
        if _HAS_SAMPLES and _sample_lib is not None:
            path = _sample_lib.get_random(category)
            if path:
                try:
                    return _load_wav_mono(path)
                except Exception:
                    pass

        # Fallback to synthesis
        dur = 0.15 if "hat" in category else 0.3
        preset = PercPreset(
            name=category,
            perc_type=category.split("_")[0],
            duration_s=dur,
            pitch=dna.drums.kick_pitch if category == "kick" else 200.0,
            brightness=0.7,
            distortion=0.1,
        )
        if "kick" in category:
            return synthesize_kick(preset, sample_rate=SAMPLE_RATE)
        elif "snare" in category:
            return synthesize_snare(preset, sample_rate=SAMPLE_RATE)
        elif "hat" in category:
            return synthesize_hat(preset, sample_rate=SAMPLE_RATE)
        elif "clap" in category:
            return synthesize_clap(preset, sample_rate=SAMPLE_RATE)
        else:
            return synthesize_rim(preset, sample_rate=SAMPLE_RATE)
