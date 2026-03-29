"""DUBFORGE — Ableton Link Integration (Tier 5)

Provides tempo and phase synchronisation with Ableton Link, the
peer-to-peer protocol used by Ableton Live and many other music apps.

The module exposes a high-level ``LinkSync`` class that wraps either:
  1. ``aalink`` / ``abletonlink`` Python C-extension (if installed), or
  2. A lightweight UDP multicast discovery fallback that can read peer
     tempo but not actively participate in the Link session.

Typical usage::

    from engine.link_sync import LinkSync

    link = LinkSync()
    link.enable()
    print(link.tempo)          # current Link tempo
    link.tempo = 150.0         # propose new tempo
    print(link.beat_phase())   # phase within bar (0-3)
    link.capture_transport()   # start playing in sync
    link.disable()

The ``get_link()`` / ``auto_enable()`` convenience helpers mirror the
``get_bridge()`` / ``auto_connect()`` pattern in ``ableton_bridge.py``.

Dependencies (optional — gracefully degraded when absent):
  pip install aalink          # preferred
  pip install link-python     # alternative binding
"""

from __future__ import annotations

import logging
import math
import struct
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("dubforge.link_sync")

# ───────────────────────────────────────────────────────────────────────
# Constants
# ───────────────────────────────────────────────────────────────────────

PHI: float = 1.6180339887498948482
FIBONACCI: list[int] = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]

LINK_MULTICAST_GROUP = "224.76.78.75"
LINK_MULTICAST_PORT = 20808


# ───────────────────────────────────────────────────────────────────────
# C-Extension Backend (preferred)
# ───────────────────────────────────────────────────────────────────────

_link_lib = None


def _load_link_lib():
    """Try to import a Link C-extension library."""
    global _link_lib
    if _link_lib is not None:
        return _link_lib

    # Try aalink first, then link-python
    for module_name in ("aalink", "link"):
        try:
            import importlib
            _link_lib = importlib.import_module(module_name)
            logger.info("Loaded Link backend: %s", module_name)
            return _link_lib
        except ImportError:
            continue

    logger.warning("No Link C-extension found — using UDP discovery fallback")
    return None


# ───────────────────────────────────────────────────────────────────────
# Lightweight UDP Discovery Fallback
# ───────────────────────────────────────────────────────────────────────

@dataclass
class LinkPeer:
    """A discovered Link peer."""
    peer_id: bytes
    tempo: float
    beat: float
    timestamp: float = 0.0


class _UDPLinkListener:
    """Minimal multicast listener that discovers Link peers on the LAN
    and reads their tempo broadcast.  This does *not* allow full
    bidirectional Link participation (tempo-propose, phase-lock) but is
    useful for read-only monitoring when no C-extension is available."""

    def __init__(self) -> None:
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._peers: dict[bytes, LinkPeer] = {}
        self._lock = threading.Lock()

    # ── lifecycle ──

    def start(self) -> None:
        if self._running:
            return
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._sock.bind(("", LINK_MULTICAST_PORT))
        except OSError as exc:
            logger.warning("Cannot bind Link multicast port: %s", exc)
            self._sock.close()
            self._sock = None
            return

        # Join multicast group
        mreq = struct.pack(
            "4s4s",
            socket.inet_aton(LINK_MULTICAST_GROUP),
            socket.inet_aton("0.0.0.0"),
        )
        self._sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        self._sock.settimeout(1.0)

        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True, name="link-udp")
        self._thread.start()
        logger.info("UDP Link listener started on port %d", LINK_MULTICAST_PORT)

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    # ── data ──

    @property
    def peer_count(self) -> int:
        with self._lock:
            return len(self._peers)

    @property
    def tempo(self) -> float:
        """Return the most recently seen peer tempo, or 120.0 default."""
        with self._lock:
            if not self._peers:
                return 120.0
            newest = max(self._peers.values(), key=lambda p: p.timestamp)
            return newest.tempo

    # ── internal ──

    def _listen(self) -> None:
        while self._running:
            try:
                data, _addr = self._sock.recvfrom(4096)
                self._parse_packet(data)
            except socket.timeout:
                continue
            except OSError:
                break

    def _parse_packet(self, data: bytes) -> None:
        """Best-effort parse of a Link UDP packet.

        The Link protocol uses a custom binary format.  We attempt to
        extract the tempo field from the payload header.  This is NOT a
        full protocol implementation — just enough to read tempo from
        broadcasts.
        """
        if len(data) < 20:
            return
        try:
            # Link header: 8-byte magic, then payload
            # The tempo is typically in the session-state message as a
            # double-precision float.  We scan for plausible tempo values
            # (40-300 BPM) in the first few 8-byte aligned slots.
            for offset in range(8, min(len(data) - 7, 128), 8):
                val = struct.unpack_from(">d", data, offset)[0]
                if 40.0 <= val <= 300.0:
                    peer_id = data[:8]
                    with self._lock:
                        self._peers[peer_id] = LinkPeer(
                            peer_id=peer_id,
                            tempo=val,
                            beat=0.0,
                            timestamp=time.monotonic(),
                        )
                    return
        except struct.error:
            pass


# ───────────────────────────────────────────────────────────────────────
# LinkSync — Unified Interface
# ───────────────────────────────────────────────────────────────────────

class LinkSync:
    """High-level Ableton Link synchronisation controller.

    Wraps a C-extension backend when available or falls back to the
    lightweight UDP listener for read-only tempo discovery.
    """

    def __init__(self, initial_tempo: float = 150.0, quantum: float = 4.0) -> None:
        self._initial_tempo = initial_tempo
        self._quantum = quantum  # beats per bar
        self._enabled = False
        self._playing = False

        # Native Link session (if C-extension available)
        self._native = None
        # Fallback listener
        self._udp: Optional[_UDPLinkListener] = None

        self._lib = _load_link_lib()

    # ── lifecycle ──

    def enable(self) -> None:
        """Enable Link and start synchronising."""
        if self._enabled:
            return

        if self._lib is not None:
            try:
                self._native = self._lib.Link(self._initial_tempo)
                self._native.enabled = True
                self._native.startStopSyncEnabled = True
                self._enabled = True
                logger.info("Link enabled via C-extension at %.1f BPM", self._initial_tempo)
                return
            except Exception as exc:
                logger.warning("C-extension Link failed: %s — falling back to UDP", exc)
                self._native = None

        # Fallback
        self._udp = _UDPLinkListener()
        self._udp.start()
        self._enabled = True
        logger.info("Link enabled via UDP fallback at %.1f BPM", self._initial_tempo)

    def disable(self) -> None:
        """Disable Link synchronisation."""
        if not self._enabled:
            return
        if self._native is not None:
            self._native.enabled = False
            self._native = None
        if self._udp is not None:
            self._udp.stop()
            self._udp = None
        self._enabled = False
        self._playing = False
        logger.info("Link disabled")

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    # ── tempo ──

    @property
    def tempo(self) -> float:
        """Current Link tempo in BPM."""
        if self._native is not None:
            state = self._native.captureSessionState()
            return state.tempo()
        if self._udp is not None:
            return self._udp.tempo
        return self._initial_tempo

    @tempo.setter
    def tempo(self, bpm: float) -> None:
        """Propose a new tempo on the Link session."""
        if not 20.0 <= bpm <= 999.0:
            logger.warning("Tempo %.1f out of range [20, 999]", bpm)
            return
        if self._native is not None:
            state = self._native.captureSessionState()
            state.setTempo(bpm, self._native.clock().micros())
            self._native.commitSessionState(state)
            logger.info("Link tempo set to %.1f", bpm)
        else:
            self._initial_tempo = bpm
            logger.info("Local tempo set to %.1f (no native Link)", bpm)

    # ── beat / phase ──

    def beat_time(self) -> float:
        """Current beat position in the Link session."""
        if self._native is not None:
            state = self._native.captureSessionState()
            return state.beatAtTime(self._native.clock().micros(), self._quantum)
        return 0.0

    def beat_phase(self) -> float:
        """Phase within the current bar (0.0 to quantum-1)."""
        if self._native is not None:
            state = self._native.captureSessionState()
            return state.phaseAtTime(self._native.clock().micros(), self._quantum)
        return 0.0

    def bar_position(self) -> float:
        """Current bar number (fractional)."""
        bt = self.beat_time()
        return bt / self._quantum

    # ── transport ──

    def capture_transport(self) -> None:
        """Request transport start — aligned to Link phase."""
        if self._native is not None:
            state = self._native.captureSessionState()
            state.setIsPlaying(True, self._native.clock().micros())
            self._native.commitSessionState(state)
        self._playing = True
        logger.info("Link transport: PLAY")

    def release_transport(self) -> None:
        """Request transport stop."""
        if self._native is not None:
            state = self._native.captureSessionState()
            state.setIsPlaying(False, self._native.clock().micros())
            self._native.commitSessionState(state)
        self._playing = False
        logger.info("Link transport: STOP")

    @property
    def is_playing(self) -> bool:
        if self._native is not None:
            state = self._native.captureSessionState()
            return state.isPlaying()
        return self._playing

    # ── peers ──

    @property
    def peer_count(self) -> int:
        """Number of Link peers (including self)."""
        if self._native is not None:
            return self._native.numPeers()
        if self._udp is not None:
            return self._udp.peer_count
        return 0

    # ── quantum ──

    @property
    def quantum(self) -> float:
        return self._quantum

    @quantum.setter
    def quantum(self, q: float) -> None:
        if q > 0:
            self._quantum = q

    # ── DUBFORGE-specific helpers ──

    def wait_for_downbeat(self, timeout: float = 30.0) -> bool:
        """Block until the next bar downbeat (phase crosses zero).

        Returns True if downbeat detected, False on timeout.
        """
        if self._native is None:
            return True  # no sync available, proceed immediately

        start = time.monotonic()
        prev_phase = self.beat_phase()

        while time.monotonic() - start < timeout:
            p = self.beat_phase()
            if p < prev_phase:  # wrapped around → downbeat
                return True
            prev_phase = p
            time.sleep(0.001)

        return False

    def fibonacci_tempo_ramp(self, start_bpm: float, end_bpm: float,
                             bars: int = 8, step_interval: float = 0.5) -> None:
        """Ramp tempo using Fibonacci-weighted curve over N bars.

        Runs in the current thread, blocking for the duration.
        """
        if not self._enabled:
            return

        beats_total = bars * self._quantum
        steps = int(beats_total / step_interval)
        if steps < 2:
            self.tempo = end_bpm
            return

        # Fibonacci-weighted interpolation
        fib_weights: list[float] = []
        a, b = 1.0, 1.0
        for _ in range(steps):
            fib_weights.append(a)
            a, b = b, a + b
        total_w = sum(fib_weights)
        cum = 0.0

        for i, w in enumerate(fib_weights):
            cum += w
            t = cum / total_w  # 0→1 Fibonacci curve
            bpm = start_bpm + (end_bpm - start_bpm) * t
            self.tempo = bpm
            time.sleep(step_interval * 60.0 / max(bpm, 40.0))

        self.tempo = end_bpm
        logger.info("Fibonacci ramp complete: %.1f → %.1f BPM", start_bpm, end_bpm)

    def golden_section_beat(self, total_beats: float) -> float:
        """Return the golden-section beat position within a region."""
        return total_beats / PHI

    def snap(self) -> dict:
        """Return a snapshot of the current Link state."""
        return {
            "enabled": self._enabled,
            "tempo": self.tempo,
            "beat": self.beat_time(),
            "phase": self.beat_phase(),
            "bar": self.bar_position(),
            "playing": self.is_playing,
            "peers": self.peer_count,
            "quantum": self._quantum,
        }


# ───────────────────────────────────────────────────────────────────────
# Singleton / convenience
# ───────────────────────────────────────────────────────────────────────

_instance: Optional[LinkSync] = None


def get_link(tempo: float = 150.0) -> LinkSync:
    """Return a shared ``LinkSync`` instance (singleton)."""
    global _instance
    if _instance is None:
        _instance = LinkSync(initial_tempo=tempo)
    return _instance


def auto_enable(tempo: float = 150.0) -> LinkSync:
    """Get the singleton and enable it — convenience for scripts."""
    link = get_link(tempo)
    if not link.is_enabled:
        link.enable()
    return link
