"""DUBFORGE — Atmosphere Pipeline.

6-stage pipeline: Pad → Drone → Noise Bed → Convolution → Variation → DC-block.
"""
from __future__ import annotations

import numpy as np

from engine.config_loader import PHI
from engine.dsp_core import SAMPLE_RATE, dc_block, svf_lowpass
from engine.log import get_logger

log = get_logger(__name__)


def _import_engine(name):
    import importlib
    try:
        return importlib.import_module(f"engine.{name}")
    except ImportError:
        return None


def _note_freq(dna, degree: int, octave: int = 3) -> float:
    semitones = [0, 2, 3, 5, 7, 8, 10]
    return dna.root_freq * (2.0 ** (octave - 1)) * (2.0 ** (semitones[degree % 7] / 12.0))


class AtmosPipeline:
    """6-stage atmosphere rendering pipeline."""

    def render_full_atmos(self, dna) -> list[dict[str, np.ndarray]]:
        sections = []
        for sec in dna.arrangement:
            log.info(f"  AtmosPipeline: {sec.name} ({sec.bars} bars, e={sec.energy:.2f})")
            result = self._render_section(dna, sec)
            sections.append(result)
        return sections

    def _render_section(self, dna, sec) -> dict[str, np.ndarray]:
        bpm = dna.bpm
        bar_dur = 4 * 60.0 / bpm
        n_samples = round(sec.bars * bar_dur * SAMPLE_RATE)

        if "pad" not in sec.elements and "drone" not in sec.elements and \
           "noise_bed" not in sec.elements:
            return {"left": np.zeros(n_samples), "right": np.zeros(n_samples)}

        buf = np.zeros(n_samples, dtype=np.float64)

        # Stage 1: Pad
        if "pad" in sec.elements:
            buf += self._render_pad(dna, sec, n_samples) * 0.5

        # Stage 2: Drone
        if "drone" in sec.elements:
            buf += self._render_drone(dna, sec, n_samples) * 0.4

        # Stage 3: Noise bed
        if "noise_bed" in sec.elements:
            buf += self._render_noise_bed(dna, sec, n_samples) * 0.25

        # Stage 4: Convolution reverb
        conv_mod = _import_engine("convolution")
        if conv_mod and hasattr(conv_mod, "ConvolutionReverb"):
            try:
                reverb = conv_mod.ConvolutionReverb()
                buf = reverb.process(buf, decay=dna.atmosphere.reverb_size,
                                     mix=0.3, sample_rate=SAMPLE_RATE)
            except Exception:
                pass

        # Stage 5: Variation
        var_mod = _import_engine("variation_engine")
        if var_mod and hasattr(var_mod, "VariationEngine"):
            try:
                ve = var_mod.VariationEngine()
                buf = ve.apply(buf, amount=0.1)
            except Exception:
                pass

        # Stage 6: DC-block + stereo spread
        buf = dc_block(buf)

        # Atmos wide stereo
        width = 0.3
        shift = max(1, int(width * 0.003 * SAMPLE_RATE))
        left = buf.copy()
        right = np.zeros_like(buf)
        right[shift:] = buf[:-shift] if shift < len(buf) else 0.0

        left *= sec.energy
        right *= sec.energy

        return {"left": left, "right": right}

    def _render_pad(self, dna, sec, n_samples):
        pad_mod = _import_engine("pad_synth")
        dur_s = n_samples / SAMPLE_RATE
        root = _note_freq(dna, 0, octave=3)
        third = _note_freq(dna, 2, octave=3)
        fifth = _note_freq(dna, 4, octave=3)

        buf = np.zeros(n_samples, dtype=np.float64)

        if pad_mod and hasattr(pad_mod, "PadPreset"):
            try:
                for freq in [root, third, fifth]:
                    preset = pad_mod.PadPreset(
                        freq=freq, duration=dur_s, style="dark",
                        attack=dna.atmosphere.pad_attack,
                        brightness=dna.atmosphere.pad_brightness,
                    )
                    audio = pad_mod.synthesize_dark_pad(preset, sample_rate=SAMPLE_RATE)
                    n = min(len(audio), n_samples)
                    buf[:n] += audio[:n] * 0.33
                return buf
            except Exception:
                pass

        # Fallback: additive pad
        t = np.arange(n_samples) / SAMPLE_RATE
        for freq in [root, third, fifth]:
            buf += np.sin(2 * np.pi * freq * t) * 0.2
            buf += np.sin(2 * np.pi * freq * 2 * t) * 0.05
        attack = min(int(dna.atmosphere.pad_attack * SAMPLE_RATE), n_samples // 3)
        release = min(int(2.0 * SAMPLE_RATE), n_samples // 3)
        if attack > 0:
            buf[:attack] *= np.linspace(0, 1, attack)
        if release > 0:
            buf[-release:] *= np.linspace(1, 0, release)
        return buf

    def _render_drone(self, dna, sec, n_samples):
        drone_mod = _import_engine("drone_synth")
        dur_s = n_samples / SAMPLE_RATE

        if drone_mod and hasattr(drone_mod, "DronePreset"):
            try:
                preset = drone_mod.DronePreset(
                    freq=dna.root_freq * 2,
                    duration=dur_s,
                    voices=dna.atmosphere.drone_voices,
                    movement=dna.atmosphere.drone_movement,
                )
                audio = drone_mod.synthesize_drone(preset, sample_rate=SAMPLE_RATE)
                n = min(len(audio), n_samples)
                buf = np.zeros(n_samples)
                buf[:n] = audio[:n]
                return buf
            except Exception:
                pass

        # Fallback
        t = np.arange(n_samples) / SAMPLE_RATE
        freq = dna.root_freq * 2
        buf = np.zeros(n_samples, dtype=np.float64)
        for v in range(5):
            detune = 1.0 + (v - 2) * 0.003 * PHI
            buf += np.sin(2 * np.pi * freq * detune * t) * 0.15
        fade = min(int(2.0 * SAMPLE_RATE), n_samples // 4)
        if fade > 0:
            buf[:fade] *= np.linspace(0, 1, fade)
            buf[-fade:] *= np.linspace(1, 0, fade)
        return buf

    def _render_noise_bed(self, dna, sec, n_samples):
        noise_level = getattr(dna.atmosphere, "noise_bed_level", 0.12)
        noise_mod = _import_engine("noise_generator")

        if noise_mod and hasattr(noise_mod, "NoisePreset"):
            try:
                dur_s = n_samples / SAMPLE_RATE
                preset = noise_mod.NoisePreset(
                    duration=dur_s,
                    noise_type="pink",
                    level=noise_level,
                )
                audio = noise_mod.synthesize_noise(preset, sample_rate=SAMPLE_RATE)
                n = min(len(audio), n_samples)
                buf = np.zeros(n_samples)
                buf[:n] = audio[:n]
                # Gate at -50dB
                gate_thresh = 10 ** (-50 / 20)
                buf[np.abs(buf) < gate_thresh] = 0.0
                return buf
            except Exception:
                pass

        # Fallback
        rng = np.random.default_rng(42)
        noise = rng.standard_normal(n_samples)
        pink = np.cumsum(noise)
        pink -= np.linspace(pink[0], pink[-1], n_samples)
        pink /= (np.max(np.abs(pink)) + 1e-12)
        fade = min(int(1.0 * SAMPLE_RATE), n_samples // 4)
        if fade > 0:
            pink[:fade] *= np.linspace(0, 1, fade)
            pink[-fade:] *= np.linspace(1, 0, fade)
        return pink * noise_level
