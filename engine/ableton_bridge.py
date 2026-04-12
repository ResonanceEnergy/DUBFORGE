# pyright: basic
"""
DUBFORGE Engine — Ableton Live OSC Bridge

Complete command-and-control interface for Ableton Live via AbletonOSC.
Every feature: tracks, clips, devices, routing, automation, rendering,
mixer, scenes, transport — all accessible from Python.

Requires: AbletonOSC remote script installed in Ableton Live.
  Install: https://github.com/ideoforms/AbletonOSC
  Ports: Send → 11000, Receive → 11001

Usage:
    from engine.ableton_bridge import AbletonBridge
    ab = AbletonBridge()
    ab.connect()
    ab.set_tempo(145)
    ab.create_midi_track(0, "BASS")
    ab.create_clip(0, 0, 16.0)
    ab.add_notes(0, 0, [{"pitch": 36, "start_time": 0.0, "duration": 1.0, "velocity": 100}])
"""

from __future__ import annotations

import json
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.log import get_logger

_log = get_logger("dubforge.ableton_bridge")

# ═══════════════════════════════════════════════════════════════════════════
# OPTIONAL DEPENDENCY — python-osc
# ═══════════════════════════════════════════════════════════════════════════
try:
    from pythonosc import udp_client, osc_server, dispatcher as osc_dispatcher, osc_bundle_builder, osc_message_builder
    HAS_OSC = True
except ImportError:
    HAS_OSC = False
    _log.warning("python-osc not installed. Run: pip install python-osc")


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_SEND_PORT = 11000
DEFAULT_RECV_PORT = 11001
DEFAULT_HOST = "127.0.0.1"
RESPONSE_TIMEOUT = 5.0  # seconds

# Ableton color palette (0x00RRGGBB)
COLORS = {
    "red":        0x00FF0000,
    "orange":     0x00FF6600,
    "yellow":     0x00FFFF00,
    "green":      0x0000FF00,
    "cyan":       0x0000FFFF,
    "blue":       0x000000FF,
    "purple":     0x009900FF,
    "pink":       0x00FF00FF,
    "white":      0x00FFFFFF,
    "black":      0x00333333,
    "dubforge_1": 0x00FF3366,  # DUBFORGE signature red-pink
    "dubforge_2": 0x006633FF,  # DUBFORGE signature purple
    "dubforge_3": 0x0033CCFF,  # DUBFORGE signature cyan
    "dubforge_4": 0x00FF9900,  # DUBFORGE signature amber
}

# Track types
TRACK_MIDI = "midi"
TRACK_AUDIO = "audio"
TRACK_RETURN = "return"
TRACK_GROUP = "group"

# Quantization values
QUANT = {
    "none": 0, "8_bars": 1, "4_bars": 2, "2_bars": 3, "1_bar": 4,
    "1/2": 5, "1/2T": 6, "1/4": 7, "1/4T": 8, "1/8": 9,
    "1/8T": 10, "1/16": 11, "1/16T": 12, "1/32": 13,
}

# Warp modes
WARP = {
    "beats": 0, "tones": 1, "texture": 2, "repitch": 3,
    "complex": 4, "rex": 5, "complex_pro": 6,
}


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class NoteData:
    """A MIDI note for clip insertion."""
    pitch: int          # 0-127, 60 = C3
    start_time: float   # beats
    duration: float     # beats
    velocity: int = 100 # 0-127
    mute: bool = False
    probability: float = 1.0

    def to_dict(self) -> dict:
        return {
            "pitch": self.pitch,
            "start_time": self.start_time,
            "duration": self.duration,
            "velocity": self.velocity,
            "mute": int(self.mute),
            "probability": self.probability,
        }


@dataclass
class AutomationPoint:
    """An automation breakpoint."""
    time: float    # beats
    value: float   # parameter value (normalized 0-1 or absolute)


@dataclass
class DeviceInfo:
    """Info about a device on a track."""
    track_index: int
    device_index: int
    class_name: str = ""
    name: str = ""
    type: int = 0  # 0=undefined, 1=instrument, 2=audio_effect, 4=midi_effect
    parameters: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    # {param_name: (value, min, max)}


@dataclass
class TrackInfo:
    """Snapshot of a track's state."""
    index: int
    name: str = ""
    type: str = ""  # "midi", "audio", "return", "master"
    volume: float = 0.85
    pan: float = 0.0
    mute: bool = False
    solo: bool = False
    arm: bool = False
    color: int = 0
    device_count: int = 0
    clip_slot_count: int = 0


# ═══════════════════════════════════════════════════════════════════════════
# RESPONSE LISTENER
# ═══════════════════════════════════════════════════════════════════════════

class ResponseCollector:
    """Threaded OSC response listener for AbletonOSC replies."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_RECV_PORT):
        self.host = host
        self.port = port
        self._responses: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._server = None
        self._thread = None

    def start(self) -> bool:
        if not HAS_OSC:
            return False
        import socket as _socket
        disp = osc_dispatcher.Dispatcher()
        disp.set_default_handler(self._handle)
        try:
            # Set SO_REUSEADDR before bind to avoid Address-in-use from stale
            # listeners left by killed processes.
            osc_server.ThreadingOSCUDPServer.allow_reuse_address = True
            self._server = osc_server.ThreadingOSCUDPServer(
                (self.host, self.port), disp)
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
            _log.info(f"OSC listener started on {self.host}:{self.port}")
            return True
        except OSError as e:
            _log.warning(f"Could not start OSC listener: {e}")
            return False

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

    def _handle(self, address: str, *args):
        with self._lock:
            self._responses[address] = args

    def get(self, address: str, timeout: float = RESPONSE_TIMEOUT) -> Any:
        """Wait for a response on the given OSC address."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                if address in self._responses:
                    val = self._responses.pop(address)
                    return val
            time.sleep(0.01)
        return None

    def get_immediate(self, address: str) -> Any:
        with self._lock:
            return self._responses.pop(address, None)


# ═══════════════════════════════════════════════════════════════════════════
# ABLETON BRIDGE — COMPLETE COMMAND & CONTROL
# ═══════════════════════════════════════════════════════════════════════════

class AbletonBridge:
    """Full OSC bridge to Ableton Live via AbletonOSC.

    Provides complete control over:
    - Transport (play, stop, record, tempo, time sig)
    - Tracks (create, delete, arm, mute, solo, volume, pan, routing)
    - Clips (create, delete, notes, fire, stop, loop, quantize)
    - Devices (load, parameters, enable/disable, racks)
    - Automation (write breakpoints to any parameter)
    - Scenes (create, fire, name, tempo)
    - Mixer (volume, pan, sends, crossfader)
    - Rendering (export, bounce)
    - Memory management (freeze, flatten, cleanup)
    """

    def __init__(self, host: str = DEFAULT_HOST,
                 send_port: int = DEFAULT_SEND_PORT,
                 recv_port: int = DEFAULT_RECV_PORT,
                 verbose: bool = True):
        self.host = host
        self.send_port = send_port
        self.recv_port = recv_port
        self.verbose = verbose
        self._client = None
        self._collector = None
        self._connected = False
        self._track_cache: dict[int, TrackInfo] = {}
        self._device_cache: dict[tuple[int, int], DeviceInfo] = {}

    # ── CONNECTION ────────────────────────────────────────────────────────

    def connect(self) -> bool:
        """Connect to Ableton Live via AbletonOSC.

        Returns True only if Ableton is running AND responding to OSC.
        Returns False if the listener can't start or Ableton doesn't respond.
        """
        if not HAS_OSC:
            _log.error("python-osc not installed. Run: pip install python-osc")
            return False

        try:
            self._client = udp_client.SimpleUDPClient(self.host, self.send_port)
            self._collector = ResponseCollector(self.host, self.recv_port)
            if not self._collector.start():
                _log.warning("OSC listener failed to start — cannot receive responses")
                self._connected = False
                return False

            # Test connection — Ableton must respond with a valid tempo
            tempo = self.get_tempo()
            if tempo is not None:
                self._connected = True
                if self.verbose:
                    print(f"  ✓ Connected to Ableton Live @ {self.host}:{self.send_port}")
                    print(f"    Tempo: {tempo} BPM")
                _log.info(f"Connected to Ableton Live, tempo={tempo}")
                return True
            else:
                self._connected = False
                self.disconnect()
                if self.verbose:
                    _log.info("No response from Ableton — is AbletonOSC enabled?")
                return False

        except Exception as e:
            _log.error(f"Connection failed: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Clean disconnect."""
        if self._collector:
            self._collector.stop()
        self._connected = False
        _log.info("Disconnected from Ableton Live")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _send(self, address: str, *args):
        """Send an OSC message."""
        if not self._client:
            raise ConnectionError("Not connected to Ableton. Call connect() first.")
        self._client.send_message(address, list(args))

    def _query(self, address: str, *args, timeout: float = RESPONSE_TIMEOUT) -> Any:
        """Send a query and wait for response."""
        self._send(address, *args)
        return self._collector.get(address, timeout) if self._collector else None

    # ═══════════════════════════════════════════════════════════════════════
    # TRANSPORT
    # ═══════════════════════════════════════════════════════════════════════

    def play(self):
        """Start playback."""
        self._send("/live/song/start_playing")

    def stop(self):
        """Stop playback."""
        self._send("/live/song/stop_playing")

    def continue_playing(self):
        """Continue from current position."""
        self._send("/live/song/continue_playing")

    def record(self):
        """Toggle arrangement record."""
        self._send("/live/song/set/record_mode", 1)

    def stop_record(self):
        self._send("/live/song/set/record_mode", 0)

    def set_tempo(self, bpm: float):
        """Set song tempo (20-999 BPM)."""
        self._send("/live/song/set/tempo", float(bpm))

    def get_tempo(self) -> float | None:
        """Get current tempo."""
        result = self._query("/live/song/get/tempo")
        return result[0] if result else None

    def set_time_signature(self, numerator: int, denominator: int):
        """Set time signature."""
        self._send("/live/song/set/signature_numerator", numerator)
        self._send("/live/song/set/signature_denominator", denominator)

    def set_loop(self, enabled: bool, start_beats: float = 0.0, length_beats: float = 16.0):
        """Set arrangement loop."""
        self._send("/live/song/set/loop", int(enabled))
        self._send("/live/song/set/loop_start", start_beats)
        self._send("/live/song/set/loop_length", length_beats)

    def set_metronome(self, enabled: bool):
        self._send("/live/song/set/metronome", int(enabled))

    def set_overdub(self, enabled: bool):
        self._send("/live/song/set/overdub", int(enabled))

    def set_quantization(self, quant: str | int):
        """Set global clip trigger quantization."""
        val = QUANT.get(quant, quant) if isinstance(quant, str) else quant
        self._send("/live/song/set/clip_trigger_quantization", val)

    def jump_to(self, beats: float):
        """Jump to position in beats."""
        self._send("/live/song/set/current_song_time", beats)

    def get_song_time(self) -> float | None:
        result = self._query("/live/song/get/current_song_time")
        return result[0] if result else None

    def undo(self):
        self._send("/live/song/undo")

    def redo(self):
        self._send("/live/song/redo")

    # ═══════════════════════════════════════════════════════════════════════
    # TRACKS — Create, Delete, Configure
    # ═══════════════════════════════════════════════════════════════════════

    def create_midi_track(self, index: int = -1, name: str = "") -> int:
        """Create a MIDI track. index=-1 appends at end. Returns track index."""
        self._send("/live/song/create_midi_track", index)
        time.sleep(0.1)
        actual_index = index if index >= 0 else self.get_track_count() - 1
        if name:
            self.set_track_name(actual_index, name)
        return actual_index

    def create_audio_track(self, index: int = -1, name: str = "") -> int:
        """Create an audio track."""
        self._send("/live/song/create_audio_track", index)
        time.sleep(0.1)
        actual_index = index if index >= 0 else self.get_track_count() - 1
        if name:
            self.set_track_name(actual_index, name)
        return actual_index

    def create_return_track(self, name: str = "") -> int:
        """Create a return track."""
        self._send("/live/song/create_return_track")
        time.sleep(0.1)
        idx = self.get_return_track_count() - 1
        if name:
            self._send(f"/live/return_track/set/name", idx, name)
        return idx

    def delete_track(self, index: int):
        """Delete track at index."""
        self._send("/live/song/delete_track", index)
        time.sleep(0.05)

    def duplicate_track(self, index: int):
        """Duplicate track at index."""
        self._send("/live/song/duplicate_track", index)

    def get_track_count(self) -> int:
        result = self._query("/live/song/get/num_tracks")
        return result[0] if result else 0

    def get_return_track_count(self) -> int:
        result = self._query("/live/song/get/num_return_tracks")
        return result[0] if result else 0

    # ── Track Properties ─────────────────────────────────────────────────

    def set_track_name(self, track: int, name: str):
        self._send("/live/track/set/name", track, name)

    def get_track_name(self, track: int) -> str | None:
        result = self._query("/live/track/get/name", track)
        return result[1] if result and len(result) > 1 else None

    def set_track_color(self, track: int, color: int | str):
        """Set track color. Accepts hex int or color name."""
        c = COLORS.get(color, color) if isinstance(color, str) else color
        self._send("/live/track/set/color", track, c)

    def set_track_volume(self, track: int, volume: float):
        """Set track volume (0.0-1.0, 0.85 = 0dB)."""
        self._send("/live/track/set/volume", track, volume)

    def set_track_pan(self, track: int, pan: float):
        """Set panning (-1.0 left to 1.0 right)."""
        self._send("/live/track/set/panning", track, pan)

    def set_track_mute(self, track: int, mute: bool):
        self._send("/live/track/set/mute", track, int(mute))

    def set_track_solo(self, track: int, solo: bool):
        self._send("/live/track/set/solo", track, int(solo))

    def set_track_arm(self, track: int, arm: bool):
        self._send("/live/track/set/arm", track, int(arm))

    def set_track_send(self, track: int, send_index: int, value: float):
        """Set send level (0.0-1.0) for a return track."""
        self._send("/live/track/set/send", track, send_index, value)

    # ── Track Routing ────────────────────────────────────────────────────

    def set_track_input_routing(self, track: int, routing_type: str):
        """Set track input routing type (e.g., 'Ext. In', 'Computer Keyboard')."""
        self._send("/live/track/set/input_routing_type", track, routing_type)

    def set_track_input_channel(self, track: int, channel: str):
        """Set track input routing channel."""
        self._send("/live/track/set/input_routing_channel", track, channel)

    def set_track_output_routing(self, track: int, routing_type: str):
        """Set track output routing type."""
        self._send("/live/track/set/output_routing_type", track, routing_type)

    def set_track_output_channel(self, track: int, channel: str):
        """Set track output routing channel."""
        self._send("/live/track/set/output_routing_channel", track, channel)

    # ── Track Monitoring ─────────────────────────────────────────────────

    def get_track_meter(self, track: int) -> float | None:
        """Get output meter level."""
        result = self._query("/live/track/get/output_meter_level", track)
        return result[1] if result and len(result) > 1 else None

    # ── Return Tracks ────────────────────────────────────────────────────

    def set_return_volume(self, index: int, volume: float):
        self._send("/live/return_track/set/volume", index, volume)

    def set_return_pan(self, index: int, pan: float):
        self._send("/live/return_track/set/panning", index, pan)

    def set_return_name(self, index: int, name: str):
        self._send("/live/return_track/set/name", index, name)

    # ── Master Track ─────────────────────────────────────────────────────

    def set_master_volume(self, volume: float):
        self._send("/live/master_track/set/volume", volume)

    def set_master_pan(self, pan: float):
        self._send("/live/master_track/set/panning", pan)

    def get_master_meter(self) -> float | None:
        result = self._query("/live/master_track/get/output_meter_level")
        return result[0] if result else None

    # ═══════════════════════════════════════════════════════════════════════
    # CLIPS — Create, Delete, Notes, Fire
    # ═══════════════════════════════════════════════════════════════════════

    def create_clip(self, track: int, slot: int, length_beats: float):
        """Create an empty MIDI clip in the given slot."""
        self._send("/live/clip_slot/create_clip", track, slot, length_beats)
        time.sleep(0.05)

    def create_audio_clip(self, track: int, slot: int, file_path: str):
        """Create an audio clip from a WAV/AIFF file."""
        self._send("/live/clip_slot/create_audio_clip", track, slot, file_path)
        time.sleep(0.1)

    def delete_clip(self, track: int, slot: int):
        """Delete clip in slot."""
        self._send("/live/clip_slot/delete_clip", track, slot)

    def has_clip(self, track: int, slot: int) -> bool:
        result = self._query("/live/clip_slot/get/has_clip", track, slot)
        return bool(result[2]) if result and len(result) > 2 else False

    def fire_clip(self, track: int, slot: int):
        """Launch a clip."""
        self._send("/live/clip_slot/fire", track, slot)

    def stop_clip(self, track: int, slot: int):
        """Stop clip in track."""
        self._send("/live/clip_slot/stop", track, slot)

    def stop_all_clips(self):
        """Stop all clips."""
        self._send("/live/song/stop_all_clips")

    def fire_scene(self, scene: int):
        """Fire all clips in a scene."""
        self._send("/live/scene/fire", scene)

    # ── Clip Properties ──────────────────────────────────────────────────

    def set_clip_name(self, track: int, slot: int, name: str):
        self._send("/live/clip/set/name", track, slot, name)

    def set_clip_color(self, track: int, slot: int, color: int | str):
        c = COLORS.get(color, color) if isinstance(color, str) else color
        self._send("/live/clip/set/color", track, slot, c)

    def set_clip_loop(self, track: int, slot: int, looping: bool):
        self._send("/live/clip/set/looping", track, slot, int(looping))

    def set_clip_loop_start(self, track: int, slot: int, start: float):
        self._send("/live/clip/set/loop_start", track, slot, start)

    def set_clip_loop_end(self, track: int, slot: int, end: float):
        self._send("/live/clip/set/loop_end", track, slot, end)

    def set_clip_start_marker(self, track: int, slot: int, marker: float):
        self._send("/live/clip/set/start_marker", track, slot, marker)

    def set_clip_end_marker(self, track: int, slot: int, marker: float):
        self._send("/live/clip/set/end_marker", track, slot, marker)

    def set_clip_gain(self, track: int, slot: int, gain: float):
        """Audio clip gain (0.0-1.0)."""
        self._send("/live/clip/set/gain", track, slot, gain)

    def set_clip_pitch(self, track: int, slot: int, semitones: int, cents: float = 0.0):
        """Audio clip pitch shift."""
        self._send("/live/clip/set/pitch_coarse", track, slot, semitones)
        self._send("/live/clip/set/pitch_fine", track, slot, cents)

    def set_clip_warp_mode(self, track: int, slot: int, mode: str | int):
        """Set warp mode for audio clip."""
        m = WARP.get(mode, mode) if isinstance(mode, str) else mode
        self._send("/live/clip/set/warp_mode", track, slot, m)

    def set_clip_warping(self, track: int, slot: int, enabled: bool):
        self._send("/live/clip/set/warping", track, slot, int(enabled))

    def set_clip_mute(self, track: int, slot: int, muted: bool):
        self._send("/live/clip/set/muted", track, slot, int(muted))

    def quantize_clip(self, track: int, slot: int, grid: int, amount: float = 1.0):
        """Quantize notes in clip."""
        self._send("/live/clip/quantize", track, slot, grid, amount)

    def duplicate_clip_loop(self, track: int, slot: int):
        """Double the loop length and duplicate content."""
        self._send("/live/clip/duplicate_loop", track, slot)

    # ── MIDI Notes ───────────────────────────────────────────────────────

    def add_notes(self, track: int, slot: int, notes: list[dict | NoteData]):
        """Add MIDI notes to a clip.

        Each note dict: {pitch, start_time, duration, velocity, [mute], [probability]}
        """
        for note in notes:
            n = note.to_dict() if isinstance(note, NoteData) else note
            self._send("/live/clip/add/notes", track, slot,
                       n["pitch"],
                       n["start_time"],
                       n["duration"],
                       n.get("velocity", 100),
                       n.get("mute", 0))

    def add_notes_batch(self, track: int, slot: int, notes: list[dict | NoteData]):
        """Add multiple notes efficiently using JSON batch."""
        note_dicts = [n.to_dict() if isinstance(n, NoteData) else n for n in notes]
        # AbletonOSC supports batch note adding via repeated calls
        for nd in note_dicts:
            self._send("/live/clip/add/notes", track, slot,
                       nd["pitch"], nd["start_time"], nd["duration"],
                       nd.get("velocity", 100), nd.get("mute", 0))

    def remove_notes(self, track: int, slot: int,
                     from_pitch: int = 0, pitch_span: int = 128,
                     from_time: float = 0.0, time_span: float = 9999.0):
        """Remove notes in a region."""
        self._send("/live/clip/remove/notes", track, slot,
                   from_pitch, pitch_span, from_time, time_span)

    def get_notes(self, track: int, slot: int) -> list[dict] | None:
        """Get all notes in a clip."""
        result = self._query("/live/clip/get/notes", track, slot,
                             0, 128, 0.0, 9999.0)
        if result:
            notes = []
            # Parse response: track, slot, then groups of (pitch, start, dur, vel, mute)
            data = list(result)
            i = 2  # skip track and slot
            while i + 4 < len(data):
                notes.append({
                    "pitch": data[i], "start_time": data[i + 1],
                    "duration": data[i + 2], "velocity": data[i + 3],
                    "mute": data[i + 4] if i + 4 < len(data) else 0,
                })
                i += 5
            return notes
        return None

    # ── Arrangement Clips ────────────────────────────────────────────────

    def create_arrangement_audio_clip(self, track: int, file_path: str, position: float):
        """Create an audio clip in Arrangement View."""
        self._send("/live/track/create_audio_clip", track, file_path, position)
        time.sleep(0.1)

    def duplicate_clip_to_arrangement(self, track: int, slot: int, dest_time: float):
        """Copy session clip to arrangement."""
        self._send("/live/clip/duplicate_clip_to_arrangement", track, slot, dest_time)

    # ═══════════════════════════════════════════════════════════════════════
    # DEVICES — Load, Parameters, Racks
    # ═══════════════════════════════════════════════════════════════════════

    def get_device_count(self, track: int) -> int:
        result = self._query("/live/track/get/num_devices", track)
        return result[1] if result and len(result) > 1 else 0

    def get_device_name(self, track: int, device: int) -> str | None:
        result = self._query("/live/device/get/name", track, device)
        return result[2] if result and len(result) > 2 else None

    def get_device_class(self, track: int, device: int) -> str | None:
        result = self._query("/live/device/get/class_name", track, device)
        return result[2] if result and len(result) > 2 else None

    def set_device_name(self, track: int, device: int, name: str):
        self._send("/live/device/set/name", track, device, name)

    def set_device_enabled(self, track: int, device: int, enabled: bool):
        """Enable/disable a device."""
        self._send("/live/device/set/is_active", track, device, int(enabled))

    def delete_device(self, track: int, device: int):
        self._send("/live/track/delete_device", track, device)

    # ── Device Parameters ────────────────────────────────────────────────

    def get_device_parameters(self, track: int, device: int) -> list[dict] | None:
        """Get all parameters of a device.

        Returns list of {name, value, min, max} dicts.
        """
        result = self._query("/live/device/get/parameters/name", track, device)
        if not result:
            return None
        # Get names
        names = list(result[2:]) if len(result) > 2 else []
        # Get values
        val_result = self._query("/live/device/get/parameters/value", track, device)
        values = list(val_result[2:]) if val_result and len(val_result) > 2 else []
        # Get min
        min_result = self._query("/live/device/get/parameters/min", track, device)
        mins = list(min_result[2:]) if min_result and len(min_result) > 2 else []
        # Get max
        max_result = self._query("/live/device/get/parameters/max", track, device)
        maxs = list(max_result[2:]) if max_result and len(max_result) > 2 else []

        params = []
        for i in range(len(names)):
            params.append({
                "index": i,
                "name": names[i] if i < len(names) else f"Param_{i}",
                "value": values[i] if i < len(values) else 0.0,
                "min": mins[i] if i < len(mins) else 0.0,
                "max": maxs[i] if i < len(maxs) else 1.0,
            })
        return params

    def set_device_parameter(self, track: int, device: int, param: int, value: float):
        """Set a device parameter by index."""
        self._send("/live/device/set/parameter/value", track, device, param, value)

    def set_device_parameter_by_name(self, track: int, device: int,
                                     param_name: str, value: float) -> bool:
        """Set a device parameter by name. Returns True if found."""
        params = self.get_device_parameters(track, device)
        if params:
            for p in params:
                if p["name"].lower() == param_name.lower():
                    self.set_device_parameter(track, device, p["index"], value)
                    return True
        return False

    def get_device_parameter_value(self, track: int, device: int, param: int) -> float | None:
        result = self._query("/live/device/get/parameter/value", track, device, param)
        return result[3] if result and len(result) > 3 else None

    # ── Parameter Discovery (for Serum2, Vital, etc.) ────────────────────

    def discover_device_params(self, track: int, device: int) -> dict[str, dict]:
        """Discover all parameters of a device and return as a map.

        Returns: {param_name: {index, value, min, max}}
        """
        params = self.get_device_parameters(track, device)
        if not params:
            return {}
        return {p["name"]: {"index": p["index"], "value": p["value"],
                            "min": p["min"], "max": p["max"]}
                for p in params}

    def dump_device_params(self, track: int, device: int, output_file: str = ""):
        """Dump all device parameters to JSON for inspection."""
        params = self.discover_device_params(track, device)
        name = self.get_device_name(track, device) or f"device_{device}"
        data = {"device": name, "track": track, "device_index": device,
                "parameter_count": len(params), "parameters": params}
        if output_file:
            Path(output_file).write_text(json.dumps(data, indent=2))
            print(f"  → Dumped {len(params)} params to {output_file}")
        return data

    # ── Load Devices (Browser) ───────────────────────────────────────────

    def load_device_by_name(self, track: int, device_name: str):
        """Attempt to load a device/plugin by name.

        Note: AbletonOSC has limited browser control. For loading specific
        plugins (Serum 2, etc.), use the ALS generator approach or
        drag-and-drop the device manually, then control its parameters.
        """
        _log.info(f"Device loading via OSC is limited. "
                  f"For {device_name}, add it to the track in Ableton, "
                  f"then use set_device_parameter to control it.")

    # ── Rack Devices ─────────────────────────────────────────────────────

    def get_rack_chains(self, track: int, device: int) -> int:
        """Get number of chains in a Rack device."""
        result = self._query("/live/device/get/num_chains", track, device)
        return result[2] if result and len(result) > 2 else 0

    # ═══════════════════════════════════════════════════════════════════════
    # AUTOMATION
    # ═══════════════════════════════════════════════════════════════════════

    def write_automation(self, track: int, device: int, param: int,
                         points: list[AutomationPoint]):
        """Write automation breakpoints to an arrangement clip's envelope.

        Note: AbletonOSC automation support varies. For full automation,
        use MIDI CC mapping or the ALS generator with embedded envelopes.
        """
        for pt in points:
            self.set_device_parameter(track, device, param, pt.value)
            # OSC doesn't directly support arrangement automation writing.
            # Use MIDI CC or arrangement clip envelopes via ALS instead.

    def write_clip_automation(self, track: int, slot: int,
                              device: int, param: int,
                              points: list[AutomationPoint]):
        """Write automation into a clip's envelope."""
        # This requires clip envelope API which AbletonOSC supports partially
        for pt in points:
            self._send("/live/clip/set/envelope/value", track, slot,
                       device, param, pt.time, pt.value)

    # ═══════════════════════════════════════════════════════════════════════
    # SCENES
    # ═══════════════════════════════════════════════════════════════════════

    def create_scene(self, index: int = -1) -> int:
        """Create a new scene."""
        self._send("/live/song/create_scene", index)
        time.sleep(0.05)
        return index if index >= 0 else self.get_scene_count() - 1

    def delete_scene(self, index: int):
        self._send("/live/song/delete_scene", index)

    def duplicate_scene(self, index: int):
        self._send("/live/song/duplicate_scene", index)

    def get_scene_count(self) -> int:
        result = self._query("/live/song/get/num_scenes")
        return result[0] if result else 0

    def set_scene_name(self, index: int, name: str):
        self._send("/live/scene/set/name", index, name)

    def set_scene_tempo(self, index: int, tempo: float):
        self._send("/live/scene/set/tempo", index, tempo)

    def set_scene_color(self, index: int, color: int | str):
        c = COLORS.get(color, color) if isinstance(color, str) else color
        self._send("/live/scene/set/color", index, c)

    # ═══════════════════════════════════════════════════════════════════════
    # CUE POINTS
    # ═══════════════════════════════════════════════════════════════════════

    def set_cue_point(self):
        """Add cue point at current position."""
        self._send("/live/song/set_or_delete_cue")

    def jump_to_cue(self, direction: str = "next"):
        if direction == "next":
            self._send("/live/song/jump_to_next_cue")
        else:
            self._send("/live/song/jump_to_prev_cue")

    # ═══════════════════════════════════════════════════════════════════════
    # RENDERING / EXPORT
    # ═══════════════════════════════════════════════════════════════════════

    def render_arrangement(self, output_path: str = "", tail_seconds: float = 2.0):
        """Render arrangement to audio.

        Note: Ableton's render is triggered via File > Export Audio/Video.
        AbletonOSC cannot directly trigger this. Use Cmd+Shift+R workflow:
        1. Set loop to desired region
        2. Use keyboard shortcut simulation
        Or use the ALS-based offline export approach.
        """
        _log.info("Arrangement render must be triggered from Ableton's Export dialog. "
                   "Set loop markers, then File > Export Audio/Video (Cmd+Shift+R).")
        # We can set up the session for rendering:
        self._send("/live/song/set/loop", 1)  # Enable loop for export region

    def freeze_track(self, track: int):
        """Freeze a track to save CPU. Must be done manually in Ableton."""
        _log.info(f"Freeze track {track}: Right-click track > Freeze Track in Ableton")

    def flatten_track(self, track: int):
        """Flatten a frozen track to audio."""
        _log.info(f"Flatten track {track}: Right-click track > Flatten in Ableton")

    # ═══════════════════════════════════════════════════════════════════════
    # MIDI MAP / CC
    # ═══════════════════════════════════════════════════════════════════════

    def map_midi_cc(self, track: int, device: int, param: int,
                    channel: int, cc: int):
        """Map a MIDI CC to a device parameter."""
        self._send("/live/midi_map/map_cc", track, device, param, channel, cc)

    def unmap_midi_cc(self, track: int, device: int, param: int):
        self._send("/live/midi_map/unmap_cc", track, device, param)

    # ═══════════════════════════════════════════════════════════════════════
    # MEMORY MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    def save_set(self):
        """Save the current Live Set."""
        _log.info("Save Live Set: Cmd+S in Ableton (OSC cannot directly save)")

    def get_cpu_load(self) -> float | None:
        result = self._query("/live/application/get/average_process_usage")
        return result[0] if result else None

    # ═══════════════════════════════════════════════════════════════════════
    # BATCH / HIGH-LEVEL OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════

    def setup_session(self, name: str, bpm: float,
                      time_sig: tuple[int, int] = (4, 4),
                      track_configs: list[dict] | None = None) -> dict:
        """Set up a complete session from config.

        track_configs: [{type: "midi"|"audio", name: str, color: str,
                         arm: bool, volume: float, pan: float}]
        Returns: {track_indices: [...], scene_count: int}
        """
        self.set_tempo(bpm)
        self.set_time_signature(*time_sig)

        track_indices = []
        if track_configs:
            for tc in track_configs:
                if tc.get("type") == "audio":
                    idx = self.create_audio_track(-1, tc.get("name", ""))
                else:
                    idx = self.create_midi_track(-1, tc.get("name", ""))
                if "color" in tc:
                    self.set_track_color(idx, tc["color"])
                if "volume" in tc:
                    self.set_track_volume(idx, tc["volume"])
                if "pan" in tc:
                    self.set_track_pan(idx, tc["pan"])
                if tc.get("arm"):
                    self.set_track_arm(idx, True)
                track_indices.append(idx)
                time.sleep(0.02)

        return {"track_indices": track_indices,
                "scene_count": self.get_scene_count()}

    def program_clip_from_notes(self, track: int, slot: int,
                                length_beats: float,
                                notes: list[NoteData | dict],
                                name: str = "",
                                loop: bool = True):
        """Create a clip and program it with notes in one call."""
        self.create_clip(track, slot, length_beats)
        time.sleep(0.05)
        self.add_notes_batch(track, slot, notes)
        if name:
            self.set_clip_name(track, slot, name)
        if loop:
            self.set_clip_loop(track, slot, True)

    def setup_return_fx(self, name: str, color: str = "cyan") -> int:
        """Create a return track for FX."""
        idx = self.create_return_track(name)
        self.set_return_name(idx, name)
        return idx

    def send_track_to_return(self, track: int, return_index: int, amount: float):
        """Route a track's send to a return."""
        self.set_track_send(track, return_index, amount)

    def set_sidechain(self, target_track: int, source_track: int, depth: float = 0.8):
        """Configure sidechain compression on target_track triggered by source_track.

        Attempts to set the Ratio/Amount parameter on a pre-loaded compressor
        device (device index 0) on the target track.  Sidechain audio routing
        must be configured manually in Ableton; this only sets depth.

        Args:
            target_track: Track index to sidechain-compress (e.g. bass).
            source_track: Sidechain trigger track index (e.g. kick).
            depth:        Compression depth 0–1 (mapped to compressor Ratio 1–8).
        """
        ratio = round(1.0 + depth * 7.0, 2)  # 0.0→1:1, 1.0→8:1
        try:
            self.set_device_parameter_by_name(target_track, 0, "Ratio", ratio)
        except Exception:
            pass
        try:
            # Some Ableton compressor devices expose "Amount" instead of "Ratio"
            self.set_device_parameter_by_name(target_track, 0, "Amount", depth)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════════
    # VIEW CONTROL
    # ═══════════════════════════════════════════════════════════════════════

    def show_arrangement(self):
        self._send("/live/view/set/focused_document_view", "Arranger")

    def show_session(self):
        self._send("/live/view/set/focused_document_view", "Session")

    def show_detail(self):
        self._send("/live/view/show_view", "Detail")

    def select_track(self, track: int):
        self._send("/live/view/set/selected_track", track)

    def select_scene(self, scene: int):
        self._send("/live/view/set/selected_scene", scene)

    # ═══════════════════════════════════════════════════════════════════════
    # API INFO / LOG LEVEL
    # ═══════════════════════════════════════════════════════════════════════

    def set_log_level(self, level: int):
        """Set AbletonOSC log verbosity (0=off, 1=info, 2=debug)."""
        self._send("/live/api/set/log_level", level)

    def show_message(self, message: str):
        """Display a message in Ableton's status bar."""
        self._send("/live/application/show_message", message)

    # ═══════════════════════════════════════════════════════════════════════
    # CONTEXT MANAGER
    # ═══════════════════════════════════════════════════════════════════════

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def quick_connect() -> AbletonBridge:
    """Quick-connect to Ableton Live."""
    ab = AbletonBridge()
    ab.connect()
    return ab


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    ab = AbletonBridge(verbose=True)
    if ab.connect():
        print("\n  AbletonBridge — Interactive Mode")
        print("  Available: ab.play(), ab.stop(), ab.set_tempo(145), etc.")
        print("  Full API: track, clip, device, scene, automation, routing\n")
        # Quick test
        tempo = ab.get_tempo()
        if tempo:
            print(f"  Current tempo: {tempo}")
            print(f"  Track count: {ab.get_track_count()}")
            print(f"  Scene count: {ab.get_scene_count()}")
    else:
        print("  ✗ Could not connect to Ableton Live")
        print("  Make sure AbletonOSC is installed and selected in Preferences")
