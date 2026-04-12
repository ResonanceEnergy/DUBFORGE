"""
DUBFORGE — Signal Chain Builder  (Session 204)

Build and manage signal processing chains: serial,
parallel, split, and mix routing with modules.
"""

import math
import os
import struct
import wave
from dataclasses import dataclass, field

from engine.config_loader import PHI
SAMPLE_RATE = 48000


@dataclass
class ChainNode:
    """A node in the signal chain."""
    name: str
    process_type: str  # "effect", "generator", "mixer", "split"
    params: dict = field(default_factory=dict)
    enabled: bool = True
    wet_dry: float = 1.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.process_type,
            "params": self.params,
            "enabled": self.enabled,
            "wet_dry": self.wet_dry,
        }


# Built-in processing functions
def _process_gain(samples: list[float], params: dict) -> list[float]:
    db = params.get("db", 0.0)
    gain = 10.0 ** (db / 20.0)
    return [min(1.0, max(-1.0, s * gain)) for s in samples]


def _process_distortion(samples: list[float], params: dict) -> list[float]:
    drive = params.get("drive", 0.5)
    amount = 1.0 + drive * 10
    return [math.tanh(s * amount) / math.tanh(amount) for s in samples]


def _process_filter_lp(samples: list[float], params: dict) -> list[float]:
    cutoff = params.get("cutoff", 5000.0)
    rc = 1.0 / (2 * math.pi * cutoff)
    dt = 1.0 / SAMPLE_RATE
    alpha = dt / (rc + dt)
    result = [samples[0] if samples else 0.0]
    for i in range(1, len(samples)):
        result.append(result[-1] + alpha * (samples[i] - result[-1]))
    return result


def _process_filter_hp(samples: list[float], params: dict) -> list[float]:
    cutoff = params.get("cutoff", 100.0)
    rc = 1.0 / (2 * math.pi * cutoff)
    dt = 1.0 / SAMPLE_RATE
    alpha = rc / (rc + dt)
    result = [samples[0] if samples else 0.0]
    prev_in = samples[0] if samples else 0.0
    for i in range(1, len(samples)):
        result.append(alpha * (result[-1] + samples[i] - prev_in))
        prev_in = samples[i]
    return result


def _process_delay(samples: list[float], params: dict) -> list[float]:
    delay_ms = params.get("delay_ms", 250.0)
    feedback = params.get("feedback", 0.3)
    delay_samples = int(SAMPLE_RATE * delay_ms / 1000)
    result = list(samples)
    for i in range(delay_samples, len(result)):
        result[i] += result[i - delay_samples] * feedback
    peak = max(abs(s) for s in result) if result else 1.0
    if peak > 1.0:
        result = [s / peak for s in result]
    return result


def _process_reverb(samples: list[float], params: dict) -> list[float]:
    decay = params.get("decay", 0.5)
    result = list(samples)
    delays = [int(SAMPLE_RATE * d) for d in [0.029, 0.037, 0.044, 0.053]]
    for d in delays:
        for i in range(d, len(result)):
            result[i] += result[i - d] * decay * 0.25
    peak = max(abs(s) for s in result) if result else 1.0
    if peak > 1.0:
        result = [s / peak for s in result]
    return result


def _process_normalize(samples: list[float], params: dict) -> list[float]:
    target_db = params.get("target_db", -1.0)
    peak = max(abs(s) for s in samples) if samples else 1.0
    if peak == 0:
        return samples
    target = 10.0 ** (target_db / 20.0)
    gain = target / peak
    return [s * gain for s in samples]


def _process_phi_saturate(samples: list[float], params: dict) -> list[float]:
    return [math.tanh(s * PHI) / math.tanh(PHI) for s in samples]


PROCESSORS = {
    "gain": _process_gain,
    "distortion": _process_distortion,
    "lowpass": _process_filter_lp,
    "highpass": _process_filter_hp,
    "delay": _process_delay,
    "reverb": _process_reverb,
    "normalize": _process_normalize,
    "phi_saturate": _process_phi_saturate,
}


class SignalChain:
    """A signal processing chain."""

    def __init__(self, name: str = "chain"):
        self.name = name
        self.nodes: list[ChainNode] = []

    def add(self, name: str, process_type: str = "effect",
            params: dict | None = None, wet_dry: float = 1.0) -> ChainNode:
        """Add a node to the chain."""
        node = ChainNode(
            name=name,
            process_type=process_type,
            params=params or {},
            wet_dry=wet_dry,
        )
        self.nodes.append(node)
        return node

    def remove(self, name: str) -> bool:
        """Remove a node by name."""
        for i, node in enumerate(self.nodes):
            if node.name == name:
                self.nodes.pop(i)
                return True
        return False

    def move(self, name: str, new_index: int) -> bool:
        """Move a node to a new position."""
        for i, node in enumerate(self.nodes):
            if node.name == name:
                self.nodes.pop(i)
                self.nodes.insert(
                    min(new_index, len(self.nodes)),
                    node
                )
                return True
        return False

    def process(self, samples: list[float]) -> list[float]:
        """Process samples through the chain."""
        result = list(samples)

        for node in self.nodes:
            if not node.enabled:
                continue

            processor = PROCESSORS.get(node.name)
            if not processor:
                continue

            processed = processor(result, node.params)

            # Wet/dry mix
            if node.wet_dry < 1.0:
                mix: list[float] = []
                for i in range(len(result)):
                    dry = result[i] * (1 - node.wet_dry)
                    wet = (processed[i] if i < len(processed) else 0.0
                           ) * node.wet_dry
                    mix.append(dry + wet)
                result = mix
            else:
                result = processed

        return result

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "nodes": [n.to_dict() for n in self.nodes],
        }


class SignalChainBuilder:
    """Build and manage signal chains."""

    def __init__(self, output_dir: str = "output/chains"):
        self.output_dir = output_dir
        self.chains: dict[str, SignalChain] = {}
        os.makedirs(output_dir, exist_ok=True)

    def create_chain(self, name: str) -> SignalChain:
        """Create a new signal chain."""
        chain = SignalChain(name)
        self.chains[name] = chain
        return chain

    def serial(self, *processors: tuple[str, dict]) -> SignalChain:
        """Build a serial chain."""
        chain = self.create_chain("serial")
        for name, params in processors:
            chain.add(name, "effect", params)
        return chain

    def parallel(self, samples: list[float],
                 *chains: SignalChain,
                 mix: str = "average") -> list[float]:
        """Process through parallel chains and mix."""
        if not chains:
            return samples

        outputs: list[list[float]] = []
        for chain in chains:
            out = chain.process(list(samples))
            outputs.append(out)

        max_len = max(len(o) for o in outputs)
        result = [0.0] * max_len

        for output in outputs:
            for i in range(len(output)):
                result[i] += output[i]

        if mix == "average":
            n = len(outputs)
            result = [s / n for s in result]

        return result

    def process(self, chain_name: str,
                samples: list[float]) -> list[float]:
        """Process samples through a named chain."""
        chain = self.chains.get(chain_name)
        if not chain:
            return samples
        return chain.process(samples)

    def render(self, chain_name: str, samples: list[float],
               filename: str = "") -> str:
        """Process and render to WAV."""
        processed = self.process(chain_name, samples)
        if not filename:
            filename = f"{chain_name}_output.wav"

        path = os.path.join(self.output_dir, filename)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            data = struct.pack(
                f"<{len(processed)}h",
                *[max(-32768, min(32767, int(s * 32767)))
                  for s in processed]
            )
            wf.writeframes(data)
        return path

    def get_available_processors(self) -> list[str]:
        """List available processors."""
        return sorted(PROCESSORS.keys())

    def get_presets(self) -> dict[str, list[tuple[str, dict]]]:
        """Get chain presets."""
        return {
            "dubstep_master": [
                ("highpass", {"cutoff": 30}),
                ("distortion", {"drive": 0.3}),
                ("lowpass", {"cutoff": 16000}),
                ("normalize", {"target_db": -1.0}),
            ],
            "bass_chain": [
                ("highpass", {"cutoff": 20}),
                ("distortion", {"drive": 0.6}),
                ("lowpass", {"cutoff": 5000}),
                ("phi_saturate", {}),
                ("normalize", {"target_db": -3.0}),
            ],
            "atmosphere": [
                ("highpass", {"cutoff": 200}),
                ("reverb", {"decay": 0.7}),
                ("delay", {"delay_ms": 375, "feedback": 0.4}),
                ("lowpass", {"cutoff": 8000}),
                ("normalize", {"target_db": -6.0}),
            ],
        }

    def get_summary(self) -> dict:
        return {
            "chains": len(self.chains),
            "processors": self.get_available_processors(),
        }


def main() -> None:
    print("Signal Chain Builder")

    builder = SignalChainBuilder()

    # Generate test signal
    n = SAMPLE_RATE
    samples = [0.8 * math.sin(2 * math.pi * 432 * i / SAMPLE_RATE)
               for i in range(n)]

    # Build chain
    chain = builder.create_chain("dubstep")
    chain.add("highpass", "effect", {"cutoff": 30})
    chain.add("distortion", "effect", {"drive": 0.4})
    chain.add("phi_saturate", "effect", {})
    chain.add("normalize", "effect", {"target_db": -1.0})

    # Process
    processed = builder.process("dubstep", samples)
    print(f"  Input: {len(samples)} samples")
    print(f"  Output: {len(processed)} samples")

    peak_in = max(abs(s) for s in samples)
    peak_out = max(abs(s) for s in processed)
    print(f"  Peak in: {peak_in:.3f}")
    print(f"  Peak out: {peak_out:.3f}")

    # Render
    path = builder.render("dubstep", samples)
    print(f"  Rendered: {path}")

    print(f"\n  Processors: {builder.get_available_processors()}")
    print("Done.")


if __name__ == "__main__":
    main()
