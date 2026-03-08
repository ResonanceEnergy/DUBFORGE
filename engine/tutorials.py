"""
DUBFORGE — Tutorial Scripts  (Session 138)

Five tutorial scripts covering core workflows.
Each returns a results dict for testability.
"""

import io
import wave
from typing import Any

import numpy as np

PHI = 1.6180339887
SAMPLE_RATE = 44100


def _make_tone(freq: float, dur: float = 1.0, amp: float = 0.5) -> np.ndarray:
    """Generate a simple sine tone."""
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    return amp * np.sin(2 * np.pi * freq * t)


def _to_wav_bytes(signal: np.ndarray) -> bytes:
    pcm = (np.clip(signal, -1, 1) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════
# TUTORIAL 1: PHI FUNDAMENTALS
# ═══════════════════════════════════════════════════════════════════════════

def tutorial_phi_fundamentals() -> dict[str, Any]:
    """Demonstrate phi ratios in frequency and time."""
    base_freq = 432.0
    phi_freq = base_freq * PHI
    ratio = phi_freq / base_freq

    # Fibonacci timing
    fib = [1, 1, 2, 3, 5, 8, 13, 21]
    fib_ratios = [fib[i + 1] / fib[i] for i in range(len(fib) - 1)]

    # Generate signals at phi-related frequencies
    sig_base = _make_tone(base_freq, 0.5)
    sig_phi = _make_tone(phi_freq, 0.5)
    combined = sig_base + sig_phi * 0.5

    return {
        "tutorial": "phi_fundamentals",
        "base_freq": base_freq,
        "phi_freq": round(phi_freq, 2),
        "ratio": round(ratio, 10),
        "fib_sequence": fib,
        "fib_ratios": [round(r, 6) for r in fib_ratios],
        "converges_to_phi": abs(fib_ratios[-1] - PHI) < 0.01,
        "signal_length": len(combined),
    }


# ═══════════════════════════════════════════════════════════════════════════
# TUTORIAL 2: SOUND DESIGN BASICS
# ═══════════════════════════════════════════════════════════════════════════

def tutorial_sound_design() -> dict[str, Any]:
    """Show sine, saw, square synthesis and harmonics."""
    dur = 0.5
    freq = 55.0  # sub bass
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)

    # Sine
    sine = 0.5 * np.sin(2 * np.pi * freq * t)
    # Saw (additive)
    saw = np.zeros_like(t)
    for h in range(1, 16):
        saw += ((-1) ** (h + 1)) * np.sin(2 * np.pi * freq * h * t) / h
    saw *= 0.5 / np.max(np.abs(saw) + 1e-12)
    # Square (odd harmonics)
    sq = np.zeros_like(t)
    for h in range(1, 16, 2):
        sq += np.sin(2 * np.pi * freq * h * t) / h
    sq *= 0.5 / np.max(np.abs(sq) + 1e-12)

    return {
        "tutorial": "sound_design",
        "frequency": freq,
        "waveforms": ["sine", "saw", "square"],
        "harmonic_count": {"sine": 1, "saw": 15, "square": 8},
        "peak_sine": round(float(np.max(np.abs(sine))), 4),
        "peak_saw": round(float(np.max(np.abs(saw))), 4),
        "peak_square": round(float(np.max(np.abs(sq))), 4),
        "sample_count": len(t),
    }


# ═══════════════════════════════════════════════════════════════════════════
# TUTORIAL 3: FX PROCESSING
# ═══════════════════════════════════════════════════════════════════════════

def tutorial_fx_processing() -> dict[str, Any]:
    """Demonstrate distortion, filtering, and reverb concepts."""
    sig = _make_tone(110.0, 0.5)

    # Soft clip distortion
    drive = 3.0
    dist = np.tanh(sig * drive)
    dist *= 0.5 / (np.max(np.abs(dist)) + 1e-12)

    # Simple low-pass via moving average
    kernel_size = 21
    kernel = np.ones(kernel_size) / kernel_size
    filtered = np.convolve(sig, kernel, mode="same")

    # Simple comb reverb
    delay_samples = int(0.03 * SAMPLE_RATE)
    reverb = np.copy(sig)
    for i in range(delay_samples, len(reverb)):
        reverb[i] += reverb[i - delay_samples] * 0.5

    return {
        "tutorial": "fx_processing",
        "effects": ["distortion", "lowpass", "comb_reverb"],
        "drive": drive,
        "filter_kernel": kernel_size,
        "delay_ms": 30,
        "rms_dry": round(float(np.sqrt(np.mean(sig ** 2))), 4),
        "rms_dist": round(float(np.sqrt(np.mean(dist ** 2))), 4),
        "rms_filtered": round(float(np.sqrt(np.mean(filtered ** 2))), 4),
        "rms_reverb": round(float(np.sqrt(np.mean(reverb ** 2))), 4),
    }


# ═══════════════════════════════════════════════════════════════════════════
# TUTORIAL 4: ARRANGEMENT & STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════

def tutorial_arrangement() -> dict[str, Any]:
    """Show song structure using Fibonacci bar counts."""
    structure = {
        "intro": 8,
        "buildup_1": 13,
        "drop_1": 21,
        "breakdown": 8,
        "buildup_2": 13,
        "drop_2": 34,
        "outro": 13,
    }
    total_bars = sum(structure.values())
    bpm = 150
    beats_per_bar = 4
    total_beats = total_bars * beats_per_bar
    duration_min = total_beats / bpm

    # Phi ratios between adjacent sections
    sections = list(structure.values())
    ratios = [sections[i + 1] / sections[i] for i in range(len(sections) - 1)]

    return {
        "tutorial": "arrangement",
        "structure": structure,
        "total_bars": total_bars,
        "bpm": bpm,
        "duration_min": round(duration_min, 2),
        "section_ratios": [round(r, 4) for r in ratios],
        "fibonacci_sections": all(b in [1, 2, 3, 5, 8, 13, 21, 34, 55, 89] for b in sections),
    }


# ═══════════════════════════════════════════════════════════════════════════
# TUTORIAL 5: EXPORT WORKFLOW
# ═══════════════════════════════════════════════════════════════════════════

def tutorial_export_workflow() -> dict[str, Any]:
    """Demonstrate the render → analyze → export pipeline."""
    # Render
    sig = _make_tone(432.0, 1.0)
    wav_bytes = _to_wav_bytes(sig)

    # Analyze
    spectrum = np.abs(np.fft.rfft(sig))
    freqs = np.fft.rfftfreq(len(sig), 1.0 / SAMPLE_RATE)
    peak_freq_idx = int(np.argmax(spectrum))
    peak_freq = float(freqs[peak_freq_idx])

    return {
        "tutorial": "export_workflow",
        "render_samples": len(sig),
        "wav_size_bytes": len(wav_bytes),
        "peak_frequency": round(peak_freq, 2),
        "formats": ["wav", "fxp", "als", "json"],
        "pipeline_stages": ["render", "analyze", "export"],
        "status": "complete",
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

ALL_TUTORIALS = {
    "phi_fundamentals": tutorial_phi_fundamentals,
    "sound_design": tutorial_sound_design,
    "fx_processing": tutorial_fx_processing,
    "arrangement": tutorial_arrangement,
    "export_workflow": tutorial_export_workflow,
}


def run_all_tutorials() -> dict[str, dict]:
    """Run all tutorials and return results."""
    results = {}
    for name, fn in ALL_TUTORIALS.items():
        results[name] = fn()
    return results


def main() -> None:
    results = run_all_tutorials()
    print(f"Tutorials: {len(results)} completed")
    for name, r in results.items():
        print(f"  [{r.get('tutorial', name)}] OK")


if __name__ == "__main__":
    main()
