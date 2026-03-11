"""
DUBFORGE — Scene System Engine  (Session 176)

Manages live performance scenes with parameter snapshots,
transitions, and automated sequencing.
"""

import math
import time
from dataclasses import dataclass, field

from engine.config_loader import PHI
@dataclass
class ParamSnapshot:
    """A single parameter value in a scene."""
    module: str
    param: str
    value: float

    def to_dict(self) -> dict:
        return {"module": self.module, "param": self.param, "value": self.value}


@dataclass
class Scene:
    """A scene containing parameter snapshots."""
    name: str
    params: list[ParamSnapshot] = field(default_factory=list)
    bpm: float = 140.0
    color: str = "#FF0000"
    tags: list[str] = field(default_factory=list)

    def get_param(self, module: str, param: str) -> float | None:
        for p in self.params:
            if p.module == module and p.param == param:
                return p.value
        return None

    def set_param(self, module: str, param: str, value: float) -> None:
        for p in self.params:
            if p.module == module and p.param == param:
                p.value = value
                return
        self.params.append(ParamSnapshot(module, param, value))

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "bpm": self.bpm,
            "color": self.color,
            "tags": self.tags,
            "params": [p.to_dict() for p in self.params],
        }


@dataclass
class SceneTransition:
    """Defines how to transition between scenes."""
    from_scene: str
    to_scene: str
    duration_beats: float = 4.0
    curve: str = "linear"  # linear, exponential, phi, s_curve

    def interpolation_factor(self, progress: float) -> float:
        """Get interpolation factor (0-1) for transition progress."""
        t = max(0.0, min(1.0, progress))
        if self.curve == "exponential":
            return t ** 2
        elif self.curve == "phi":
            return t ** (1.0 / PHI)
        elif self.curve == "s_curve":
            return 0.5 * (1.0 + math.tanh(4.0 * (t - 0.5)))
        return t  # linear


class SceneManager:
    """Manages a collection of scenes and transitions."""

    def __init__(self):
        self.scenes: dict[str, Scene] = {}
        self.transitions: list[SceneTransition] = []
        self.active_scene: str | None = None
        self.sequence: list[str] = []
        self.sequence_index: int = 0
        self._transition_start: float = 0.0
        self._transitioning: bool = False
        self._target_scene: str = ""

    def add_scene(self, scene: Scene) -> None:
        """Add a scene."""
        self.scenes[scene.name] = scene

    def remove_scene(self, name: str) -> bool:
        """Remove a scene."""
        if name in self.scenes:
            del self.scenes[name]
            return True
        return False

    def activate(self, name: str) -> bool:
        """Instantly activate a scene."""
        if name in self.scenes:
            self.active_scene = name
            self._transitioning = False
            return True
        return False

    def start_transition(self, target: str,
                          duration_beats: float = 4.0,
                          curve: str = "linear") -> bool:
        """Start transitioning to a target scene."""
        if target not in self.scenes or self.active_scene is None:
            return False

        self.transitions.append(SceneTransition(
            from_scene=self.active_scene,
            to_scene=target,
            duration_beats=duration_beats,
            curve=curve,
        ))
        self._target_scene = target
        self._transitioning = True
        self._transition_start = time.monotonic()
        return True

    def get_current_params(self, bpm: float = 140.0) -> dict[str, dict[str, float]]:
        """Get interpolated parameters for current state."""
        if self.active_scene is None:
            return {}

        scene = self.scenes.get(self.active_scene)
        if scene is None:
            return {}

        if not self._transitioning:
            result: dict[str, dict[str, float]] = {}
            for p in scene.params:
                result.setdefault(p.module, {})[p.param] = p.value
            return result

        # Transitioning
        target = self.scenes.get(self._target_scene)
        if target is None:
            return {}

        elapsed = time.monotonic() - self._transition_start
        beat_s = 60.0 / bpm
        trans = self.transitions[-1] if self.transitions else None
        dur_s = (trans.duration_beats if trans else 4.0) * beat_s

        progress = elapsed / dur_s if dur_s > 0 else 1.0
        if progress >= 1.0:
            self.active_scene = self._target_scene
            self._transitioning = False
            progress = 1.0

        factor = trans.interpolation_factor(progress) if trans else progress

        # Interpolate
        result = {}
        all_keys: set[tuple[str, str]] = set()
        for p in scene.params:
            all_keys.add((p.module, p.param))
        for p in target.params:
            all_keys.add((p.module, p.param))

        for module, param in all_keys:
            val_a = scene.get_param(module, param)
            val_b = target.get_param(module, param)
            if val_a is not None and val_b is not None:
                val = val_a + (val_b - val_a) * factor
            elif val_b is not None:
                val = val_b * factor
            elif val_a is not None:
                val = val_a * (1.0 - factor)
            else:
                continue
            result.setdefault(module, {})[param] = val

        return result

    def set_sequence(self, scene_names: list[str]) -> None:
        """Set scene playback sequence."""
        self.sequence = [s for s in scene_names if s in self.scenes]
        self.sequence_index = 0

    def advance_sequence(self) -> str | None:
        """Move to next scene in sequence."""
        if not self.sequence:
            return None
        self.sequence_index = (self.sequence_index + 1) % len(self.sequence)
        name = self.sequence[self.sequence_index]
        self.activate(name)
        return name

    def get_summary(self) -> dict:
        return {
            "scenes": list(self.scenes.keys()),
            "active": self.active_scene,
            "transitioning": self._transitioning,
            "sequence": self.sequence,
            "sequence_index": self.sequence_index,
        }


# Pre-built dubstep scenes
def create_dubstep_scenes() -> list[Scene]:
    """Create a set of dubstep performance scenes."""
    return [
        Scene(
            name="Intro",
            bpm=140.0,
            color="#4A0080",
            tags=["ambient", "buildup"],
            params=[
                ParamSnapshot("sub_bass", "frequency", 55.0),
                ParamSnapshot("sub_bass", "drive", 0.1),
                ParamSnapshot("reverb", "mix", 0.6),
                ParamSnapshot("sidechain", "depth", 0.3),
                ParamSnapshot("filter", "cutoff", 2000.0),
            ],
        ),
        Scene(
            name="Buildup",
            bpm=140.0,
            color="#FF6600",
            tags=["energy", "tension"],
            params=[
                ParamSnapshot("riser", "rate", 0.5),
                ParamSnapshot("filter", "cutoff", 4000.0),
                ParamSnapshot("sidechain", "depth", 0.5),
                ParamSnapshot("reverb", "mix", 0.4),
                ParamSnapshot("noise", "level", 0.3),
            ],
        ),
        Scene(
            name="Drop",
            bpm=140.0,
            color="#FF0000",
            tags=["heavy", "bass"],
            params=[
                ParamSnapshot("sub_bass", "frequency", 40.0),
                ParamSnapshot("sub_bass", "drive", 0.7),
                ParamSnapshot("wobble", "rate", 4.0),
                ParamSnapshot("wobble", "depth", 0.9),
                ParamSnapshot("sidechain", "depth", 0.8),
                ParamSnapshot("filter", "cutoff", 800.0),
                ParamSnapshot("distortion", "amount", 0.6),
            ],
        ),
        Scene(
            name="Breakdown",
            bpm=140.0,
            color="#0066FF",
            tags=["melodic", "ambient"],
            params=[
                ParamSnapshot("pad", "cutoff", 3000.0),
                ParamSnapshot("pad", "mix", 0.7),
                ParamSnapshot("reverb", "mix", 0.5),
                ParamSnapshot("delay", "mix", 0.4),
                ParamSnapshot("sidechain", "depth", 0.2),
            ],
        ),
        Scene(
            name="Second_Drop",
            bpm=140.0,
            color="#FF0033",
            tags=["heavy", "filthy"],
            params=[
                ParamSnapshot("sub_bass", "frequency", 36.0),
                ParamSnapshot("sub_bass", "drive", 0.9),
                ParamSnapshot("wobble", "rate", 8.0),
                ParamSnapshot("wobble", "depth", 1.0),
                ParamSnapshot("sidechain", "depth", 0.9),
                ParamSnapshot("distortion", "amount", 0.8),
                ParamSnapshot("filter", "cutoff", 600.0),
            ],
        ),
        Scene(
            name="Outro",
            bpm=140.0,
            color="#330066",
            tags=["wind_down"],
            params=[
                ParamSnapshot("reverb", "mix", 0.7),
                ParamSnapshot("filter", "cutoff", 1500.0),
                ParamSnapshot("sidechain", "depth", 0.1),
                ParamSnapshot("sub_bass", "drive", 0.05),
            ],
        ),
    ]


def main() -> None:
    print("Scene System Engine")

    mgr = SceneManager()
    for scene in create_dubstep_scenes():
        mgr.add_scene(scene)

    print(f"  Scenes: {list(mgr.scenes.keys())}")

    mgr.activate("Intro")
    print(f"  Active: {mgr.active_scene}")

    params = mgr.get_current_params()
    print(f"  Params: {len(params)} modules")

    mgr.set_sequence(["Intro", "Buildup", "Drop", "Breakdown",
                       "Second_Drop", "Outro"])
    next_scene = mgr.advance_sequence()
    print(f"  Next in sequence: {next_scene}")

    summary = mgr.get_summary()
    print(f"  Summary: {summary}")
    print("Done.")


if __name__ == "__main__":
    main()
