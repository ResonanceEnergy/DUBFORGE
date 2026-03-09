"""
DUBFORGE — Auto-Mixer / Gain Staging Engine  (Session 165)

Automatic gain staging, loudness normalisation, and
headroom management for multi-element mixes.
"""

import math
from dataclasses import dataclass, field

PHI = 1.6180339887
SAMPLE_RATE = 48000

# Target loudness levels (LUFS)
TARGET_LUFS = -14.0  # Streaming standard
TARGET_HEADROOM_DB = 3.0  # Headroom above peak


@dataclass
class TrackInfo:
    """Information about a single track/element."""
    name: str
    signal: list[float]
    element_type: str = "unknown"
    gain_db: float = 0.0
    pan: float = 0.0  # -1 L, 0 C, 1 R
    mute: bool = False
    solo: bool = False


@dataclass
class GainStagingResult:
    """Result of auto gain staging."""
    tracks: list[dict] = field(default_factory=list)
    master_gain_db: float = 0.0
    headroom_db: float = 0.0
    peak_db: float = 0.0
    rms_db: float = 0.0

    def to_dict(self) -> dict:
        return {
            "tracks": self.tracks,
            "master_gain_db": round(self.master_gain_db, 1),
            "headroom_db": round(self.headroom_db, 1),
            "peak_db": round(self.peak_db, 1),
            "rms_db": round(self.rms_db, 1),
        }


# Priority levels for gain staging (higher = louder)
ELEMENT_PRIORITY: dict[str, float] = {
    "kick": 1.0,
    "snare": 0.9,
    "sub_bass": 0.95,
    "bass": 0.85,
    "lead": 0.75,
    "vocal": 0.8,
    "pad": 0.5,
    "hihat": 0.6,
    "fx": 0.4,
    "riser": 0.5,
    "ambient": 0.3,
}


def measure_rms(signal: list[float]) -> float:
    """Measure RMS of a signal."""
    if not signal:
        return 0.0
    return math.sqrt(sum(s * s for s in signal) / len(signal))


def measure_peak(signal: list[float]) -> float:
    """Measure peak of a signal."""
    if not signal:
        return 0.0
    return max(abs(s) for s in signal)


def db_from_linear(linear: float) -> float:
    """Convert linear to dB."""
    return 20.0 * math.log10(max(linear, 1e-10))


def linear_from_db(db: float) -> float:
    """Convert dB to linear."""
    return 10.0 ** (db / 20.0)


def auto_gain_stage(tracks: list[TrackInfo],
                     target_rms_db: float = -14.0,
                     headroom_db: float = 3.0) -> GainStagingResult:
    """Automatically set gain levels for all tracks."""
    result = GainStagingResult()

    if not tracks:
        return result

    # Measure current levels
    measurements = []
    for track in tracks:
        if track.mute:
            continue
        rms = measure_rms(track.signal)
        peak = measure_peak(track.signal)
        rms_db = db_from_linear(rms)
        peak_db = db_from_linear(peak)
        priority = ELEMENT_PRIORITY.get(track.element_type, 0.5)
        measurements.append({
            "track": track,
            "rms": rms,
            "peak": peak,
            "rms_db": rms_db,
            "peak_db": peak_db,
            "priority": priority,
        })

    if not measurements:
        return result

    # Calculate target level per track based on priority
    max_priority = max(m["priority"] for m in measurements)

    for m in measurements:
        track = m["track"]
        # Target level proportional to priority
        rel_priority = m["priority"] / max_priority
        track_target = target_rms_db + 6 * (rel_priority - 1.0)

        # Calculate needed gain
        current_rms = m["rms_db"]
        needed_gain = track_target - current_rms

        # Apply PHI-ratio limiting to prevent extreme gains
        max_gain = 12.0  # dB
        min_gain = -24.0  # dB
        needed_gain = max(min_gain, min(max_gain, needed_gain))

        result.tracks.append({
            "name": track.name,
            "type": track.element_type,
            "current_rms_db": round(current_rms, 1),
            "target_rms_db": round(track_target, 1),
            "gain_adjustment_db": round(needed_gain, 1),
            "priority": round(m["priority"], 2),
        })

    # Calculate master gain for headroom
    # Simulate summed signal with adjustments
    max_combined_peak = 0.0
    for m in measurements:
        gain = 0.0
        for t in result.tracks:
            if t["name"] == m["track"].name:
                gain = t["gain_adjustment_db"]
                break
        adjusted_peak = m["peak"] * linear_from_db(gain)
        max_combined_peak += adjusted_peak

    if max_combined_peak > 0:
        combined_peak_db = db_from_linear(max_combined_peak)
        master_gain = -(combined_peak_db + headroom_db)
    else:
        master_gain = 0.0
        combined_peak_db = -float("inf")

    result.master_gain_db = round(master_gain, 1)
    result.peak_db = round(combined_peak_db + master_gain, 1)
    result.headroom_db = round(-result.peak_db, 1)

    return result


def apply_gain(signal: list[float], gain_db: float) -> list[float]:
    """Apply gain in dB to a signal."""
    gain = linear_from_db(gain_db)
    return [s * gain for s in signal]


def normalize(signal: list[float], target_db: float = -1.0) -> list[float]:
    """Normalize signal to target peak level."""
    peak = measure_peak(signal)
    if peak <= 0:
        return signal
    target = linear_from_db(target_db)
    scale = target / peak
    return [s * scale for s in signal]


def sum_tracks(tracks: list[TrackInfo]) -> list[float]:
    """Sum all non-muted tracks."""
    if not tracks:
        return []
    active = [t for t in tracks if not t.mute]
    if not active:
        return []

    max_len = max(len(t.signal) for t in active)
    output = [0.0] * max_len

    for track in active:
        gain = linear_from_db(track.gain_db)
        for i, s in enumerate(track.signal):
            output[i] += s * gain

    return output


def gain_staging_text(result: GainStagingResult) -> str:
    """Format gain staging as readable text."""
    lines = [
        "**Auto Gain Staging**",
        f"Master: {result.master_gain_db:+.1f}dB | "
        f"Peak: {result.peak_db:.1f}dB | "
        f"Headroom: {result.headroom_db:.1f}dB",
        "",
    ]
    for t in result.tracks:
        adj = t["gain_adjustment_db"]
        icon = "↑" if adj > 0 else "↓" if adj < 0 else "="
        lines.append(
            f"  {icon} **{t['name']}** ({t['type']}): "
            f"{t['current_rms_db']:.1f}dB → {t['target_rms_db']:.1f}dB "
            f"({adj:+.1f}dB)")
    return "\n".join(lines)


def main() -> None:
    print("Auto-Mixer / Gain Staging Engine")
    # Generate test tracks
    import random
    rng = random.Random(42)
    tracks = []
    test_data = [
        ("Kick", "kick", 0.8),
        ("Sub", "sub_bass", 0.7),
        ("Lead", "lead", 0.3),
        ("Pad", "pad", 0.15),
        ("Snare", "snare", 0.5),
    ]
    for name, etype, level in test_data:
        n = 44100
        sig = [math.sin(2 * math.pi * 110 * i / 44100) * level
               + rng.gauss(0, 0.01)
               for i in range(n)]
        tracks.append(TrackInfo(name, sig, etype))

    result = auto_gain_stage(tracks)
    print(gain_staging_text(result))
    print("Done.")


if __name__ == "__main__":
    main()
