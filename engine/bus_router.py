"""
DUBFORGE — Bus Router  (Session 218)

Audio bus routing system — submix buses, sends,
insert chains, routing matrix.
"""

import math
from dataclasses import dataclass, field

from engine.config_loader import PHI
SAMPLE_RATE = 48000


@dataclass
class BusChannel:
    """An audio channel routed to a bus."""
    name: str
    samples: list[float] = field(default_factory=list)
    gain: float = 1.0
    pan: float = 0.0  # -1 left, +1 right
    mute: bool = False
    solo: bool = False
    send_levels: dict[str, float] = field(default_factory=dict)


@dataclass
class Bus:
    """An audio bus (submix group)."""
    name: str
    gain: float = 1.0
    mute: bool = False
    channels: list[str] = field(default_factory=list)
    parent_bus: str | None = None

    # Accumulated audio
    buffer: list[float] = field(default_factory=list)


class BusRouter:
    """Route audio through bus system."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.channels: dict[str, BusChannel] = {}
        self.buses: dict[str, Bus] = {}

        # Always have a master bus
        self.buses["master"] = Bus(name="master", gain=1.0)

    def add_channel(self, name: str, samples: list[float],
                    gain: float = 1.0, bus: str = "master") -> BusChannel:
        """Add a channel."""
        ch = BusChannel(name=name, samples=list(samples), gain=gain)
        self.channels[name] = ch

        if bus not in self.buses:
            self.add_bus(bus)
        self.buses[bus].channels.append(name)

        return ch

    def add_bus(self, name: str, gain: float = 1.0,
                parent: str = "master") -> Bus:
        """Add a bus."""
        bus = Bus(name=name, gain=gain, parent_bus=parent)
        self.buses[name] = bus
        return bus

    def set_send(self, channel: str, bus: str, level: float) -> None:
        """Set send level from channel to bus."""
        if channel in self.channels:
            self.channels[channel].send_levels[bus] = level

    def _mix_to_bus(self, bus_name: str) -> list[float]:
        """Mix all channels routed to a bus."""
        bus = self.buses.get(bus_name)
        if not bus:
            return []

        # Check for solos
        has_solo = any(
            self.channels[ch].solo
            for ch in bus.channels
            if ch in self.channels
        )

        # Find max length
        max_len = 0
        for ch_name in bus.channels:
            ch = self.channels.get(ch_name)
            if ch and ch.samples:
                max_len = max(max_len, len(ch.samples))

        # Also include child buses
        for child_name, child_bus in self.buses.items():
            if child_bus.parent_bus == bus_name and child_name != bus_name:
                child_audio = self._mix_to_bus(child_name)
                max_len = max(max_len, len(child_audio))

        if max_len == 0:
            return []

        result = [0.0] * max_len

        # Mix channels
        for ch_name in bus.channels:
            ch = self.channels.get(ch_name)
            if not ch or ch.mute:
                continue
            if has_solo and not ch.solo:
                continue

            for i in range(min(len(ch.samples), max_len)):
                result[i] += ch.samples[i] * ch.gain

        # Mix child buses
        for child_name, child_bus in self.buses.items():
            if child_bus.parent_bus == bus_name and child_name != bus_name:
                if child_bus.mute:
                    continue
                child_audio = self._mix_to_bus(child_name)
                for i in range(min(len(child_audio), max_len)):
                    result[i] += child_audio[i] * child_bus.gain

        # Mix sends
        for ch_name, ch in self.channels.items():
            for send_bus, send_level in ch.send_levels.items():
                if send_bus == bus_name and ch_name not in bus.channels:
                    if ch.mute or (has_solo and not ch.solo):
                        continue
                    for i in range(min(len(ch.samples), max_len)):
                        result[i] += ch.samples[i] * ch.gain * send_level

        # Apply bus gain
        result = [s * bus.gain for s in result]
        bus.buffer = result

        return result

    def render(self) -> list[float]:
        """Render the master bus output."""
        return self._mix_to_bus("master")

    def render_stereo(self) -> tuple[list[float], list[float]]:
        """Render stereo output with pan."""
        master = self.buses.get("master")
        if not master:
            return [], []

        max_len = max(
            (len(self.channels[ch].samples)
             for ch in master.channels
             if ch in self.channels and self.channels[ch].samples),
            default=0,
        )

        left = [0.0] * max_len
        right = [0.0] * max_len

        for ch_name in master.channels:
            ch = self.channels.get(ch_name)
            if not ch or ch.mute:
                continue

            # Constant power pan
            angle = (ch.pan + 1) * math.pi / 4
            l_gain = math.cos(angle) * ch.gain
            r_gain = math.sin(angle) * ch.gain

            for i in range(min(len(ch.samples), max_len)):
                left[i] += ch.samples[i] * l_gain
                right[i] += ch.samples[i] * r_gain

        g = master.gain
        left = [s * g for s in left]
        right = [s * g for s in right]

        return left, right

    def get_bus_levels(self) -> dict[str, float]:
        """Get peak levels of all buses."""
        levels: dict[str, float] = {}
        for name, bus in self.buses.items():
            audio = self._mix_to_bus(name)
            pk = max(abs(s) for s in audio) if audio else 0.0
            levels[name] = round(
                20 * math.log10(pk) if pk > 0 else -120, 1
            )
        return levels

    def get_channel_levels(self) -> dict[str, float]:
        """Get peak levels of all channels."""
        levels: dict[str, float] = {}
        for name, ch in self.channels.items():
            pk = max(abs(s) for s in ch.samples) if ch.samples else 0.0
            levels[name] = round(
                20 * math.log10(pk * ch.gain) if pk * ch.gain > 0 else -120, 1
            )
        return levels

    def create_dubstep_template(self) -> None:
        """Create Subtronics-aligned dubstep bus layout (v7.0.0).

        Bus hierarchy:
            master
            ├── drums        (DRUMS, SC_TRIGGER)
            ├── bass         (MID_BASS, SUB, GROWL, WOBBLE, RIDDIM, FORMANT)
            ├── melodics     (LEAD, COUNTER, VOCAL, CHORDS, PAD, ARP)
            ├── fx           (IMPACTS, RISERS, TRANSITIONS, ATMOS)
            ├── reverb_send  (Return A — shared space)
            ├── delay_send   (Return B — tempo-synced)
            └── parallel_comp (Return C — heavy ratio, blended back)
        """
        self.add_bus("drums", gain=1.0)
        self.add_bus("bass", gain=0.9)
        self.add_bus("melodics", gain=0.7)
        self.add_bus("fx", gain=0.5)
        self.add_bus("reverb_send", gain=0.3)
        self.add_bus("delay_send", gain=0.3)
        self.add_bus("parallel_comp", gain=0.25)

    def get_routing_info(self) -> dict:
        """Get routing configuration."""
        return {
            "buses": {
                name: {
                    "gain": bus.gain,
                    "mute": bus.mute,
                    "parent": bus.parent_bus,
                    "channel_count": len(bus.channels),
                    "channels": bus.channels,
                }
                for name, bus in self.buses.items()
            },
            "channels": {
                name: {
                    "gain": ch.gain,
                    "pan": ch.pan,
                    "mute": ch.mute,
                    "solo": ch.solo,
                    "sends": ch.send_levels,
                }
                for name, ch in self.channels.items()
            },
        }


def main() -> None:
    print("Bus Router")
    router = BusRouter()

    # Create dubstep layout
    router.create_dubstep_template()

    # Add channels
    n = SAMPLE_RATE
    kick = [0.9 * math.sin(2 * math.pi * 60 * i / SAMPLE_RATE) *
            max(0, 1 - i / (SAMPLE_RATE * 0.3))
            for i in range(n)]
    sub = [0.8 * math.sin(2 * math.pi * 40 * i / SAMPLE_RATE)
           for i in range(n)]
    lead = [0.5 * math.sin(2 * math.pi * 880 * i / SAMPLE_RATE)
            for i in range(n)]

    router.add_channel("kick", kick, gain=0.9, bus="drums")
    router.add_channel("sub", sub, gain=0.85, bus="bass")
    router.add_channel("lead", lead, gain=0.6, bus="synths")

    # Set reverb send
    router.set_send("lead", "reverb_send", 0.3)

    # Render
    output = router.render()
    print(f"  Output: {len(output) / SAMPLE_RATE:.2f}s")

    # Levels
    levels = router.get_bus_levels()
    for bus, level in levels.items():
        if level > -120:
            print(f"  {bus}: {level:.1f} dB")

    # Routing info
    info = router.get_routing_info()
    print(f"  Buses: {len(info['buses'])}")
    print(f"  Channels: {len(info['channels'])}")

    print("Done.")


if __name__ == "__main__":
    main()
