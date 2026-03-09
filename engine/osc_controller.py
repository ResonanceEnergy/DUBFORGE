"""
DUBFORGE — OSC Controller Engine  (Session 169)

Open Sound Control message building and routing for
DAW communication. Generates OSC-compatible byte messages.
"""

import struct
import time
from dataclasses import dataclass, field

PHI = 1.6180339887


@dataclass
class OSCMessage:
    """An OSC message."""
    address: str
    args: list = field(default_factory=list)
    timestamp: float = 0.0

    def to_bytes(self) -> bytes:
        """Encode as OSC binary format."""
        # Address
        addr = self.address.encode("ascii") + b"\x00"
        while len(addr) % 4 != 0:
            addr += b"\x00"

        # Type tag
        type_chars = ","
        arg_data = b""
        for arg in self.args:
            if isinstance(arg, int):
                type_chars += "i"
                arg_data += struct.pack(">i", arg)
            elif isinstance(arg, float):
                type_chars += "f"
                arg_data += struct.pack(">f", arg)
            elif isinstance(arg, str):
                type_chars += "s"
                s = arg.encode("ascii") + b"\x00"
                while len(s) % 4 != 0:
                    s += b"\x00"
                arg_data += s
            elif isinstance(arg, bool):
                type_chars += "T" if arg else "F"

        tag = type_chars.encode("ascii") + b"\x00"
        while len(tag) % 4 != 0:
            tag += b"\x00"

        return addr + tag + arg_data

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "args": self.args,
            "timestamp": self.timestamp,
        }


@dataclass
class OSCBundle:
    """An OSC bundle of messages."""
    timetag: float = 0.0
    messages: list[OSCMessage] = field(default_factory=list)

    def to_bytes(self) -> bytes:
        header = b"#bundle\x00"
        # Timetag (NTP format, simplified)
        tt = struct.pack(">Q", int(self.timetag * 1000000))
        data = header + tt
        for msg in self.messages:
            msg_bytes = msg.to_bytes()
            data += struct.pack(">i", len(msg_bytes))
            data += msg_bytes
        return data


# Standard OSC addresses for DAW control
class OSCAddresses:
    # Transport
    PLAY = "/transport/play"
    STOP = "/transport/stop"
    RECORD = "/transport/record"
    BPM = "/transport/bpm"
    POSITION = "/transport/position"

    # Mixer
    TRACK_VOLUME = "/mixer/track/{}/volume"
    TRACK_PAN = "/mixer/track/{}/pan"
    TRACK_MUTE = "/mixer/track/{}/mute"
    TRACK_SOLO = "/mixer/track/{}/solo"
    MASTER_VOLUME = "/mixer/master/volume"

    # Parameters
    PARAM = "/param/{}/{}"  # device/parameter
    MACRO = "/macro/{}"

    # DUBFORGE custom
    MODULE_TRIGGER = "/dubforge/module/{}"
    PHI_SYNC = "/dubforge/phi/sync"
    SUBPHONICS_CMD = "/dubforge/subphonics/command"


class OSCController:
    """OSC message router and builder."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9000):
        self.host = host
        self.port = port
        self._message_log: list[OSCMessage] = []
        self._max_log = 100
        self._routes: dict[str, list[callable]] = {}

    def send(self, address: str, *args) -> OSCMessage:
        """Create and log an OSC message."""
        msg = OSCMessage(
            address=address,
            args=list(args),
            timestamp=time.time(),
        )
        self._message_log.append(msg)
        if len(self._message_log) > self._max_log:
            self._message_log = self._message_log[-self._max_log:]

        # Route to handlers
        if address in self._routes:
            for handler in self._routes[address]:
                handler(msg)

        return msg

    def on(self, address: str, handler: callable) -> None:
        """Register a handler for an OSC address."""
        if address not in self._routes:
            self._routes[address] = []
        self._routes[address].append(handler)

    # Transport helpers
    def play(self) -> OSCMessage:
        return self.send(OSCAddresses.PLAY, 1)

    def stop(self) -> OSCMessage:
        return self.send(OSCAddresses.STOP, 1)

    def record(self) -> OSCMessage:
        return self.send(OSCAddresses.RECORD, 1)

    def set_bpm(self, bpm: float) -> OSCMessage:
        return self.send(OSCAddresses.BPM, bpm)

    # Mixer helpers
    def set_track_volume(self, track: int, volume: float) -> OSCMessage:
        return self.send(
            OSCAddresses.TRACK_VOLUME.format(track), volume,
        )

    def set_track_pan(self, track: int, pan: float) -> OSCMessage:
        return self.send(
            OSCAddresses.TRACK_PAN.format(track), pan,
        )

    def mute_track(self, track: int, mute: bool = True) -> OSCMessage:
        return self.send(
            OSCAddresses.TRACK_MUTE.format(track), int(mute),
        )

    def solo_track(self, track: int, solo: bool = True) -> OSCMessage:
        return self.send(
            OSCAddresses.TRACK_SOLO.format(track), int(solo),
        )

    # DUBFORGE helpers
    def trigger_module(self, module: str) -> OSCMessage:
        return self.send(
            OSCAddresses.MODULE_TRIGGER.format(module), 1,
        )

    def phi_sync(self) -> OSCMessage:
        return self.send(OSCAddresses.PHI_SYNC, PHI)

    def subphonics_command(self, command: str) -> OSCMessage:
        return self.send(OSCAddresses.SUBPHONICS_CMD, command)

    # Status
    def message_log(self, n: int = 10) -> list[dict]:
        return [m.to_dict() for m in self._message_log[-n:]]

    def status(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "messages_sent": len(self._message_log),
            "routes": len(self._routes),
            "recent": self.message_log(5),
        }

    def status_text(self) -> str:
        s = self.status()
        lines = [
            f"**OSC Controller** — {s['host']}:{s['port']}",
            f"Messages sent: {s['messages_sent']} | "
            f"Routes: {s['routes']}",
        ]
        if s["recent"]:
            lines.append("\n**Recent:**")
            for m in s["recent"]:
                args_str = ", ".join(str(a) for a in m["args"])
                lines.append(f"  → {m['address']} ({args_str})")
        return "\n".join(lines)


# Module singleton
_controller: OSCController | None = None


def get_controller() -> OSCController:
    global _controller
    if _controller is None:
        _controller = OSCController()
    return _controller


def main() -> None:
    print("OSC Controller Engine")
    ctrl = OSCController("127.0.0.1", 9000)

    # Test messages
    ctrl.play()
    ctrl.set_bpm(140.0)
    ctrl.set_track_volume(1, 0.8)
    ctrl.set_track_pan(1, -0.3)
    ctrl.trigger_module("sub_bass")
    ctrl.phi_sync()
    ctrl.subphonics_command("render wobble bass")

    print(ctrl.status_text())

    # Test binary encoding
    msg = ctrl.send("/test", 42, 3.14, "hello")
    data = msg.to_bytes()
    print(f"  Binary message: {len(data)} bytes")
    print("Done.")


if __name__ == "__main__":
    main()
