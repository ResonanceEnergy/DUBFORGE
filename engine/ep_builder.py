"""
DUBFORGE — EP Builder  (Session 195)

Full EP rendering pipeline: arrange tracks, master,
export with metadata, artwork placeholder, and tracklist.
"""

import json
import math
import os
import struct
import time
import wave
from dataclasses import dataclass, field

from engine.config_loader import PHI, A4_432
SAMPLE_RATE = 48000
@dataclass
class Track:
    """An EP track."""
    number: int
    title: str
    bpm: float = 140.0
    key: str = "F"
    duration: float = 180.0  # seconds
    style: str = "dubstep"
    samples: list[float] = field(default_factory=list)
    wav_path: str = ""

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "title": self.title,
            "bpm": self.bpm,
            "key": self.key,
            "duration": round(self.duration, 1),
            "style": self.style,
        }


@dataclass
class EPConfig:
    """EP configuration."""
    title: str = "DUBFORGE EP"
    artist: str = "DUBFORGE"
    genre: str = "Dubstep"
    year: int = 2025
    label: str = "PHI Records"
    catalog: str = "PHI-001"
    master_bpm: float = 140.0

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "artist": self.artist,
            "genre": self.genre,
            "year": self.year,
            "label": self.label,
            "catalog": self.catalog,
            "bpm": self.master_bpm,
        }


# Dubstep note frequencies (432 Hz tuning)
KEYS = {
    "C": A4_432 * 2 ** (-9 / 12),
    "D": A4_432 * 2 ** (-7 / 12),
    "E": A4_432 * 2 ** (-5 / 12),
    "F": A4_432 * 2 ** (-4 / 12),
    "G": A4_432 * 2 ** (-2 / 12),
    "A": A4_432,
    "B": A4_432 * 2 ** (2 / 12),
}

# EP styles with characteristic patterns
STYLE_PATTERNS = {
    "dubstep": {"drop_position": 0.382, "buildup_ratio": PHI / 5,
                "energy_curve": "exponential"},
    "riddim": {"drop_position": 0.25, "buildup_ratio": 0.15,
               "energy_curve": "square"},
    "melodic": {"drop_position": 0.5, "buildup_ratio": 0.3,
                "energy_curve": "sine"},
    "tearout": {"drop_position": 0.3, "buildup_ratio": 0.1,
                "energy_curve": "sawtooth"},
}


def _write_wav(path: str, samples: list[float],
               sr: int = SAMPLE_RATE) -> str:
    """Write 16-bit mono WAV."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        data = struct.pack(
            f"<{len(samples)}h",
            *[max(-32768, min(32767, int(s * 32767))) for s in samples]
        )
        wf.writeframes(data)
    return path


class EPBuilder:
    """Build and export complete EPs."""

    def __init__(self, output_dir: str = "output/ep"):
        self.output_dir = output_dir
        self.config = EPConfig()
        self.tracks: list[Track] = []

    def configure(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)

    def add_track(self, title: str, **kwargs) -> Track:
        """Add a track to the EP."""
        number = len(self.tracks) + 1
        track = Track(
            number=number,
            title=title,
            bpm=kwargs.get("bpm", self.config.master_bpm),
            key=kwargs.get("key", "F"),
            duration=kwargs.get("duration", 180.0),
            style=kwargs.get("style", "dubstep"),
        )
        self.tracks.append(track)
        return track

    def _generate_track_audio(self, track: Track) -> list[float]:
        """Generate audio for a track."""
        n = int(SAMPLE_RATE * track.duration)
        freq = KEYS.get(track.key, KEYS["F"])
        style = STYLE_PATTERNS.get(track.style, STYLE_PATTERNS["dubstep"])

        samples: list[float] = []
        drop_pos = style["drop_position"]
        drop_sample = int(n * drop_pos)

        for i in range(n):
            t = i / SAMPLE_RATE
            pos = i / n

            # Base sub
            sub = 0.3 * math.sin(2 * math.pi * freq / 4 * t)

            # Mid bass (wobble during drop)
            if i > drop_sample:
                wobble_rate = track.bpm / 60 * 2
                wobble = math.sin(2 * math.pi * wobble_rate * t)
                mid = 0.4 * math.sin(
                    2 * math.pi * freq * t
                ) * (0.5 + 0.5 * wobble)
            else:
                # Buildup
                buildup = min(1.0, pos / drop_pos) if drop_pos > 0 else 1.0
                mid = 0.2 * buildup * math.sin(2 * math.pi * freq * t)

            # Hi percussion
            beat_period = 60.0 / track.bpm
            beat_phase = (t % beat_period) / beat_period
            hi = 0.0
            if beat_phase < 0.05:
                hi = 0.15 * (1 - beat_phase / 0.05)

            # Energy envelope
            if style["energy_curve"] == "exponential":
                env = min(1.0, pos ** 0.5)
            elif style["energy_curve"] == "sine":
                env = 0.5 + 0.5 * math.sin(math.pi * pos)
            elif style["energy_curve"] == "square":
                env = 1.0 if i > drop_sample else 0.5
            else:
                env = pos

            sample = (sub + mid + hi) * env * 0.7
            samples.append(max(-1.0, min(1.0, sample)))

        # Apply fade in/out
        fade_in = int(SAMPLE_RATE * 0.5)
        fade_out = int(SAMPLE_RATE * 2.0)
        for i in range(min(fade_in, len(samples))):
            samples[i] *= i / fade_in
        for i in range(min(fade_out, len(samples))):
            idx = len(samples) - 1 - i
            samples[idx] *= i / fade_out

        return samples

    def _master_track(self, samples: list[float]) -> list[float]:
        """Simple mastering: normalize + soft clip."""
        if not samples:
            return samples

        peak = max(abs(s) for s in samples)
        if peak == 0:
            return samples

        # Normalize to -1dB
        target = 10 ** (-1.0 / 20.0)
        gain = target / peak
        mastered = [s * gain for s in samples]

        # Soft clip
        mastered = [math.tanh(s * 1.2) / math.tanh(1.2) for s in mastered]

        return mastered

    def render(self, duration_override: float = 0) -> dict:
        """Render all tracks."""
        ep_dir = os.path.join(
            self.output_dir,
            self.config.title.replace(" ", "_")
        )
        os.makedirs(ep_dir, exist_ok=True)

        results: list[dict] = []

        for track in self.tracks:
            if duration_override > 0:
                track.duration = duration_override

            # Generate
            audio = self._generate_track_audio(track)

            # Master
            audio = self._master_track(audio)

            # Export
            filename = f"{track.number:02d}_{track.title.replace(' ', '_')}.wav"
            path = os.path.join(ep_dir, filename)
            _write_wav(path, audio)
            track.wav_path = path
            track.samples = []  # don't keep in memory

            results.append({
                "track": track.number,
                "title": track.title,
                "path": path,
                "duration": track.duration,
                "samples": len(audio),
            })

        # Write tracklist
        self._write_tracklist(ep_dir)

        # Write metadata
        self._write_metadata(ep_dir)

        return {
            "ep_dir": ep_dir,
            "tracks": results,
            "total_tracks": len(results),
            "config": self.config.to_dict(),
        }

    def _write_tracklist(self, ep_dir: str) -> None:
        """Write tracklist file."""
        lines = [
            f"# {self.config.title}",
            f"### {self.config.artist}",
            "",
            f"**Label:** {self.config.label}",
            f"**Catalog:** {self.config.catalog}",
            f"**Year:** {self.config.year}",
            f"**Genre:** {self.config.genre}",
            "",
            "## Tracklist",
            "",
        ]
        for t in self.tracks:
            mins = int(t.duration // 60)
            secs = int(t.duration % 60)
            lines.append(f"{t.number}. {t.title} [{mins}:{secs:02d}] "
                          f"({t.bpm} BPM, {t.key})")

        lines.extend([
            "",
            "---",
            f"*Rendered with DUBFORGE | PHI = {PHI} | A4 = {A4_432} Hz*",
        ])

        with open(os.path.join(ep_dir, "TRACKLIST.md"), "w") as f:
            f.write("\n".join(lines))

    def _write_metadata(self, ep_dir: str) -> None:
        """Write EP metadata JSON."""
        meta = {
            "ep": self.config.to_dict(),
            "tracks": [t.to_dict() for t in self.tracks],
            "rendered": time.strftime("%Y-%m-%d %H:%M:%S"),
            "engine": "DUBFORGE v4.0.0",
            "phi": PHI,
            "tuning": A4_432,
        }
        with open(os.path.join(ep_dir, "metadata.json"), "w") as f:
            json.dump(meta, f, indent=2)


def create_default_ep(output_dir: str = "output/ep",
                      duration: float = 5.0) -> dict:
    """Create a default dubstep EP."""
    builder = EPBuilder(output_dir)
    builder.configure(
        title="PHI Sessions Vol 1",
        artist="DUBFORGE",
        label="PHI Records",
    )

    builder.add_track("Resonance", key="F", style="dubstep")
    builder.add_track("Wobble Matrix", key="G", style="riddim")
    builder.add_track("Golden Drop", key="A", style="melodic", bpm=150)
    builder.add_track("Tearout Protocol", key="E", style="tearout", bpm=145)
    builder.add_track("Ascension", key="C", style="dubstep")

    return builder.render(duration_override=duration)


def main() -> None:
    print("EP Builder")

    result = create_default_ep(duration=2.0)
    print(f"  EP: {result['config']['title']}")
    print(f"  Tracks: {result['total_tracks']}")
    for t in result["tracks"]:
        print(f"    {t['track']}. {t['title']} — {t['duration']}s")
    print("Done.")


if __name__ == "__main__":
    main()
