#!/usr/bin/env python3
"""Create a minimal Ableton ALS template with one Serum 2 instance per preset.

Usage
-----
    # Create template with just one default Serum 2 instance:
    python3 tools/make_state_template.py

    # Create template with a specific DUBFORGE preset loaded:
    python3 tools/make_state_template.py --preset "DF Bass Lead"

Workflow
--------
1. Run this script → creates output/ableton/_state_capture_template.als
2. Open the ALS in Ableton Live 12
3. For each Serum 2 track, load the desired preset in Serum 2's browser
4. Save (Cmd+S) — Ableton writes its native IBStream state into the ALS
5. Run: python3 tools/extract_vst3_state.py output/ableton/_state_capture_template.als -p "Serum 2" -o engine/_captured_serum2_state.py
6. The extracted state is now Ableton-native and can be embedded in generated ALS files.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.als_generator import ALSProject, ALSTrack, write_als


def main():
    out_dir = Path("output/ableton")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "_state_capture_template.als"

    # Create a single MIDI track with Serum 2 — no MIDI data needed,
    # just the plugin device so Ableton loads Serum 2.
    track = ALSTrack(
        name="Serum2 State Capture",
        track_type="midi",
        color=3,
        device_names=["Serum 2"],
    )

    project = ALSProject(
        name="DUBFORGE State Capture",
        bpm=127.0,
        tracks=[track],
    )

    write_als(project, str(out_path))
    size = out_path.stat().st_size
    print(f"Template ALS written: {out_path} ({size:,} bytes)")
    print()
    print("Next steps:")
    print("  1. Open in Ableton Live 12")
    print("  2. Load desired preset in Serum 2")
    print("  3. Save the ALS (Cmd+S)")
    print("  4. Run: python3 tools/extract_vst3_state.py \\")
    print(f"       {out_path} -p 'Serum 2' --first -o engine/_captured_serum2_state.py")
    print("  5. Then update engine/serum2_preset.py to use the captured state")


if __name__ == "__main__":
    main()
