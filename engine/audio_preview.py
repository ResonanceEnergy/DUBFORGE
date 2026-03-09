"""
DUBFORGE — Audio Preview Engine  (Session 145)

Renders audio from any synth module and encodes it as base64 WAV
for inline browser playback in the SUBPHONICS chat interface.

Usage:
    from engine.audio_preview import render_preview, preview_to_html
    result = render_preview("sub_bass")
    html = preview_to_html(result)
"""

import base64
import io
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

PHI = 1.6180339887
SAMPLE_RATE = 48000


@dataclass
class AudioPreview:
    """Result of a preview render."""
    module_name: str
    duration_s: float
    sample_rate: int
    samples: int
    wav_base64: str
    peak_db: float
    rms_db: float
    elapsed_ms: float
    metadata: dict = field(default_factory=dict)


def _signal_to_wav_bytes(signal: np.ndarray, sr: int = SAMPLE_RATE) -> bytes:
    """Convert numpy signal to WAV bytes in memory."""
    signal = np.clip(signal, -1.0, 1.0)
    pcm = (signal * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


def _analyze_signal(signal: np.ndarray) -> tuple[float, float]:
    """Return peak dB and RMS dB of a signal."""
    peak = float(np.max(np.abs(signal)))
    rms = float(np.sqrt(np.mean(signal ** 2)))
    peak_db = 20 * np.log10(peak + 1e-12)
    rms_db = 20 * np.log10(rms + 1e-12)
    return round(peak_db, 1), round(rms_db, 1)


def generate_preview_signal(module_name: str,
                            duration: float = 1.0,
                            freq: float = 55.0) -> np.ndarray:
    """Generate a short preview signal for a given module type."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)

    if module_name in ("sub_bass", "bass_oneshot"):
        # Sub sine with phi-envelope
        env = np.exp(-t * PHI)
        sig = np.sin(2 * np.pi * freq * t) * env

    elif module_name in ("wobble_bass",):
        lfo = 0.5 + 0.5 * np.sin(2 * np.pi * (PHI * 3) * t)
        sig = np.sin(2 * np.pi * freq * t) * lfo
        sig *= np.exp(-t * 0.5)

    elif module_name in ("lead_synth",):
        sig = np.sin(2 * np.pi * freq * 2 * t)
        sig += 0.5 * np.sin(2 * np.pi * freq * 2 * PHI * t)
        sig *= np.exp(-t * 1.5)
        sig *= 0.6

    elif module_name in ("pad_synth", "chord_pad", "ambient_texture"):
        sig = np.zeros_like(t)
        for i, fib in enumerate([1, 2, 3, 5, 8]):
            sig += np.sin(2 * np.pi * freq * fib * t) / (i + 1)
        sig *= np.exp(-t * 0.3)
        sig *= 0.4

    elif module_name in ("drum_generator",):
        # Kick-like: pitch drop + noise burst
        pitch = freq * 4 * np.exp(-t * 30)
        body = np.sin(2 * np.pi * np.cumsum(pitch / SAMPLE_RATE))
        noise = np.random.randn(len(t)) * np.exp(-t * 50) * 0.3
        sig = (body + noise) * np.exp(-t * 8)

    elif module_name in ("perc_synth",):
        sig = np.sin(2 * np.pi * freq * 8 * t)
        sig *= np.exp(-t * 20)

    elif module_name in ("riser_synth",):
        sweep = freq * (1 + t / duration * 8)
        sig = np.sin(2 * np.pi * np.cumsum(sweep / SAMPLE_RATE))
        sig *= t / duration  # fade in

    elif module_name in ("impact_hit",):
        sig = np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t * 15)
        sig += np.random.randn(len(t)) * np.exp(-t * 30) * 0.5

    elif module_name in ("noise_generator",):
        sig = np.random.randn(len(t)) * np.exp(-t * 2) * 0.5

    elif module_name in ("arp_synth", "trance_arp"):
        sig = np.zeros_like(t)
        for i in range(8):
            note_freq = freq * (PHI ** (i % 5))
            start = int(i * len(t) / 8)
            end = int((i + 0.7) * len(t) / 8)
            if end > len(t):
                end = len(t)
            env = np.exp(-np.linspace(0, 3, end - start))
            sig[start:end] += np.sin(
                2 * np.pi * note_freq * t[start:end]) * env

    elif module_name in ("granular_synth",):
        sig = np.zeros_like(t)
        n_grains = 21  # Fibonacci
        for i in range(n_grains):
            pos = int(np.random.rand() * len(t) * 0.8)
            grain_len = int(SAMPLE_RATE * 0.03)
            if pos + grain_len > len(t):
                continue
            grain_t = np.linspace(0, 0.03, grain_len)
            grain = np.sin(2 * np.pi * freq * (1 + i * 0.2) * grain_t)
            grain *= np.hanning(grain_len)
            sig[pos:pos + grain_len] += grain * 0.3

    elif module_name in ("pluck_synth",):
        # Simple Karplus-Strong-ish
        period = int(SAMPLE_RATE / (freq * 4))
        buf = np.random.randn(period) * 0.5
        sig = np.zeros(len(t))
        for i in range(len(sig)):
            sig[i] = buf[i % period]
            buf[i % period] = 0.5 * (buf[i % period] +
                                      buf[(i + 1) % period])
        sig *= np.exp(-t * 3)

    elif module_name in ("drone_synth",):
        sig = np.sin(2 * np.pi * freq * t)
        sig += 0.5 * np.sin(2 * np.pi * freq * PHI * t)
        sig += 0.3 * np.sin(2 * np.pi * freq * PHI * PHI * t)
        sig *= 0.4

    elif module_name in ("formant_synth",):
        formants = [800, 1200, 2500]
        sig = np.zeros_like(t)
        for f in formants:
            bw = f * 0.1
            sig += np.sin(2 * np.pi * f * t) * np.exp(-t * bw / 1000)
        sig *= np.sin(2 * np.pi * freq * t)
        sig *= 0.3

    elif module_name in ("glitch_engine",):
        sig = np.random.randn(len(t)) * 0.3
        # Stutter
        chunk = len(t) // 13
        for i in range(0, len(t), chunk * 2):
            end = min(i + chunk, len(t))
            sig[i:end] = np.sin(2 * np.pi * freq * 4 * t[i:end])
        sig *= np.exp(-t * 1.0)

    elif module_name in ("riddim_engine",):
        sig = np.sin(2 * np.pi * freq * t)
        gate = (np.sin(2 * np.pi * 8 * t) > 0).astype(float)
        sig *= gate
        sig *= np.exp(-t * 1.0)

    elif module_name in ("vocal_chop",):
        formants = [600, 1000, 2800]
        sig = np.zeros_like(t)
        for f in formants:
            sig += np.sin(2 * np.pi * f * t) * 0.3
        sig *= np.sin(2 * np.pi * 5 * t) > 0  # chop
        sig *= 0.5

    else:
        # Generic sine with phi envelope
        sig = np.sin(2 * np.pi * freq * t) * np.exp(-t * PHI)

    # Normalize
    peak = np.max(np.abs(sig))
    if peak > 0:
        sig = sig / peak * 0.9

    return sig.astype(np.float64)


def render_preview(module_name: str,
                   duration: float = 1.0,
                   freq: float = 55.0) -> AudioPreview:
    """Render a preview of a module and return base64 WAV."""
    t0 = time.time()

    signal = generate_preview_signal(module_name, duration, freq)
    wav_bytes = _signal_to_wav_bytes(signal)
    wav_b64 = base64.b64encode(wav_bytes).decode("ascii")
    peak_db, rms_db = _analyze_signal(signal)

    elapsed = round((time.time() - t0) * 1000, 1)

    return AudioPreview(
        module_name=module_name,
        duration_s=duration,
        sample_rate=SAMPLE_RATE,
        samples=len(signal),
        wav_base64=wav_b64,
        peak_db=peak_db,
        rms_db=rms_db,
        elapsed_ms=elapsed,
        metadata={"freq": freq},
    )


def preview_to_html(preview: AudioPreview) -> str:
    """Generate HTML audio player for a preview."""
    return (
        f'<audio controls src="data:audio/wav;base64,{preview.wav_base64}"></audio>'
        f'<br><small>{preview.module_name} | {preview.duration_s}s | '
        f'{preview.peak_db} dBFS peak | {preview.rms_db} dBFS RMS | '
        f'{preview.elapsed_ms}ms</small>'
    )


def preview_to_dict(preview: AudioPreview) -> dict:
    """Convert preview to JSON-serializable dict."""
    return {
        "module": preview.module_name,
        "duration_s": preview.duration_s,
        "sample_rate": preview.sample_rate,
        "samples": preview.samples,
        "wav_base64": preview.wav_base64,
        "peak_db": preview.peak_db,
        "rms_db": preview.rms_db,
        "elapsed_ms": preview.elapsed_ms,
        "metadata": preview.metadata,
    }


def export_preview_wav(module_name: str,
                       output_dir: str = "output/previews",
                       duration: float = 1.0) -> str:
    """Render preview and save as .wav file."""
    signal = generate_preview_signal(module_name, duration)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"preview_{module_name}.wav"
    wav_bytes = _signal_to_wav_bytes(signal)
    path.write_bytes(wav_bytes)
    return str(path)


def main() -> None:
    modules = ["sub_bass", "wobble_bass", "lead_synth", "drum_generator",
               "pad_synth", "arp_synth", "riser_synth", "impact_hit"]
    print(f"Audio Preview Engine — rendering {len(modules)} previews")
    for mod in modules:
        preview = render_preview(mod)
        print(f"  {mod}: {preview.duration_s}s, {preview.peak_db} dBFS, "
              f"{len(preview.wav_base64)} base64 chars, {preview.elapsed_ms}ms")
    print("Done.")


if __name__ == "__main__":
    main()
