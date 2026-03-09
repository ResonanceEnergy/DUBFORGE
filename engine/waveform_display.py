"""
DUBFORGE — Waveform Display  (Session 231)

ASCII and data waveform visualization for terminal
and data export. Peak/RMS display, stereo meters.
"""

import math
from dataclasses import dataclass

PHI = 1.6180339887
SAMPLE_RATE = 44100


@dataclass
class WaveformData:
    """Waveform data for display."""
    peaks: list[float]  # positive peaks per column
    rms: list[float]  # RMS per column
    width: int
    duration_s: float
    peak_db: float
    rms_db: float

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "duration_s": round(self.duration_s, 3),
            "peak_db": round(self.peak_db, 1),
            "rms_db": round(self.rms_db, 1),
            "peak_values": [round(p, 4) for p in self.peaks],
        }


class WaveformDisplay:
    """Generate waveform visualizations."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    def analyze(self, samples: list[float],
                width: int = 80) -> WaveformData:
        """Analyze audio for waveform display."""
        if not samples:
            return WaveformData([], [], width, 0, -120, -120)

        n = len(samples)
        chunk_size = max(1, n // width)
        peaks: list[float] = []
        rms_vals: list[float] = []

        for i in range(0, n, chunk_size):
            chunk = samples[i:i + chunk_size]
            if chunk:
                pk = max(abs(s) for s in chunk)
                r = math.sqrt(sum(s * s for s in chunk) / len(chunk))
                peaks.append(pk)
                rms_vals.append(r)

        overall_peak = max(abs(s) for s in samples)
        overall_rms = math.sqrt(sum(s * s for s in samples) / n)

        return WaveformData(
            peaks=peaks[:width],
            rms=rms_vals[:width],
            width=len(peaks[:width]),
            duration_s=n / self.sample_rate,
            peak_db=20 * math.log10(overall_peak) if overall_peak > 0 else -120,
            rms_db=20 * math.log10(overall_rms) if overall_rms > 0 else -120,
        )

    def render_ascii(self, samples: list[float],
                     width: int = 60, height: int = 10) -> str:
        """Render ASCII waveform."""
        data = self.analyze(samples, width)
        if not data.peaks:
            return "[no audio]"

        lines: list[str] = []
        max_pk = max(data.peaks) if data.peaks else 1.0

        for row in range(height, 0, -1):
            threshold = row / height * max_pk
            line = ""
            for col in range(data.width):
                pk = data.peaks[col]
                rms = data.rms[col] if col < len(data.rms) else 0

                if pk >= threshold:
                    if rms >= threshold:
                        line += "█"
                    else:
                        line += "▓"
                elif pk >= threshold * 0.7:
                    line += "░"
                else:
                    line += " "
            lines.append(f"│{line}│")

        # Bottom border
        lines.append("└" + "─" * data.width + "┘")
        # Time markers
        dur = data.duration_s
        lines.append(f" 0s{' ' * (data.width - 6)}{dur:.1f}s")

        return "\n".join(lines)

    def render_meter(self, level_db: float, width: int = 40,
                     ceiling_db: float = 0.0,
                     floor_db: float = -60.0) -> str:
        """Render a level meter."""
        rng = ceiling_db - floor_db
        pos = int((level_db - floor_db) / rng * width)
        pos = max(0, min(width, pos))

        bar = ""
        for i in range(width):
            db_at = floor_db + (i / width) * rng
            if i < pos:
                if db_at > -3:
                    bar += "█"  # red zone
                elif db_at > -12:
                    bar += "▓"  # yellow zone
                else:
                    bar += "░"  # green zone
            else:
                bar += "·"

        return f"[{bar}] {level_db:+.1f}dB"

    def render_stereo_meters(self, left_db: float, right_db: float,
                             width: int = 30) -> str:
        """Render stereo level meters."""
        l_meter = self.render_meter(left_db, width)
        r_meter = self.render_meter(right_db, width)
        return f"L {l_meter}\nR {r_meter}"

    def render_spectrum_bars(self, band_levels: dict[str, float],
                             width: int = 20) -> str:
        """Render frequency band levels as bars."""
        lines: list[str] = []
        for band, level_db in band_levels.items():
            filled = int(max(0, (level_db + 60) / 60 * width))
            bar = "█" * filled + "·" * (width - filled)
            lines.append(f"{band:>10s} [{bar}] {level_db:+.1f}dB")
        return "\n".join(lines)

    def generate_overview(self, samples: list[float],
                          title: str = "Audio") -> str:
        """Generate a complete waveform overview."""
        if not samples:
            return f"{title}: [empty]"

        data = self.analyze(samples, 50)
        waveform = self.render_ascii(samples, 50, 8)
        meter = self.render_meter(data.peak_db)

        lines = [
            f"╔══ {title} ══╗",
            f"  Duration: {data.duration_s:.2f}s",
            f"  Peak: {data.peak_db:.1f}dB  RMS: {data.rms_db:.1f}dB",
            f"  Level: {meter}",
            "",
            waveform,
        ]

        return "\n".join(lines)


def main() -> None:
    print("Waveform Display")
    display = WaveformDisplay()

    # Generate test signal with varying amplitude
    n = SAMPLE_RATE * 3
    samples: list[float] = []
    for i in range(n):
        t = i / SAMPLE_RATE
        # Amplitude envelope: fade in, sustain, fade out
        if t < 0.5:
            env = t * 2
        elif t < 2.5:
            env = 1.0
        else:
            env = (3.0 - t) * 2

        env = max(0, env)
        s = env * 0.8 * math.sin(2 * math.pi * 200 * t)
        # Add some harmonics
        s += env * 0.3 * math.sin(2 * math.pi * 400 * t)
        s += env * 0.15 * math.sin(2 * math.pi * 600 * t)
        samples.append(s)

    # Full overview
    overview = display.generate_overview(samples, "Test Signal")
    print(overview)

    # Meters
    print("\n  Level meters:")
    for db in [-30, -18, -12, -6, -3, -1, 0]:
        print(f"    {display.render_meter(db, 30)}")

    # Stereo
    print("\n  Stereo:")
    print(f"    {display.render_stereo_meters(-12.0, -9.5, 25)}")

    # Band levels
    print("\n  Spectrum:")
    bands = {
        "sub": -24.0,
        "bass": -12.0,
        "low_mid": -15.0,
        "mid": -18.0,
        "high_mid": -22.0,
        "high": -30.0,
    }
    print(display.render_spectrum_bars(bands, 15))

    print("\nDone.")


if __name__ == "__main__":
    main()
