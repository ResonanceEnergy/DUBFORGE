"""
DUBFORGE — Clip Manager  (Session 223)

Manage audio clips — clip pool, regions, playlist,
arrangement editing, clip properties.
"""

import math
from dataclasses import dataclass, field

from engine.config_loader import PHI
SAMPLE_RATE = 48000


@dataclass
class AudioClip:
    """An audio clip with metadata."""
    name: str
    samples: list[float]
    sample_rate: int = SAMPLE_RATE
    color: str = "#00FF88"
    gain: float = 1.0
    pitch_shift: float = 0.0  # semitones
    start_offset: int = 0  # clip start offset
    end_offset: int = 0  # clip end offset
    loop: bool = False
    tags: list[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.effective_length / self.sample_rate

    @property
    def effective_length(self) -> int:
        end = len(self.samples) - self.end_offset
        return max(0, end - self.start_offset)

    @property
    def effective_samples(self) -> list[float]:
        end = len(self.samples) - self.end_offset
        return self.samples[self.start_offset:end]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "duration": round(self.duration, 4),
            "sample_count": self.effective_length,
            "gain": self.gain,
            "pitch_shift": self.pitch_shift,
            "loop": self.loop,
            "color": self.color,
            "tags": self.tags,
        }


@dataclass
class ClipRegion:
    """A clip placed on a timeline."""
    clip_name: str
    position: float  # seconds
    duration: float | None = None  # None = full clip
    gain: float = 1.0
    fade_in_ms: float = 0.0
    fade_out_ms: float = 0.0


class ClipManager:
    """Manage a pool of audio clips."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.clips: dict[str, AudioClip] = {}
        self.tracks: dict[str, list[ClipRegion]] = {}

    def add_clip(self, name: str, samples: list[float],
                 **kwargs) -> AudioClip:
        """Add a clip to the pool."""
        clip = AudioClip(name=name, samples=list(samples), **kwargs)
        self.clips[name] = clip
        return clip

    def remove_clip(self, name: str) -> bool:
        """Remove a clip."""
        if name in self.clips:
            del self.clips[name]
            return True
        return False

    def duplicate_clip(self, name: str,
                       new_name: str | None = None) -> AudioClip | None:
        """Duplicate a clip."""
        if name not in self.clips:
            return None
        src = self.clips[name]
        new = new_name or f"{name}_copy"
        return self.add_clip(
            new,
            list(src.samples),
            gain=src.gain,
            color=src.color,
            tags=list(src.tags),
        )

    def trim_clip(self, name: str,
                  start_ms: float = 0,
                  end_ms: float | None = None) -> bool:
        """Trim clip start/end."""
        clip = self.clips.get(name)
        if not clip:
            return False

        clip.start_offset = int(start_ms * self.sample_rate / 1000)
        if end_ms is not None:
            end_sample = int(end_ms * self.sample_rate / 1000)
            clip.end_offset = max(0, len(clip.samples) - end_sample)

        return True

    def add_track(self, name: str) -> None:
        """Add a track."""
        if name not in self.tracks:
            self.tracks[name] = []

    def place_clip(self, track: str, clip_name: str,
                   position: float, **kwargs) -> ClipRegion | None:
        """Place a clip on a track."""
        if clip_name not in self.clips:
            return None
        if track not in self.tracks:
            self.add_track(track)

        region = ClipRegion(
            clip_name=clip_name,
            position=position,
            **kwargs,
        )
        self.tracks[track].append(region)
        return region

    def render_track(self, track: str) -> list[float]:
        """Render a track to audio."""
        regions = self.tracks.get(track, [])
        if not regions:
            return []

        # Find total length
        max_end = 0.0
        for r in regions:
            clip = self.clips.get(r.clip_name)
            if clip:
                dur = r.duration or clip.duration
                max_end = max(max_end, r.position + dur)

        n = int(max_end * self.sample_rate)
        output = [0.0] * n

        for r in regions:
            clip = self.clips.get(r.clip_name)
            if not clip:
                continue

            start_idx = int(r.position * self.sample_rate)
            samples = clip.effective_samples
            gain = r.gain * clip.gain

            fi = int(r.fade_in_ms * self.sample_rate / 1000)
            fo = int(r.fade_out_ms * self.sample_rate / 1000)

            for i in range(len(samples)):
                idx = start_idx + i
                if 0 <= idx < n:
                    s = samples[i] * gain

                    # Fades
                    if fi > 0 and i < fi:
                        s *= i / fi
                    if fo > 0 and i >= len(samples) - fo:
                        s *= (len(samples) - i) / fo

                    output[idx] += s

        return output

    def render_all(self) -> list[float]:
        """Render all tracks mixed."""
        if not self.tracks:
            return []

        rendered: list[list[float]] = []
        for track in self.tracks:
            rendered.append(self.render_track(track))

        max_len = max(len(r) for r in rendered) if rendered else 0
        output = [0.0] * max_len

        for r in rendered:
            for i in range(len(r)):
                output[i] += r[i]

        # Limit
        pk = max(abs(s) for s in output) if output else 1.0
        if pk > 1.0:
            output = [s / pk for s in output]

        return output

    def search_clips(self, tag: str | None = None,
                     name_contains: str | None = None) -> list[AudioClip]:
        """Search clips by tag or name."""
        results: list[AudioClip] = []
        for clip in self.clips.values():
            if tag and tag not in clip.tags:
                continue
            if name_contains and name_contains.lower() not in clip.name.lower():
                continue
            results.append(clip)
        return results

    def get_pool_info(self) -> dict:
        """Get clip pool information."""
        total_samples = sum(
            clip.effective_length for clip in self.clips.values()
        )
        return {
            "clip_count": len(self.clips),
            "track_count": len(self.tracks),
            "total_duration_s": round(total_samples / self.sample_rate, 2),
            "clips": [c.to_dict() for c in self.clips.values()],
        }


def main() -> None:
    print("Clip Manager")
    mgr = ClipManager()

    # Create clips
    for freq, name in [(60, "sub_bass"), (220, "mid_bass"), (440, "lead")]:
        n = int(0.5 * SAMPLE_RATE)
        audio = [0.7 * math.sin(2 * math.pi * freq * i / SAMPLE_RATE)
                 for i in range(n)]
        mgr.add_clip(name, audio, tags=["synth"], color="#00FF88")

    # Create arrangement
    mgr.add_track("bass")
    mgr.add_track("melody")

    mgr.place_clip("bass", "sub_bass", 0.0)
    mgr.place_clip("bass", "mid_bass", 0.5)
    mgr.place_clip("melody", "lead", 0.25, gain=0.6)

    # Render
    output = mgr.render_all()
    print(f"  Output: {len(output) / SAMPLE_RATE:.2f}s")

    info = mgr.get_pool_info()
    print(f"  Clips: {info['clip_count']}")
    print(f"  Tracks: {info['track_count']}")
    print(f"  Total duration: {info['total_duration_s']}s")

    print("Done.")


if __name__ == "__main__":
    main()
