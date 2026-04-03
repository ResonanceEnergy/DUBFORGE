"""
DUBFORGE — Multi-Track Renderer  (Session 197)

Multi-track mixing and rendering: track layering,
volume/pan/solo/mute, bus routing, final mixdown.
"""

import math
import os
import struct
import wave
from dataclasses import dataclass, field

from engine.config_loader import PHI
from engine.turboquant import (
    CompressedAudioBuffer,
    TurboQuantConfig,
    compress_audio_buffer,
    phi_optimal_bits,
)
from engine.accel import write_wav

SAMPLE_RATE = 48000


def _write_wav(path: str, samples: list[float],
               sr: int = SAMPLE_RATE) -> str:
    """Delegates to engine.audio_mmap.write_wav_fast."""
    import numpy as np
    _s = np.asarray(samples, dtype=np.float64) if not isinstance(samples, np.ndarray) else samples
    write_wav(str(path), _s, sample_rate=sr)
    return str(path)




@dataclass
class MixTrack:
    """A track in the mix."""
    name: str
    samples: list[float] = field(default_factory=list)
    volume: float = 1.0  # linear
    pan: float = 0.0  # -1 = L, 0 = C, +1 = R
    muted: bool = False
    solo: bool = False
    bus: str = "master"
    send_level: float = 0.0
    send_bus: str = ""

    def set_volume_db(self, db: float) -> None:
        self.volume = 10.0 ** (db / 20.0)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "samples": len(self.samples),
            "volume": round(self.volume, 3),
            "pan": self.pan,
            "muted": self.muted,
            "solo": self.solo,
            "bus": self.bus,
        }


@dataclass
class Bus:
    """A mix bus."""
    name: str
    volume: float = 1.0
    tracks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "volume": round(self.volume, 3),
            "tracks": self.tracks,
        }


class MultiTrackRenderer:
    """Multi-track mixing and rendering engine."""

    def __init__(self, output_dir: str = "output/mixes",
                 sample_rate: int = SAMPLE_RATE):
        self.output_dir = output_dir
        self.sample_rate = sample_rate
        self.tracks: dict[str, MixTrack] = {}
        self.buses: dict[str, Bus] = {"master": Bus("master")}
        os.makedirs(output_dir, exist_ok=True)

    def add_track(self, name: str, samples: list[float] = None,
                  **kwargs) -> MixTrack:
        """Add a track to the mix."""
        track = MixTrack(
            name=name,
            samples=samples or [],
            volume=kwargs.get("volume", 1.0),
            pan=kwargs.get("pan", 0.0),
            bus=kwargs.get("bus", "master"),
        )
        self.tracks[name] = track

        # Auto-register to bus
        bus_name = track.bus
        if bus_name not in self.buses:
            self.buses[bus_name] = Bus(bus_name)
        self.buses[bus_name].tracks.append(name)

        return track

    def add_bus(self, name: str, volume: float = 1.0) -> Bus:
        """Add a mix bus."""
        bus = Bus(name=name, volume=volume)
        self.buses[name] = bus
        return bus

    def generate_tone(self, freq: float, duration: float = 2.0,
                      amplitude: float = 0.8) -> list[float]:
        """Generate a test tone."""
        n = int(self.sample_rate * duration)
        return [amplitude * math.sin(2 * math.pi * freq * i / self.sample_rate)
                for i in range(n)]

    def generate_sub(self, freq: float = 40.0,
                     duration: float = 2.0) -> list[float]:
        """Generate sub bass with PHI harmonics."""
        n = int(self.sample_rate * duration)
        samples: list[float] = []
        for i in range(n):
            t = i / self.sample_rate
            s = 0.6 * math.sin(2 * math.pi * freq * t)
            s += 0.2 * math.sin(2 * math.pi * freq * PHI * t)
            s += 0.1 * math.sin(2 * math.pi * freq * 2 * t)
            samples.append(s)
        return samples

    def generate_kick(self, bpm: float = 140.0,
                      duration: float = 2.0) -> list[float]:
        """Generate kicks at BPM."""
        n = int(self.sample_rate * duration)
        beat_samples = int(self.sample_rate * 60 / bpm)
        samples: list[float] = []

        for i in range(n):
            pos = i % beat_samples
            if pos < int(self.sample_rate * 0.05):
                t = pos / self.sample_rate
                freq = 200 * math.exp(-t * 40) + 40
                env = math.exp(-t * 20)
                samples.append(0.9 * env * math.sin(2 * math.pi * freq * t))
            else:
                samples.append(0.0)

        return samples

    def _mix_to_mono(self) -> list[float]:
        """Mix all tracks to mono."""
        # Determine max length
        max_len = 0
        for track in self.tracks.values():
            if len(track.samples) > max_len:
                max_len = len(track.samples)

        if max_len == 0:
            return []

        # Check for solo
        any_solo = any(t.solo for t in self.tracks.values())

        # Mix by bus
        bus_mixes: dict[str, list[float]] = {}

        for bus_name, bus in self.buses.items():
            bus_mix = [0.0] * max_len

            for track_name in bus.tracks:
                track = self.tracks.get(track_name)
                if not track:
                    continue
                if track.muted:
                    continue
                if any_solo and not track.solo:
                    continue

                for i in range(min(len(track.samples), max_len)):
                    bus_mix[i] += track.samples[i] * track.volume

            # Apply bus volume
            bus_mix = [s * bus.volume for s in bus_mix]
            bus_mixes[bus_name] = bus_mix

        # Sum all buses into master
        master = [0.0] * max_len
        for bus_name, bus_mix in bus_mixes.items():
            if bus_name == "master":
                for i in range(max_len):
                    master[i] += bus_mix[i]
            else:
                # Non-master buses route to master
                master_bus = self.buses.get("master")
                if master_bus:
                    vol = master_bus.volume
                    for i in range(max_len):
                        master[i] += bus_mix[i] * vol

        return master

    def _mix_to_stereo(self) -> tuple[list[float], list[float]]:
        """Mix all tracks to stereo."""
        max_len = max(
            (len(t.samples) for t in self.tracks.values()), default=0
        )
        if max_len == 0:
            return [], []

        left = [0.0] * max_len
        right = [0.0] * max_len

        any_solo = any(t.solo for t in self.tracks.values())

        for track in self.tracks.values():
            if track.muted:
                continue
            if any_solo and not track.solo:
                continue

            # Pan law (constant power)
            pan_angle = (track.pan + 1) * math.pi / 4
            l_gain = math.cos(pan_angle) * track.volume
            r_gain = math.sin(pan_angle) * track.volume

            for i in range(min(len(track.samples), max_len)):
                left[i] += track.samples[i] * l_gain
                right[i] += track.samples[i] * r_gain

        return left, right

    def render_mono(self, filename: str = "mixdown.wav") -> str:
        """Render mono mixdown."""
        mix = self._mix_to_mono()

        # Normalize
        peak = max(abs(s) for s in mix) if mix else 1.0
        if peak > 1.0:
            mix = [s / peak for s in mix]

        # TurboQuant compress mono mixdown
        tq_cfg = TurboQuantConfig(bit_width=phi_optimal_bits(len(mix)))
        compress_audio_buffer(
            mix, "mono_mixdown", tq_cfg,
            sample_rate=self.sample_rate, label=filename,
        )

        path = os.path.join(self.output_dir, filename)
        return _write_wav(path, mix, self.sample_rate)

    def render_stereo(self, filename: str = "mixdown_stereo.wav") -> str:
        """Render stereo mixdown."""
        left, right = self._mix_to_stereo()
        if not left:
            return ""

        # Interleave
        stereo: list[float] = []
        for i in range(len(left)):
            stereo.append(left[i])
            stereo.append(right[i])

        # Normalize
        peak = max(abs(s) for s in stereo) if stereo else 1.0
        if peak > 1.0:
            stereo = [s / peak for s in stereo]

        # TurboQuant compress stereo mixdown
        tq_cfg = TurboQuantConfig(bit_width=phi_optimal_bits(len(stereo)))
        compress_audio_buffer(
            stereo, "stereo_mixdown", tq_cfg,
            sample_rate=self.sample_rate, label=filename,
        )

        path = os.path.join(self.output_dir, filename)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with wave.open(path, "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            data = struct.pack(
                f"<{len(stereo)}h",
                *[max(-32768, min(32767, int(s * 32767))) for s in stereo]
            )
            wf.writeframes(data)
        return path

    def render_stems(self, prefix: str = "stem") -> list[str]:
        """Render individual track stems."""
        stems: list[str] = []
        for name, track in self.tracks.items():
            if not track.samples:
                continue
            filename = f"{prefix}_{name.replace(' ', '_')}.wav"
            path = os.path.join(self.output_dir, filename)
            _write_wav(path, track.samples, self.sample_rate)
            stems.append(path)
        return stems

    def get_levels(self) -> dict[str, float]:
        """Get peak levels for each track."""
        levels: dict[str, float] = {}
        for name, track in self.tracks.items():
            if track.samples:
                peak = max(abs(s) for s in track.samples)
                db = 20 * math.log10(peak) if peak > 0 else -96.0
                levels[name] = round(db, 1)
            else:
                levels[name] = -96.0
        return levels

    def get_summary(self) -> dict:
        """Get mix summary."""
        return {
            "tracks": len(self.tracks),
            "buses": len(self.buses),
            "total_samples": sum(
                len(t.samples) for t in self.tracks.values()
            ),
            "levels": self.get_levels(),
        }


def main() -> None:
    print("Multi-Track Renderer")

    renderer = MultiTrackRenderer()

    # Add tracks
    renderer.add_track("kick", renderer.generate_kick(140, 2.0),
                        volume=0.9, pan=0.0)
    renderer.add_track("sub", renderer.generate_sub(40, 2.0),
                        volume=0.7, pan=0.0)
    renderer.add_track("lead", renderer.generate_tone(432, 2.0, 0.5),
                        volume=0.6, pan=-0.3)
    renderer.add_track("pad", renderer.generate_tone(216, 2.0, 0.3),
                        volume=0.4, pan=0.3)

    # Render
    mono_path = renderer.render_mono()
    stereo_path = renderer.render_stereo()
    stems = renderer.render_stems()

    print(f"  Mono: {mono_path}")
    print(f"  Stereo: {stereo_path}")
    print(f"  Stems: {len(stems)}")
    print(f"  Levels: {renderer.get_levels()}")
    print("Done.")


if __name__ == "__main__":
    main()
