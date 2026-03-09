"""
DUBFORGE — Clip Launcher Engine  (Session 167)

Trigger and sequence audio clips with quantized launching,
scene management, and follow actions. Live performance core.
"""

from dataclasses import dataclass, field
from enum import Enum

PHI = 1.6180339887
SAMPLE_RATE = 48000


class ClipState(Enum):
    STOPPED = "stopped"
    QUEUED = "queued"
    PLAYING = "playing"
    RECORDING = "recording"


class FollowAction(Enum):
    NONE = "none"
    NEXT = "next"
    PREVIOUS = "previous"
    RANDOM = "random"
    STOP = "stop"
    LOOP = "loop"


@dataclass
class Clip:
    """An audio clip that can be triggered."""
    name: str
    signal: list[float] = field(default_factory=list)
    bpm: float = 140.0
    bars: int = 4
    state: ClipState = ClipState.STOPPED
    loop: bool = True
    volume: float = 1.0
    mute: bool = False
    follow_action: FollowAction = FollowAction.LOOP
    follow_beats: int = 16  # After how many beats
    color: str = "#8B5CF6"  # Purple default

    @property
    def duration_s(self) -> float:
        return self.bars * 4 * 60.0 / self.bpm

    @property
    def length_samples(self) -> int:
        if self.signal:
            return len(self.signal)
        return int(self.duration_s * SAMPLE_RATE)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "bpm": self.bpm,
            "bars": self.bars,
            "loop": self.loop,
            "volume": self.volume,
            "mute": self.mute,
            "color": self.color,
            "has_audio": len(self.signal) > 0,
            "duration_s": round(self.duration_s, 2),
        }


@dataclass
class Track:
    """A vertical track containing clips."""
    name: str
    clips: list[Clip] = field(default_factory=list)
    volume: float = 1.0
    pan: float = 0.0
    mute: bool = False
    solo: bool = False
    armed: bool = False

    def active_clip(self) -> Clip | None:
        for c in self.clips:
            if c.state == ClipState.PLAYING:
                return c
        return None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "volume": self.volume,
            "pan": self.pan,
            "mute": self.mute,
            "solo": self.solo,
            "clips": [c.to_dict() for c in self.clips],
        }


@dataclass
class Scene:
    """A horizontal scene (row of clips to trigger simultaneously)."""
    name: str
    clip_indices: dict[str, int] = field(default_factory=dict)
    # Maps track_name -> clip_index
    bpm: float = 140.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "bpm": self.bpm,
            "clips": self.clip_indices,
        }


class ClipLauncher:
    """Live clip launcher with scene management."""

    def __init__(self, bpm: float = 140.0):
        self.bpm = bpm
        self.tracks: list[Track] = []
        self.scenes: list[Scene] = []
        self._playing = False
        self._beat_count = 0
        self._start_time = 0.0

    def add_track(self, name: str) -> Track:
        track = Track(name=name)
        self.tracks.append(track)
        return track

    def add_clip(self, track_name: str, clip: Clip) -> bool:
        for t in self.tracks:
            if t.name == track_name:
                t.clips.append(clip)
                return True
        return False

    def add_scene(self, scene: Scene) -> None:
        self.scenes.append(scene)

    def launch_clip(self, track_name: str, clip_index: int) -> bool:
        """Launch a specific clip (queued for next beat)."""
        for t in self.tracks:
            if t.name == track_name:
                if 0 <= clip_index < len(t.clips):
                    # Stop current playing clip
                    for c in t.clips:
                        if c.state == ClipState.PLAYING:
                            c.state = ClipState.STOPPED
                    t.clips[clip_index].state = ClipState.PLAYING
                    return True
        return False

    def stop_clip(self, track_name: str) -> bool:
        """Stop all clips on a track."""
        for t in self.tracks:
            if t.name == track_name:
                for c in t.clips:
                    c.state = ClipState.STOPPED
                return True
        return False

    def launch_scene(self, scene_index: int) -> bool:
        """Launch all clips in a scene."""
        if 0 <= scene_index < len(self.scenes):
            scene = self.scenes[scene_index]
            self.bpm = scene.bpm
            for track_name, clip_idx in scene.clip_indices.items():
                self.launch_clip(track_name, clip_idx)
            return True
        return False

    def stop_all(self) -> None:
        """Stop all clips."""
        for t in self.tracks:
            for c in t.clips:
                c.state = ClipState.STOPPED
        self._playing = False

    def get_playing_clips(self) -> list[tuple[str, Clip]]:
        """Get all currently playing clips."""
        result = []
        for t in self.tracks:
            ac = t.active_clip()
            if ac:
                result.append((t.name, ac))
        return result

    def status(self) -> dict:
        """Get launcher status."""
        playing = self.get_playing_clips()
        return {
            "bpm": self.bpm,
            "playing": len(playing),
            "tracks": len(self.tracks),
            "scenes": len(self.scenes),
            "total_clips": sum(len(t.clips) for t in self.tracks),
            "active_clips": [
                {"track": name, "clip": c.name}
                for name, c in playing
            ],
        }

    def status_text(self) -> str:
        """Human-readable status."""
        s = self.status()
        lines = [
            f"**Clip Launcher** — {s['bpm']}BPM",
            f"Tracks: {s['tracks']} | Clips: {s['total_clips']} | "
            f"Playing: {s['playing']}",
        ]
        if s["active_clips"]:
            lines.append("\n**Now Playing:**")
            for ac in s["active_clips"]:
                lines.append(f"  ▶ {ac['track']}: {ac['clip']}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "bpm": self.bpm,
            "tracks": [t.to_dict() for t in self.tracks],
            "scenes": [s.to_dict() for s in self.scenes],
        }


def create_default_launcher(bpm: float = 140.0) -> ClipLauncher:
    """Create a default clip launcher with standard tracks."""
    launcher = ClipLauncher(bpm)

    track_names = ["Drums", "Bass", "Lead", "Pad", "FX"]
    for name in track_names:
        launcher.add_track(name)

    # Create default scenes
    launcher.add_scene(Scene("Intro", {}, bpm))
    launcher.add_scene(Scene("Build", {}, bpm))
    launcher.add_scene(Scene("Drop", {}, bpm))
    launcher.add_scene(Scene("Break", {}, bpm))
    launcher.add_scene(Scene("Drop 2", {}, bpm))
    launcher.add_scene(Scene("Outro", {}, bpm))

    return launcher


# Module singleton
_launcher: ClipLauncher | None = None


def get_launcher() -> ClipLauncher:
    global _launcher
    if _launcher is None:
        _launcher = create_default_launcher()
    return _launcher


def main() -> None:
    print("Clip Launcher Engine")
    launcher = create_default_launcher(140)

    # Add test clips
    for track in launcher.tracks:
        clip = Clip(f"{track.name} Loop 1", bpm=140, bars=4)
        launcher.add_clip(track.name, clip)
        clip2 = Clip(f"{track.name} Loop 2", bpm=140, bars=8)
        launcher.add_clip(track.name, clip2)

    # Launch some clips
    launcher.launch_clip("Drums", 0)
    launcher.launch_clip("Bass", 0)

    print(launcher.status_text())
    print(f"  Tracks: {[t.name for t in launcher.tracks]}")
    print(f"  Scenes: {[s.name for s in launcher.scenes]}")
    print("Done.")


if __name__ == "__main__":
    main()
