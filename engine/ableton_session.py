"""DUBFORGE — Ableton Session Lifecycle Manager

Shared helpers for fresh Ableton session management between phases.
Each phase calls ensure_fresh_ableton_session() at startup to guarantee
it runs in its own isolated Live session.

API:
    detect_ableton_app() -> str
    ensure_fresh_ableton_session(template_als=None, timeout_s=45.0) -> bool
    close_ableton_session(save=False) -> bool
    open_ableton_session(als_path=None) -> bool
    wait_for_ableton_osc(host="127.0.0.1", port=11000, timeout_s=30.0) -> bool
"""
from __future__ import annotations

import socket
import subprocess
import time

# ── Constants ────────────────────────────────────────────────────────────────

_ABLETON_APP_CACHE: str | None = None
OSC_HOST = "127.0.0.1"
OSC_SEND_PORT = 11000
OSC_RECV_PORT = 11001


def detect_ableton_app() -> str:
    """Detect the installed Ableton Live application name.

    Scans /Applications for 'Ableton Live*.app', falls back to running
    process list, then defaults to 'Ableton Live 12 Standard'.
    Result is cached for subsequent calls.
    """
    global _ABLETON_APP_CACHE
    if _ABLETON_APP_CACHE is not None:
        return _ABLETON_APP_CACHE

    from pathlib import Path

    # 1. Installed .app bundles in /Applications
    candidates = sorted(Path("/Applications").glob("Ableton Live*.app"), reverse=True)
    if candidates:
        _ABLETON_APP_CACHE = candidates[0].stem
        return _ABLETON_APP_CACHE

    # 2. Running process via System Events
    try:
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get name of every process '
             'whose name contains "Ableton"'],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            name = result.stdout.strip().split(",")[0].strip()
            if name:
                _ABLETON_APP_CACHE = name
                return _ABLETON_APP_CACHE
    except Exception:
        pass

    _ABLETON_APP_CACHE = "Ableton Live 12 Standard"
    return _ABLETON_APP_CACHE


# ── Low-level osascript helpers ───────────────────────────────────────────────

def _osascript(script: str, timeout_s: float = 20.0) -> bool:
    """Run an AppleScript fragment. Returns True on success."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=timeout_s,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  ⚠ osascript timed out after {timeout_s}s")
        return False
    except FileNotFoundError:
        print("  ⚠ osascript not found — not running on macOS?")
        return False


def _ableton_is_running() -> bool:
    """Check if Ableton Live is in the running applications list."""
    app = detect_ableton_app()
    result = subprocess.run(
        ["osascript", "-e",
         f'tell application "System Events" to '
         f'(name of processes) contains "{app}"'],
        capture_output=True, timeout=5.0,
    )
    return result.stdout.strip() == b"true"


# ── OSC readiness probe ───────────────────────────────────────────────────────

def wait_for_ableton_osc(
    host: str = OSC_HOST,
    port: int = OSC_SEND_PORT,
    timeout_s: float = 30.0,
) -> bool:
    """Poll until Ableton's AbletonOSC server accepts a TCP connection.

    AbletonOSC uses UDP, so we probe by attempting a socket connection to
    the OSC port. A refused connection means Live isn't ready yet; success
    (even immediate close) means the port is open and Live is responsive.
    Falls back to a short sleep-based retry on UDP-only setups.
    """
    deadline = time.monotonic() + timeout_s
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            # Try importing AbletonBridge for a proper OSC handshake
            from engine.ableton_bridge import AbletonBridge
            bridge = AbletonBridge(
                host=host,
                send_port=port,
                recv_port=OSC_RECV_PORT,
                verbose=False,
            )
            if bridge.connect():
                bridge.disconnect()
                print(f"  ✓ Ableton OSC ready (attempt {attempt})")
                return True
        except Exception:
            pass

        # Fallback: TCP port probe (slower but works on most setups)
        try:
            with socket.create_connection((host, port), timeout=1.0):
                print(f"  ✓ Ableton OSC port open (attempt {attempt})")
                return True
        except (ConnectionRefusedError, OSError):
            pass

        print(f"  … waiting for Ableton OSC ({attempt}) …")
        time.sleep(2.5)

    print(f"  ⚠ Ableton OSC did not respond within {timeout_s}s")
    return False


# ── Session lifecycle ─────────────────────────────────────────────────────────

def close_ableton_session(save: bool = False) -> bool:
    """Save (optionally) and close every open document in Ableton Live.

    Args:
        save: If True, saves before closing. Defaults to False (discard).

    Returns:
        True if the osascript executed without error.
    """
    saving = "yes" if save else "no"
    app = detect_ableton_app()
    script = (
        f'tell application "{app}"\n'
        f'    activate\n'
        f'    close every document saving {saving}\n'
        f'end tell'
    )
    ok = _osascript(script, timeout_s=20.0)
    if ok:
        print("  ✓ Ableton session closed")
        time.sleep(1.5)  # Brief pause for Live to settle
    else:
        print("  ⚠ close_ableton_session: osascript failed (session may be unsaved or Live not open)")
    return ok


def open_ableton_session(als_path: str | None = None) -> bool:
    """Open a fresh Ableton session — either a blank document or a specific ALS.

    Args:
        als_path: Absolute path to an .als file, or None for a blank session.

    Returns:
        True if the osascript executed without error.
    """
    if als_path:
        from pathlib import Path
        p = Path(als_path)
        if not p.exists():
            print(f"  ⚠ open_ableton_session: ALS not found: {als_path}")
            als_path = None  # Fall back to blank

    app = detect_ableton_app()
    if als_path:
        script = (
            f'tell application "{app}"\n'
            f'    activate\n'
            f'    open POSIX file "{als_path}"\n'
            f'end tell'
        )
        label = f"ALS: {als_path}"
    else:
        # Open a new blank document
        script = (
            f'tell application "{app}"\n'
            f'    activate\n'
            f'    set newDoc to make new document\n'
            f'end tell'
        )
        label = "blank session"

    ok = _osascript(script, timeout_s=20.0)
    if ok:
        print(f"  ✓ Ableton session opened: {label}")
        time.sleep(3.0)  # Allow Live to fully load the session
    else:
        print(f"  ⚠ open_ableton_session: osascript failed (Live may not be running)")
    return ok


# ── Top-level helper called by each phase ────────────────────────────────────

def ensure_fresh_ableton_session(
    template_als: str | None = None,
    osc_timeout_s: float = 45.0,
) -> bool:
    """Guarantee a clean Ableton session for the calling phase.

    Sequence:
        1. Activate Ableton Live (bring to front)
        2. Close any open documents (no save)
        3. Open template ALS or blank document
        4. Wait until AbletonOSC is responsive

    Args:
        template_als: Optional path to a template .als file to open.
        osc_timeout_s: How long to wait for AbletonOSC to respond (default 45s).

    Returns:
        True if Ableton is ready for OSC commands. False on failure (caller
        should decide whether to abort or continue without Ableton).
    """
    print("  → Preparing fresh Ableton session …")

    # Step 1: Activate Live (launch if not running or bring to front)
    _osascript(
        f'tell application "{detect_ableton_app()}" to activate',
        timeout_s=10.0,
    )
    time.sleep(1.0)

    # Step 2: Close existing documents
    close_ableton_session(save=False)

    # Step 3: Open fresh session
    open_ableton_session(als_path=template_als)

    # Step 4: Wait for OSC readiness
    ready = wait_for_ableton_osc(timeout_s=osc_timeout_s)
    return ready
