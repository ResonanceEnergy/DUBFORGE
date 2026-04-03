#!/usr/bin/env python3
"""DUBFORGE Launch Orchestrator — render track + open all browser apps.

Usage:
    python launch.py                          # Render default track + launch all UIs
    python launch.py --track wild-ones        # Wild Ones V12 (MIDI+ALS)
    python launch.py --track apology          # Apology V4 (MIDI+ALS)
    python launch.py --track forge            # Full forge pipeline
    python launch.py --track quick            # Quick default track
    python launch.py --ui-only               # Skip rendering, just launch UIs
    python launch.py --render-only           # Render only, no UIs
    python launch.py --studio                # Launch studio only
    python launch.py --launchpad             # Launch launchpad only
    python launch.py --analyzer              # Launch analyzer only

Ports:
    Studio:    http://localhost:7860
    Analyzer:  http://localhost:7861
    Launchpad: http://localhost:7870
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
PYTHON = sys.executable

# ── Browser App Definitions ─────────────────────────────────────────────

APPS = {
    "studio": {
        "script": "dubforge_studio.py",
        "port": 7860,
        "label": "DUBFORGE Studio",
    },
    "analyzer": {
        "script": "dubstep_analyzer_ui.py",
        "port": 7861,
        "label": "Taste Analyzer",
    },
    "launchpad": {
        "script": "dubforge_launchpad.py",
        "port": 7870,
        "label": "Launchpad",
    },
}

# ── Track Definitions ───────────────────────────────────────────────────

TRACKS = {
    "wild-ones": {
        "script": "make_wild_ones_v12.py",
        "label": "Wild Ones V12 (MIDI+ALS+GALATCIA)",
    },
    "apology": {
        "script": "make_apology_v4.py",
        "label": "The Apology That Never Came V4 (MIDI+ALS)",
    },
    "forge": {
        "script": "forge.py",
        "label": "Full Forge Pipeline",
    },
    "quick": {
        "script": "make_track.py",
        "label": "Quick Dubstep Track",
    },
}


def _banner() -> None:
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║          DUBFORGE — Launch Orchestrator                     ║")
    print("║          Render + Browser Apps in one command               ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()


def render_track(track_key: str) -> bool:
    """Render a track by key. Returns True on success."""
    info = TRACKS[track_key]
    script = PROJECT / info["script"]

    if not script.exists():
        print(f"  ✗ Script not found: {script}")
        return False

    print(f"  ▸ Rendering: {info['label']}")
    print(f"    Script: {script.name}")
    print()

    t0 = time.time()
    result = subprocess.run(
        [PYTHON, str(script)],
        cwd=str(PROJECT),
    )
    elapsed = time.time() - t0

    if result.returncode == 0:
        print(f"\n  ✓ Render complete ({elapsed:.0f}s)")
        return True
    else:
        print(f"\n  ✗ Render FAILED (exit {result.returncode}, {elapsed:.0f}s)")
        return False


def launch_app(name: str, app: dict) -> subprocess.Popen | None:
    """Launch a Gradio browser app as a background process."""
    script = PROJECT / app["script"]
    port = app["port"]

    if not script.exists():
        print(f"  ✗ {app['label']}: {script.name} not found")
        return None

    print(f"  ▸ {app['label']:20s} → http://localhost:{port}")

    proc = subprocess.Popen(
        [PYTHON, str(script), "--port", str(port)],
        cwd=str(PROJECT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def wait_for_port(port: int, timeout: float = 30.0) -> bool:
    """Wait until a port is accepting connections."""
    import socket

    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def open_browsers(apps_to_launch: list[str]) -> None:
    """Open browser tabs for launched apps."""
    for name in apps_to_launch:
        port = APPS[name]["port"]
        url = f"http://localhost:{port}"
        webbrowser.open(url)
        time.sleep(0.3)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DUBFORGE Launch Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Tracks:
  wild-ones    Wild Ones V12 — MIDI+ALS+GALATCIA (Fibonacci, 144 bars)
  apology      The Apology That Never Came V4 — MIDI+ALS (144 bars)
  forge        Full forge pipeline (stems + wavetables + presets + ALS)
  quick        Quick default dubstep track (WAV render)

Browser Apps:
  Studio       http://localhost:7860  (render, preview, analyze, master)
  Analyzer     http://localhost:7861  (SoundCloud taste + emulation)
  Launchpad    http://localhost:7870  (idea wizard + FORGE IT)
""",
    )

    parser.add_argument(
        "--track", "-t",
        choices=list(TRACKS.keys()),
        default="quick",
        help="Track to render (default: quick)",
    )
    parser.add_argument("--ui-only", action="store_true", help="Skip rendering, launch UIs only")
    parser.add_argument("--render-only", action="store_true", help="Render only, no UIs")
    parser.add_argument("--studio", action="store_true", help="Launch studio only")
    parser.add_argument("--launchpad", action="store_true", help="Launch launchpad only")
    parser.add_argument("--analyzer", action="store_true", help="Launch analyzer only")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser tabs")

    args = parser.parse_args()

    _banner()

    # Determine which apps to launch
    specific_apps = []
    if args.studio:
        specific_apps.append("studio")
    if args.launchpad:
        specific_apps.append("launchpad")
    if args.analyzer:
        specific_apps.append("analyzer")

    apps_to_launch = specific_apps if specific_apps else list(APPS.keys())

    # ── Phase 1: Render ──────────────────────────────────────────────
    if not args.ui_only:
        print("━━━ Phase 1: RENDER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        success = render_track(args.track)
        if not success and not args.render_only:
            print("  ⚠ Render failed — continuing to UI launch")
        print()

    if args.render_only:
        return

    # ── Phase 2: Launch Browser Apps ─────────────────────────────────
    print("━━━ Phase 2: BROWSER APPS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    processes: list[subprocess.Popen] = []
    for name in apps_to_launch:
        proc = launch_app(name, APPS[name])
        if proc:
            processes.append(proc)

    if not processes:
        print("  ✗ No apps launched")
        return

    print()

    # Wait for apps to be ready
    print("  Waiting for servers...", end="", flush=True)
    ready = []
    for name in apps_to_launch:
        port = APPS[name]["port"]
        if wait_for_port(port, timeout=45):
            ready.append(name)
            print(f" ✓{port}", end="", flush=True)
        else:
            print(f" ✗{port}", end="", flush=True)
    print()

    # Open browser tabs
    if not args.no_browser and ready:
        print("  Opening browser tabs...")
        open_browsers(ready)

    print()
    print("━━━ RUNNING ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for name in apps_to_launch:
        port = APPS[name]["port"]
        label = APPS[name]["label"]
        status = "✓" if name in ready else "✗"
        print(f"  [{status}] {label:20s}  http://localhost:{port}")
    print()
    print("  Press Ctrl+C to stop all servers")
    print()

    # Wait for Ctrl+C
    def _shutdown(sig, frame):
        print("\n  Shutting down...")
        for p in processes:
            p.terminate()
        for p in processes:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        print("  ✓ All servers stopped")
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Keep alive
    try:
        while True:
            # Check if any process died
            for p in processes:
                if p.poll() is not None:
                    pass  # Don't exit — others may still be running
            time.sleep(2)
    except KeyboardInterrupt:
        _shutdown(None, None)


if __name__ == "__main__":
    main()
