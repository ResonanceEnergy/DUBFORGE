"""
DUBFORGE — Plugin Host  (Session 229)

Host-side plugin management — scan, load, route,
parameter automation, preset management.
(Scaffold for future VST/AU integration.)
"""

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from engine.config_loader import PHI
SAMPLE_RATE = 48000


@dataclass
class PluginParameter:
    """A plugin parameter."""
    name: str
    value: float = 0.0
    min_val: float = 0.0
    max_val: float = 1.0
    default: float = 0.0
    unit: str = ""
    label: str = ""

    @property
    def normalized(self) -> float:
        rng = self.max_val - self.min_val
        return (self.value - self.min_val) / rng if rng > 0 else 0.0


@dataclass
class PluginInfo:
    """Plugin metadata."""
    name: str
    plugin_type: str = "internal"  # internal, vst3, au
    vendor: str = "DUBFORGE"
    version: str = "1.0.0"
    category: str = "effect"  # effect, instrument, analyzer
    input_channels: int = 1
    output_channels: int = 1
    parameters: list[PluginParameter] = field(default_factory=list)
    presets: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.plugin_type,
            "vendor": self.vendor,
            "version": self.version,
            "category": self.category,
            "inputs": self.input_channels,
            "outputs": self.output_channels,
            "param_count": len(self.parameters),
            "preset_count": len(self.presets),
        }


class InternalPlugin:
    """Base class for internal plugins."""

    def __init__(self, info: PluginInfo):
        self.info = info
        self._bypassed = False

    @property
    def bypassed(self) -> bool:
        return self._bypassed

    def bypass(self, state: bool = True) -> None:
        self._bypassed = state

    def process(self, samples: list[float]) -> list[float]:
        """Process audio. Override in subclasses."""
        if self._bypassed:
            return list(samples)
        return list(samples)

    def get_parameter(self, name: str) -> float | None:
        for p in self.info.parameters:
            if p.name == name:
                return p.value
        return None

    def set_parameter(self, name: str, value: float) -> bool:
        for p in self.info.parameters:
            if p.name == name:
                p.value = max(p.min_val, min(p.max_val, value))
                return True
        return False


class GainPlugin(InternalPlugin):
    """Simple gain plugin."""

    def __init__(self):
        super().__init__(PluginInfo(
            name="DUBFORGE Gain",
            parameters=[
                PluginParameter("gain_db", 0.0, -60.0, 24.0, 0.0, "dB"),
            ],
        ))

    def process(self, samples: list[float]) -> list[float]:
        if self._bypassed:
            return list(samples)
        gain_db = self.get_parameter("gain_db") or 0.0
        gain = 10 ** (gain_db / 20)
        return [s * gain for s in samples]


class SaturatePlugin(InternalPlugin):
    """Saturation plugin."""

    def __init__(self):
        super().__init__(PluginInfo(
            name="DUBFORGE Saturate",
            parameters=[
                PluginParameter("drive", 0.5, 0.0, 1.0, 0.5),
                PluginParameter("mix", 1.0, 0.0, 1.0, 1.0),
            ],
        ))

    def process(self, samples: list[float]) -> list[float]:
        if self._bypassed:
            return list(samples)
        drive = self.get_parameter("drive") or 0.5
        mix = self.get_parameter("mix") or 1.0
        d = 1 + drive * 10

        result: list[float] = []
        for s in samples:
            wet = math.tanh(d * s)
            result.append(wet * mix + s * (1 - mix))
        return result


class FilterPlugin(InternalPlugin):
    """Simple filter plugin."""

    def __init__(self):
        super().__init__(PluginInfo(
            name="DUBFORGE Filter",
            parameters=[
                PluginParameter("cutoff", 1000.0, 20.0, 20000.0, 1000.0, "Hz"),
                PluginParameter("resonance", 0.5, 0.0, 1.0, 0.5),
            ],
        ))
        self._y1 = 0.0
        self._y2 = 0.0

    def process(self, samples: list[float]) -> list[float]:
        if self._bypassed:
            return list(samples)
        cutoff = self.get_parameter("cutoff") or 1000.0
        alpha = 2 * math.pi * cutoff / SAMPLE_RATE
        alpha = min(0.99, alpha)

        result: list[float] = []
        for s in samples:
            self._y1 += alpha * (s - self._y1)
            result.append(self._y1)
        return result


class PluginHost:
    """Manage and route plugins."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.plugins: dict[str, InternalPlugin] = {}
        self.chain: list[str] = []

        # Register built-in plugins
        self._builtins = {
            "gain": GainPlugin,
            "saturate": SaturatePlugin,
            "filter": FilterPlugin,
        }

    def create_plugin(self, plugin_type: str,
                      instance_name: str | None = None) -> InternalPlugin | None:
        """Create a plugin instance."""
        factory = self._builtins.get(plugin_type)
        if not factory:
            return None

        plugin = factory()
        name = instance_name or f"{plugin_type}_{len(self.plugins)}"
        self.plugins[name] = plugin
        self.chain.append(name)
        return plugin

    def remove_plugin(self, name: str) -> bool:
        """Remove a plugin."""
        if name in self.plugins:
            del self.plugins[name]
            if name in self.chain:
                self.chain.remove(name)
            return True
        return False

    def reorder(self, order: list[str]) -> None:
        """Reorder plugin chain."""
        self.chain = [n for n in order if n in self.plugins]

    def process(self, samples: list[float]) -> list[float]:
        """Process through entire chain."""
        result = list(samples)
        for name in self.chain:
            plugin = self.plugins.get(name)
            if plugin:
                result = plugin.process(result)
        return result

    def get_chain_info(self) -> list[dict]:
        """Get chain configuration."""
        info: list[dict] = []
        for name in self.chain:
            plugin = self.plugins.get(name)
            if plugin:
                d = plugin.info.to_dict()
                d["instance_name"] = name
                d["bypassed"] = plugin.bypassed
                d["params"] = {
                    p.name: p.value for p in plugin.info.parameters
                }
                info.append(d)
        return info

    def save_chain(self, path: str) -> None:
        """Save chain configuration."""
        data = {
            "chain": self.chain,
            "plugins": {},
        }
        for name in self.chain:
            p = self.plugins.get(name)
            if p:
                data["plugins"][name] = {
                    "type": p.info.name,
                    "bypassed": p.bypassed,
                    "params": {
                        param.name: param.value
                        for param in p.info.parameters
                    },
                }

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def list_available(self) -> list[str]:
        """List available plugin types."""
        return list(self._builtins.keys())


def main() -> None:
    print("Plugin Host")
    host = PluginHost()

    # Build chain
    host.create_plugin("gain", "input_gain")
    host.create_plugin("saturate", "drive")
    host.create_plugin("filter", "low_pass")

    # Configure
    host.plugins["input_gain"].set_parameter("gain_db", 6.0)
    host.plugins["drive"].set_parameter("drive", 0.7)
    host.plugins["low_pass"].set_parameter("cutoff", 2000.0)

    # Process
    n = SAMPLE_RATE
    samples = [0.3 * math.sin(2 * math.pi * 440 * i / SAMPLE_RATE)
               for i in range(n)]

    output = host.process(samples)
    print(f"  Input peak: {max(abs(s) for s in samples):.3f}")
    print(f"  Output peak: {max(abs(s) for s in output):.3f}")

    # Chain info
    info = host.get_chain_info()
    for p in info:
        print(f"  {p['instance_name']}: {p['name']} "
              f"params={p['params']}")

    print(f"\n  Available: {host.list_available()}")
    print("Done.")


if __name__ == "__main__":
    main()
