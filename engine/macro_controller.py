"""
DUBFORGE — Macro Controller  (Session 203)

Macro parameter mapping: map one control to multiple
parameters with scaling, curves, and ranges.
"""

import math
from dataclasses import dataclass, field

PHI = 1.6180339887


@dataclass
class ParameterMapping:
    """Maps a macro to a target parameter."""
    target_module: str
    target_param: str
    min_value: float = 0.0
    max_value: float = 1.0
    curve: str = "linear"  # linear, exponential, log, phi, inverse
    inverted: bool = False

    def to_dict(self) -> dict:
        return {
            "module": self.target_module,
            "param": self.target_param,
            "min": self.min_value,
            "max": self.max_value,
            "curve": self.curve,
            "inverted": self.inverted,
        }


@dataclass
class Macro:
    """A macro controller."""
    name: str
    value: float = 0.0
    default: float = 0.0
    label: str = ""
    color: str = "#FFD700"
    mappings: list[ParameterMapping] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": round(self.value, 4),
            "default": self.default,
            "label": self.label,
            "mappings": [m.to_dict() for m in self.mappings],
        }


# Preset macro configurations for dubstep
MACRO_PRESETS = {
    "wobble_depth": {
        "label": "Wobble Depth",
        "mappings": [
            {"module": "wobble_bass", "param": "depth",
             "min": 0.0, "max": 1.0, "curve": "linear"},
            {"module": "lfo_matrix", "param": "amount",
             "min": 0.0, "max": 1.0, "curve": "exponential"},
        ]
    },
    "darkness": {
        "label": "Darkness",
        "mappings": [
            {"module": "intelligent_eq", "param": "high_cut",
             "min": 20000, "max": 2000, "curve": "log"},
            {"module": "reverb_delay", "param": "decay",
             "min": 0.5, "max": 5.0, "curve": "linear"},
            {"module": "stereo_imager", "param": "width",
             "min": 1.0, "max": 0.3, "curve": "phi"},
        ]
    },
    "aggression": {
        "label": "Aggression",
        "mappings": [
            {"module": "multiband_distortion", "param": "drive",
             "min": 0.0, "max": 1.0, "curve": "exponential"},
            {"module": "dynamics", "param": "ratio",
             "min": 2.0, "max": 20.0, "curve": "exponential"},
            {"module": "noise_generator", "param": "level",
             "min": 0.0, "max": 0.3, "curve": "linear"},
        ]
    },
    "phi_morph": {
        "label": "PHI Morph",
        "mappings": [
            {"module": "spectral_morph", "param": "blend",
             "min": 0.0, "max": 1.0, "curve": "phi"},
            {"module": "wavetable_morph", "param": "position",
             "min": 0.0, "max": 1.0, "curve": "phi"},
        ]
    },
}


class MacroController:
    """Macro parameter mapping engine."""

    def __init__(self, num_macros: int = 8):
        self.macros: dict[str, Macro] = {}
        self.parameter_state: dict[str, dict[str, float]] = {}

        # Initialize default macros
        for i in range(num_macros):
            name = f"macro_{i + 1}"
            self.macros[name] = Macro(
                name=name,
                label=f"Macro {i + 1}",
                color=f"#{hex(int(0xFFD700 + i * 0x110011) & 0xFFFFFF)[2:]}",
            )

    def _apply_curve(self, value: float, curve: str) -> float:
        """Apply curve to normalized value [0-1]."""
        v = max(0.0, min(1.0, value))

        if curve == "linear":
            return v
        elif curve == "exponential":
            return v * v
        elif curve == "log":
            return math.sqrt(v)
        elif curve == "phi":
            return v ** (1 / PHI)
        elif curve == "inverse":
            return 1.0 - v
        elif curve == "s_curve":
            return v * v * (3 - 2 * v)
        else:
            return v

    def add_macro(self, name: str, label: str = "",
                  default: float = 0.0) -> Macro:
        """Add a named macro."""
        macro = Macro(
            name=name,
            label=label or name,
            default=default,
            value=default,
        )
        self.macros[name] = macro
        return macro

    def add_mapping(self, macro_name: str,
                    target_module: str, target_param: str,
                    min_value: float = 0.0, max_value: float = 1.0,
                    curve: str = "linear",
                    inverted: bool = False) -> bool:
        """Add a parameter mapping to a macro."""
        macro = self.macros.get(macro_name)
        if not macro:
            return False

        mapping = ParameterMapping(
            target_module=target_module,
            target_param=target_param,
            min_value=min_value,
            max_value=max_value,
            curve=curve,
            inverted=inverted,
        )
        macro.mappings.append(mapping)
        return True

    def set_value(self, macro_name: str,
                  value: float) -> dict[str, dict[str, float]]:
        """Set macro value and compute all mapped parameters."""
        macro = self.macros.get(macro_name)
        if not macro:
            return {}

        macro.value = max(0.0, min(1.0, value))
        results: dict[str, dict[str, float]] = {}

        for mapping in macro.mappings:
            # Apply curve
            v = macro.value
            if mapping.inverted:
                v = 1.0 - v
            curved = self._apply_curve(v, mapping.curve)

            # Scale to range
            param_val = mapping.min_value + (
                mapping.max_value - mapping.min_value
            ) * curved

            # Store result
            module = mapping.target_module
            if module not in results:
                results[module] = {}
            results[module][mapping.target_param] = round(param_val, 6)

            # Update global state
            if module not in self.parameter_state:
                self.parameter_state[module] = {}
            self.parameter_state[module][mapping.target_param] = param_val

        return results

    def get_value(self, macro_name: str) -> float:
        """Get current macro value."""
        macro = self.macros.get(macro_name)
        return macro.value if macro else 0.0

    def reset(self, macro_name: str = "") -> None:
        """Reset macro(s) to default."""
        if macro_name:
            macro = self.macros.get(macro_name)
            if macro:
                macro.value = macro.default
                self.set_value(macro_name, macro.default)
        else:
            for name, macro in self.macros.items():
                macro.value = macro.default
                self.set_value(name, macro.default)

    def load_preset(self, preset_name: str) -> bool:
        """Load a macro preset."""
        preset = MACRO_PRESETS.get(preset_name)
        if not preset:
            return False

        _macro = self.add_macro(preset_name, preset.get("label", ""))
        for m in preset.get("mappings", []):
            self.add_mapping(
                preset_name,
                m["module"], m["param"],
                m.get("min", 0), m.get("max", 1),
                m.get("curve", "linear"),
                m.get("inverted", False),
            )

        return True

    def get_parameter_state(self) -> dict:
        """Get all current parameter values."""
        return dict(self.parameter_state)

    def get_presets(self) -> list[str]:
        """List available presets."""
        return list(MACRO_PRESETS.keys())

    def get_summary(self) -> dict:
        """Get macro controller summary."""
        return {
            "macros": len(self.macros),
            "total_mappings": sum(
                len(m.mappings) for m in self.macros.values()
            ),
            "active": [
                name for name, m in self.macros.items()
                if m.value != m.default
            ],
        }


def main() -> None:
    print("Macro Controller")

    ctrl = MacroController(8)

    # Load presets
    ctrl.load_preset("wobble_depth")
    ctrl.load_preset("darkness")
    ctrl.load_preset("aggression")

    # Set values
    result = ctrl.set_value("wobble_depth", 0.75)
    print(f"  Wobble @ 0.75: {result}")

    result = ctrl.set_value("darkness", 0.5)
    print(f"  Darkness @ 0.5: {result}")

    result = ctrl.set_value("aggression", 1.0)
    print(f"  Aggression @ 1.0: {result}")

    # Summary
    print(f"\n  Presets: {ctrl.get_presets()}")
    print(f"  Summary: {ctrl.get_summary()}")
    print("Done.")


if __name__ == "__main__":
    main()
