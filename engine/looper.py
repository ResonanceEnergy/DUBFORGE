"""
DUBFORGE — Looper Engine  (Session 168)

Multi-layer loop recording and playback with overdub,
undo, reverse, half-speed, and PHI-ratio loop lengths.
"""

import math
import os
import struct
import wave
from dataclasses import dataclass, field
from enum import Enum

from engine.config_loader import PHI
SAMPLE_RATE = 48000


class LoopState(Enum):
    EMPTY = "empty"
    RECORDING = "recording"
    PLAYING = "playing"
    OVERDUBBING = "overdubbing"
    STOPPED = "stopped"


@dataclass
class LoopLayer:
    """A single layer in a loop."""
    signal: list[float] = field(default_factory=list)
    volume: float = 1.0
    mute: bool = False


@dataclass
class Loop:
    """A multi-layer loop."""
    name: str = "Loop"
    layers: list[LoopLayer] = field(default_factory=list)
    length_samples: int = 0
    state: LoopState = LoopState.EMPTY
    playhead: int = 0
    master_volume: float = 1.0
    reverse: bool = False
    half_speed: bool = False
    feedback: float = 1.0  # For overdub decay

    @property
    def duration_s(self) -> float:
        return self.length_samples / SAMPLE_RATE if self.length_samples else 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "layers": len(self.layers),
            "length_samples": self.length_samples,
            "duration_s": round(self.duration_s, 2),
            "reverse": self.reverse,
            "half_speed": self.half_speed,
            "playhead": self.playhead,
        }


class Looper:
    """Multi-loop looper engine."""

    def __init__(self, n_loops: int = 4):
        self.loops: list[Loop] = [
            Loop(name=f"Loop {i + 1}") for i in range(n_loops)
        ]
        self._undo_stack: list[tuple[int, LoopLayer]] = []
        self._max_undo = 10

    def record(self, loop_index: int, signal: list[float]) -> bool:
        """Record a signal into a loop."""
        if not (0 <= loop_index < len(self.loops)):
            return False
        loop = self.loops[loop_index]

        if loop.state == LoopState.EMPTY:
            # First recording sets loop length
            layer = LoopLayer(signal=list(signal))
            loop.layers = [layer]
            loop.length_samples = len(signal)
            loop.state = LoopState.PLAYING
            return True
        return False

    def overdub(self, loop_index: int, signal: list[float]) -> bool:
        """Overdub onto an existing loop."""
        if not (0 <= loop_index < len(self.loops)):
            return False
        loop = self.loops[loop_index]

        if loop.state in (LoopState.PLAYING, LoopState.STOPPED):
            # Trim or pad signal to loop length
            trimmed = signal[:loop.length_samples]
            if len(trimmed) < loop.length_samples:
                trimmed += [0.0] * (loop.length_samples - len(trimmed))

            layer = LoopLayer(signal=trimmed)
            # Save for undo
            self._undo_stack.append((loop_index, layer))
            if len(self._undo_stack) > self._max_undo:
                self._undo_stack.pop(0)

            loop.layers.append(layer)
            return True
        return False

    def undo(self, loop_index: int) -> bool:
        """Remove last overdub layer."""
        if not (0 <= loop_index < len(self.loops)):
            return False
        loop = self.loops[loop_index]
        if len(loop.layers) > 1:
            loop.layers.pop()
            return True
        return False

    def clear(self, loop_index: int) -> bool:
        """Clear a loop."""
        if not (0 <= loop_index < len(self.loops)):
            return False
        loop = self.loops[loop_index]
        loop.layers = []
        loop.length_samples = 0
        loop.state = LoopState.EMPTY
        loop.playhead = 0
        return True

    def toggle_reverse(self, loop_index: int) -> bool:
        if not (0 <= loop_index < len(self.loops)):
            return False
        self.loops[loop_index].reverse = not self.loops[loop_index].reverse
        return True

    def toggle_half_speed(self, loop_index: int) -> bool:
        if not (0 <= loop_index < len(self.loops)):
            return False
        self.loops[loop_index].half_speed = \
            not self.loops[loop_index].half_speed
        return True

    def play(self, loop_index: int) -> bool:
        if not (0 <= loop_index < len(self.loops)):
            return False
        loop = self.loops[loop_index]
        if loop.state != LoopState.EMPTY:
            loop.state = LoopState.PLAYING
            return True
        return False

    def stop(self, loop_index: int) -> bool:
        if not (0 <= loop_index < len(self.loops)):
            return False
        self.loops[loop_index].state = LoopState.STOPPED
        self.loops[loop_index].playhead = 0
        return True

    def stop_all(self) -> None:
        for loop in self.loops:
            if loop.state == LoopState.PLAYING:
                loop.state = LoopState.STOPPED
                loop.playhead = 0

    def get_mixed_signal(self, loop_index: int) -> list[float]:
        """Get the mixed-down signal for a loop."""
        if not (0 <= loop_index < len(self.loops)):
            return []
        loop = self.loops[loop_index]
        if not loop.layers:
            return []

        n = loop.length_samples
        mixed = [0.0] * n

        for layer in loop.layers:
            if layer.mute:
                continue
            for i in range(min(n, len(layer.signal))):
                mixed[i] += layer.signal[i] * layer.volume

        # Apply reverse
        if loop.reverse:
            mixed = list(reversed(mixed))

        # Apply half speed (simple stretch)
        if loop.half_speed:
            stretched = [0.0] * (n * 2)
            for i in range(n * 2):
                src = i / 2.0
                idx = int(src)
                frac = src - idx
                if idx + 1 < n:
                    stretched[i] = mixed[idx] * (1 - frac) + \
                        mixed[idx + 1] * frac
                elif idx < n:
                    stretched[i] = mixed[idx]
            mixed = stretched

        # Master volume
        mixed = [s * loop.master_volume for s in mixed]
        return mixed

    def status(self) -> dict:
        return {
            "loops": [lp.to_dict() for lp in self.loops],
            "active": sum(1 for lp in self.loops
                          if lp.state == LoopState.PLAYING),
        }

    def status_text(self) -> str:
        lines = ["**Looper** — {} loops".format(len(self.loops))]
        for i, loop in enumerate(self.loops):
            icon = {
                LoopState.EMPTY: "⬜",
                LoopState.RECORDING: "🔴",
                LoopState.PLAYING: "▶️",
                LoopState.OVERDUBBING: "🟡",
                LoopState.STOPPED: "⏹",
            }.get(loop.state, "?")
            layers = len(loop.layers)
            dur = f"{loop.duration_s:.1f}s" if loop.duration_s else "empty"
            mods = []
            if loop.reverse:
                mods.append("REV")
            if loop.half_speed:
                mods.append("½×")
            mod_str = f" [{','.join(mods)}]" if mods else ""
            lines.append(f"  {icon} {loop.name}: {dur}, "
                          f"{layers} layers{mod_str}")
        return "\n".join(lines)


def generate_loop_signal(freq: float, duration_s: float,
                          waveform: str = "sine",
                          sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Generate a simple loop signal for testing."""
    n = int(duration_s * sample_rate)
    dt = 1.0 / sample_rate
    signal = [0.0] * n

    for i in range(n):
        t = i * dt
        if waveform == "sine":
            signal[i] = math.sin(2 * math.pi * freq * t)
        elif waveform == "saw":
            phase = (freq * t) % 1.0
            signal[i] = 2.0 * phase - 1.0

    return signal


def _write_wav(path: str, signal: list[float],
               sample_rate: int = SAMPLE_RATE) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    peak = max(abs(s) for s in signal) if signal else 1.0
    scale = 32767.0 / max(peak, 1e-10) * 0.9
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = b"".join(
            struct.pack("<h", max(-32768, min(32767, int(s * scale))))
            for s in signal
        )
        wf.writeframes(frames)
    return path


def main() -> None:
    print("Looper Engine")
    looper = Looper(4)

    # Record a loop
    sig = generate_loop_signal(110, 2.0, "sine")
    looper.record(0, sig)

    # Overdub
    sig2 = generate_loop_signal(220, 2.0, "saw")
    looper.overdub(0, [s * 0.3 for s in sig2])

    # Toggle effects
    looper.toggle_reverse(0)
    looper.play(0)

    print(looper.status_text())

    # Export
    mixed = looper.get_mixed_signal(0)
    if mixed:
        path = _write_wav("output/drums/looper_test.wav", mixed)
        print(f"  Exported: {path}")
    print("Done.")


if __name__ == "__main__":
    main()
