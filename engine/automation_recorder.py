"""
DUBFORGE — Automation Recorder  (Session 207)

Record, edit, and playback parameter automation curves.
Supports linear/bezier/step interpolation, tempo sync,
and PHI-curve automation.
"""

import math
from dataclasses import dataclass, field

PHI = 1.6180339887
SAMPLE_RATE = 48000


@dataclass
class AutomationPoint:
    """A single automation point."""
    time: float  # seconds
    value: float
    curve: str = "linear"  # linear, step, exponential, phi, bezier

    def to_dict(self) -> dict:
        return {
            "time": round(self.time, 4),
            "value": round(self.value, 4),
            "curve": self.curve,
        }


@dataclass
class AutomationLane:
    """An automation lane for one parameter."""
    name: str
    target_module: str
    target_param: str
    points: list[AutomationPoint] = field(default_factory=list)
    min_value: float = 0.0
    max_value: float = 1.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "module": self.target_module,
            "param": self.target_param,
            "points": [p.to_dict() for p in self.points],
            "range": [self.min_value, self.max_value],
        }


class AutomationRecorder:
    """Record and playback parameter automation."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.lanes: dict[str, AutomationLane] = {}
        self.recording: bool = False
        self._record_buffer: dict[str, list[tuple[float, float]]] = {}

    def create_lane(self, name: str, target_module: str,
                    target_param: str,
                    min_val: float = 0.0,
                    max_val: float = 1.0) -> AutomationLane:
        """Create an automation lane."""
        lane = AutomationLane(
            name=name,
            target_module=target_module,
            target_param=target_param,
            min_value=min_val,
            max_value=max_val,
        )
        self.lanes[name] = lane
        return lane

    def add_point(self, lane_name: str, time: float, value: float,
                  curve: str = "linear") -> bool:
        """Add a point to an automation lane."""
        lane = self.lanes.get(lane_name)
        if not lane:
            return False

        # Clamp value
        value = max(lane.min_value, min(lane.max_value, value))

        point = AutomationPoint(time=time, value=value, curve=curve)
        lane.points.append(point)
        lane.points.sort(key=lambda p: p.time)
        return True

    def remove_point(self, lane_name: str, index: int) -> bool:
        """Remove a point by index."""
        lane = self.lanes.get(lane_name)
        if not lane or index >= len(lane.points):
            return False
        lane.points.pop(index)
        return True

    def clear_lane(self, lane_name: str) -> bool:
        """Clear all points from a lane."""
        lane = self.lanes.get(lane_name)
        if not lane:
            return False
        lane.points.clear()
        return True

    # --- Recording ---

    def start_recording(self, lane_names: list[str] = None) -> None:
        """Start recording automation."""
        self.recording = True
        names = lane_names or list(self.lanes.keys())
        for name in names:
            self._record_buffer[name] = []

    def record_value(self, lane_name: str, time: float,
                     value: float) -> None:
        """Record a value during recording."""
        if not self.recording:
            return
        if lane_name in self._record_buffer:
            self._record_buffer[lane_name].append((time, value))

    def stop_recording(self, thin_threshold: float = 0.01) -> dict:
        """Stop recording and process recorded data."""
        self.recording = False
        result: dict[str, int] = {}

        for lane_name, buffer in self._record_buffer.items():
            lane = self.lanes.get(lane_name)
            if not lane or not buffer:
                continue

            # Thin the data: remove points that don't change much
            thinned: list[tuple[float, float]] = [buffer[0]]
            for i in range(1, len(buffer) - 1):
                prev_val = thinned[-1][1]
                curr_val = buffer[i][1]
                if abs(curr_val - prev_val) > thin_threshold:
                    thinned.append(buffer[i])

            if buffer:
                thinned.append(buffer[-1])

            # Add to lane
            for t, v in thinned:
                lane.points.append(
                    AutomationPoint(time=t, value=v, curve="linear")
                )
            lane.points.sort(key=lambda p: p.time)

            result[lane_name] = len(thinned)

        self._record_buffer.clear()
        return result

    # --- Interpolation ---

    def _interpolate(self, p1: AutomationPoint,
                     p2: AutomationPoint,
                     t: float) -> float:
        """Interpolate between two points."""
        if p1.time == p2.time:
            return p2.value

        normalized = (t - p1.time) / (p2.time - p1.time)
        normalized = max(0.0, min(1.0, normalized))

        curve = p1.curve

        if curve == "step":
            return p1.value

        elif curve == "linear":
            return p1.value + (p2.value - p1.value) * normalized

        elif curve == "exponential":
            shaped = normalized * normalized
            return p1.value + (p2.value - p1.value) * shaped

        elif curve == "phi":
            shaped = normalized ** (1 / PHI)
            return p1.value + (p2.value - p1.value) * shaped

        elif curve == "bezier":
            # Cubic ease-in-out
            if normalized < 0.5:
                shaped = 4 * normalized ** 3
            else:
                shaped = 1 - (-2 * normalized + 2) ** 3 / 2
            return p1.value + (p2.value - p1.value) * shaped

        elif curve == "sine":
            shaped = 0.5 * (1 - math.cos(math.pi * normalized))
            return p1.value + (p2.value - p1.value) * shaped

        return p1.value + (p2.value - p1.value) * normalized

    def get_value_at(self, lane_name: str, time: float) -> float:
        """Get interpolated value at time."""
        lane = self.lanes.get(lane_name)
        if not lane or not lane.points:
            return 0.0

        # Before first point
        if time <= lane.points[0].time:
            return lane.points[0].value

        # After last point
        if time >= lane.points[-1].time:
            return lane.points[-1].value

        # Find surrounding points
        for i in range(len(lane.points) - 1):
            p1 = lane.points[i]
            p2 = lane.points[i + 1]
            if p1.time <= time <= p2.time:
                return self._interpolate(p1, p2, time)

        return lane.points[-1].value

    def render_lane(self, lane_name: str,
                    duration: float) -> list[float]:
        """Render automation lane to sample-rate buffer."""
        n = int(self.sample_rate * duration)
        buffer: list[float] = []
        for i in range(n):
            t = i / self.sample_rate
            buffer.append(self.get_value_at(lane_name, t))
        return buffer

    # --- Generation ---

    def generate_lfo(self, lane_name: str, rate: float = 1.0,
                     shape: str = "sine", depth: float = 1.0,
                     duration: float = 4.0,
                     center: float = 0.5) -> int:
        """Generate LFO automation."""
        lane = self.lanes.get(lane_name)
        if not lane:
            return 0

        points_per_cycle = 32
        total_points = int(rate * duration * points_per_cycle)
        count = 0

        for i in range(total_points):
            t = i * duration / total_points
            phase = (t * rate) % 1.0

            if shape == "sine":
                val = math.sin(2 * math.pi * phase)
            elif shape == "triangle":
                val = 4 * abs(phase - 0.5) - 1
            elif shape == "saw":
                val = 2 * phase - 1
            elif shape == "square":
                val = 1.0 if phase < 0.5 else -1.0
            elif shape == "phi_saw":
                val = 2 * (phase ** (1 / PHI)) - 1
            else:
                val = math.sin(2 * math.pi * phase)

            scaled = center + val * depth * 0.5
            scaled = max(lane.min_value, min(lane.max_value, scaled))

            lane.points.append(
                AutomationPoint(time=t, value=scaled, curve="linear")
            )
            count += 1

        lane.points.sort(key=lambda p: p.time)
        return count

    def generate_ramp(self, lane_name: str,
                      start_val: float, end_val: float,
                      start_time: float = 0.0,
                      end_time: float = 4.0,
                      curve: str = "linear") -> bool:
        """Generate a ramp automation."""
        return (
            self.add_point(lane_name, start_time, start_val, curve) and
            self.add_point(lane_name, end_time, end_val, curve)
        )

    def apply_to_samples(self, samples: list[float],
                         lane_name: str,
                         mode: str = "multiply") -> list[float]:
        """Apply automation to audio samples."""
        duration = len(samples) / self.sample_rate
        automation = self.render_lane(lane_name, duration)

        result: list[float] = []
        for i, s in enumerate(samples):
            a = automation[i] if i < len(automation) else (
                automation[-1] if automation else 1.0
            )

            if mode == "multiply":
                result.append(s * a)
            elif mode == "add":
                result.append(s + a)
            elif mode == "replace":
                result.append(a)
            else:
                result.append(s * a)

        return result

    def get_summary(self) -> dict:
        return {
            "lanes": len(self.lanes),
            "total_points": sum(
                len(lane.points) for lane in self.lanes.values()
            ),
            "recording": self.recording,
            "lane_details": {
                name: len(lane.points)
                for name, lane in self.lanes.items()
            },
        }


def main() -> None:
    print("Automation Recorder")

    rec = AutomationRecorder()

    # Create lanes
    rec.create_lane("filter", "bass", "cutoff", 100, 10000)
    rec.create_lane("volume", "master", "gain", 0, 1)

    # Add points
    rec.add_point("filter", 0.0, 500, "linear")
    rec.add_point("filter", 1.0, 5000, "phi")
    rec.add_point("filter", 2.0, 200, "exponential")
    rec.add_point("filter", 4.0, 8000, "bezier")

    # Get values
    for t in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0]:
        v = rec.get_value_at("filter", t)
        print(f"  t={t:.1f}s → cutoff={v:.0f}")

    # Generate LFO
    rec.create_lane("wobble", "bass", "wobble_depth", 0, 1)
    count = rec.generate_lfo("wobble", rate=4.0, shape="sine",
                              depth=0.8, duration=2.0)
    print(f"\n  LFO: {count} points")

    print(f"\n  Summary: {rec.get_summary()}")
    print("Done.")


if __name__ == "__main__":
    main()
