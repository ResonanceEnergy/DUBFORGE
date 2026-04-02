"""DUBFORGE — FX Pipeline.

6-stage pipeline: Riser/Impact → Transition → Glitch → Beat-Repeat → Mix → DC-block.
"""
from __future__ import annotations

import numpy as np

from engine.config_loader import PHI
from engine.dsp_core import SAMPLE_RATE, dc_block, svf_lowpass
from engine.log import get_logger

log = get_logger(__name__)

# Lazy imports for optional deps
def _import_engine(name):
    import importlib
    try:
        return importlib.import_module(f"engine.{name}")
    except ImportError:
        return None


class FxPipeline:
    """6-stage FX rendering pipeline."""

    def render_full_fx(self, dna) -> list[dict[str, np.ndarray]]:
        sections = []
        for sec in dna.arrangement:
            log.info(f"  FxPipeline: {sec.name} ({sec.bars} bars, e={sec.energy:.2f})")
            result = self._render_section(dna, sec)
            sections.append(result)
        return sections

    def _render_section(self, dna, sec) -> dict[str, np.ndarray]:
        bpm = dna.bpm
        bar_dur = 4 * 60.0 / bpm
        n_samples = round(sec.bars * bar_dur * SAMPLE_RATE)

        if "fx" not in sec.elements and "riser" not in sec.elements:
            return {"left": np.zeros(n_samples), "right": np.zeros(n_samples)}

        buf = np.zeros(n_samples, dtype=np.float64)

        # Stage 1: Risers
        if "riser" in sec.elements or sec.name.lower() in ("build", "build2"):
            buf += self._render_riser(dna, sec, n_samples)

        # Stage 2: Impacts / downlifters at section start
        if sec.name.lower() in ("drop1", "drop1b", "drop2", "drop2b"):
            buf += self._render_impact(dna, n_samples)

        # Stage 3: Transition FX
        transition_mod = _import_engine("transition_fx")
        if transition_mod and hasattr(transition_mod, "render_transition"):
            try:
                tx = transition_mod.render_transition(
                    duration=0.5, style="reverse_crash", sample_rate=SAMPLE_RATE)
                if len(tx) <= n_samples:
                    buf[:len(tx)] += tx * 0.3
            except Exception:
                pass

        # Stage 4: Glitch fills for high-energy sections
        if sec.energy > 0.8:
            glitch_mod = _import_engine("glitch_engine")
            if glitch_mod and hasattr(glitch_mod, "GlitchEngine"):
                try:
                    ge = glitch_mod.GlitchEngine()
                    fill_len = min(int(0.5 * SAMPLE_RATE), n_samples)
                    fill = ge.generate(fill_len, intensity=sec.energy)
                    buf[-fill_len:] += fill * 0.2
                except Exception:
                    pass

        # Stage 5: Beat repeat on last bar
        beat_mod = _import_engine("beat_repeat")
        if beat_mod and hasattr(beat_mod, "BeatRepeat") and sec.energy > 0.6:
            try:
                last_bar = int(bar_dur * SAMPLE_RATE)
                if last_bar <= n_samples:
                    segment = buf[-last_bar:].copy()
                    br = beat_mod.BeatRepeat()
                    repeated = br.process(segment, divisions=4)
                    buf[-len(repeated):] = repeated * 0.5
            except Exception:
                pass

        # Stage 6: DC-block
        buf = dc_block(buf)
        # Stereo: FX spread wide
        width = 0.4
        left = buf * (1.0 + width * 0.5)
        right_shifted = np.zeros_like(buf)
        shift = int(0.001 * SAMPLE_RATE)  # 1ms decorrelation
        right_shifted[shift:] = buf[:-shift] if shift < len(buf) else 0.0
        right = right_shifted * (1.0 + width * 0.5)

        return {"left": left * sec.energy, "right": right * sec.energy}

    def _render_riser(self, dna, sec, n_samples):
        riser_mod = _import_engine("riser_synth")
        if riser_mod and hasattr(riser_mod, "RiserPreset"):
            try:
                dur_s = n_samples / SAMPLE_RATE
                start_freq = getattr(dna.fx, "riser_start_freq", 150.0)
                end_freq = getattr(dna.fx, "riser_end_freq", 8000.0)
                preset = riser_mod.RiserPreset(
                    start_freq=start_freq,
                    end_freq=end_freq,
                    duration=dur_s,
                    intensity=dna.fx.riser_intensity,
                )
                audio = riser_mod.synthesize_noise_sweep(preset, sample_rate=SAMPLE_RATE)
                if len(audio) > n_samples:
                    audio = audio[:n_samples]
                elif len(audio) < n_samples:
                    padded = np.zeros(n_samples)
                    padded[:len(audio)] = audio
                    audio = padded
                return audio * 0.6
            except Exception:
                pass

        # Fallback
        t = np.arange(n_samples) / SAMPLE_RATE
        dur_s = n_samples / SAMPLE_RATE
        freq = 150.0 * (8000.0 / 150.0) ** (t / max(dur_s, 0.01))
        phase = np.cumsum(freq / SAMPLE_RATE) * 2 * np.pi
        return np.sin(phase) * np.linspace(0, 0.5, n_samples)

    def _render_impact(self, dna, n_samples):
        impact_mod = _import_engine("impact_hit")
        if impact_mod and hasattr(impact_mod, "ImpactPreset"):
            try:
                preset = impact_mod.ImpactPreset(
                    freq=dna.root_freq * 2,
                    duration=0.8,
                    style="sub_drop",
                )
                audio = impact_mod.synthesize_impact(preset, sample_rate=SAMPLE_RATE)
                buf = np.zeros(n_samples, dtype=np.float64)
                end = min(len(audio), n_samples)
                buf[:end] = audio[:end] * 0.7
                return buf
            except Exception:
                pass

        # Fallback: simple impact
        buf = np.zeros(n_samples, dtype=np.float64)
        t = np.arange(min(int(0.8 * SAMPLE_RATE), n_samples)) / SAMPLE_RATE
        impact = np.sin(2 * np.pi * 50 * t) * np.exp(-5 * t)
        buf[:len(impact)] = impact * 0.6
        return buf
