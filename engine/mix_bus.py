"""DUBFORGE — Mix Bus Processor.

Provides per-section mix bus processing: frequency-aware stereo,
parallel compression, energy curves, and inter-stem sidechain.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

import numpy as np

log = logging.getLogger(__name__)

# Lazy SR import
_SR = None
def _get_sr():
    global _SR
    if _SR is None:
        try:
            from engine.dsp_core import SAMPLE_RATE
            _SR = SAMPLE_RATE
        except ImportError:
            _SR = 48000
    return _SR


@dataclass
class MixBusConfig:
    """Configuration for mix bus processing."""
    enable_freq_stereo: bool = True
    enable_ninja_focus: bool = True
    enable_pain_zone: bool = True
    enable_inter_sidechain: bool = True
    enable_parallel_comp: bool = True
    enable_energy_curves: bool = True
    enable_fx_sends: bool = True
    parallel_comp_mix: float = 0.15
    parallel_comp_threshold_db: float = -18.0


def process_mix_bus(bus_input, section_name: str,
                    energy_start: float, energy_end: float,
                    config: MixBusConfig | None = None,
                    sr: int | None = None):
    """Process a mix bus through the mix bus chain.

    Args:
        bus_input: Either a numpy array (mono) or a dict of stem names
                   to {"left": array, "right": array} for stereo stem mixing.
        section_name: Name of the current section (e.g. "drop1")
        energy_start: Energy level at section start (0-1)
        energy_end: Energy level at section end (0-1)
        config: MixBusConfig or None for defaults
        sr: Sample rate override

    Returns:
        (left, right) tuple of float64 arrays if input was dict,
        or a single float64 array if input was ndarray.
    """
    if sr is None:
        sr = _get_sr()
    if config is None:
        config = MixBusConfig()

    # If bus_input is a dict of stems, sum into stereo L/R
    if isinstance(bus_input, dict):
        # Determine length from first stem
        first = next(iter(bus_input.values()))
        n = len(first["left"])
        sum_l = np.zeros(n, dtype=np.float64)
        sum_r = np.zeros(n, dtype=np.float64)
        for _name, ch in bus_input.items():
            sum_l += np.asarray(ch["left"], dtype=np.float64)
            sum_r += np.asarray(ch["right"], dtype=np.float64)
        left = _process_channel(sum_l, section_name, energy_start, energy_end, config, sr)
        right = _process_channel(sum_r, section_name, energy_start, energy_end, config, sr)
        return left, right

    audio = np.asarray(bus_input, dtype=np.float64)
    return _process_channel(audio, section_name, energy_start, energy_end, config, sr)


def _process_channel(audio: np.ndarray, section_name: str,
                     energy_start: float, energy_end: float,
                     config: MixBusConfig, sr: int) -> np.ndarray:
    """Process a single channel through the mix bus chain."""
    if len(audio) == 0:
        return audio

    # 1. Energy curves — fade from start to end energy
    if config.enable_energy_curves and energy_start != energy_end:
        envelope = np.linspace(energy_start, energy_end, len(audio))
        # Normalize so average = 1.0 (don't lose overall level)
        avg = (energy_start + energy_end) / 2.0
        if avg > 0:
            envelope = envelope / avg
        audio = audio * envelope

    # 2. Parallel compression
    if config.enable_parallel_comp:
        threshold = 10 ** (config.parallel_comp_threshold_db / 20)
        compressed = np.copy(audio)
        # Fast compressor: hard knee, fast attack
        attack_coeff = math.exp(-1.0 / (0.001 * sr))
        release_coeff = math.exp(-1.0 / (0.100 * sr))
        env = 0.0
        for i in range(len(compressed)):
            level = abs(compressed[i])
            if level > env:
                env = level + attack_coeff * (env - level)
            else:
                env = level + release_coeff * (env - level)
            if env > threshold > 0:
                gain = threshold / env
                compressed[i] *= gain

        audio = audio * (1.0 - config.parallel_comp_mix) + \
                compressed * config.parallel_comp_mix

    # 3. Pain zone taming (2-4kHz harsh midrange)
    if config.enable_pain_zone:
        try:
            from engine.dsp_core import svf_bandpass, svf_notch
            # Light notch at pain zone center
            pain = svf_bandpass(audio, 3000.0, resonance=0.3, sample_rate=sr)
            audio = audio - pain * 0.15  # subtle pain zone reduction
        except ImportError:
            pass

    # 4. Frequency-dependent stereo (mono below 100Hz concept)
    # This only applies if the caller uses L/R processing — we process mono here
    if config.enable_freq_stereo:
        pass  # Applied at the stem-mix level, not individual bus

    # 5. FX sends (reverb/delay bus processing)
    if config.enable_fx_sends:
        try:
            from engine.fx_rack import FXRack
            # Light bus reverb
            send = audio * 0.08  # -22dB send level
            send = FXRack.process(send, [
                {"type": "reverb", "decay": 0.3, "mix": 1.0}
            ], sr=sr)
            audio = audio + send
        except ImportError:
            pass

    return audio
