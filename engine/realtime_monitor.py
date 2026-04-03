"""
DUBFORGE — Real-Time Monitor  (Session 139)

Live phase-coherence display prototype.
Captures signal snapshots, computes phi metrics in real-time.
"""

import json
import time
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from engine.config_loader import PHI
from engine.accel import fft, ifft
SAMPLE_RATE = 48000


@dataclass
class MonitorSnapshot:
    """A single monitoring snapshot."""
    timestamp: float
    rms: float
    peak: float
    spectral_centroid: float
    phi_coherence: float
    crest_factor: float


@dataclass
class MonitorSession:
    """A monitoring session with history."""
    snapshots: list[MonitorSnapshot] = field(default_factory=list)
    max_history: int = 256

    def add(self, snap: MonitorSnapshot) -> None:
        self.snapshots.append(snap)
        if len(self.snapshots) > self.max_history:
            self.snapshots = self.snapshots[-self.max_history:]

    def latest(self) -> Optional[MonitorSnapshot]:
        return self.snapshots[-1] if self.snapshots else None

    def avg_phi_coherence(self) -> float:
        if not self.snapshots:
            return 0.0
        return sum(s.phi_coherence for s in self.snapshots) / len(self.snapshots)

    def peak_rms(self) -> float:
        if not self.snapshots:
            return 0.0
        return max(s.rms for s in self.snapshots)

    def to_dict(self) -> dict:
        return {
            "n_snapshots": len(self.snapshots),
            "avg_phi_coherence": round(self.avg_phi_coherence(), 6),
            "peak_rms": round(self.peak_rms(), 6),
            "latest": asdict(self.latest()) if self.latest() else None,
        }


# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def analyze_chunk(signal: np.ndarray, sr: int = SAMPLE_RATE) -> MonitorSnapshot:
    """Analyze a chunk of audio signal."""
    if len(signal) == 0:
        return MonitorSnapshot(
            timestamp=time.time(), rms=0.0, peak=0.0,
            spectral_centroid=0.0, phi_coherence=0.0, crest_factor=0.0)

    rms = float(np.sqrt(np.mean(signal ** 2)))
    peak = float(np.max(np.abs(signal)))

    # Spectral centroid
    n_fft = min(len(signal), 4096)
    spectrum = np.abs(fft(signal[:n_fft]))
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    total = np.sum(spectrum) + 1e-12
    centroid = float(np.sum(freqs * spectrum) / total)

    # Phi coherence: check if spectral peaks follow phi ratios
    phi_coherence = _compute_phi_coherence(spectrum, freqs)

    crest = peak / rms if rms > 1e-12 else 0.0

    return MonitorSnapshot(
        timestamp=time.time(),
        rms=round(rms, 6),
        peak=round(peak, 6),
        spectral_centroid=round(centroid, 2),
        phi_coherence=round(phi_coherence, 6),
        crest_factor=round(crest, 4),
    )


def _compute_phi_coherence(spectrum: np.ndarray, freqs: np.ndarray) -> float:
    """Measure how well spectral peaks follow phi ratios."""
    if len(spectrum) < 4:
        return 0.0

    # Find top 5 spectral peaks
    n_peaks = min(5, len(spectrum) // 4)
    peak_indices = np.argsort(spectrum)[-n_peaks:]
    peak_freqs = sorted(freqs[peak_indices])
    peak_freqs = [f for f in peak_freqs if f > 20]

    if len(peak_freqs) < 2:
        return 0.0

    # Check ratios between adjacent peaks
    coherence_scores = []
    for i in range(len(peak_freqs) - 1):
        if peak_freqs[i] > 0:
            ratio = peak_freqs[i + 1] / peak_freqs[i]
            # How close to phi or small integer ratios
            phi_dist = min(abs(ratio - PHI), abs(ratio - 2.0), abs(ratio - 1.5))
            score = max(0.0, 1.0 - phi_dist)
            coherence_scores.append(score)

    return sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0.0


def analyze_wav_file(path: str) -> MonitorSession:
    """Analyze a .wav file in chunks and return a MonitorSession."""
    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    chunk_size = sr  # 1-second chunks
    session = MonitorSession()

    for i in range(0, len(samples), chunk_size):
        chunk = samples[i:i + chunk_size]
        snap = analyze_chunk(chunk, sr)
        session.add(snap)

    return session


def monitor_signal_stream(signals: list[np.ndarray]) -> MonitorSession:
    """Monitor a stream of signal chunks."""
    session = MonitorSession()
    for sig in signals:
        snap = analyze_chunk(sig)
        session.add(snap)
    return session


def export_monitor_report(session: MonitorSession,
                          output_dir: str = "output/analysis") -> str:
    """Export a monitor session report as JSON."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = str(Path(output_dir) / "monitor_report.json")

    data = session.to_dict()
    data["snapshots"] = [asdict(s) for s in session.snapshots]

    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    # Generate test signal with phi harmonics
    dur = 3.0
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    freq = 432.0
    sig = 0.3 * np.sin(2 * np.pi * freq * t)
    sig += 0.2 * np.sin(2 * np.pi * freq * PHI * t)
    sig += 0.1 * np.sin(2 * np.pi * freq * PHI * PHI * t)

    # Monitor in chunks
    chunk_size = SAMPLE_RATE
    chunks = [sig[i:i + chunk_size] for i in range(0, len(sig), chunk_size)]
    session = monitor_signal_stream(chunks)

    print(f"Real-Time Monitor: {len(session.snapshots)} snapshots")
    print(f"  Avg phi coherence: {session.avg_phi_coherence():.4f}")
    print(f"  Peak RMS: {session.peak_rms():.4f}")
    if session.latest():
        snap = session.latest()
        print(f"  Latest — centroid: {snap.spectral_centroid} Hz, "
              f"crest: {snap.crest_factor}")


if __name__ == "__main__":
    main()
