"""
DUBFORGE — Performance Recorder Engine  (Session 170)

Records parameter changes, clip launches, and control
movements during live performance for later recall/editing.
"""

import json
import os
import time
from dataclasses import dataclass, field

PHI = 1.6180339887


@dataclass
class PerformanceEvent:
    """A single recorded performance event."""
    timestamp: float  # Seconds from start
    event_type: str  # param, clip, note, control, command
    target: str  # Module or control name
    value: float | str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": round(self.timestamp, 4),
            "type": self.event_type,
            "target": self.target,
            "value": self.value,
            "metadata": self.metadata,
        }


@dataclass
class PerformanceRecording:
    """A complete performance recording."""
    name: str = "Performance"
    events: list[PerformanceEvent] = field(default_factory=list)
    bpm: float = 140.0
    start_time: float = 0.0
    duration_s: float = 0.0
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "bpm": self.bpm,
            "duration_s": round(self.duration_s, 2),
            "event_count": len(self.events),
            "tags": self.tags,
            "events": [e.to_dict() for e in self.events],
        }


class PerformanceRecorder:
    """Records and plays back performance data."""

    def __init__(self, bpm: float = 140.0):
        self.bpm = bpm
        self._recording = False
        self._playing = False
        self._start_time = 0.0
        self._current: PerformanceRecording | None = None
        self._recordings: list[PerformanceRecording] = []
        self._max_recordings = 50

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def is_playing(self) -> bool:
        return self._playing

    def start_recording(self, name: str = "") -> PerformanceRecording:
        """Start recording a performance."""
        if not name:
            name = f"Performance {len(self._recordings) + 1}"
        self._current = PerformanceRecording(
            name=name,
            bpm=self.bpm,
            start_time=time.time(),
        )
        self._start_time = time.time()
        self._recording = True
        return self._current

    def stop_recording(self) -> PerformanceRecording | None:
        """Stop recording and save."""
        if not self._recording or not self._current:
            return None
        self._recording = False
        self._current.duration_s = time.time() - self._start_time
        self._recordings.append(self._current)
        if len(self._recordings) > self._max_recordings:
            self._recordings.pop(0)
        result = self._current
        self._current = None
        return result

    def record_event(self, event_type: str, target: str,
                      value=None, **metadata) -> PerformanceEvent | None:
        """Record a single event."""
        if not self._recording or not self._current:
            return None
        timestamp = time.time() - self._start_time
        event = PerformanceEvent(
            timestamp=timestamp,
            event_type=event_type,
            target=target,
            value=value,
            metadata=metadata,
        )
        self._current.events.append(event)
        return event

    def record_param(self, target: str, value: float,
                      **meta) -> PerformanceEvent | None:
        return self.record_event("param", target, value, **meta)

    def record_clip(self, target: str,
                     action: str = "launch") -> PerformanceEvent | None:
        return self.record_event("clip", target, action)

    def record_command(self, command: str) -> PerformanceEvent | None:
        return self.record_event("command", "subphonics", command)

    def get_recording(self, index: int = -1
                       ) -> PerformanceRecording | None:
        """Get a recording by index."""
        if not self._recordings:
            return None
        try:
            return self._recordings[index]
        except IndexError:
            return None

    def list_recordings(self) -> list[dict]:
        """List all recordings."""
        return [
            {
                "index": i,
                "name": r.name,
                "duration_s": round(r.duration_s, 2),
                "events": len(r.events),
                "bpm": r.bpm,
            }
            for i, r in enumerate(self._recordings)
        ]

    def save_to_file(self, recording: PerformanceRecording,
                      path: str = "") -> str:
        """Save recording to JSON file."""
        if not path:
            safe_name = recording.name.lower().replace(" ", "_")
            path = f"output/memory/performances/{safe_name}.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(recording.to_dict(), f, indent=2)
        return path

    def load_from_file(self, path: str) -> PerformanceRecording | None:
        """Load recording from JSON file."""
        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

        recording = PerformanceRecording(
            name=data.get("name", "Loaded"),
            bpm=data.get("bpm", 140.0),
            duration_s=data.get("duration_s", 0.0),
            tags=data.get("tags", []),
        )
        for e in data.get("events", []):
            recording.events.append(PerformanceEvent(
                timestamp=e.get("timestamp", 0.0),
                event_type=e.get("type", "unknown"),
                target=e.get("target", ""),
                value=e.get("value"),
                metadata=e.get("metadata", {}),
            ))
        self._recordings.append(recording)
        return recording

    def get_events_at(self, recording: PerformanceRecording,
                       time_s: float,
                       window_s: float = 0.01
                       ) -> list[PerformanceEvent]:
        """Get events near a specific time."""
        return [
            e for e in recording.events
            if abs(e.timestamp - time_s) <= window_s
        ]

    def quantize(self, recording: PerformanceRecording,
                  grid_beats: float = 0.25) -> PerformanceRecording:
        """Quantize event timings to a grid."""
        beat_duration = 60.0 / recording.bpm
        grid_s = grid_beats * beat_duration

        quantized = PerformanceRecording(
            name=f"{recording.name} (quantized)",
            bpm=recording.bpm,
            duration_s=recording.duration_s,
        )
        for e in recording.events:
            q_time = round(e.timestamp / grid_s) * grid_s
            quantized.events.append(PerformanceEvent(
                timestamp=q_time,
                event_type=e.event_type,
                target=e.target,
                value=e.value,
                metadata=e.metadata,
            ))
        return quantized

    def status(self) -> dict:
        return {
            "recording": self._recording,
            "playing": self._playing,
            "recordings_count": len(self._recordings),
            "current_events": len(self._current.events)
            if self._current else 0,
        }

    def status_text(self) -> str:
        s = self.status()
        state = "🔴 Recording" if s["recording"] else \
                "▶️ Playing" if s["playing"] else "⏹ Idle"
        lines = [
            f"**Performance Recorder** — {state}",
            f"Recordings: {s['recordings_count']}",
        ]
        if s["recording"]:
            lines.append(f"Current events: {s['current_events']}")
        recs = self.list_recordings()
        if recs:
            lines.append("\n**Recordings:**")
            for r in recs[-5:]:
                lines.append(f"  [{r['index']}] {r['name']}: "
                              f"{r['duration_s']}s, {r['events']} events")
        return "\n".join(lines)


# Module singleton
_recorder: PerformanceRecorder | None = None


def get_recorder() -> PerformanceRecorder:
    global _recorder
    if _recorder is None:
        _recorder = PerformanceRecorder()
    return _recorder


def main() -> None:
    print("Performance Recorder Engine")
    rec = PerformanceRecorder(140)

    # Simulate a performance
    _perf = rec.start_recording("Test Performance")
    rec.record_param("volume", 0.8, track="drums")
    rec.record_clip("drums/loop1", "launch")
    rec.record_command("make sub bass")
    rec.record_param("filter_cutoff", 2000.0, track="bass")
    result = rec.stop_recording()

    if result:
        print(f"  Recorded: {result.name}, {len(result.events)} events")
        # Quantize
        q = rec.quantize(result)
        print(f"  Quantized: {len(q.events)} events")

    print(rec.status_text())
    print("Done.")


if __name__ == "__main__":
    main()
