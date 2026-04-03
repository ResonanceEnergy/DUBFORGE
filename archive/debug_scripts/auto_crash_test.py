"""Automated Ableton crash tester.

Launches Ableton with each test ALS file, waits a few seconds,
then checks if the process is still alive.
  - Alive after 5s  = LOADS OK
  - Dead within 5s  = CRASH

IMPORTANT: Close Ableton before running this script.
"""
import subprocess
import time
import os
import sys

ABLETON = r"C:\ProgramData\Ableton\Live 12 Standard\Program\Ableton Live 12 Standard.exe"
TEST_DIR = os.path.join(os.path.dirname(__file__), "output", "ableton", "test_v12strip")
WAIT_SECS = 8  # time to wait before checking if process is alive

# Also test the original V12 as control
V12 = os.path.join(os.path.dirname(__file__), "output", "ableton", "Wild_Ones_V12.als")

# Test files in order of importance
TEST_FILES = [
    ("s9_bare_skeleton.als", "V12 skeleton: no names, no notes, no automation"),
    ("s6_no_notes.als",      "V12 structure + names, zero notes"),
    ("s1_plain_names.als",   "V12 data, plain track names (no [Serum2:])"),
    ("s2_no_automation.als", "V12 data, no automation envelopes"),
    ("s7_simple_notes.als",  "V12 structure, simple 4-note clips"),
    ("s5_drums_only.als",    "Only DRUMS track + returns"),
    ("s4_2tracks_only.als",  "Only DRUMS + BASS + returns"),
]


def kill_ableton():
    """Kill any running Ableton process."""
    os.system('taskkill /f /im "Ableton Live 12 Standard.exe" >nul 2>&1')
    time.sleep(2)


def test_file(als_path, desc):
    """Launch Ableton with the given ALS file and check for crash."""
    kill_ableton()

    print(f"\n  Testing: {os.path.basename(als_path)}")
    print(f"  Desc:    {desc}")
    print(f"  Waiting {WAIT_SECS}s... ", end="", flush=True)

    proc = subprocess.Popen([ABLETON, als_path])
    time.sleep(WAIT_SECS)

    poll = proc.poll()
    if poll is not None:
        print(f"CRASH (exit code {poll})")
        return False
    else:
        print("LOADS OK")
        kill_ableton()
        return True


def main():
    if not os.path.exists(ABLETON):
        print(f"ERROR: Ableton not found at {ABLETON}")
        sys.exit(1)

    print(f"Ableton: {ABLETON}")
    print(f"Test dir: {TEST_DIR}")
    print(f"Wait time: {WAIT_SECS}s per test")
    print(f"\nKilling any running Ableton...")
    kill_ableton()

    results = []

    # First test the original V12 as a control (should crash)
    if os.path.exists(V12):
        ok = test_file(V12, "CONTROL: Original V12 (should crash)")
        results.append(("Wild_Ones_V12.als", ok))

    # Then test each stripped variant
    for fname, desc in TEST_FILES:
        fpath = os.path.join(TEST_DIR, fname)
        if not os.path.exists(fpath):
            print(f"\n  SKIP: {fname} (not found)")
            results.append((fname, None))
            continue
        ok = test_file(fpath, desc)
        results.append((fname, ok))

    kill_ableton()

    # Summary
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    for fname, ok in results:
        status = "LOADS" if ok else ("CRASH" if ok is False else "SKIP")
        marker = "✓" if ok else ("✗" if ok is False else "?")
        print(f"  {marker} {fname:30s} {status}")

    # Diagnosis
    print(f"\n{'='*60}")
    print("DIAGNOSIS")
    print(f"{'='*60}")
    rmap = {fname: ok for fname, ok in results}

    if rmap.get("s9_bare_skeleton.als") is False:
        print("  s9 CRASHES = XML structure/IDs broken in V12 pipeline")
        print("  Need to compare V12's ID allocation vs td's")
    elif rmap.get("s9_bare_skeleton.als") is True:
        print("  s9 LOADS = XML structure is fine")
        if rmap.get("s6_no_notes.als") is True:
            print("  s6 LOADS = Note data is the crash trigger")
            if rmap.get("s7_simple_notes.als") is True:
                print("  s7 LOADS = Simple notes work, V12's specific note values crash")
                print("  → Fix: sanitize note data in _inject_midi_clips()")
            elif rmap.get("s7_simple_notes.als") is False:
                print("  s7 CRASHES = Even simple notes crash with V12 structure")
                print("  → Possible: clip length or KeyTrack structure issue")
        elif rmap.get("s6_no_notes.als") is False:
            print("  s6 CRASHES = NOT the note data!")
            if rmap.get("s1_plain_names.als") is True:
                print("  s1 LOADS = Track names with brackets cause crash!")
                print("  → Fix: sanitize track names, remove brackets")
            elif rmap.get("s1_plain_names.als") is False:
                print("  s1 CRASHES = NOT the track names either")
                print("  → Need deeper investigation into automation or other data")


if __name__ == "__main__":
    main()
